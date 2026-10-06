"""Read and write the legacy JSON task format."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING, cast

from src.domains.tasks.models import Todo

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION = 1


def _serialize_optional_date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_optional_date(value: object) -> date | None:
    if value in {None, ""}:
        return None
    return date.fromisoformat(str(value))


def _parse_optional_text(value: object) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)


def _parse_text_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(entry) for entry in value)


def _parse_metadata(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(entry) for key, entry in value.items()}


def _serialize_todo(todo: Todo) -> dict[str, object]:
    return {
        "identifier": todo.identifier,
        "title": todo.title,
        "due_on": _serialize_optional_date(todo.due_on),
        "notes": todo.notes,
        "is_completed": todo.is_completed,
        "completed_on": _serialize_optional_date(todo.completed_on),
        "created_on": _serialize_optional_date(todo.created_on),
        "priority": todo.priority,
        "projects": list(todo.projects),
        "contexts": list(todo.contexts),
        "metadata": todo.metadata,
    }


def _deserialize_todo(payload: dict[str, object]) -> Todo:
    return Todo(
        identifier=str(payload["identifier"]),
        title=str(payload["title"]),
        due_on=_parse_optional_date(payload.get("due_on")),
        notes=str(payload.get("notes", "")),
        is_completed=bool(payload.get("is_completed")),
        completed_on=_parse_optional_date(payload.get("completed_on")),
        created_on=_parse_optional_date(payload.get("created_on")),
        priority=_parse_optional_text(payload.get("priority")),
        projects=_parse_text_tuple(payload.get("projects")),
        contexts=_parse_text_tuple(payload.get("contexts")),
        metadata=_parse_metadata(payload.get("metadata")),
    )


class JsonTodoStore:
    """Persist one-time todos in JSON storage."""

    def __init__(self, storage_path: Path) -> None:
        """Initialize the store with its JSON storage path."""
        self._storage_path = storage_path

    def load_todos(self) -> list[Todo]:
        """Load all todos from JSON storage."""
        payload = self._read_payload()
        tasks = cast("list[dict[str, object]]", payload["tasks"])
        return [_deserialize_todo(task) for task in tasks]

    def save_todos(self, todos: list[Todo]) -> None:
        """Write all todos to JSON storage atomically."""
        payload = {
            "schema_version": SCHEMA_VERSION,
            "tasks": [_serialize_todo(todo) for todo in todos],
        }
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._storage_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temp_path.replace(self._storage_path)

    def _read_payload(self) -> dict[str, object]:
        if not self._storage_path.exists():
            return {"schema_version": SCHEMA_VERSION, "tasks": []}

        payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCHEMA_VERSION:
            msg = f"unsupported schema_version: {payload.get('schema_version')}"
            raise ValueError(msg)
        if not isinstance(payload.get("tasks"), list):
            msg = "tasks must be a list"
            raise TypeError(msg)
        return cast("dict[str, object]", payload)
