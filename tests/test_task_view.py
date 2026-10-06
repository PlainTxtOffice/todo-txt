"""Check Qt views delegate commands and preferences to controllers."""

import json

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from src.adapters.storage.done_text import DoneTextStore
from src.adapters.storage.todo_text import TodoTextStore
from src.config.settings import load_settings
from src.domains.tasks.models import TaskBoard
from src.gui.controllers.preferences import ViewPreferences
from src.gui.controllers.tasks import TaskController
from src.gui.views.root_window.panes.task_view import TaskView


@pytest.fixture
def view_setup(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "todo.txt"
    path.write_text("Original\n", encoding="utf-8")
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "priority": {"minimum": "A", "maximum": "E"},
                "todoFile": str(path),
            }
        ),
        encoding="utf-8",
    )
    store = TodoTextStore(path)
    board = TaskBoard(store.load_todos())
    controller = TaskController(
        board, store, DoneTextStore(tmp_path / "done.txt")
    )
    view = TaskView(controller, ViewPreferences(settings_path))
    yield view, controller, settings_path
    view.close()
    app.processEvents()


def test_view_save_complete_export_archive(view_setup, tmp_path, monkeypatch):
    """Exercise the view wiring across the extracted controller boundary."""
    view, controller, settings_path = view_setup
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes
    )
    view.todo_list.setCurrentRow(0)
    view.task_editor._title_edit.setText("Updated")
    view.save_task()
    assert controller.list_todos()[0].title == "Updated"
    view.todo_list.setCurrentRow(0)
    view.complete_selected()
    assert controller.list_todos()[0].is_completed
    exported = tmp_path / "export.txt"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args: (str(exported), "")
    )
    view.export_tasks()
    assert "Updated" in exported.read_text()
    view.set_show_file_lines(show_file_lines=False)
    assert load_settings(settings_path).show_file_lines is False
    view.archive_completed()
    assert view.todo_list.count() == 0
    assert "Updated" in controller.archive_path.read_text()


def test_view_conflict_restores_checkbox(view_setup, monkeypatch):
    """Declining reload must restore the checkbox to the retained board state."""
    view, controller, _ = view_setup
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No
    )
    controller.storage_path.write_text("External edit\n", encoding="utf-8")
    view.todo_list.item(0).setCheckState(Qt.CheckState.Checked)
    assert controller.list_todos()[0].is_completed is False
    assert view.todo_list.item(0).checkState() == Qt.CheckState.Unchecked
    assert controller.storage_path.read_text() == "External edit\n"


@pytest.mark.parametrize(
    "minimum,maximum,valid", [("Z", "A", False), ("B", "D", True)]
)
def test_settings_dialog_uses_validated_model(
    view_setup, monkeypatch, minimum, maximum, valid
):
    """The dialog rejects reversed bounds and preserves other preferences."""
    from dataclasses import replace

    from src.gui.views.settings import settings_dialog

    view, _, settings_path = view_setup
    previous = replace(load_settings(settings_path), show_file_lines=False)
    saved = []
    warnings = []
    monkeypatch.setattr(settings_dialog, "load_settings", lambda: previous)
    monkeypatch.setattr(
        settings_dialog,
        "save_file_settings",
        lambda settings, *args, **kwargs: saved.append(settings),
    )
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: warnings.append(args)
    )
    dialog = settings_dialog.SettingsDialog(view)
    dialog.minimum_priority.setCurrentText(minimum)
    dialog.maximum_priority.setCurrentText(maximum)
    dialog._save()
    assert bool(saved) is valid
    assert bool(warnings) is not valid
    if valid:
        assert saved[0].show_file_lines is False
        assert saved[0].priority.minimum == "B"
    dialog.close()


def test_editor_saves_projects(view_setup):
    """Typed projects are saved to todo.txt with or without a leading +."""
    view, controller, _ = view_setup
    view.todo_list.setCurrentRow(0)
    assert view.task_editor._projects_edit.text() == ""
    view.task_editor._projects_edit.setText("+Home work +Home")
    assert view.task_editor.has_unsaved_changes()
    view.save_task()
    assert controller.list_todos()[0].projects == ("Home", "work")
    assert controller.storage_path.read_text() == "Original +Home +work\n"
    view.todo_list.setCurrentRow(0)
    assert view.task_editor._projects_edit.text() == "+Home +work"
    assert not view.task_editor.has_unsaved_changes()


def test_editor_adds_known_project(view_setup):
    """Choosing a project from the dropdown appends it once."""
    view, _, _ = view_setup
    project_box = view.task_editor._project_box
    assert not project_box.isEnabled()
    view.todo_list.setCurrentRow(0)
    view.task_editor._projects_edit.setText("work +Home")
    view.save_task()
    assert project_box.isEnabled()
    assert [
        project_box.itemData(index) for index in range(project_box.count())
    ] == [None, "Home", "work"]
    view.new_task()
    view.task_editor._projects_edit.setText("Errands")
    project_box.activated.emit(1)
    project_box.activated.emit(1)
    assert view.task_editor._projects_edit.text() == "Errands +Home"
    assert project_box.currentIndex() == 0
    assert view.task_editor.has_unsaved_changes()
