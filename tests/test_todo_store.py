"""Test JSON todo persistence."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.adapters.storage.done_text import DoneTextStore
from src.adapters.storage.json_tasks import JsonTodoStore
from src.adapters.storage.notes import NotesStore
from src.adapters.storage.todo_text import TodoTextStore
from src.application.archive import archive_completed_todos
from src.domains.tasks.models import Todo
from src.ports.tasks import TodoFileChangedError


def test_store_round_trip_preserves_todo_fields(tmp_path: Path) -> None:
    """Saving and loading should preserve one-time task state."""
    store = JsonTodoStore(tmp_path / "todos.json")
    todo = Todo(
        "t1",
        "Gym",
        date(2026, 7, 20),
        notes="Before work",
        is_completed=True,
        completed_on=date(2026, 7, 19),
        created_on=date(2026, 7, 18),
    )

    store.save_todos([todo])
    loaded = store.load_todos()

    assert loaded == [todo]


def test_missing_store_loads_as_empty(tmp_path: Path) -> None:
    """A missing store file should produce an empty task list."""
    store = JsonTodoStore(tmp_path / "missing.json")
    assert store.load_todos() == []


def test_store_ignores_old_recurrence_fields(tmp_path: Path) -> None:
    """Old recurrence metadata should not prevent loading a task."""
    storage_path = tmp_path / "todos.json"
    storage_path.write_text(
        '{"schema_version": 1, "tasks": [{"identifier": "old", '
        '"title": "Legacy task", "due_on": "2026-07-20", '
        '"recurrence": {"kind": "weekly"}}]}',
        encoding="utf-8",
    )

    loaded = JsonTodoStore(storage_path).load_todos()

    assert loaded[0].title == "Legacy task"
    assert loaded[0].is_completed is False


def test_text_store_rejects_write_after_external_change(tmp_path: Path) -> None:
    """Saving should preserve an externally modified todo.txt file."""
    storage_path = tmp_path / "todo.txt"
    storage_path.write_text("Original id:one\n", encoding="utf-8")
    store = TodoTextStore(storage_path)
    todos = store.load_todos()
    storage_path.write_text("External id:two\n", encoding="utf-8")

    with pytest.raises(TodoFileChangedError):
        store.save_todos(todos)

    assert storage_path.read_text(encoding="utf-8") == "External id:two\n"


def test_text_store_reports_external_change(tmp_path: Path) -> None:
    """Change detection should compare against the loaded revision."""
    storage_path = tmp_path / "todo.txt"
    storage_path.write_text("Original id:one\n", encoding="utf-8")
    store = TodoTextStore(storage_path)
    store.load_todos()
    assert store.has_external_changes() is False

    storage_path.write_text("External id:two\n", encoding="utf-8")

    assert store.has_external_changes() is True


def test_text_store_writes_new_tasks_atomically(tmp_path: Path) -> None:
    """Saving should replace todo.txt without leaving temporary files."""
    storage_path = tmp_path / "todo.txt"
    store = TodoTextStore(storage_path)
    assert store.load_todos() == []
    todo = Todo("in-memory-id", "Call Mom")

    store.save_todos([todo])

    assert storage_path.read_text(encoding="utf-8") == "Call Mom\n"
    assert list(tmp_path.glob("*.tmp")) == []


def test_text_store_finds_dropbox_conflicted_copies(tmp_path: Path) -> None:
    """Conflict discovery should only return related todo.txt copies."""
    storage_path = tmp_path / "todo.txt"
    conflicted_path = tmp_path / "todo (device's conflicted copy).txt"
    conflicted_path.touch()
    (tmp_path / "other (device's conflicted copy).txt").touch()
    store = TodoTextStore(storage_path)

    assert store.find_conflicted_copies() == [conflicted_path]


def test_text_store_preserves_crlf_line_endings(tmp_path: Path) -> None:
    """Saving should reuse the line ending style already in the file."""
    storage_path = tmp_path / "todo.txt"
    storage_path.write_bytes(b"Buy milk\r\nCall Mom\r\n")
    store = TodoTextStore(storage_path)
    todos = store.load_todos()
    todos[0].title = "Buy oat milk"

    store.save_todos(todos)

    assert storage_path.read_bytes() == b"Buy oat milk\r\nCall Mom\r\n"


def test_text_store_preserves_untouched_lines_verbatim(tmp_path: Path) -> None:
    """Editing one task should leave every other line byte-identical."""
    storage_path = tmp_path / "todo.txt"
    storage_path.write_text(
        "(B) 2026-07-06 read book due:2026-07-10  +personal\n"
        "2026-07-19 list xbox controllers\n",
        encoding="utf-8",
        newline="",
    )
    store = TodoTextStore(storage_path)
    todos = store.load_todos()
    todos[1].title = "list xbox controllers and games"

    store.save_todos(todos)

    assert storage_path.read_text(encoding="utf-8").splitlines() == [
        "(B) 2026-07-06 read book due:2026-07-10  +personal",
        "2026-07-19 list xbox controllers and games",
    ]


def test_text_store_keeps_file_order_and_appends_new_tasks(
    tmp_path: Path,
) -> None:
    """Saving should not reorder the file when the caller sorts tasks."""
    storage_path = tmp_path / "todo.txt"
    storage_path.write_text(
        "Buy milk\nCall Mom\n",
        encoding="utf-8",
        newline="",
    )
    store = TodoTextStore(storage_path)
    todos = store.load_todos()
    resorted = [todos[1], todos[0], Todo("new-id", "Water plants")]

    store.save_todos(resorted)

    assert storage_path.read_text(encoding="utf-8").splitlines() == [
        "Buy milk",
        "Call Mom",
        "Water plants",
    ]


def _completed_setup(tmp_path: Path) -> tuple[Path, Path]:
    """Create a todo.txt with one completed task and a done.txt."""
    todo_path = tmp_path / "todo.txt"
    todo_path.write_bytes(b"x 2026-09-01 Pay invoice  +bills\r\nCall Mom\r\n")
    done_path = tmp_path / "done.txt"
    done_path.write_bytes(b"x 2026-07-29 Older task\r\n")
    return todo_path, done_path


def test_archive_appends_completed_lines_verbatim(tmp_path: Path) -> None:
    """Archiving should move the completed line into done.txt unchanged."""
    todo_path, done_path = _completed_setup(tmp_path)
    store = TodoTextStore(todo_path)
    done_store = DoneTextStore(done_path)

    archive_completed_todos(store.load_todos(), store, done_store)

    assert done_path.read_bytes() == (
        b"x 2026-07-29 Older task\r\n"
        b"x 2026-09-01 Pay invoice  +bills\r\n"
    )


def test_archive_leaves_remaining_todo_lines_intact(tmp_path: Path) -> None:
    """Archiving should keep the open tasks byte-for-byte in todo.txt."""
    todo_path, done_path = _completed_setup(tmp_path)
    store = TodoTextStore(todo_path)

    remaining = archive_completed_todos(
        store.load_todos(),
        store,
        DoneTextStore(done_path),
    )

    assert todo_path.read_bytes() == b"Call Mom\r\n"
    assert [todo.title for todo in remaining] == ["Call Mom"]


def test_archive_aborts_when_todo_file_changed(tmp_path: Path) -> None:
    """A stale todo.txt should abort before either file is written."""
    todo_path, done_path = _completed_setup(tmp_path)
    store = TodoTextStore(todo_path)
    todos = store.load_todos()
    todo_path.write_bytes(b"Written by another device\r\n")
    done_before = done_path.read_bytes()

    with pytest.raises(TodoFileChangedError):
        archive_completed_todos(todos, store, DoneTextStore(done_path))

    assert todo_path.read_bytes() == b"Written by another device\r\n"
    assert done_path.read_bytes() == done_before


def test_archive_without_completed_tasks_writes_nothing(
    tmp_path: Path,
) -> None:
    """Archiving nothing should leave both files untouched."""
    todo_path = tmp_path / "todo.txt"
    todo_path.write_bytes(b"Call Mom\r\n")
    done_path = tmp_path / "done.txt"
    store = TodoTextStore(todo_path)

    archive_completed_todos(
        store.load_todos(),
        store,
        DoneTextStore(done_path),
    )

    assert todo_path.read_bytes() == b"Call Mom\r\n"
    assert done_path.exists() is False


def test_archive_creates_done_file_when_missing(tmp_path: Path) -> None:
    """A missing done.txt should be created using the todo line ending."""
    todo_path = tmp_path / "todo.txt"
    todo_path.write_bytes(b"x Pay invoice\n")
    done_path = tmp_path / "done.txt"
    store = TodoTextStore(todo_path)

    archive_completed_todos(
        store.load_todos(),
        store,
        DoneTextStore(done_path),
    )

    assert done_path.read_bytes() == b"x Pay invoice\n"


def _notes_setup(tmp_path: Path, contents: str) -> tuple[Path, Path]:
    """Create a todo.txt and return it with a notes file path."""
    todo_path = tmp_path / "todo.txt"
    todo_path.write_text(contents, encoding="utf-8", newline="")
    return todo_path, tmp_path / "data" / "notes.json"


def test_notes_stay_out_of_todo_file(tmp_path: Path) -> None:
    """Notes should be saved to program data and restored on reload."""
    todo_path, notes_path = _notes_setup(tmp_path, "2026-09-20 Pay rent\n")
    store = TodoTextStore(todo_path, NotesStore(notes_path))
    todos = store.load_todos()
    todos[0].notes = "Use the new account"

    store.save_todos(todos)

    assert todo_path.read_text(encoding="utf-8") == "2026-09-20 Pay rent\n"
    reloaded = TodoTextStore(todo_path, NotesStore(notes_path)).load_todos()
    assert reloaded[0].notes == "Use the new account"


def test_notes_follow_task_completed_elsewhere(tmp_path: Path) -> None:
    """Completing a task in another app should keep its note attached."""
    todo_path, notes_path = _notes_setup(
        tmp_path,
        "(A) 2026-09-20 Pay rent due:2026-10-01\n",
    )
    store = TodoTextStore(todo_path, NotesStore(notes_path))
    todos = store.load_todos()
    todos[0].notes = "Use the new account"
    store.save_todos(todos)

    todo_path.write_text(
        "x 2026-09-27 2026-09-20 Pay rent +Home due:2026-10-01 pri:A\n",
        encoding="utf-8",
    )

    reloaded = TodoTextStore(todo_path, NotesStore(notes_path)).load_todos()
    assert reloaded[0].notes == "Use the new account"


def test_notes_follow_title_edits_in_the_program(tmp_path: Path) -> None:
    """Renaming a task in the program should move its note, not copy it."""
    todo_path, notes_path = _notes_setup(tmp_path, "Pay rent\n")
    store = TodoTextStore(todo_path, NotesStore(notes_path))
    todos = store.load_todos()
    todos[0].notes = "Use the new account"
    store.save_todos(todos)

    todos[0].title = "Pay October rent"
    store.save_todos(todos)

    assert notes_path.read_text(encoding="utf-8").count("rent") == 1
    reloaded = TodoTextStore(todo_path, NotesStore(notes_path)).load_todos()
    assert reloaded[0].notes == "Use the new account"


def test_notes_match_titles_typed_with_projects(tmp_path: Path) -> None:
    """A title typed with +project should find its note after reload."""
    todo_path, notes_path = _notes_setup(tmp_path, "")
    store = TodoTextStore(todo_path, NotesStore(notes_path))
    store.load_todos()

    store.save_todos([Todo("new", "Pay rent +Home", notes="Monthly")])

    reloaded = TodoTextStore(todo_path, NotesStore(notes_path)).load_todos()
    assert reloaded[0].title == "Pay rent"
    assert reloaded[0].notes == "Monthly"


def test_notes_are_removed_with_their_task(tmp_path: Path) -> None:
    """Deleting a task should drop its note from program data."""
    todo_path, notes_path = _notes_setup(tmp_path, "Pay rent\nCall Mom\n")
    store = TodoTextStore(todo_path, NotesStore(notes_path))
    todos = store.load_todos()
    todos[0].notes = "Use the new account"
    store.save_todos(todos)

    store.save_todos(todos[1:])

    assert "account" not in notes_path.read_text(encoding="utf-8")


def test_invalid_notes_file_is_set_aside(tmp_path: Path) -> None:
    """An unreadable notes file should not block loading tasks."""
    todo_path, notes_path = _notes_setup(tmp_path, "Pay rent\n")
    notes_path.parent.mkdir(parents=True)
    notes_path.write_text("{not json", encoding="utf-8")

    todos = TodoTextStore(todo_path, NotesStore(notes_path)).load_todos()

    assert todos[0].notes == ""
    assert notes_path.with_name("notes.json.invalid").read_text(
        encoding="utf-8",
    ) == "{not json"


def test_text_store_keeps_lines_intact_across_repeated_saves(
    tmp_path: Path,
) -> None:
    """A second save in one session should still touch only edited lines."""
    storage_path = tmp_path / "todo.txt"
    storage_path.write_text(
        "Water plants  +home\n(B) Call Mom\nBuy milk\n",
        encoding="utf-8",
        newline="",
    )
    store = TodoTextStore(storage_path)
    todos = store.load_todos()
    todos[2].title = "Buy oat milk"
    store.save_todos(todos)

    todos[1].title = "Call Mom back"
    store.save_todos(sorted(todos, key=lambda todo: todo.title))

    assert storage_path.read_text(encoding="utf-8").splitlines() == [
        "Water plants  +home",
        "(B) Call Mom back",
        "Buy oat milk",
    ]
