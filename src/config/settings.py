"""Load application settings from JSON."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

from src.config.path_handler import DATA_DIR, ROOT_DIR
from src.domains.tasks.arrangement import GroupBy, SortOrder
from src.domains.tasks.models import is_priority_letter

# Settings live in the base folder beside logs and data: beside the
# executable in a compiled build, whose onefile extraction directory is
# deleted on exit, and at the untracked repository root otherwise, so
# personal paths never enter version control.
SETTINGS_PATH = ROOT_DIR / "settings.json"
DEFAULT_SETTINGS_PATH = Path(__file__).with_name("settings.default.json")


@dataclass(frozen=True, slots=True)
class PrioritySettings:
    """Represent priority validation bounds."""

    minimum: str
    maximum: str

    def __post_init__(self) -> None:
        """Reject invalid letters and reversed priority bounds."""
        for name, value in (
            ("minimum", self.minimum),
            ("maximum", self.maximum),
        ):
            if not isinstance(value, str) or not is_priority_letter(value):
                msg = f"priority {name} must be A-Z"
                raise ValueError(msg)
        if self.minimum > self.maximum:
            msg = "Minimum priority must come before maximum priority."
            raise ValueError(msg)


class DateDisplayFormat(StrEnum):
    """Identify supported date presentation formats."""

    ISO = "iso"
    WEEKDAY_SHORT = "weekday_short"


BUILT_IN_SETTINGS: dict[str, object] = {
    "priority": {"minimum": "A", "maximum": "E"},
    "dateDisplayFormat": DateDisplayFormat.ISO.value,
}


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Represent application-level settings."""

    priority: PrioritySettings
    todo_file: Path = DATA_DIR / "todo.txt"
    done_file: Path = DATA_DIR / "done.txt"
    date_display_format: DateDisplayFormat = DateDisplayFormat.ISO
    done_file_explicit: bool = False
    sort_order: SortOrder = SortOrder.COMPLETION
    group_by: GroupBy = GroupBy.NONE
    show_file_lines: bool = True
    recurring_enabled: bool = False
    recurring_folder: Path | None = None


def load_settings(
    settings_path: Path = SETTINGS_PATH,
    default_settings_path: Path = DEFAULT_SETTINGS_PATH,
) -> AppSettings:
    """Load application settings from JSON.

    - Writes a settings file from the release defaults when none
      exists, so a portable build configures itself on first run.
    - Falls back to built-in defaults when no defaults file was
      bundled, which keeps development and tests working.
    """
    if not settings_path.exists():
        _write_default_settings(settings_path, default_settings_path)
    payload = _read_settings(settings_path)
    todo_file = _parse_todo_file(payload)
    return AppSettings(
        priority=_parse_priority(payload),
        todo_file=todo_file,
        done_file=_parse_done_file(payload, todo_file),
        date_display_format=_parse_date_display_format(payload),
        done_file_explicit=payload.get("doneFile") is not None,
        sort_order=_parse_sort_order(payload),
        group_by=_parse_group_by(payload),
        show_file_lines=_parse_show_file_lines(payload),
        recurring_enabled=_parse_recurring_enabled(payload),
        recurring_folder=_parse_recurring_folder(payload),
    )


