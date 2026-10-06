"""Represent recurring templates and immutable period occurrences."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Cadence(StrEnum):
    """Identify the supported calendar periods."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass(frozen=True)
class Template:
    """Describe work available throughout each calendar period.

    The identifier is stable across suggested-weekday changes. Weekdays are
    guidance only; imported checkbox state never represents completion.
    """

    identifier: str
    title: str
    cadence: Cadence
    suggested_day: str | None = None


@dataclass(frozen=True)
class Period:
    """Describe an inclusive start and exclusive end in local calendar dates."""

    start: date
    end: date


@dataclass(frozen=True)
class Occurrence:
    """Retain a template snapshot and its separate completion record."""

    identifier: int
    template_id: str
    title: str
    cadence: Cadence
    period: Period
    suggested_day: str | None
    completed_on: date | None = None
