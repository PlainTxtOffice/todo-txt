"""Persist task notes separately from shared task files."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from src.adapters.export import format_todo_line, parse_todo_text
from src.adapters.storage.text_files import replace_text

if TYPE_CHECKING:
    from pathlib import Path

    from src.domains.tasks.models import Todo

NOTES_SCHEMA_VERSION = 1
logger = logging.getLogger(__name__)
_NoteKey = tuple[str, str]


def _calc_note_key(todo: Todo) -> _NoteKey:
    """Key a note by the creation date and title todo.txt will reload.

    Formatting and reparsing the task makes a title typed with +project
    or @context words match the shorter title read back from the file.
    """
    reloaded = parse_todo_text(format_todo_line(todo))[0]
    created_on = reloaded.created_on.isoformat() if reloaded.created_on else ""
    return (created_on, reloaded.title)


def _parse_note_entries(payload: object) -> dict[_NoteKey, str]:
    if not isinstance(payload, dict):
        msg = "notes payload must be an object"
        raise TypeError(msg)
    if payload.get("schema_version") != NOTES_SCHEMA_VERSION:
        msg = f"unsupported schema_version: {payload.get('schema_version')}"
        raise ValueError(msg)
    entries = payload["notes"]
    if not isinstance(entries, list):
        msg = "notes must be a list"
        raise TypeError(msg)
    return {
        (str(entry["created"]), str(entry["title"])): str(entry["notes"])
        for entry in entries
    }


class NotesStore:
    """Keep task notes in program data, outside the shared todo.txt.

    - Matches notes to tasks by creation date and title, so a note stays
      attached when another app completes the task or changes its
      priority, due date, projects, or contexts.
    - Moves a note when the program renames its task and drops it when
      the program deletes or archives the task.
    - Keeps notes whose task is not in the current list, such as one
      renamed in another app.
    """

    def __init__(self, storage_path: Path) -> None:
        """Initialize the store with its notes file path."""
        self._storage_path = storage_path
        self._loaded_keys: dict[str, _NoteKey] = {}

    @property
    def storage_path(self) -> Path:
        """Return the notes file path."""
        return self._storage_path

    def apply_notes(self, todos: list[Todo]) -> None:
        """Set each task's notes from the notes file."""
        entries = self._read_entries()
        self._loaded_keys = {}
        for todo in todos:
            key = _calc_note_key(todo)
            todo.notes = entries.get(key, "")
            self._loaded_keys[todo.identifier] = key

    def save_notes(self, todos: list[Todo]) -> None:
        """Write the notes for the given tasks to the notes file."""
        entries = self._read_entries()
        for key in self._loaded_keys.values():
            entries.pop(key, None)
        self._loaded_keys = {}
        for todo in todos:
            key = _calc_note_key(todo)
            self._loaded_keys[todo.identifier] = key
            if todo.notes:
                entries[key] = todo.notes
        payload = {
            "schema_version": NOTES_SCHEMA_VERSION,
            "notes": [
                {"created": created, "title": title, "notes": notes}
                for (created, title), notes in entries.items()
            ],
        }
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        replace_text(
            self._storage_path,
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        )

    def _read_entries(self) -> dict[_NoteKey, str]:
        if not self._storage_path.exists():
            return {}
        try:
            return _parse_note_entries(
                json.loads(self._storage_path.read_text(encoding="utf-8")),
            )
        except (ValueError, TypeError, KeyError):
            invalid_path = self._storage_path.with_name(
                f"{self._storage_path.name}.invalid",
            )
            logger.warning(
                "Could not read %s; moved it to %s",
                self._storage_path,
                invalid_path,
                exc_info=True,
            )
            self._storage_path.replace(invalid_path)
            return {}
