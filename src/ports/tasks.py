"""Define task persistence and archive contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from src.domains.tasks.models import Todo


class TodoFileChangedError(RuntimeError):
    """Report that todo.txt changed after it was loaded."""


class TaskStore(Protocol):
    """Describe revision-aware task storage needed by workflows."""

    @property
    def storage_path(self) -> Path:
        """Return the task file path."""
        ...

    @property
    def newline(self) -> str:
        """Return the loaded line ending style."""
        ...

    def load_todos(self) -> list[Todo]:
        """Load tasks and retain their storage revision."""
        ...

    def save_todos(self, todos: list[Todo]) -> None:
        """Save tasks, rejecting a stale revision."""
        ...

    def ensure_current(self) -> None:
        """Raise TodoFileChangedError for a stale revision."""
        ...

    def render_line(self, todo: Todo) -> str:
        """Return the original line when its task is unchanged."""
        ...


class ArchiveStore(Protocol):
    """Describe storage that appends completed task lines."""

    @property
    def storage_path(self) -> Path:
        """Return the archive file path."""
        ...

    def append_lines(self, lines: list[str], default_newline: str) -> None:
        """Append lines using the archive's existing line endings."""
        ...
