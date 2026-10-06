"""Append completed task lines to done.txt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.adapters.storage.text_files import (
    detect_newline,
    read_task_text,
    replace_text,
)

if TYPE_CHECKING:
    from pathlib import Path


class DoneTextStore:
    """Append archived todo.txt lines to a shared done.txt file."""

    def __init__(self, storage_path: Path) -> None:
        """Initialize the store with its done.txt storage path."""
        self._storage_path = storage_path

    @property
    def storage_path(self) -> Path:
        """Return the shared done.txt path."""
        return self._storage_path

    def append_lines(self, lines: list[str], default_newline: str) -> None:
        """Append lines without rewriting the existing archive."""
        if not lines:
            return
        existing = read_task_text(self._storage_path)
        newline = detect_newline(existing, default=default_newline)
        if existing and not existing.endswith(("\n", "\r")):
            existing += newline
        appended = "".join(f"{line}{newline}" for line in lines)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        replace_text(self._storage_path, existing + appended)
