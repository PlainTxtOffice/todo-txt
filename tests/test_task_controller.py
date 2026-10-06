"""Exercise task commands through real temporary storage without Qt."""

from datetime import date

import pytest

from src.adapters.storage.done_text import DoneTextStore
from src.adapters.storage.notes import NotesStore
from src.adapters.storage.todo_text import TodoTextStore
from src.domains.tasks.models import TaskBoard, TaskEdits
from src.gui.controllers.tasks import TaskController
from src.ports.tasks import TodoFileChangedError


@pytest.fixture
def controller_setup(tmp_path):
    path = tmp_path / "todo.txt"
    path.write_bytes(b"2026-09-20 Original  +home\r\n")
    store = TodoTextStore(path, NotesStore(tmp_path / "notes.json"))
    board = TaskBoard(store.load_todos())
    archive = DoneTextStore(tmp_path / "done.txt")
    return TaskController(board, store, archive), board, store, archive


def test_edit_complete_archive_and_export(controller_setup, tmp_path):
    """Controller commands preserve notes and archive completed tasks."""
    controller, board, store, archive = controller_setup
    identifier = board.todos[0].identifier
    edits = TaskEdits(
        "Updated", date(2026, 10, 1), "Private note", "B", ("home",)
    )
    assert controller.save_task(identifier, edits) == identifier
    assert board.todos[0].notes == "Private note"
    assert "Private note" not in store.storage_path.read_text()
    controller.complete_task(identifier, edits)
    assert controller.completed_count() == 1
    export = tmp_path / "export.txt"
    controller.export_tasks(export)
    assert export.read_text().startswith("x ")
    controller.archive_completed()
    assert board.todos == []
    assert store.storage_path.read_bytes() == b""
    assert "Updated" in archive.storage_path.read_text()
    assert (
        "Private note"
        not in store.storage_path.with_name("notes.json").read_text()
    )


def test_create_delete_and_reload(controller_setup):
    """Task identifiers survive saves and later file changes can be reloaded."""
    controller, board, store, _ = controller_setup
    identifier = controller.save_task(
        None, TaskEdits("New", None, "", None, ())
    )
    assert controller.look_todo(identifier).title == "New"
    controller.set_completed(identifier, is_completed=True)
    assert controller.look_todo(identifier).is_completed
    controller.delete_task(identifier)
    assert controller.look_todo(identifier) is None
    assert len(board.todos) == 1
    store.storage_path.write_text("External\n", encoding="utf-8")
    controller.reload_tasks()
    assert [todo.title for todo in board.todos] == ["External"]


@pytest.mark.parametrize(
    "command", ["create", "edit", "delete", "complete", "toggle"]
)
def test_conflict_keeps_visible_board(controller_setup, command):
    """A stale-file rejection must not mutate visible state or external bytes."""
    controller, board, store, _ = controller_setup
    original = board.todos[0]
    identifier = original.identifier
    edits = TaskEdits("Changed", None, "Changed note", "A", ())
    store.storage_path.write_text("External edit\n", encoding="utf-8")
    commands = {
        "create": lambda: controller.save_task(None, edits),
        "edit": lambda: controller.save_task(identifier, edits),
        "delete": lambda: controller.delete_task(identifier),
        "complete": lambda: controller.complete_task(identifier, edits),
        "toggle": lambda: controller.set_completed(
            identifier, is_completed=True
        ),
    }
    with pytest.raises(TodoFileChangedError):
        commands[command]()
    assert board.todos == [original]
    assert original.title == "Original"
    assert original.is_completed is False
    assert original.notes == ""
    assert store.storage_path.read_text() == "External edit\n"


def test_invalid_edit_keeps_visible_board(controller_setup):
    """Invalid priority must not partially apply the title and notes."""
    controller, board, store, _ = controller_setup
    original_bytes = store.storage_path.read_bytes()
    with pytest.raises(ValueError, match="priority"):
        controller.save_task(
            board.todos[0].identifier,
            TaskEdits("Changed", None, "note", "AA", ()),
        )
    assert board.todos[0].title == "Original"
    assert board.todos[0].notes == ""
    assert store.storage_path.read_bytes() == original_bytes


def test_archive_append_failure_keeps_tasks(controller_setup, monkeypatch):
    """Failure to append must leave active storage and board unchanged."""
    controller, board, store, archive = controller_setup
    controller.set_completed(board.todos[0].identifier, is_completed=True)
    before = store.storage_path.read_bytes()

    def fail(*args, **kwargs):
        raise OSError("Archive locked")

    monkeypatch.setattr(archive, "append_lines", fail)
    with pytest.raises(OSError, match="Archive locked"):
        controller.archive_completed()
    assert store.storage_path.read_bytes() == before
    assert controller.completed_count() == 1


def test_archive_removal_failure_retains_both_copies(
    controller_setup, monkeypatch
):
    """Preserve append-before-remove behavior if the second write fails."""
    controller, board, store, archive = controller_setup
    controller.set_completed(board.todos[0].identifier, is_completed=True)
    before = store.storage_path.read_bytes()

    def fail(*args, **kwargs):
        raise OSError("Todo locked")

    monkeypatch.setattr(store, "save_todos", fail)
    with pytest.raises(OSError, match="Todo locked"):
        controller.archive_completed()
    assert store.storage_path.read_bytes() == before
    assert archive.storage_path.read_bytes() == before
    assert controller.completed_count() == 1
