"""Test archive relocation and the user's prompt choices."""

import json
from dataclasses import replace

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from src.application import file_change
from src.config.settings import load_settings
from src.domains.tasks.archive import ArchiveAction
from src.gui.views.settings.archive_prompt import ask_archive_move


@pytest.fixture
def locations(tmp_path):
    """Create an archive and settings without using personal files."""
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    (old / "done.txt").write_bytes(b"x 2026-09-15 Task\r\n")
    (new / "todo.txt").write_text("Next task\n", encoding="utf-8")
    config = tmp_path / "settings.json"
    config.write_text(
        json.dumps(
            {
                "priority": {"minimum": "A", "maximum": "E"},
                "todoFile": str(old / "todo.txt"),
            }
        ),
        encoding="utf-8",
    )
    previous = load_settings(config)
    return config, previous, replace(previous, todo_file=new / "todo.txt")


def test_move_archive(locations):
    """Move exact bytes and derive the archive path on restart."""
    config, previous, selected = locations
    original = previous.done_file.read_bytes()
    file_change.save_file_settings(
        selected,
        previous,
        archive_action=ArchiveAction.MOVE,
        settings_path=config,
    )
    assert not previous.done_file.exists()
    assert load_settings(config).done_file.read_bytes() == original


def test_existing_archive_is_preserved(locations):
    """Refuse to overwrite a destination, even after prompt approval."""
    config, previous, selected = locations
    destination = selected.todo_file.with_name("done.txt")
    destination.write_bytes(b"Existing")
    with pytest.raises(FileExistsError):
        file_change.save_file_settings(
            selected,
            previous,
            archive_action=ArchiveAction.MOVE,
            settings_path=config,
        )
    assert destination.read_bytes() == b"Existing"
    assert previous.done_file.exists()
    assert load_settings(config).todo_file == previous.todo_file


def test_save_failure_retains_source(locations, monkeypatch):
    """Remove the new copy when settings cannot be saved."""
    config, previous, selected = locations

    def fail(*args):
        raise OSError("Save failed")

    monkeypatch.setattr(file_change, "save_settings", fail)
    with pytest.raises(OSError, match="Save failed"):
        file_change.save_file_settings(
            selected,
            previous,
            archive_action=ArchiveAction.MOVE,
            settings_path=config,
        )
    assert previous.done_file.exists()
    assert not selected.todo_file.with_name("done.txt").exists()


@pytest.mark.parametrize(
    "answer, expected",
    [
        (QMessageBox.StandardButton.Yes, ArchiveAction.MOVE),
        (QMessageBox.StandardButton.No, ArchiveAction.KEEP),
        (QMessageBox.StandardButton.Cancel, None),
    ],
)
def test_prompt_choices(locations, monkeypatch, answer, expected):
    """Distinguish move, leave, and cancellation."""
    app = QApplication.instance() or QApplication([])
    _, previous, selected = locations
    monkeypatch.setattr(QMessageBox, "question", lambda *args: answer)
    assert ask_archive_move(None, previous, selected.todo_file) is expected
    assert app is not None


def test_explicit_default_is_preserved(locations, monkeypatch):
    """An explicit path stays fixed even when it equals the old default."""
    config, previous, selected = locations
    payload = json.loads(config.read_text())
    payload["doneFile"] = str(previous.done_file)
    config.write_text(json.dumps(payload), encoding="utf-8")
    previous = load_settings(config)

    def unexpected(*args):
        pytest.fail("Explicit archive must not prompt")

    monkeypatch.setattr(QMessageBox, "question", unexpected)
    assert (
        ask_archive_move(None, previous, selected.todo_file)
        is ArchiveAction.KEEP
    )
    file_change.save_file_settings(selected, previous, settings_path=config)
    assert load_settings(config).done_file == previous.done_file


def test_decline_keeps_old_archive(locations):
    """Declining a move uses the new default and retains the old file."""
    config, previous, selected = locations
    file_change.save_file_settings(selected, previous, settings_path=config)
    assert previous.done_file.exists()
    assert load_settings(config).done_file == selected.todo_file.with_name(
        "done.txt"
    )
    assert not load_settings(config).done_file.exists()


def test_atomic_settings_failure(locations, monkeypatch):
    """A failed settings replacement retains settings and the source archive."""
    from src.config import settings

    config, previous, selected = locations
    original = config.read_bytes()

    def fail(*args):
        raise PermissionError("Locked settings")

    monkeypatch.setattr(settings.Path, "replace", fail)
    with pytest.raises(PermissionError):
        file_change.save_file_settings(
            selected,
            previous,
            archive_action=ArchiveAction.MOVE,
            settings_path=config,
        )
    assert config.read_bytes() == original
    assert previous.done_file.exists()
    assert not selected.todo_file.with_name("done.txt").exists()


