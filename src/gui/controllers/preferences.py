"""Load and persist task-list preferences for the GUI."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from src.config.settings import (
    SETTINGS_PATH,
    AppSettings,
    load_settings,
    save_settings,
)

if TYPE_CHECKING:
    from pathlib import Path

    from src.domains.tasks.arrangement import GroupBy, SortOrder


class ViewPreferences:
    """Bind view preference operations to an application settings file."""

    def __init__(self, settings_path: Path = SETTINGS_PATH) -> None:
        """Select the settings file used by preference operations."""
        self._settings_path = settings_path

    def load(self) -> AppSettings:
        """Load current display and file settings."""
        return load_settings(self._settings_path)

    def save(
        self,
        sort_order: SortOrder,
        group_by: GroupBy,
        *,
        show_file_lines: bool,
    ) -> None:
        """Persist view choices while retaining other application settings."""
        save_settings(
            replace(
                self.load(),
                sort_order=sort_order,
                group_by=group_by,
                show_file_lines=show_file_lines,
            ),
            self._settings_path,
        )
