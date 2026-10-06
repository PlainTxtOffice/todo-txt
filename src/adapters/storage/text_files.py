"""Read task text and line endings, and replace task text atomically."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def read_task_text(storage_path: Path) -> str:
    """Return a task file's exact text, or an empty string if it is absent.

    Line endings are kept as written so callers can detect and preserve
    the file's newline style.
    """
    if not storage_path.exists():
        return ""
    return storage_path.read_text(encoding="utf-8", newline="")


def detect_newline(contents: str, default: str) -> str:
    """Return the existing line ending style or the supplied default."""
    if "\r\n" in contents:
        return "\r\n"
    if "\n" in contents:
        return "\n"
    return default


def replace_text(storage_path: Path, contents: str) -> None:
    """Flush and atomically replace text, cleaning up failed writes."""
    file_descriptor, temp_name = tempfile.mkstemp(
        dir=storage_path.parent,
        prefix=f".{storage_path.name}.",
        suffix=".tmp",
        text=True,
    )
    temp_path = storage_path.with_name(Path(temp_name).name)
    try:
        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            file.write(contents)
            file.flush()
            os.fsync(file.fileno())
        Path(temp_path).replace(storage_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
