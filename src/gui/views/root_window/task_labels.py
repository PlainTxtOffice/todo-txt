"""Format task labels for presentation in the root window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.gui.views.root_window.dates import format_display_date

if TYPE_CHECKING:
    from datetime import date

    from src.config.settings import DateDisplayFormat


def format_task_label(
    title: str,
    due_on: date | None,
    priority: str | None,
    date_display_format: DateDisplayFormat,
) -> str:
    """Format a task list label with optional priority and due date."""
    priority_label = f"({priority}) " if priority is not None else ""
    due_label = (
        format_display_date(due_on, date_display_format)
        if due_on is not None
        else "No due date"
    )
    return f"{priority_label}{due_label} - {title}"
