"""Coordinate optional recurrence behind a premium entitlement port."""

from datetime import date
from pathlib import Path

from src.domains.premium.access import RecurringEntitlement
from src.domains.recurring.models import Occurrence
from src.ports.recurring import OccurrenceStore, TemplateSource


class RecurringWorkflow:
    """Combine template input with occurrence persistence.

    Calendar and billing rules stay with their own domains.
    """

    def __init__(
        self,
        source: TemplateSource,
        store: OccurrenceStore,
        entitlement: RecurringEntitlement,
    ) -> None:
        """Bind replaceable template, state, and access adapters."""
        self.source = source
        self.store = store
        self.entitlement = entitlement

    def _require_access(self) -> None:
        """Recheck access on every generation and completion command."""
        if not self.entitlement.allows_recurring():
            raise PermissionError(self.entitlement.description)

    def refresh(self, folder: Path, today: date) -> list[Occurrence]:
        """Validate all templates, generate current work once, and read it."""
        self._require_access()
        templates = self.source.load(folder)
        self.store.generate(templates, today)
        return self.store.list_current(today)

    def list_current(self, today: date) -> list[Occurrence]:
        """Read retained state even when premium access or opt-in is off."""
        return self.store.list_current(today)

    def complete(
        self,
        identifier: int,
        today: date,
        *,
        completed: bool,
    ) -> None:
        """Check access, then save completion without touching templates."""
        self._require_access()
        self.store.complete(identifier, today, completed=completed)
