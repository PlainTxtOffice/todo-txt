"""Test todo.txt parsing and export behavior."""

from __future__ import annotations

from datetime import date

import pytest

from src.adapters.export import export_todo_text, parse_todo_text
from src.domains.tasks.models import Todo


def test_export_formats_open_todo_metadata() -> None:
    """Export should place todo.txt metadata according to the spec."""
    open_todo = Todo(
        "open",
        "Call Mom",
        date(2026, 7, 20),
        created_on=date(2026, 7, 18),
        priority="A",
        projects=("Family",),
        contexts=("phone",),
        metadata={"rec": "weekly"},
    )

    result = export_todo_text([open_todo])

    assert result == (
        "(A) 2026-07-18 Call Mom +Family @phone "
        "due:2026-07-20 rec:weekly\n"
    )


def test_export_formats_completed_todo_metadata() -> None:
    """Export should preserve completed dates and priority metadata."""
    done_todo = Todo(
        "done",
        "Pay invoice",
        date(2026, 7, 19),
        is_completed=True,
        completed_on=date(2026, 7, 18),
        created_on=date(2026, 7, 1),
        priority="B",
    )

    result = export_todo_text([done_todo])

    assert result == (
        "x 2026-07-18 2026-07-01 Pay invoice "
        "due:2026-07-19 pri:B\n"
    )


def test_parse_reads_spec_fields() -> None:
    """Parse should extract the structured fields from todo.txt lines."""
    todos = parse_todo_text(
        "(A) 2011-03-02 Call Mom +Family @phone "
        "due:2011-03-05 rec:weekly\n"
        "x 2011-03-03 2011-03-02 Review pull request "
        "+TodoTxtTouch @github pri:B\n",
    )

    assert len(todos) == 2
    assert todos[0].title == "Call Mom"
    assert todos[0].identifier != ""
    assert todos[0].priority == "A"
    assert todos[0].created_on == date(2011, 3, 2)
    assert todos[0].due_on == date(2011, 3, 5)
    assert todos[0].projects == ("Family",)
    assert todos[0].contexts == ("phone",)
    assert todos[0].metadata == {"rec": "weekly"}
    assert todos[1].is_completed is True
    assert todos[1].completed_on == date(2011, 3, 3)
    assert todos[1].priority == "B"
    assert todos[1].due_on is None


def test_parse_keeps_id_as_metadata() -> None:
    """External id tags must not control internal task identity."""
    todos = parse_todo_text("Call Mom id:task-123\nCall Mom id:task-123\n")

    assert todos[0].identifier != "task-123"
    assert todos[0].identifier != todos[1].identifier
    assert todos[0].metadata == {"id": "task-123"}
    todos[0].title = "Call Dad"
    assert export_todo_text(todos) == (
        "Call Dad id:task-123\nCall Mom id:task-123\n"
    )


def test_export_omits_identifier_metadata() -> None:
    """Export should keep in-memory identifiers out of the shared file."""
    todo = Todo("in-memory-id", "Call Mom", created_on=date(2026, 7, 18))

    result = export_todo_text([todo])

    assert result == "2026-07-18 Call Mom\n"


def test_parse_keeps_invalid_due_date_in_title() -> None:
    """A malformed due date should stay visible instead of failing."""
    todo = parse_todo_text("Pay rent due:2026-13-45\n")[0]

    assert todo.due_on is None
    assert todo.title == "Pay rent due:2026-13-45"


def test_parse_keeps_invalid_priorities_in_title() -> None:
    """Lowercase or multi-letter priorities should not fail parsing."""
    todos = parse_todo_text("(a) Call Mom\nx Pay rent pri:ab\n")

    assert todos[0].priority is None
    assert todos[0].title == "(a) Call Mom"
    assert todos[1].priority is None
    assert todos[1].title == "Pay rent pri:ab"


@pytest.mark.parametrize("letter", ["A", "M", "Z", "a", "AB", "1", "É"])
def test_parse_reads_exactly_the_priorities_a_todo_accepts(
    letter: str,
) -> None:
    """A priority the model accepts must load back from todo.txt."""
    try:
        Todo("check", "Call Mom", priority=letter)
    except ValueError:
        is_accepted = False
    else:
        is_accepted = True

    open_todo, completed_todo = parse_todo_text(
        f"({letter}) Call Mom\nx Pay rent pri:{letter}\n"
    )

    assert (open_todo.priority == letter) is is_accepted
    assert (completed_todo.priority == letter) is is_accepted


def test_parse_ignores_non_standard_date_forms() -> None:
    """Only YYYY-MM-DD should count as a creation date."""
    todo = parse_todo_text("20260101 Call Mom\n")[0]

    assert todo.created_on is None
    assert todo.title == "20260101 Call Mom"


def test_parse_uses_whole_line_when_title_is_empty() -> None:
    """A line with no title words should load as its raw text."""
    todos = parse_todo_text("x 2026-01-01\n+Home @phone\n")

    assert [todo.title for todo in todos] == ["x 2026-01-01", "+Home @phone"]
    assert todos[0].is_completed is False
    assert todos[1].projects == ()


def test_export_leaves_notes_out_of_todo_text() -> None:
    """Notes belong to program data, not the shared todo.txt line."""
    todo = Todo("n", "Call Mom", notes="Ask about Sunday")

    assert export_todo_text([todo]) == "Call Mom\n"
