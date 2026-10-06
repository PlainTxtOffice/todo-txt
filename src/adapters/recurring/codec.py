"""Validate and serialize versioned occurrence and completion JSON state."""

import json
from dataclasses import dataclass, field
from datetime import date
from typing import cast

from src.domains.recurring.models import Cadence, Occurrence, Period
from src.domains.recurring.periods import calc_period

_DAYS = {
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}
_FIELDS = {
    "template_id",
    "title",
    "cadence",
    "period_start",
    "period_end",
    "suggested_day",
}


@dataclass
class RecurrenceState:
    """Hold validated snapshots and separate completions for one atomic save."""

    next_identifier: int = 1
    occurrences: dict[int, Occurrence] = field(default_factory=dict)
    completions: dict[int, date] = field(default_factory=dict)


def _mapping(value: object) -> dict[str, object]:
    """Reject non-object state instead of coercing user records."""
    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        msg = "Recurring state must contain JSON objects."
        raise ValueError(msg)
    return cast("dict[str, object]", value)


def _text(value: object) -> str:
    """Require a non-empty string for a stored title or template identity."""
    if not isinstance(value, str) or not value.strip():
        msg = "Recurring state text must be a non-empty string."
        raise ValueError(msg)
    return value


def _identifier(value: str) -> int:
    """Require canonical positive integer keys, retaining legacy numeric IDs."""
    if (
        not value.isascii()
        or not value.isdecimal()
        or str(int(value)) != value
        or int(value) < 1
    ):
        msg = "Recurring state identifier must be a positive integer key."
        raise ValueError(
            msg,
        )
    return int(value)


def _date(value: object) -> date:
    """Require canonical ISO calendar dates."""
    text = _text(value)
    parsed = date.fromisoformat(text)
    if parsed.isoformat() != text:
        msg = "Recurring state dates must use YYYY-MM-DD."
        raise ValueError(msg)
    return parsed


def _occurrence(identifier: int, value: object) -> Occurrence:
    """Validate each stored snapshot without discarding unknown fields."""
    record = _mapping(value)
    if record.keys() != _FIELDS:
        msg = "Recurring occurrence has missing or unknown fields."
        raise ValueError(msg)
    cadence = Cadence(_text(record["cadence"]))
    period = Period(_date(record["period_start"]), _date(record["period_end"]))
    if period != calc_period(cadence, period.start):
        msg_0 = "Recurring occurrence has invalid calendar boundaries."
        raise ValueError(
            msg_0,
        )
    day = record["suggested_day"]
    if day is not None and (
        not isinstance(day, str)
        or day not in _DAYS
        or cadence != Cadence.WEEKLY
    ):
        msg_1 = "Recurring occurrence has invalid weekday guidance."
        raise ValueError(msg_1)
    return Occurrence(
        identifier,
        _text(record["template_id"]),
        _text(record["title"]),
        cadence,
        period,
        cast("str | None", day),
    )


def parse_state(payload: object) -> RecurrenceState:
    """Reject malformed schemas, duplicate periods, and orphaned completion."""
    root = _mapping(payload)
    if root.keys() != {
        "schema_version",
        "next_identifier",
        "occurrences",
        "completions",
    }:
        msg = "Recurring state has missing or unknown fields."
        raise ValueError(msg)
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        msg_0 = "Unsupported recurring state schema_version."
        raise ValueError(msg_0)
    counter = root["next_identifier"]
    if type(counter) is not int or counter < 1:
        msg_1 = "Recurring state next_identifier must be a positive integer."
        raise ValueError(
            msg_1,
        )
    state = RecurrenceState(next_identifier=counter)
    periods = set()
    for key, value in _mapping(root["occurrences"]).items():
        row = _occurrence(_identifier(key), value)
        natural_key = (row.template_id, row.period.start)
        if natural_key in periods:
            msg = "Duplicate recurring template period in state."
            raise ValueError(msg)
        periods.add(natural_key)
        state.occurrences[row.identifier] = row
    if counter <= max(state.occurrences, default=0):
        msg = "Recurring state next_identifier would reuse an existing ID."
        raise ValueError(
            msg,
        )
    for key, value in _mapping(root["completions"]).items():
        identifier = _identifier(key)
        completed_on = _date(value)
        completed_row = state.occurrences.get(identifier)
        if (
            completed_row is None
            or not completed_row.period.start
            <= completed_on
            < completed_row.period.end
        ):
            msg = "Recurring completion has no matching active period."
            raise ValueError(
                msg,
            )
        state.completions[identifier] = completed_on
    return state


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys instead of silently keeping the last one."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = f"Duplicate JSON key in recurring state: {key}"
            raise ValueError(msg)
        result[key] = value
    return result


def decode_state(contents: bytes) -> RecurrenceState:
    """Read UTF-8 JSON and validate the complete state before any mutation."""
    try:
        payload: object = json.loads(
            contents.decode("utf-8"),
            object_pairs_hook=_unique_pairs,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        msg = f"Could not read recurring JSON state: {exc}"
        raise ValueError(msg) from exc
    return parse_state(payload)


def format_state(state: RecurrenceState) -> str:
    """Serialize validated UTF-8 snapshots and separate completion records."""
    payload = {
        "schema_version": 1,
        "next_identifier": state.next_identifier,
        "occurrences": {
            str(key): {
                "template_id": row.template_id,
                "title": row.title,
                "cadence": row.cadence.value,
                "period_start": row.period.start.isoformat(),
                "period_end": row.period.end.isoformat(),
                "suggested_day": row.suggested_day,
            }
            for key, row in state.occurrences.items()
        },
        "completions": {
            str(key): day.isoformat() for key, day in state.completions.items()
        },
    }
    parse_state(payload)
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
