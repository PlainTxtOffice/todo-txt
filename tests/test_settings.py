"""Test application settings persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.path_handler import DATA_DIR
from src.config.settings import (
    AppSettings,
    DateDisplayFormat,
    PrioritySettings,
    load_settings,
    save_settings,
)
from src.domains.tasks.arrangement import GroupBy, SortOrder


def test_save_settings_preserves_unknown_keys(tmp_path: Path) -> None:
    """Saving settings should not discard unrelated JSON values."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"theme": "dark", "priority": {"minimum": "A", "maximum": "Z"}}',
        encoding="utf-8",
    )

    save_settings(
        AppSettings(priority=PrioritySettings(minimum="B", maximum="D")),
        settings_path,
    )

    loaded = load_settings(settings_path)
    assert loaded.priority == PrioritySettings(minimum="B", maximum="D")
    assert '"theme": "dark"' in settings_path.read_text(encoding="utf-8")


def test_load_settings_rejects_invalid_priority(tmp_path: Path) -> None:
    """Priority bounds should stay within todo.txt A-Z values."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "a", "maximum": "Z"}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="priority minimum must be A-Z"):
        load_settings(settings_path)


def test_settings_round_trip_todo_file(tmp_path: Path) -> None:
    """Settings should retain the configured shared todo.txt path."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "Z"}}',
        encoding="utf-8",
    )
    todo_file = tmp_path / "shared" / "todo.txt"

    save_settings(
        AppSettings(
            priority=PrioritySettings(minimum="A", maximum="Z"),
            todo_file=todo_file,
        ),
        settings_path,
    )

    assert load_settings(settings_path).todo_file == todo_file


def test_settings_round_trip_date_display_format(tmp_path: Path) -> None:
    """Settings should retain the selected date presentation format."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "Z"}}',
        encoding="utf-8",
    )

    save_settings(
        AppSettings(
            priority=PrioritySettings(minimum="A", maximum="Z"),
            date_display_format=DateDisplayFormat.WEEKDAY_SHORT,
        ),
        settings_path,
    )

    assert (
        load_settings(settings_path).date_display_format
        is DateDisplayFormat.WEEKDAY_SHORT
    )


def test_settings_round_trip_view_choices(tmp_path: Path) -> None:
    """Settings should retain the selected sort order and grouping."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "Z"}}',
        encoding="utf-8",
    )
    assert load_settings(settings_path).sort_order is SortOrder.COMPLETION
    assert load_settings(settings_path).group_by is GroupBy.NONE

    save_settings(
        AppSettings(
            priority=PrioritySettings(minimum="A", maximum="Z"),
            sort_order=SortOrder.PRIORITY,
            group_by=GroupBy.PROJECT,
        ),
        settings_path,
    )

    loaded = load_settings(settings_path)
    assert loaded.sort_order is SortOrder.PRIORITY
    assert loaded.group_by is GroupBy.PROJECT


def test_settings_round_trip_show_file_lines(tmp_path: Path) -> None:
    """Settings should show todo.txt lines unless turned off."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "Z"}}',
        encoding="utf-8",
    )
    assert load_settings(settings_path).show_file_lines is True

    save_settings(
        AppSettings(
            priority=PrioritySettings(minimum="A", maximum="Z"),
            show_file_lines=False,
        ),
        settings_path,
    )

    assert load_settings(settings_path).show_file_lines is False


def test_load_settings_rejects_non_boolean_show_file_lines(
    tmp_path: Path,
) -> None:
    """A quoted boolean should fail rather than read as true."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "Z"}, '
        '"showFileLines": "false"}',
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="showFileLines must be"):
        load_settings(settings_path)


def test_load_settings_rejects_unknown_sort_order(tmp_path: Path) -> None:
    """An unsupported sort order should fail with a clear message."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "Z"}, "sortOrder": "size"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="sortOrder must be"):
        load_settings(settings_path)


def test_done_file_defaults_beside_the_todo_file(tmp_path: Path) -> None:
    """An unset doneFile should resolve to done.txt beside todo.txt."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "E"}, '
        '"todoFile": "/shared/todo/todo.txt"}',
        encoding="utf-8",
    )

    loaded = load_settings(settings_path)

    assert loaded.done_file == Path("/shared/todo/done.txt")


def test_done_file_honors_an_explicit_path(tmp_path: Path) -> None:
    """A configured doneFile should override the derived default."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "E"}, '
        '"todoFile": "/shared/todo/todo.txt", '
        '"doneFile": "/archive/finished.txt"}',
        encoding="utf-8",
    )

    loaded = load_settings(settings_path)

    assert loaded.done_file == Path("/archive/finished.txt")


def test_missing_settings_file_is_created_from_bundled_defaults(
    tmp_path: Path,
) -> None:
    """A first run should write a settings file from the bundled defaults."""
    settings_path = tmp_path / "settings.json"
    default_path = tmp_path / "settings.default.json"
    default_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "E"}}',
        encoding="utf-8",
    )

    loaded = load_settings(settings_path, default_path)

    assert settings_path.exists()
    assert loaded.priority == PrioritySettings(minimum="A", maximum="E")


def test_existing_settings_file_is_not_overwritten_by_defaults(
    tmp_path: Path,
) -> None:
    """Seeding must never discard settings the user already saved."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "B", "maximum": "D"}}',
        encoding="utf-8",
    )
    default_path = tmp_path / "settings.default.json"
    default_path.write_text(
        '{"priority": {"minimum": "A", "maximum": "E"}}',
        encoding="utf-8",
    )

    loaded = load_settings(settings_path, default_path)

    assert loaded.priority == PrioritySettings(minimum="B", maximum="D")


def test_missing_defaults_file_falls_back_to_built_in_settings(
    tmp_path: Path,
) -> None:
    """The app must still start when no defaults file was bundled."""
    settings_path = tmp_path / "settings.json"

    loaded = load_settings(settings_path, tmp_path / "absent.json")

    assert settings_path.exists()
    assert loaded.priority == PrioritySettings(minimum="A", maximum="E")


def test_seeded_settings_keep_task_files_under_the_base_root(
    tmp_path: Path,
) -> None:
    """Defaults must not carry a developer path into a portable build."""
    settings_path = tmp_path / "settings.json"

    loaded = load_settings(settings_path, tmp_path / "absent.json")

    assert loaded.todo_file == DATA_DIR / "todo.txt"
    assert loaded.done_file == DATA_DIR / "done.txt"


@pytest.mark.parametrize(
    "minimum,maximum",
    [("Z", "A"), ("", "Z"), ("AB", "Z"), ("A", "z"), (None, "Z")],
)
def test_priority_model_rejects_invalid_bounds(minimum, maximum):
    """All callers must receive validation, not just the settings dialog."""
    with pytest.raises(ValueError):
        PrioritySettings(minimum=minimum, maximum=maximum)


def test_settings_reject_reversed_priority_bounds(tmp_path):
    """Hand-edited settings must not create an empty priority selector."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"priority": {"minimum": "Z", "maximum": "A"}}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Minimum priority"):
        load_settings(settings_path)


def test_single_priority_range_is_valid():
    """A range may intentionally contain exactly one priority."""
    assert PrioritySettings(minimum="C", maximum="C").maximum == "C"
