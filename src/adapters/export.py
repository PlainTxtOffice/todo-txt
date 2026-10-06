"""Parse and export todos using the todo.txt text format."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING
from uuid import uuid4

from src.domains.tasks.models import Todo, is_priority_letter

if TYPE_CHECKING:
    from pathlib import Path

_PRIORITY_TOKEN_LENGTH = 3
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def write_todo_text(todos: list[Todo], destination: Path) -> None:
    """Write a todo.txt export to the selected destination."""
    destination.write_text(export_todo_text(todos), encoding="utf-8")


def export_todo_text(todos: list[Todo]) -> str:
    """Format todos as todo.txt-compatible lines."""
    lines = [format_todo_line(todo) for todo in todos]
    return "\n".join(lines) + ("\n" if lines else "")


def parse_todo_text(contents: str) -> list[Todo]:
    """Parse todo.txt-compatible lines into todos."""
    return [
        _parse_todo_line(line) for line in contents.splitlines() if line.strip()
    ]


def format_todo_line(todo: Todo) -> str:
    """Format one todo as a todo.txt line."""
    parts: list[str] = []
    if todo.is_completed:
        parts.append("x")
        if todo.completed_on is not None:
            parts.append(todo.completed_on.isoformat())
    elif todo.priority is not None:
        parts.append(f"({todo.priority})")
    if todo.created_on is not None:
        parts.append(todo.created_on.isoformat())
    parts.append(todo.title)
    parts.extend(f"+{project}" for project in todo.projects)
    parts.extend(f"@{context}" for context in todo.contexts)
    if todo.due_on is not None:
        parts.append(f"due:{todo.due_on.isoformat()}")
    parts.extend(_format_metadata(todo))
    return " ".join(parts)


def _format_metadata(todo: Todo) -> list[str]:
    metadata = dict(todo.metadata)
    if todo.is_completed and todo.priority is not None:
        metadata.setdefault("pri", todo.priority)
    return [f"{key}:{value}" for key, value in metadata.items()]


def _parse_todo_fields(line: str) -> Todo:
    tokens = line.split()
    is_completed, completed_on, token_index = _parse_completion(tokens)
    priority, token_index = _parse_priority(tokens, token_index)
    created_on, token_index = _parse_created_on(tokens, token_index)
    parsed_tokens = _parse_body_tokens(tokens[token_index:])
    if not parsed_tokens.title_words:
        msg = "title is required"
        raise ValueError(msg)
    return Todo(
        identifier=uuid4().hex,
        title=" ".join(parsed_tokens.title_words),
        due_on=parsed_tokens.due_on,
        is_completed=is_completed,
        completed_on=completed_on,
        created_on=created_on,
        priority=parsed_tokens.priority or priority,
        projects=tuple(parsed_tokens.projects),
        contexts=tuple(parsed_tokens.contexts),
        metadata=parsed_tokens.metadata,
    )


def _parse_todo_line(line: str) -> Todo:
    """Parse one line, keeping an unparseable line as a plain title.

    A line with no title words, or one whose fields fail validation,
    loads with its whole text as the title, so a hand edit never
    blocks startup and the line is saved back unchanged.
    """
    try:
        return _parse_todo_fields(line)
    except ValueError:
        return Todo(identifier=uuid4().hex, title=line)


def _parse_completion(tokens: list[str]) -> tuple[bool, date | None, int]:
    if not tokens or tokens[0] != "x":
        return False, None, 0
    if len(tokens) > 1 and _is_date(tokens[1]):
        return True, date.fromisoformat(tokens[1]), 2
    return True, None, 1


def _parse_priority(
    tokens: list[str],
    token_index: int,
) -> tuple[str | None, int]:
    if token_index < len(tokens) and _is_priority(tokens[token_index]):
        return tokens[token_index][1], token_index + 1
    return None, token_index


def _parse_created_on(
    tokens: list[str],
    token_index: int,
) -> tuple[date | None, int]:
    if token_index < len(tokens) and _is_date(tokens[token_index]):
        return date.fromisoformat(tokens[token_index]), token_index + 1
    return None, token_index


@dataclass(slots=True)
class _ParsedTokens:
    """Collect structured fields parsed from a todo.txt body."""

    title_words: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    due_on: date | None = None
    priority: str | None = None


def _parse_body_tokens(tokens: list[str]) -> _ParsedTokens:
    parsed_tokens = _ParsedTokens()
    for token in tokens:
        if _is_project(token):
            parsed_tokens.projects.append(token[1:])
        elif _is_context(token):
            parsed_tokens.contexts.append(token[1:])
        elif _is_metadata(token):
            _parse_metadata_token(parsed_tokens, token)
        else:
            parsed_tokens.title_words.append(token)
    return parsed_tokens


def _parse_metadata_token(parsed_tokens: _ParsedTokens, token: str) -> None:
    """Store a key:value token, keeping a malformed due or pri visible."""
    key, value = token.split(":", maxsplit=1)
    if key == "due" and _is_date(value):
        parsed_tokens.due_on = date.fromisoformat(value)
    elif key == "pri" and is_priority_letter(value):
        parsed_tokens.priority = value
    elif key in {"due", "pri"}:
        parsed_tokens.title_words.append(token)
    else:
        parsed_tokens.metadata[key] = value


def _is_priority(token: str) -> bool:
    return (
        len(token) == _PRIORITY_TOKEN_LENGTH
        and token[0] == "("
        and token[-1] == ")"
        and is_priority_letter(token[1])
    )


def _is_date(token: str) -> bool:
    if _DATE_PATTERN.fullmatch(token) is None:
        return False
    try:
        date.fromisoformat(token)
    except ValueError:
        return False
    return True


def _is_project(token: str) -> bool:
    return token.startswith("+") and len(token) > 1


def _is_context(token: str) -> bool:
    return token.startswith("@") and len(token) > 1


def _is_metadata(token: str) -> bool:
    if token.count(":") != 1:
        return False
    key, value = token.split(":", maxsplit=1)
    return bool(key and value)
