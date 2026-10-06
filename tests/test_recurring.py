"""Verify recurrence periods, input safety, idempotency, and completion."""

import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pytest

from src.adapters.recurring.json_state import JsonOccurrences
from src.adapters.recurring.markdown import MarkdownTemplates, parse_templates
from src.application.recurring import RecurringWorkflow
from src.config.settings import load_settings, save_settings
from src.domains.premium.access import (
    PreviewEntitlement,
    UnavailableEntitlement,
)
from src.domains.recurring.models import Cadence, Period
from src.domains.recurring.periods import calc_period
from src.gui.controllers.recurring import RecurringController

FIXTURES = Path(__file__).parent / "fixtures" / "recurring"


@pytest.fixture
def recurring_setup(tmp_path):
    """Copy example inputs and isolate every persistent file."""
    folder = tmp_path / "templates"
    shutil.copytree(FIXTURES, folder)
    store = JsonOccurrences(tmp_path / "state" / "recurring.json")
    workflow = RecurringWorkflow(
        MarkdownTemplates(), store, PreviewEntitlement()
    )
    return folder, store, workflow


@pytest.mark.parametrize(
    "cadence,today,start,end",
    [
        (
            Cadence.WEEKLY,
            date(2026, 9, 28),
            date(2026, 9, 28),
            date(2026, 10, 5),
        ),
        (
            Cadence.WEEKLY,
            date(2026, 10, 4),
            date(2026, 9, 28),
            date(2026, 10, 5),
        ),
        (
            Cadence.WEEKLY,
            date(2026, 10, 5),
            date(2026, 10, 5),
            date(2026, 10, 12),
        ),
        (
            Cadence.WEEKLY,
            date(2027, 1, 1),
            date(2026, 12, 28),
            date(2027, 1, 4),
        ),
        (
            Cadence.MONTHLY,
            date(2028, 2, 29),
            date(2028, 2, 1),
            date(2028, 3, 1),
        ),
        (
            Cadence.MONTHLY,
            date(2026, 12, 31),
            date(2026, 12, 1),
            date(2027, 1, 1),
        ),
        (
            Cadence.QUARTERLY,
            date(2026, 3, 31),
            date(2026, 1, 1),
            date(2026, 4, 1),
        ),
        (
            Cadence.QUARTERLY,
            date(2026, 4, 1),
            date(2026, 4, 1),
            date(2026, 7, 1),
        ),
        (
            Cadence.QUARTERLY,
            date(2026, 10, 1),
            date(2026, 10, 1),
            date(2027, 1, 1),
        ),
    ],
)
def test_calendar_boundaries(cadence, today, start, end):
    """Use inclusive local calendar starts and exclusive ends."""
    assert calc_period(cadence, today) == Period(start, end)


def test_examples_ignore_checks_and_old_metadata(recurring_setup):
    """Import eight templates without interpreting April, Q2, or old checks."""
    folder, _, workflow = recurring_setup
    before = {path.name: path.read_bytes() for path in folder.iterdir()}
    rows = workflow.refresh(folder, date(2026, 10, 1))
    assert len(rows) == 8
    assert all(row.completed_on is None for row in rows)
    weekly = {row.title: row for row in rows if row.cadence == Cadence.WEEKLY}
    assert weekly["Medium"].suggested_day == "Sunday"
    assert weekly["Substack"].suggested_day == "Monday"
    assert all(
        row.period.start == date(2026, 10, 1)
        for row in rows
        if row.cadence == Cadence.MONTHLY
    )
    assert before == {path.name: path.read_bytes() for path in folder.iterdir()}


def test_early_completion_survives_suggested_day_and_restart(recurring_setup):
    """Completing Sunday's work on Monday satisfies that entire week."""
    folder, store, workflow = recurring_setup
    monday = date(2026, 9, 28)
    rows = workflow.refresh(folder, monday)
    medium = next(row for row in rows if row.title == "Medium")
    workflow.complete(medium.identifier, monday, completed=True)
    restarted = RecurringWorkflow(
        MarkdownTemplates(), JsonOccurrences(store.path), PreviewEntitlement()
    )
    for today in (monday, date(2026, 10, 1), date(2026, 10, 4)):
        rows = restarted.refresh(folder, today)
        matches = [row for row in rows if row.title == "Medium"]
        assert len(matches) == 1
        assert matches[0].identifier == medium.identifier
        assert matches[0].completed_on == monday
    next_week = next(
        row
        for row in restarted.refresh(folder, date(2026, 10, 5))
        if row.title == "Medium"
    )
    assert next_week.identifier != medium.identifier
    assert next_week.completed_on is None


