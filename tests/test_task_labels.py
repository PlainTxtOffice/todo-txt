"""Test task-list label presentation."""

from datetime import date

from src.config.settings import DateDisplayFormat
from src.gui.views.root_window.task_labels import format_task_label


def test_task_label_renders_priority() -> None:
    """Prioritized tasks should show their todo.txt priority marker."""
    result = format_task_label(
        "Call Mom",
        date(2026, 1, 14),
        "A",
        DateDisplayFormat.WEEKDAY_SHORT,
    )

    assert result == "(A) Wed, Jan 14, 2026 - Call Mom"


def test_task_label_omits_missing_priority() -> None:
    """Unprioritized tasks should retain the existing label shape."""
    result = format_task_label(
        "Call Mom",
        None,
        None,
        DateDisplayFormat.ISO,
    )

    assert result == "No due date - Call Mom"