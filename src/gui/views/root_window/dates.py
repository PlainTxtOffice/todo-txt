"""Format dates for presentation in the root window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.config.settings import DateDisplayFormat

if TYPE_CHECKING:
    from datetime import date


def format_display_date(
    value: date,
    display_format: DateDisplayFormat,
) -> str:
    """Format a date using the selected presentation format."""
    if display_format is DateDisplayFormat.WEEKDAY_SHORT:
        return f"{value:%a, %b} {value.day}, {value:%Y}"
    return value.isoformat()


def qt_date_display_pattern(display_format: DateDisplayFormat) -> str:
    """Return the Qt date pattern for a presentation format."""
    if display_format is DateDisplayFormat.WEEKDAY_SHORT:
        return "ddd, MMM d, yyyy"
    return "yyyy-MM-dd"