def test_suggested_day_edit_does_not_duplicate(recurring_setup):
    """Changing guidance preserves identity and the current snapshot."""
    folder, _, workflow = recurring_setup
    rows = workflow.refresh(folder, date(2026, 9, 28))
    medium = next(row for row in rows if row.title == "Medium")
    path = folder / "weekly.md"
    path.write_text(path.read_text().replace("## Sunday", "## Friday"))
    rows = workflow.refresh(folder, date(2026, 10, 2))
    assert [row.identifier for row in rows if row.title == "Medium"] == [
        medium.identifier
    ]


def test_missed_periods_not_backfilled(recurring_setup):
    """A long absence generates only current periods and retains past records."""
    folder, store, workflow = recurring_setup
    workflow.refresh(folder, date(2026, 1, 5))
    rows = workflow.refresh(folder, date(2026, 10, 1))
    assert len(rows) == 8
    payload = json.loads(store.path.read_text(encoding="utf-8"))
    assert len(payload["occurrences"]) == 16
    assert len(payload["completions"]) == 0


def test_quarterly_rollover_and_monthly_completion(recurring_setup):
    """A named quarterly template rolls once at the calendar boundary."""
    folder, _, workflow = recurring_setup
    (folder / "quarterly.md").write_text("- [ ] Review plans\n")
    rows = workflow.refresh(folder, date(2026, 9, 30))
    quarterly = next(row for row in rows if row.cadence == Cadence.QUARTERLY)
    monthly = next(row for row in rows if row.cadence == Cadence.MONTHLY)
    workflow.complete(monthly.identifier, date(2026, 9, 30), completed=True)
    assert next(
        row
        for row in workflow.refresh(folder, date(2026, 9, 30))
        if row.identifier == monthly.identifier
    ).completed_on
    next_rows = workflow.refresh(folder, date(2026, 10, 1))
    assert len(next_rows) == 9
    assert (
        next(
            row for row in next_rows if row.cadence == Cadence.QUARTERLY
        ).identifier
        != quarterly.identifier
    )
    assert all(row.completed_on is None for row in next_rows)


def test_concurrent_generation_once(recurring_setup):
    """Concurrent processes' independent connections share the unique key."""
    folder, store, workflow = recurring_setup
    templates = workflow.source.load(folder)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(
            pool.map(
                lambda _: JsonOccurrences(store.path).generate(
                    templates, date(2026, 10, 1)
                ),
                range(8),
            )
        )
    assert len(store.list_current(date(2026, 10, 1))) == 8


def test_completion_idempotent_and_reopen_explicit(recurring_setup):
    """Retries retain the first completion date; reopening is a separate action."""
    folder, store, workflow = recurring_setup
    row = workflow.refresh(folder, date(2026, 9, 28))[0]
    workflow.complete(row.identifier, date(2026, 9, 28), completed=True)
    workflow.complete(row.identifier, date(2026, 9, 29), completed=True)
    assert store.list_current(date(2026, 9, 29))[0].completed_on == date(
        2026, 9, 28
    )
    workflow.complete(row.identifier, date(2026, 9, 29), completed=False)
    assert store.list_current(date(2026, 9, 29))[0].completed_on is None
    with pytest.raises(ValueError, match="current period"):
        workflow.complete(row.identifier, date(2026, 10, 1), completed=True)


def test_parse_error_does_not_partly_generate(recurring_setup):
    """Validate all files before any occurrence write."""
    folder, store, workflow = recurring_setup
    (folder / "monthly.md").write_text("- [ ] Repeat\n- [x] repeat\n")
    with pytest.raises(ValueError, match="Duplicate"):
        workflow.refresh(folder, date(2026, 10, 1))
    assert not store.path.exists()