def save_settings(
    settings: AppSettings,
    settings_path: Path = SETTINGS_PATH,
) -> None:
    """Save application settings while preserving unknown keys."""
    payload = _read_settings(settings_path)
    payload["priority"] = {
        "minimum": settings.priority.minimum,
        "maximum": settings.priority.maximum,
    }
    payload["todoFile"] = str(settings.todo_file)
    payload["dateDisplayFormat"] = settings.date_display_format.value
    payload["sortOrder"] = settings.sort_order.value
    payload["groupBy"] = settings.group_by.value
    payload["showFileLines"] = settings.show_file_lines
    payload["recurringEnabled"] = settings.recurring_enabled
    payload["recurringFolder"] = (
        str(settings.recurring_folder) if settings.recurring_folder else None
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=settings_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(json.dumps(payload, indent=2) + "\n")
        temporary_path.replace(settings_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _read_settings(settings_path: Path) -> dict[str, object]:
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "settings payload must be an object"
        raise TypeError(msg)
    return cast("dict[str, object]", payload)


def _write_default_settings(
    settings_path: Path,
    default_settings_path: Path,
) -> None:
    """Create a settings file from the release defaults.

    - Missing parent directories are created.
    - The bundled defaults file is copied verbatim when present so a
      build can ship its own release-safe values.
    - Built-in defaults are written when no defaults file exists.
    """
    if default_settings_path.is_file():
        payload = default_settings_path.read_text(encoding="utf-8")
    else:
        payload = json.dumps(BUILT_IN_SETTINGS, indent=2) + "\n"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(payload, encoding="utf-8")


def _parse_priority(payload: dict[str, object]) -> PrioritySettings:
    priority_payload = payload.get("priority")
    if not isinstance(priority_payload, dict):
        msg = "priority settings must be an object"
        raise TypeError(msg)
    priority = cast("dict[str, object]", priority_payload)
    return PrioritySettings(
        minimum=cast("str", priority.get("minimum")),
        maximum=cast("str", priority.get("maximum")),
    )


def _parse_todo_file(payload: dict[str, object]) -> Path:
    value = payload.get("todoFile")
    if value is None:
        return DATA_DIR / "todo.txt"
    if not isinstance(value, str) or not value.strip():
        msg = "todoFile must be a non-empty path"
        raise ValueError(msg)
    return Path(value).expanduser()


def _parse_done_file(payload: dict[str, object], todo_file: Path) -> Path:
    """Derive done.txt beside todo.txt unless a path is configured."""
    value = payload.get("doneFile")
    if value is None:
        return todo_file.parent / "done.txt"
    if not isinstance(value, str) or not value.strip():
        msg = "doneFile must be a non-empty path"
        raise ValueError(msg)
    return Path(value).expanduser()


def _parse_date_display_format(
    payload: dict[str, object],
) -> DateDisplayFormat:
    value = payload.get("dateDisplayFormat", DateDisplayFormat.ISO.value)
    if not isinstance(value, str):
        msg = "dateDisplayFormat must be a supported format"
        raise TypeError(msg)
    try:
        return DateDisplayFormat(value)
    except ValueError as exc:
        msg = "dateDisplayFormat must be a supported format"
        raise ValueError(msg) from exc


def _parse_sort_order(payload: dict[str, object]) -> SortOrder:
    value = payload.get("sortOrder", SortOrder.COMPLETION.value)
    if not isinstance(value, str):
        msg = "sortOrder must be a supported sort order"
        raise TypeError(msg)
    try:
        return SortOrder(value)
    except ValueError as exc:
        msg = "sortOrder must be a supported sort order"
        raise ValueError(msg) from exc


def _parse_group_by(payload: dict[str, object]) -> GroupBy:
    value = payload.get("groupBy", GroupBy.NONE.value)
    if not isinstance(value, str):
        msg = "groupBy must be a supported grouping"
        raise TypeError(msg)
    try:
        return GroupBy(value)
    except ValueError as exc:
        msg = "groupBy must be a supported grouping"
        raise ValueError(msg) from exc


def _parse_show_file_lines(payload: dict[str, object]) -> bool:
    value = payload.get("showFileLines", True)
    if not isinstance(value, bool):
        msg = "showFileLines must be true or false"
        raise TypeError(msg)
    return value


def _parse_recurring_enabled(payload: dict[str, object]) -> bool:
    """Require an explicit boolean opt-in; installs default to disabled."""
    value = payload.get("recurringEnabled", False)
    if not isinstance(value, bool):
        msg = "recurringEnabled must be true or false"
        raise TypeError(msg)
    return value


def _parse_recurring_folder(payload: dict[str, object]) -> Path | None:
    """Read an optional template location without accessing the folder."""
    value = payload.get("recurringFolder")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        msg = "recurringFolder must be a non-empty path"
        raise ValueError(msg)
    return Path(value).expanduser()
