"""Define one-time todo entities and workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from string import ascii_uppercase
from uuid import uuid4


@dataclass(slots=True)
class Todo:
    """Represent one task that can be completed once."""

    identifier: str
    title: str
    due_on: date | None = None
    # Notes live in program data, not todo.txt, so they are left out of
    # equality; the todo.txt store compares tasks to spot changed lines.
    notes: str = field(default="", compare=False)
    is_completed: bool = False
    completed_on: date | None = None
    created_on: date | None = None
    priority: str | None = None
    projects: tuple[str, ...] = ()
    contexts: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate user-controlled fields."""
        self.title = self.title.strip()
        self.notes = self.notes.strip()
        self.priority = _clean_priority(self.priority)
        self.projects = _clean_labels(self.projects)
        self.contexts = _clean_labels(self.contexts)
        self.metadata = _clean_metadata(self.metadata)
        if not self.title:
            msg = "title is required"
            raise ValueError(msg)

    def set_completed(
        self,
        *,
        is_completed: bool,
        completed_on: date | None = None,
    ) -> None:
        """Set completion state without changing the due date."""
        self.is_completed = is_completed
        self.completed_on = (
            completed_on or _local_today() if is_completed else None
        )


@dataclass(frozen=True, slots=True)
class TaskEdits:
    """Carry the user-editable fields of one task."""

    title: str
    due_on: date | None
    notes: str
    priority: str | None
    projects: tuple[str, ...]


@dataclass(slots=True)
class TaskBoard:
    """Hold todo state and domain-level task workflows."""

    todos: list[Todo] = field(default_factory=list)

    def list_todos(self) -> list[Todo]:
        """Return tasks sorted by completion, due date, and title."""
        return sorted(
            self.todos,
            key=lambda todo: (
                todo.is_completed,
                todo.due_on or date.max,
                todo.title.lower(),
            ),
        )

    def list_projects(self) -> list[str]:
        """Return each project used by any task once, A to Z."""
        projects = {project for todo in self.todos for project in todo.projects}
        return sorted(
            projects, key=lambda project: (project.casefold(), project)
        )

    def replace_todos(self, todos: list[Todo]) -> None:
        """Replace all task state with a freshly loaded revision."""
        self.todos = todos

    def create_todo(
        self,
        title: str,
        due_on: date | None,
        notes: str = "",
        *,
        priority: str | None = None,
        projects: tuple[str, ...] = (),
    ) -> Todo:
        """Create and retain a one-time todo."""
        todo = Todo(
            identifier=uuid4().hex,
            title=title,
            due_on=due_on,
            notes=notes,
            created_on=_local_today(),
            priority=priority,
            projects=projects,
        )
        self.todos.append(todo)
        return todo

    def update_todo(self, identifier: str, edits: TaskEdits) -> Todo:
        """Update editable fields for a todo."""
        todo = self._look_todo(identifier)
        clean_title = edits.title.strip()
        if not clean_title:
            msg = "title is required"
            raise ValueError(msg)
        todo.title = clean_title
        todo.due_on = edits.due_on
        todo.notes = edits.notes.strip()
        todo.priority = _clean_priority(edits.priority)
        todo.projects = _clean_labels(edits.projects)
        return todo

    def delete_todo(self, identifier: str) -> None:
        """Delete one todo by identifier."""
        self.todos.remove(self._look_todo(identifier))

    def set_todo_completed(
        self,
        identifier: str,
        *,
        is_completed: bool,
        completed_on: date | None = None,
    ) -> Todo:
        """Set a todo's completion state."""
        todo = self._look_todo(identifier)
        todo.set_completed(
            is_completed=is_completed,
            completed_on=completed_on,
        )
        return todo

    def _look_todo(self, identifier: str) -> Todo:
        for todo in self.todos:
            if todo.identifier == identifier:
                return todo
        msg = f"todo not found: {identifier}"
        raise ValueError(msg)


def _local_today() -> date:
    """Return today's date in the computer's time zone.

    Creation and completion dates follow the user's calendar, so a
    task added in the evening is not stamped with tomorrow's UTC date.
    """
    return datetime.now().astimezone().date()


def is_priority_letter(value: str) -> bool:
    """Report whether value is one todo.txt priority letter, A to Z."""
    return len(value) == 1 and value in ascii_uppercase


def _clean_priority(priority: str | None) -> str | None:
    if priority is None:
        return None
    clean_priority = priority.strip()
    if not is_priority_letter(clean_priority):
        msg = "priority must be A-Z"
        raise ValueError(msg)
    return clean_priority


def _clean_labels(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value.strip() for value in values if value.strip())


def _clean_metadata(values: dict[str, str]) -> dict[str, str]:
    return {
        str(key).strip(): str(value).strip()
        for key, value in values.items()
        if str(key).strip() and str(value).strip()
    }
