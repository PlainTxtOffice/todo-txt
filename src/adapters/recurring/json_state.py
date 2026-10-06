"""Persist recurrence in locked, atomically replaced JSON sidecar state."""

from dataclasses import replace
from datetime import date
from pathlib import Path

from src.adapters.recurring.codec import (
    RecurrenceState,
    decode_state,
    format_state,
)
from src.adapters.recurring.locking import lock_state
from src.adapters.recurring.sqlite import read_legacy_state
from src.adapters.storage.text_files import replace_text
from src.domains.recurring.models import Occurrence, Template
from src.domains.recurring.periods import calc_period


class JsonOccurrences:
    """Retain period snapshots and completion without modifying ordinary tasks.

    Every operation reloads under a local OS lock. JSON takes precedence over
    legacy SQLite; if JSON is absent, a validated legacy snapshot is imported
    atomically once. The original database is never written or removed.
    """

    def __init__(self, path: Path, legacy_path: Path | None = None) -> None:
        """Select current and optional legacy state without writing files."""
        self.path = path.expanduser().resolve()
        self.legacy_path = (
            legacy_path.expanduser().resolve() if legacy_path else None
        )
        self.lock_path = self.path.with_name(self.path.name + ".lock")

    def _read_bytes(self) -> bytes | None:
        """Read a snapshot, returning None only when the file is missing."""
        try:
            return self.path.read_bytes()
        except FileNotFoundError:
            return None

    def _load(self) -> tuple[RecurrenceState, bytes | None, bool]:
        """Read JSON or import a complete legacy snapshot under the lock."""
        before = self._read_bytes()
        if before is not None:
            return decode_state(before), before, False
        if self.legacy_path is not None and self.legacy_path.exists():
            return read_legacy_state(self.legacy_path), None, True
        return RecurrenceState(), None, False

    def _write(self, state: RecurrenceState, before: bytes | None) -> None:
        """Validate and atomically save, rejecting observed outside edits."""
        contents = format_state(state)
        if self._read_bytes() != before:
            msg = "Recurring JSON changed outside the app. Reload and retry."
            raise ValueError(msg)
        replace_text(self.path, contents)

    def generate(self, templates: list[Template], today: date) -> None:
        """Add current-period work once, keeping every existing snapshot."""
        with lock_state(self.lock_path):
            state, before, imported = self._load()
            keys = {
                (row.template_id, row.period.start)
                for row in state.occurrences.values()
            }
            changed = imported
            for template in templates:
                period = calc_period(template.cadence, today)
                key = (template.identifier, period.start)
                if key in keys:
                    continue
                identifier = state.next_identifier
                state.occurrences[identifier] = Occurrence(
                    identifier,
                    template.identifier,
                    template.title,
                    template.cadence,
                    period,
                    template.suggested_day,
                )
                state.next_identifier += 1
                keys.add(key)
                changed = True
            if changed:
                self._write(state, before)

    def list_current(self, today: date) -> list[Occurrence]:
        """Read current work and completions, importing legacy history once."""
        if not self.path.exists() and not (
            self.legacy_path and self.legacy_path.exists()
        ):
            return []
        with lock_state(self.lock_path):
            state, before, imported = self._load()
            if imported:
                self._write(state, before)
            rows = [
                replace(row, completed_on=state.completions.get(row.identifier))
                for row in state.occurrences.values()
                if row.period.start <= today < row.period.end
            ]
        return sorted(rows, key=lambda row: (row.cadence.value, row.identifier))

    def complete(
        self, identifier: int, today: date, *, completed: bool
    ) -> None:
        """Complete or explicitly reopen current work under the state lock."""
        with lock_state(self.lock_path):
            state, before, imported = self._load()
            row = state.occurrences.get(identifier)
            if (
                type(identifier) is not int
                or row is None
                or not row.period.start <= today < row.period.end
            ):
                msg = "Occurrence is no longer in the current period."
                raise ValueError(msg)
            changed = imported
            if completed and identifier not in state.completions:
                state.completions[identifier] = today
                changed = True
            elif not completed and identifier in state.completions:
                del state.completions[identifier]
                changed = True
            if changed:
                self._write(state, before)
