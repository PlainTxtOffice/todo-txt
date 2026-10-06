"""Import legacy SQLite recurrence read-only without deleting its source."""

import sqlite3
from pathlib import Path

from src.adapters.recurring.codec import RecurrenceState, parse_state


def read_legacy_state(path: Path) -> RecurrenceState:
    """Read a consistent legacy snapshot, retaining every ID and completion.

    Opens the source in read-only mode and validates all records before JSON
    can be written. Invalid, unsupported, or inaccessible state raises an
    error; no empty replacement or partial import is returned.
    """
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=2,
        )
        connection.execute("BEGIN")
        if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            msg = "Legacy recurring SQLite state failed integrity checks."
            raise ValueError(
                msg,
            )
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(occurrence)")
        ]
        completion_columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(completion)")
        ]
        if set(columns) != {
            "identifier",
            "template_id",
            "title",
            "cadence",
            "period_start",
            "period_end",
            "suggested_day",
        } or set(completion_columns) != {"occurrence_id", "completed_on"}:
            msg_0 = "Unsupported legacy recurring SQLite schema."
            raise ValueError(msg_0)
        rows = connection.execute(
            "SELECT identifier, template_id, title, cadence, period_start, "
            "period_end, suggested_day FROM occurrence",
        ).fetchall()
        completions = connection.execute(
            "SELECT occurrence_id, completed_on FROM completion",
        ).fetchall()
        identifiers = [row[0] for row in rows]
        if any(type(key) is not int or key < 1 for key in identifiers):
            msg_1 = "Legacy occurrence IDs must be positive integers."
            raise ValueError(msg_1)
        if len(set(identifiers)) != len(rows) or len(
            {row[0] for row in completions},
        ) != len(completions):
            msg_2 = "Duplicate identifiers in legacy recurring SQLite state."
            raise ValueError(
                msg_2,
            )
        payload = {
            "schema_version": 1,
            "next_identifier": max(identifiers, default=0) + 1,
            "occurrences": {
                str(row[0]): dict(
                    zip(
                        (
                            "template_id",
                            "title",
                            "cadence",
                            "period_start",
                            "period_end",
                            "suggested_day",
                        ),
                        row[1:],
                        strict=True,
                    ),
                )
                for row in rows
            },
            "completions": {str(row[0]): row[1] for row in completions},
        }
        return parse_state(payload)
    except sqlite3.Error as exc:
        msg_3 = f"Could not read legacy recurring SQLite state: {exc}"
        raise ValueError(
            msg_3,
        ) from exc
    finally:
        if connection is not None:
            connection.close()
