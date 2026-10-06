"""Test date presentation formats."""

from datetime import date

from src.config.settings import DateDisplayFormat
from src.gui.views.root_window.dates import (
    format_display_date,
    qt_date_display_pattern,
)


def test_format_display_date_as_iso() -> None:
    """ISO presentation should preserve the existing display."""
    result = format_display_date(
        date(2026, 1, 14),
        DateDisplayFormat.ISO,
    )

    assert result == "2026-01-14"


def test_format_display_date_with_abbreviated_weekday() -> None:
    """Weekday presentation should include a correct compact weekday."""
    result = format_display_date(
        date(2026, 1, 14),
        DateDisplayFormat.WEEKDAY_SHORT,
    )

    assert result == "Wed, Jan 14, 2026"


def test_qt_pattern_matches_weekday_presentation() -> None:
    """Qt controls should use the equivalent weekday date pattern."""
    assert (
        qt_date_display_pattern(DateDisplayFormat.WEEKDAY_SHORT)
        == "ddd, MMM d, yyyy"
    )