def test_explicit_identity_survives_rename():
    """An explicit ID protects identity through a template rename."""
    before = parse_templates(
        "- [ ] Old <!-- recurring-id: review -->", Cadence.WEEKLY
    )
    after = parse_templates(
        "- [x] New <!-- recurring-id: review -->", Cadence.WEEKLY
    )
    assert before[0].identifier == after[0].identifier
    assert after[0].title == "New"
    with pytest.raises(ValueError, match="Duplicate"):
        parse_templates(
            "- [ ] One <!-- recurring-id: same -->\n"
            "- [ ] Two <!-- recurring-id: same -->",
            Cadence.WEEKLY,
        )


def test_bad_input_and_corrupt_state(recurring_setup):
    """Show input/state errors instead of replacing broken files."""
    folder, store, workflow = recurring_setup
    with pytest.raises(ValueError, match="front matter"):
        parse_templates("---\nmonth: April\n", Cadence.MONTHLY)
    with pytest.raises(ValueError, match="existing"):
        workflow.refresh(folder / "missing", date(2026, 10, 1))
    store.path.parent.mkdir()
    store.path.write_bytes(b"broken JSON")
    with pytest.raises(ValueError):
        workflow.refresh(folder, date(2026, 10, 1))
    assert store.path.read_bytes() == b"broken JSON"


def test_default_denial_and_revocation(recurring_setup):
    """Access is checked on every mutation and cannot be saved as a preference."""
    folder, store, workflow = recurring_setup
    denied = RecurringWorkflow(workflow.source, store, UnavailableEntitlement())
    with pytest.raises(PermissionError):
        denied.refresh(folder, date(2026, 10, 1))
    assert not store.path.exists()
    row = workflow.refresh(folder, date(2026, 10, 1))[0]
    with pytest.raises(PermissionError):
        denied.complete(row.identifier, date(2026, 10, 1), completed=True)
    assert denied.list_current(date(2026, 10, 1))


def test_controller_opt_in_and_settings_preservation(recurring_setup, tmp_path):
    """Disabled recurrence has no state writes; preference saves retain other keys."""
    folder, store, workflow = recurring_setup
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "priority": {"minimum": "A", "maximum": "E"},
                "custom": 123,
                "todoFile": str(tmp_path / "todo.txt"),
            }
        )
    )
    (tmp_path / "todo.txt").write_bytes(
        b"Existing task\r\nx 2026-09-01 Done\r\n"
    )
    before = (tmp_path / "todo.txt").read_bytes()
    controller = RecurringController(
        workflow, settings_path, lambda: date(2026, 10, 1)
    )
    assert not load_settings(settings_path).recurring_enabled
    assert controller.refresh() == []
    assert not store.path.exists()
    controller.save_preferences(str(folder), enabled=True)
    row = controller.refresh()[0]
    controller.complete(row.identifier, completed=True)
    controller.save_preferences(str(folder), enabled=False)
    with pytest.raises(PermissionError, match="disabled"):
        controller.complete(row.identifier, completed=False)
    assert controller.refresh()[0].completed_on == date(2026, 10, 1)
    assert (tmp_path / "todo.txt").read_bytes() == before
    assert json.loads(settings_path.read_text())["custom"] == 123
    settings = load_settings(settings_path)
    save_settings(settings, settings_path)
    assert load_settings(settings_path).recurring_folder == folder


@pytest.mark.parametrize(
    "key,value",
    [
        ("recurringEnabled", "true"),
        ("recurringFolder", ""),
        ("recurringFolder", 42),
    ],
)
def test_invalid_recurring_settings(tmp_path, key, value):
    """Malformed persisted recurrence configuration fails explicitly."""
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"priority": {"minimum": "A", "maximum": "E"}, key: value})
    )
    with pytest.raises((TypeError, ValueError)):
        load_settings(path)


def test_preview_only_interpreted(monkeypatch):
    """A CLI preview switch never grants entitlement to a compiled release."""
    from src import bootstrap

    monkeypatch.setattr(bootstrap.sys, "argv", ["app", "--premium-preview"])
    monkeypatch.setattr(bootstrap, "IS_COMPILED", False)
    assert bootstrap.build_recurring_controller().workflow.entitlement.allows_recurring()
    monkeypatch.setattr(bootstrap, "IS_COMPILED", True)
    assert not bootstrap.build_recurring_controller().workflow.entitlement.allows_recurring()
    monkeypatch.setattr(bootstrap, "IS_COMPILED", False)
    monkeypatch.setattr(bootstrap.sys, "argv", ["app"])
    assert not bootstrap.build_recurring_controller().workflow.entitlement.allows_recurring()
