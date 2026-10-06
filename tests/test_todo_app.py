"""Test application-level todo workflows."""

from __future__ import annotations

from datetime import date

import pytest

from src.domains.tasks.models import TaskBoard, TaskEdits, Todo


def test_create_complete_and_delete_todo() -> None:
    """The board should retain a completed task without rolling it forward."""
    board = TaskBoard()
    todo = board.create_todo("Submit report", date(2026, 7, 20))

    completed = board.set_todo_completed(
        todo.identifier,
        is_completed=True,
        completed_on=date(2026, 7, 19),
    )

    assert completed.is_completed is True
    assert completed.completed_on == date(2026, 7, 19)
    assert completed.due_on == date(2026, 7, 20)
    board.delete_todo(todo.identifier)
    assert board.list_todos() == []


def test_update_todo_changes_editable_fields() -> None:
    """Update should replace title, due date, notes, and projects."""
    board = TaskBoard()
    todo = board.create_todo("Draft", date(2026, 7, 20))

    updated = board.update_todo(
        todo.identifier,
        TaskEdits(
            "Final draft",
            date(2026, 7, 21),
            "Send to Alex",
            priority=None,
            projects=(" Work ", ""),
        ),
    )

    assert updated.title == "Final draft"
    assert updated.due_on == date(2026, 7, 21)
    assert updated.notes == "Send to Alex"
    assert updated.projects == ("Work",)


def test_create_and_update_todo_priority() -> None:
    """Create and update should retain editor-selected priorities."""
    board = TaskBoard()
    todo = board.create_todo(
        "Draft",
        date(2026, 7, 20),
        priority="B",
    )

    updated = board.update_todo(
        todo.identifier,
        TaskEdits("Draft", date(2026, 7, 20), "", priority="D", projects=()),
    )

    assert updated.priority == "D"


def test_replace_todos_uses_reloaded_state() -> None:
    """Reloading should replace stale board contents."""
    board = TaskBoard()
    board.create_todo("Local", date(2026, 7, 20))

    board.replace_todos([])

    assert board.list_todos() == []


def test_todo_accepts_full_spec_priority_range() -> None:
    """Domain tasks should accept every todo.txt priority."""
    assert Todo("task", "Later", priority="Z").priority == "Z"


def test_todo_rejects_invalid_priority() -> None:
    """Domain tasks should reject priorities outside todo.txt A-Z."""
    with pytest.raises(ValueError, match="priority must be A-Z"):
        Todo("task", "Invalid", priority="AA")
