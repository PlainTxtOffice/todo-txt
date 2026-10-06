"""Define completed-task selection and archive relocation choices."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domains.tasks.models import Todo


class ArchiveAction(StrEnum):
    """Identify the user's choice for the previous task archive."""

    KEEP = "keep"
    MOVE = "move"
    MERGE = "merge"
    OVERWRITE = "overwrite"


def partition_completed(todos: list[Todo]) -> tuple[list[Todo], list[Todo]]:
    """Return completed and remaining tasks without changing their order."""
    completed: list[Todo] = []
    remaining: list[Todo] = []
    for todo in todos:
        (completed if todo.is_completed else remaining).append(todo)
    return completed, remaining
