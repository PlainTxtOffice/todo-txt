"""Test task list sorting and grouping."""

from __future__ import annotations

from datetime import date

from src.domains.tasks.arrangement import (
    GroupBy,
    SortOrder,
    group_todos,
    sort_todos,
)
from src.domains.tasks.models import Todo

TODAY = date(2026, 9, 27)


def _todo(title: str, **fields: object) -> Todo:
    return Todo(identifier=title, title=title, **fields)  # type: ignore[arg-type]


def _titles(todos: list[Todo]) -> list[str]:
    return [todo.title for todo in todos]


def test_completion_sort_matches_board_default() -> None:
    """Completion sort should keep open tasks first, then due date."""
    todos = [
        _todo("done", is_completed=True, due_on=date(2026, 1, 1)),
        _todo("later", due_on=date(2026, 12, 1)),
        _todo("undated"),
        _todo("soon", due_on=date(2026, 10, 1)),
    ]

    sorted_todos = sort_todos(todos, SortOrder.COMPLETION)

    assert _titles(sorted_todos) == ["soon", "later", "undated", "done"]


def test_priority_sort_places_unprioritized_last() -> None:
    """Priority sort should order A-Z and put missing priorities last."""
    todos = [
        _todo("none"),
        _todo("b", priority="B"),
        _todo("a done", priority="A", is_completed=True),
        _todo("a", priority="A"),
    ]

    sorted_todos = sort_todos(todos, SortOrder.PRIORITY)

    assert _titles(sorted_todos) == ["a", "a done", "b", "none"]


def test_project_sort_uses_first_project() -> None:
    """Project sort should order by first project, unassigned last."""
    todos = [
        _todo("loose"),
        _todo("work", projects=("Work",)),
        _todo("home", projects=("home", "Work")),
    ]

    sorted_todos = sort_todos(todos, SortOrder.PROJECT)

    assert _titles(sorted_todos) == ["home", "work", "loose"]


def test_alphabetical_sort_ignores_case() -> None:
    """Alphabetical sort should compare titles without case."""
    todos = [_todo("banana"), _todo("Apple"), _todo("cherry")]

    sorted_todos = sort_todos(todos, SortOrder.ALPHABETICAL)

    assert _titles(sorted_todos) == ["Apple", "banana", "cherry"]


def test_group_by_due_date_uses_fixed_bucket_order() -> None:
    """Due date groups should run from overdue to undated."""
    todos = [
        _todo("undated"),
        _todo("later", due_on=date(2026, 12, 1)),
        _todo("week", due_on=date(2026, 10, 2)),
        _todo("today", due_on=TODAY),
        _todo("late", due_on=date(2026, 9, 1)),
    ]

    groups = group_todos(todos, GroupBy.DUE_DATE, TODAY)

    assert [group.label for group in groups] == [
        "Overdue",
        "Today",
        "Next 7 Days",
        "Later",
        "No Due Date",
    ]


def test_group_by_project_lists_shared_tasks_in_each_group() -> None:
    """A task with two projects should appear under both projects."""
    todos = [
        _todo("both", projects=("Work", "home")),
        _todo("loose"),
        _todo("work", projects=("Work",)),
    ]

    groups = group_todos(todos, GroupBy.PROJECT, TODAY)

    assert [(group.label, _titles(group.todos)) for group in groups] == [
        ("+home", ["both"]),
        ("+Work", ["both", "work"]),
        ("No Project", ["loose"]),
    ]


def test_group_by_priority_places_unprioritized_last() -> None:
    """Priority groups should run A-Z with the catch-all group last."""
    todos = [_todo("none"), _todo("c", priority="C"), _todo("a", priority="A")]

    groups = group_todos(todos, GroupBy.PRIORITY, TODAY)

    assert [group.label for group in groups] == [
        "Priority A",
        "Priority C",
        "No Priority",
    ]


def test_group_by_completion_omits_empty_groups() -> None:
    """Completion grouping should skip a group that has no tasks."""
    groups = group_todos([_todo("open")], GroupBy.COMPLETION, TODAY)

    assert [group.label for group in groups] == ["Active"]
