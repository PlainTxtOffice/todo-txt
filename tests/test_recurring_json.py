"""Verify JSON durability, corruption safeguards, migration, and local locking."""

import json
import multiprocessing
import sqlite3
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import pytest

from src.adapters.recurring.json_state import JsonOccurrences
from src.adapters.recurring.locking import lock_state
from src.domains.recurring.models import Cadence, Template

TODAY = date(2026, 9, 28)
MEDIUM = Template("weekly:medium", "Medium", Cadence.WEEKLY, "Sunday")


def _legacy_file(path):
    """Create current and historical SQLite records only in a test folder."""
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE occurrence (
                identifier INTEGER PRIMARY KEY, template_id TEXT NOT NULL,
                title TEXT NOT NULL, cadence TEXT NOT NULL,
                period_start TEXT NOT NULL, period_end TEXT NOT NULL,
                suggested_day TEXT, UNIQUE(template_id, period_start)
            );
            CREATE TABLE completion (
                occurrence_id INTEGER PRIMARY KEY, completed_on TEXT NOT NULL
            );
            INSERT INTO occurrence VALUES
                (5, 'weekly:medium', 'Medium', 'weekly', '2026-01-05', '2026-01-12', 'Sunday'),
                (42, 'weekly:medium', 'Medium', 'weekly', '2026-09-28', '2026-10-05', 'Sunday');
            INSERT INTO completion VALUES (5, '2026-01-05'), (42, '2026-09-28');
        """)


def _process_complete(command):
    """Generate and complete distinct work from a separate spawned process."""
    path, selected = command
    store = JsonOccurrences(Path(path))
    templates = [
        Template(f"weekly:{i}", f"Task {i}", Cadence.WEEKLY) for i in range(8)
    ]
    store.generate(templates, TODAY)
    row = next(
        row
        for row in store.list_current(TODAY)
        if row.title == f"Task {selected}"
    )
    store.complete(row.identifier, TODAY, completed=True)


def _hold_lock(path, ready, release):
    """Hold a lock in a child process so the parent can test crash recovery."""
    with lock_state(Path(path)):
        ready.set()
        release.wait(30)


def test_json_format_and_noop_refresh(tmp_path, monkeypatch):
    """Preserve stable IDs, separate completion, UTF-8, and no-op file contents."""
    from src.adapters.recurring import json_state

    store = JsonOccurrences(tmp_path / "recurring.json")
    store.generate(
        [MEDIUM, Template("monthly:café", "Café", Cadence.MONTHLY)], TODAY
    )
    before = store.path.read_bytes()
    payload = json.loads(before)
    assert payload["schema_version"] == 1
    assert payload["next_identifier"] == 3
    assert len(payload["occurrences"]) == 2
    assert payload["completions"] == {}
    assert "Café" in before.decode("utf-8")
    monkeypatch.setattr(
        json_state,
        "replace_text",
        lambda *args: pytest.fail("No-op must not save"),
    )
    restarted = JsonOccurrences(store.path)
    restarted.generate([MEDIUM], TODAY)
    assert store.path.read_bytes() == before
    assert [row.identifier for row in restarted.list_current(TODAY)] == [2, 1]


def test_concurrent_processes_keep_all_completions(tmp_path):
    """Serialize whole transactions across app processes without lost updates."""
    path = tmp_path / "recurring.json"
    with ProcessPoolExecutor(
        max_workers=4, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        list(pool.map(_process_complete, [(str(path), i) for i in range(8)]))
    rows = JsonOccurrences(path).list_current(TODAY)
    assert len(rows) == 8
    assert {row.identifier for row in rows} == set(range(1, 9))
    assert all(row.completed_on == TODAY for row in rows)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["occurrences"]) == len(payload["completions"]) == 8


def test_lock_timeout_and_release(tmp_path):
    """A competing writer times out safely and can retry after release."""
    path = tmp_path / "recurring.json.lock"
    with (
        lock_state(path),
        pytest.raises(OSError, match="Another app instance"),
        lock_state(path, timeout=0.05),
    ):
        pytest.fail("Competing lock unexpectedly acquired")
    with lock_state(path, timeout=0.05):
        assert path.exists()


def test_process_exit_releases_lock(tmp_path):
    """An interrupted app leaves a harmless sidecar rather than a stale lock."""
    context = multiprocessing.get_context("spawn")
    path = tmp_path / "recurring.json.lock"
    ready, release = context.Event(), context.Event()
    process = context.Process(
        target=_hold_lock, args=(str(path), ready, release)
    )
    process.start()
    try:
        assert ready.wait(10)
        process.terminate()
        process.join(timeout=10)
        assert not process.is_alive()
        with lock_state(path, timeout=0.1):
            assert path.exists()
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)


def test_legacy_import_retains_ids_and_history(tmp_path):
    """Migrate all history once and leave the database byte-for-byte intact."""
    legacy = tmp_path / "recurring.sqlite3"
    _legacy_file(legacy)
    original = legacy.read_bytes()
    store = JsonOccurrences(tmp_path / "recurring.json", legacy)
    rows = store.list_current(TODAY)
    assert len(rows) == 1
    assert rows[0].identifier == 42 and rows[0].completed_on == TODAY
    payload = json.loads(store.path.read_text(encoding="utf-8"))
    assert set(payload["occurrences"]) == {"5", "42"}
    assert payload["completions"] == {"5": "2026-01-05", "42": "2026-09-28"}
    assert payload["next_identifier"] == 43
    store.generate([MEDIUM], TODAY)
    assert len(store.list_current(TODAY)) == 1
    store.complete(42, TODAY, completed=False)
    assert (
        JsonOccurrences(store.path, legacy).list_current(TODAY)[0].completed_on
        is None
    )
    store.generate([MEDIUM], date(2026, 10, 5))
    assert store.list_current(date(2026, 10, 5))[0].identifier == 43
    assert legacy.read_bytes() == original


@pytest.mark.parametrize("operation", ["generate", "list"])
def test_invalid_legacy_never_creates_json(tmp_path, operation):
    """A broken database never becomes an empty or partial replacement."""
    legacy = tmp_path / "recurring.sqlite3"
    legacy.write_bytes(b"corrupt SQLite")
    store = JsonOccurrences(tmp_path / "recurring.json", legacy)
    with pytest.raises(ValueError, match="legacy recurring SQLite"):
        if operation == "generate":
            store.generate([MEDIUM], TODAY)
        else:
            store.list_current(TODAY)
    assert not store.path.exists()
    assert legacy.read_bytes() == b"corrupt SQLite"


@pytest.mark.parametrize("mutation", ["schema", "orphan", "period"])
def test_invalid_legacy_records_are_not_imported(tmp_path, mutation):
    """Validate the complete legacy schema and records before writing JSON."""
    legacy = tmp_path / "recurring.sqlite3"
    _legacy_file(legacy)
    with sqlite3.connect(legacy) as connection:
        if mutation == "schema":
            connection.execute("ALTER TABLE occurrence ADD COLUMN unknown TEXT")
        elif mutation == "orphan":
            connection.execute(
                "INSERT INTO completion VALUES (99, '2026-09-28')"
            )
        else:
            connection.execute(
                "UPDATE occurrence SET period_end='2026-10-06' WHERE identifier=42"
            )
    original = legacy.read_bytes()
    store = JsonOccurrences(tmp_path / "recurring.json", legacy)
    with pytest.raises(ValueError):
        store.list_current(TODAY)
    assert not store.path.exists()
    assert legacy.read_bytes() == original


def test_existing_json_wins_and_corrupt_json_never_falls_back(tmp_path):
    """Do not merge stale SQLite or hide corruption by reverting to old state."""
    legacy = tmp_path / "recurring.sqlite3"
    _legacy_file(legacy)
    store = JsonOccurrences(tmp_path / "recurring.json")
    store.generate([MEDIUM], TODAY)
    imported = JsonOccurrences(store.path, legacy)
    assert imported.list_current(TODAY)[0].identifier == 1
    assert imported.list_current(TODAY)[0].completed_on is None
    store.path.write_bytes(b"broken JSON")
    with pytest.raises(ValueError):
        imported.generate([MEDIUM], TODAY)
    assert store.path.read_bytes() == b"broken JSON"


@pytest.mark.parametrize("failure", ["fsync", "replace"])
def test_failed_atomic_save_retains_existing_state(
    tmp_path, monkeypatch, failure
):
    """Failed flush or replacement preserves completion and cleans temp files."""
    from src.adapters.storage import text_files

    store = JsonOccurrences(tmp_path / "recurring.json")
    store.generate([MEDIUM], TODAY)
    original = store.path.read_bytes()

    def fail(*args):
        raise OSError("Simulated write failure")

    if failure == "fsync":
        monkeypatch.setattr(text_files.os, "fsync", fail)
    else:
        monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError, match="Simulated"):
        store.complete(1, TODAY, completed=True)
    assert store.path.read_bytes() == original
    assert not list(tmp_path.glob(".recurring.json.*.tmp"))


def test_failed_migration_save_can_retry(tmp_path, monkeypatch):
    """An interrupted JSON import leaves the source intact for a safe retry."""
    from src.adapters.recurring import json_state

    legacy = tmp_path / "recurring.sqlite3"
    _legacy_file(legacy)
    original = legacy.read_bytes()
    store = JsonOccurrences(tmp_path / "recurring.json", legacy)

    def fail(*args):
        raise OSError("Simulated import failure")

    with monkeypatch.context() as context:
        context.setattr(json_state, "replace_text", fail)
        with pytest.raises(OSError):
            store.list_current(TODAY)
    assert not store.path.exists()
    assert legacy.read_bytes() == original
    assert store.list_current(TODAY)[0].identifier == 42


def test_observed_external_edit_is_not_overwritten(tmp_path, monkeypatch):
    """Detect a non-cooperating editor changing JSON during a transaction."""
    from src.adapters.recurring import json_state

    store = JsonOccurrences(tmp_path / "recurring.json")
    store.generate([MEDIUM], TODAY)
    formatter = json_state.format_state
    payload = json.loads(store.path.read_text(encoding="utf-8"))
    payload["completions"]["1"] = "2026-09-28"
    external = json.dumps(payload).encode()

    def external_edit(state):
        store.path.write_bytes(external)
        return formatter(state)

    monkeypatch.setattr(json_state, "format_state", external_edit)
    with pytest.raises(ValueError, match="changed outside"):
        store.generate([MEDIUM], date(2026, 10, 5))
    assert store.path.read_bytes() == external


@pytest.mark.parametrize(
    "mutation",
    [
        "version",
        "counter",
        "boolean",
        "unknown",
        "orphan",
        "period",
        "duplicate",
        "day",
        "completion",
        "key",
    ],
)
def test_invalid_json_records_never_overwritten(tmp_path, mutation):
    """Reject malformed state rather than dropping fields or regenerating work."""
    store = JsonOccurrences(tmp_path / "recurring.json")
    store.generate([MEDIUM], TODAY)
    payload = json.loads(store.path.read_text(encoding="utf-8"))
    if mutation == "version":
        payload["schema_version"] = 2
    elif mutation == "counter":
        payload["next_identifier"] = 1
    elif mutation == "boolean":
        payload["schema_version"] = True
    elif mutation == "unknown":
        payload["unknown"] = "must not disappear"
    elif mutation == "orphan":
        payload["completions"]["99"] = "2026-09-28"
    elif mutation == "period":
        payload["occurrences"]["1"]["period_end"] = "2026-10-06"
    elif mutation == "duplicate":
        payload["occurrences"]["2"] = payload["occurrences"]["1"].copy()
        payload["next_identifier"] = 3
    elif mutation == "day":
        payload["occurrences"]["1"]["suggested_day"] = "Someday"
    elif mutation == "completion":
        payload["completions"]["1"] = "2026-10-05"
    else:
        payload["occurrences"]["01"] = payload["occurrences"].pop("1")
    original = json.dumps(payload).encode()
    store.path.write_bytes(original)
    with pytest.raises(ValueError):
        store.generate([MEDIUM], TODAY)
    assert store.path.read_bytes() == original


@pytest.mark.parametrize(
    "contents", [b"\xff", b'{"schema_version":1,"schema_version":2}', b"[]"]
)
def test_invalid_json_encoding_and_duplicate_keys(tmp_path, contents):
    """Reject invalid UTF-8 and duplicate keys before they can conceal records."""
    store = JsonOccurrences(tmp_path / "recurring.json")
    store.path.write_bytes(contents)
    with pytest.raises(ValueError):
        store.list_current(TODAY)
    assert store.path.read_bytes() == contents
