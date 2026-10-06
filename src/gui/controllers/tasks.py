"""Coordinate task commands without depending on Qt widgets."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from src.adapters.export import write_todo_text
from src.application.archive import archive_completed_todos
from src.domains.tasks.archive import partition_completed

if TYPE_CHECKING:
    from pathlib import Path

    from src.domains.tasks.models import TaskBoard, TaskEdits, Todo
    from src.ports.tasks import ArchiveStore, TaskStore


class TaskController:
    """Apply task commands and adopt state only after successful saves."""

    def __init__(
        self,
        board: TaskBoard,
        store: TaskStore,
        archive: ArchiveStore,
    ) -> None:
        """Bind task state to its persistence ports."""
        self._board = board
        self._store = store
        self._archive = archive

    @property
    def storage_path(self) -> Path:
        """Return the active task file path for presentation."""
        return self._store.storage_path

    @property
    def archive_path(self) -> Path:
        """Return the archive path for confirmation messages."""
        return self._archive.storage_path

    def list_todos(self) -> list[Todo]:
        """Return the current tasks in their default display order."""
        return self._board.list_todos()

    def list_projects(self) -> list[str]:
        """Return the projects used by current tasks, A to Z."""
        return self._board.list_projects()

    def look_todo(self, identifier: str) -> Todo | None:
        """Return a task by identifier, or None when it is absent."""
        return next(
            (
                todo
                for todo in self._board.todos
                if todo.identifier == identifier
            ),
            None,
        )

    def _prepare_edit(
        self,
        identifier: str | None,
        edits: TaskEdits,
    ) -> tuple[TaskBoard, Todo]:
        """Validate edits on a copy of the visible task board."""
        candidate = deepcopy(self._board)
        if identifier is None:
            todo = candidate.create_todo(
                edits.title,
                edits.due_on,
                edits.notes,
                priority=edits.priority,
                projects=edits.projects,
            )
        else:
            todo = candidate.update_todo(identifier, edits)
        return candidate, todo

    def _persist(self, candidate: TaskBoard) -> None:
        """Save candidate tasks before replacing the visible board."""
        self._store.save_todos(candidate.list_todos())
        self._board.replace_todos(candidate.todos)

    def save_task(self, identifier: str | None, edits: TaskEdits) -> str:
        """Create or update and persist a task, returning its identifier."""
        candidate, todo = self._prepare_edit(identifier, edits)
        self._persist(candidate)
        return todo.identifier

    def complete_task(self, identifier: str, edits: TaskEdits) -> str:
        """Save edits and toggle completion as a single task command."""
        candidate, todo = self._prepare_edit(identifier, edits)
        candidate.set_todo_completed(
            identifier,
            is_completed=not todo.is_completed,
        )
        self._persist(candidate)
        return identifier

    def delete_task(self, identifier: str) -> None:
        """Delete a task from persistence and then from visible state."""
        candidate = deepcopy(self._board)
        candidate.delete_todo(identifier)
        self._persist(candidate)

    def set_completed(self, identifier: str, *, is_completed: bool) -> None:
        """Persist an explicit completion state from the task list."""
        candidate = deepcopy(self._board)
        candidate.set_todo_completed(identifier, is_completed=is_completed)
        self._persist(candidate)

    def completed_count(self) -> int:
        """Return the number of tasks eligible for archiving."""
        completed, _ = partition_completed(self._board.todos)
        return len(completed)

    def archive_completed(self) -> None:
        """Archive completed tasks before updating the visible board."""
        remaining = archive_completed_todos(
            self._board.list_todos(),
            self._store,
            self._archive,
        )
        self._board.replace_todos(remaining)

    def reload_tasks(self) -> None:
        """Replace task state with the latest persisted revision."""
        self._board.replace_todos(self._store.load_todos())

    def export_tasks(self, destination: Path) -> None:
        """Write current tasks as todo.txt to the chosen destination."""
        write_todo_text(self._board.list_todos(), destination)
