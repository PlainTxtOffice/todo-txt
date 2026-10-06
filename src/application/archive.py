"""Coordinate safe transfer of completed tasks into the archive."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domains.tasks.archive import partition_completed

if TYPE_CHECKING:
    from src.domains.tasks.models import Todo
    from src.ports.tasks import ArchiveStore, TaskStore


def archive_completed_todos(
    todos: list[Todo],
    store: TaskStore,
    done_store: ArchiveStore,
) -> list[Todo]:
    """Move completed todos into done.txt and return the remaining todos."""
    store.ensure_current()
    completed, remaining = partition_completed(todos)
    if not completed:
        return list(todos)

    # Append before removing so an interrupted archive duplicates rather
    # than loses tasks.
    done_store.append_lines(
        [store.render_line(todo) for todo in completed],
        default_newline=store.newline,
    )
    store.save_todos(remaining)
    return remaining
