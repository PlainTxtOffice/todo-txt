"""Persist todo.txt revisions and preserve unchanged lines."""

from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

from src.adapters.export import format_todo_line, parse_todo_text
from src.adapters.storage.text_files import (
    detect_newline,
    read_task_text,
    replace_text,
)
from src.ports.tasks import TodoFileChangedError

if TYPE_CHECKING:
    from pathlib import Path

    from src.adapters.storage.notes import NotesStore
    from src.domains.tasks.models import Todo


def _hash_text(contents: str) -> str:
    return sha256(contents.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class _BaselineLine:
    """Remember one line of todo.txt exactly as it was loaded."""

    order: int
    text: str
    todo: Todo


class TodoTextStore:
    """Persist todos in a shared todo.txt file with stale-write protection."""

    def __init__(
        self,
        storage_path: Path,
        notes_store: NotesStore | None = None,
    ) -> None:
        """Initialize the store with its todo.txt storage path.

        When a notes store is given, task notes are loaded from and
        saved to it alongside todo.txt, since notes never go in the
        shared file.
        """
        self._storage_path = storage_path
        self._notes_store = notes_store
        self._loaded_hash: str | None = None
        self._newline: str = os.linesep
        self._baseline: dict[str, _BaselineLine] = {}

    def load_todos(self) -> list[Todo]:
        """Load todos and remember the exact file revision."""
        contents = read_task_text(self._storage_path)
        todos = self._adopt_contents(contents)
        if self._notes_store is not None:
            self._notes_store.apply_notes(todos)
        return todos

    def ensure_current(self) -> None:
        """Raise unless todo.txt still matches the loaded revision."""
        if self._loaded_hash is None:
            msg = "todo.txt must be loaded before it can be saved"
            raise RuntimeError(msg)
        if self.has_external_changes():
            msg = "todo.txt changed outside this application"
            raise TodoFileChangedError(msg)

    def save_todos(self, todos: list[Todo]) -> None:
        """Atomically save todos unless the loaded file revision changed."""
        self.ensure_current()
        ordered = self._in_file_order(todos)
        lines = [self.render_line(todo) for todo in ordered]
        contents = "".join(f"{line}{self._newline}" for line in lines)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        replace_text(self._storage_path, contents)
        self._adopt_saved_lines(contents, lines, ordered)
        if self._notes_store is not None:
            self._notes_store.save_notes(todos)

    def _adopt_saved_lines(
        self,
        contents: str,
        lines: list[str],
        todos: list[Todo],
    ) -> None:
        """Rebuild the baseline from the saved tasks, keeping their ids.

        Reparsing the saved text would mint new identifiers, and the
        next save would then treat every caller task as new.
        """
        self._loaded_hash = _hash_text(contents)
        self._baseline = {
            todo.identifier: _BaselineLine(order, line, deepcopy(todo))
            for order, (line, todo) in enumerate(zip(lines, todos, strict=True))
        }

    def render_line(self, todo: Todo) -> str:
        """Return the todo's original line when its fields are unchanged."""
        baseline = self._baseline.get(todo.identifier)
        if baseline is not None and baseline.todo == todo:
            return baseline.text
        return format_todo_line(todo)

    def _in_file_order(self, todos: list[Todo]) -> list[Todo]:
        """Keep known tasks in their file position and append new ones."""

        def position(entry: tuple[int, Todo]) -> tuple[int, int]:
            index, todo = entry
            baseline = self._baseline.get(todo.identifier)
            if baseline is None:
                return (1, index)
            return (0, baseline.order)

        return [todo for _, todo in sorted(enumerate(todos), key=position)]

    def _adopt_contents(self, contents: str) -> list[Todo]:
        """Treat contents as the loaded revision and rebuild the baseline."""
        self._loaded_hash = _hash_text(contents)
        self._newline = detect_newline(contents, default=self._newline)
        todos = parse_todo_text(contents)
        texts = [line for line in contents.splitlines() if line.strip()]
        self._baseline = {
            todo.identifier: _BaselineLine(order, text, deepcopy(todo))
            for order, (text, todo) in enumerate(zip(texts, todos, strict=True))
        }
        return todos

    @property
    def storage_path(self) -> Path:
        """Return the shared todo.txt path."""
        return self._storage_path

    @property
    def newline(self) -> str:
        """Return the line ending style detected in todo.txt."""
        return self._newline

    def has_external_changes(self) -> bool:
        """Report whether todo.txt differs from the loaded revision."""
        if self._loaded_hash is None:
            return False
        contents = read_task_text(self._storage_path)
        return _hash_text(contents) != self._loaded_hash

    def find_conflicted_copies(self) -> list[Path]:
        """Return Dropbox conflicted copies beside the shared file."""
        if not self._storage_path.parent.exists():
            return []
        stem = self._storage_path.stem.casefold()
        suffix = self._storage_path.suffix.casefold()
        return sorted(
            path
            for path in self._storage_path.parent.iterdir()
            if path.is_file()
            and path.suffix.casefold() == suffix
            and path.stem.casefold().startswith(stem)
            and "conflicted copy" in path.stem.casefold()
        )