def test_dialog_cancel_preserves_all(locations, monkeypatch):
    """Cancelling the archive prompt does not save other settings either."""
    from src.gui.views.settings import settings_dialog

    app = QApplication.instance() or QApplication([])
    config, previous, selected = locations
    original = config.read_bytes()
    monkeypatch.setattr(settings_dialog, "load_settings", lambda: previous)
    monkeypatch.setattr(settings_dialog, "ask_archive_move", lambda *args: None)

    def unexpected(*args, **kwargs):
        pytest.fail("Cancelled dialog must not save")

    monkeypatch.setattr(settings_dialog, "save_file_settings", unexpected)
    dialog = settings_dialog.SettingsDialog()
    dialog.todo_file.setText(str(selected.todo_file))
    dialog._save()
    assert config.read_bytes() == original
    assert previous.done_file.exists()
    dialog.close()
    assert app is not None


@pytest.mark.parametrize(
    "action", [ArchiveAction.MERGE, ArchiveAction.OVERWRITE]
)
def test_existing_archive_action(locations, action):
    """Merge retains duplicates; overwrite replaces the destination."""
    config, previous, selected = locations
    incoming = previous.done_file.read_bytes()
    destination = selected.todo_file.with_name("done.txt")
    destination.write_bytes(incoming)
    file_change.save_file_settings(
        selected,
        previous,
        archive_action=action,
        settings_path=config,
    )
    expected = incoming * 2 if action == ArchiveAction.MERGE else incoming
    assert destination.read_bytes() == expected
    assert not previous.done_file.exists()
    assert load_settings(config).done_file == destination


@pytest.mark.parametrize(
    "existing", [b"", b"First", b"First\r\nSecond", b"First\n"]
)
def test_merge_line_boundary(locations, existing):
    """A missing final newline must not join two completed tasks."""
    config, previous, selected = locations
    incoming = previous.done_file.read_bytes()
    destination = selected.todo_file.with_name("done.txt")
    destination.write_bytes(existing)
    file_change.save_file_settings(
        selected,
        previous,
        archive_action=ArchiveAction.MERGE,
        settings_path=config,
    )
    assert (
        destination.read_bytes().splitlines()
        == existing.splitlines() + incoming.splitlines()
    )
    assert destination.read_bytes().startswith(existing)


@pytest.mark.parametrize(
    "action", [ArchiveAction.MERGE, ArchiveAction.OVERWRITE]
)
def test_action_save_failure(locations, monkeypatch, action):
    """A settings error restores both archives exactly."""
    config, previous, selected = locations
    destination = selected.todo_file.with_name("done.txt")
    destination.write_bytes(b"Original\r\n")
    incoming = previous.done_file.read_bytes()

    def fail(*args):
        raise OSError("Settings locked")

    monkeypatch.setattr(file_change, "save_settings", fail)
    with pytest.raises(OSError, match="Settings locked"):
        file_change.save_file_settings(
            selected,
            previous,
            archive_action=action,
            settings_path=config,
        )
    assert destination.read_bytes() == b"Original\r\n"
    assert previous.done_file.read_bytes() == incoming
    assert load_settings(config).todo_file == previous.todo_file


@pytest.mark.parametrize(
    "label, confirmation, expected",
    [
        ("Merge", None, ArchiveAction.MERGE),
        ("Use Existing", None, ArchiveAction.KEEP),
        ("Cancel", None, None),
        (
            "Overwrite...",
            QMessageBox.StandardButton.Yes,
            ArchiveAction.OVERWRITE,
        ),
        ("Overwrite...", QMessageBox.StandardButton.Cancel, None),
    ],
)
def test_collision_choices(
    locations, monkeypatch, label, confirmation, expected
):
    """Exercise the real collision dialog and overwrite confirmation."""
    from PySide6.QtCore import QTimer

    app = QApplication.instance() or QApplication([])
    _, previous, selected = locations
    selected.todo_file.with_name("done.txt").write_bytes(b"Existing")
    confirmations = []

    def confirm(*args):
        confirmations.append(args)
        return confirmation

    monkeypatch.setattr(QMessageBox, "warning", confirm)

    def click_choice():
        dialog = app.activeModalWidget()
        for button in dialog.buttons():
            if button.text().replace("&", "") == label:
                button.click()
                return
        dialog.reject()
        pytest.fail(f"Missing choice: {label}")

    QTimer.singleShot(0, click_choice)
    assert ask_archive_move(None, previous, selected.todo_file) == expected
    assert bool(confirmations) == (label == "Overwrite...")
