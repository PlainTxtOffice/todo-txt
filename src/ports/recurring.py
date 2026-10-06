"""Define persistence and template-input boundaries for recurrence."""

from datetime import date
from pathlib import Path
from typing import Protocol

from src.domains.recurring.models import Occurrence, Template


class TemplateSource(Protocol):
    """Load templates without changing source files."""

    def load(self, folder: Path) -> list[Template]:
        """Read and validate all supported template files."""
        ...


class OccurrenceStore(Protocol):
    """Persist occurrences and completion separately from ordinary tasks."""

    def generate(self, templates: list[Template], today: date) -> None:
        """Create missing current-period snapshots idempotently."""
        ...

    def list_current(self, today: date) -> list[Occurrence]:
        """Read generated occurrences whose period contains today."""
        ...

    def complete(
        self,
        identifier: int,
        today: date,
        *,
        completed: bool,
    ) -> None:
        """Persist completion or reopening for a current-period occurrence."""
        ...
