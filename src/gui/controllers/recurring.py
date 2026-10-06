"""Coordinate recurring preferences and commands without depending on Qt."""

from collections.abc import Callable
from dataclasses import replace
from datetime import date
from pathlib import Path

from src.application.recurring import RecurringWorkflow
from src.config.settings import (
    SETTINGS_PATH,
    AppSettings,
    load_settings,
    save_settings,
)
from src.domains.recurring.models import Occurrence


class RecurringController:
    """Enforce opt-in and delegate recurring persistence to the application."""

    def __init__(
        self,
        workflow: RecurringWorkflow,
        settings_path: Path = SETTINGS_PATH,
        clock: Callable[[], date] = date.today,
    ) -> None:
        """Bind application settings and a local-date clock."""
        self.workflow = workflow
        self.settings_path = settings_path
        self.clock = clock

    def load_preferences(self) -> AppSettings:
        """Read current settings rather than retaining a stale snapshot."""
        return load_settings(self.settings_path)

    def save_preferences(self, folder: str, *, enabled: bool) -> None:
        """Validate opt-in before saving it; never generate work during save."""
        path = Path(folder).expanduser().resolve() if folder.strip() else None
        if enabled:
            if not self.workflow.entitlement.allows_recurring():
                raise PermissionError(self.workflow.entitlement.description)
            if path is None:
                msg = "Select a recurring template folder."
                raise ValueError(msg)
            self.workflow.source.load(path)
        save_settings(
            replace(
                self.load_preferences(),
                recurring_enabled=enabled,
                recurring_folder=path,
            ),
            self.settings_path,
        )

    def can_edit(self) -> bool:
        """Return whether opt-in and premium access both allow edits now."""
        return (
            self.load_preferences().recurring_enabled
            and self.workflow.entitlement.allows_recurring()
        )

    def refresh(self) -> list[Occurrence]:
        """Generate only if opted in and entitled; else read retained work."""
        settings = self.load_preferences()
        today = self.clock()
        if (
            settings.recurring_enabled
            and self.workflow.entitlement.allows_recurring()
        ):
            if settings.recurring_folder is None:
                msg = "Select a recurring template folder."
                raise ValueError(msg)
            return self.workflow.refresh(settings.recurring_folder, today)
        return self.workflow.list_current(today)

    def complete(self, identifier: int, *, completed: bool) -> None:
        """Require current opt-in before delegating a completion command."""
        if not self.load_preferences().recurring_enabled:
            msg = "Recurring tasks are disabled."
            raise PermissionError(msg)
        self.workflow.complete(identifier, self.clock(), completed=completed)
