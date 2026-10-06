"""Sort and group todos for presentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.domains.tasks.models import Todo

_UPCOMING_DAYS = 7
_LAST_SORT_KEY = "￿"


class SortOrder(StrEnum):
    """Identify supported task list sort orders."""

    COMPLETION = "completion"
    DUE_DATE = "due_date"
    PRIORITY = "priority"
    CREATED = "created"
    ALPHABETICAL = "alphabetical"
    PROJECT = "project"
    CONTEXT = "context"


class GroupBy(StrEnum):
    """Identify supported task list groupings."""

    NONE = "none"
    COMPLETION = "completion"
    DUE_DATE = "due_date"
    PRIORITY = "priority"
    PROJECT = "project"
    CONTEXT = "context"


@dataclass(slots=True)
class TaskGroup:
    """Represent one labeled group of todos."""

    label: str
    todos: list[Todo] = field(default_factory=list)


def _calc_tiebreak(todo: Todo) -> tuple[bool, str, date, str]:
    return (
        todo.is_completed,
        todo.priority or _LAST_SORT_KEY,
        todo.due_on or date.max,
        todo.title.lower(),
    )


def _calc_label_key(labels: tuple[str, ...]) -> str:
    return labels[0].lower() if labels else _LAST_SORT_KEY


_SORT_KEYS: dict[SortOrder, Callable[[Todo], tuple[object, ...]]] = {
    SortOrder.COMPLETION: lambda todo: (
        todo.is_completed,
        todo.due_on or date.max,
        todo.title.lower(),
    ),
    SortOrder.DUE_DATE: lambda todo: (
        todo.due_on or date.max,
        *_calc_tiebreak(todo),
    ),
    SortOrder.PRIORITY: lambda todo: (
        todo.priority or _LAST_SORT_KEY,
        *_calc_tiebreak(todo),
    ),
    SortOrder.CREATED: lambda todo: (
        todo.created_on or date.max,
        *_calc_tiebreak(todo),
    ),
    SortOrder.ALPHABETICAL: lambda todo: (
        todo.title.lower(),
        todo.is_completed,
    ),
    SortOrder.PROJECT: lambda todo: (
        _calc_label_key(todo.projects),
        *_calc_tiebreak(todo),
    ),
    SortOrder.CONTEXT: lambda todo: (
        _calc_label_key(todo.contexts),
        *_calc_tiebreak(todo),
    ),
}


def sort_todos(todos: list[Todo], sort_order: SortOrder) -> list[Todo]:
    """Return todos ordered by the selected sort order.

    Tasks without the sorted field come last, and ties fall back to
    completion, priority, due date, and title.
    """
    return sorted(todos, key=_SORT_KEYS[sort_order])


def _calc_due_label(todo: Todo, today: date) -> str:
    if todo.due_on is None:
        return "No Due Date"
    if todo.due_on < today:
        return "Overdue"
    if todo.due_on == today:
        return "Today"
    if todo.due_on <= today + timedelta(days=_UPCOMING_DAYS):
        return "Next 7 Days"
    return "Later"


def _calc_group_labels(
    todo: Todo,
    group_by: GroupBy,
    today: date,
) -> tuple[str, ...]:
    if group_by is GroupBy.COMPLETION:
        return ("Completed" if todo.is_completed else "Active",)
    if group_by is GroupBy.DUE_DATE:
        return (_calc_due_label(todo, today),)
    if group_by is GroupBy.PRIORITY:
        return (
            f"Priority {todo.priority}" if todo.priority else "No Priority",
        )
    if group_by is GroupBy.PROJECT:
        return tuple(f"+{project}" for project in todo.projects) or (
            "No Project",
        )
    if group_by is GroupBy.CONTEXT:
        return tuple(f"@{context}" for context in todo.contexts) or (
            "No Context",
        )
    return ("All Tasks",)


_FIXED_GROUP_ORDER: dict[GroupBy, tuple[str, ...]] = {
    GroupBy.COMPLETION: ("Active", "Completed"),
    GroupBy.DUE_DATE: (
        "Overdue",
        "Today",
        "Next 7 Days",
        "Later",
        "No Due Date",
    ),
}

_FALLBACK_LABELS: dict[GroupBy, str] = {
    GroupBy.PRIORITY: "No Priority",
    GroupBy.PROJECT: "No Project",
    GroupBy.CONTEXT: "No Context",
}


def _calc_group_order(group_by: GroupBy, label: str) -> tuple[int, str]:
    fixed_order = _FIXED_GROUP_ORDER.get(group_by)
    if fixed_order is not None:
        return (fixed_order.index(label), label)
    is_fallback = label == _FALLBACK_LABELS.get(group_by)
    return (int(is_fallback), label.lower())


def group_todos(
    todos: list[Todo],
    group_by: GroupBy,
    today: date,
) -> list[TaskGroup]:
    """Split sorted todos into labeled groups.

    - Keeps each group's todos in the order they were passed in.
    - Lists a todo under every project or context it names.
    - Omits empty groups and places the catch-all group last.
    """
    groups: dict[str, TaskGroup] = {}
    for todo in todos:
        for label in _calc_group_labels(todo, group_by, today):
            groups.setdefault(label, TaskGroup(label)).todos.append(todo)
    return sorted(
        groups.values(),
        key=lambda group: _calc_group_order(group_by, group.label),
    )
