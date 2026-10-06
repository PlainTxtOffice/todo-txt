"""Exercise supported Qt recurring controls with isolated example files."""

import json
import shutil
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QPushButton,
    QStyle,
    QStyleOptionViewItem,
)

from src.adapters.recurring.json_state import JsonOccurrences
from src.adapters.recurring.markdown import MarkdownTemplates
from src.application.recurring import RecurringWorkflow
from src.domains.premium.access import (
    PreviewEntitlement,
    UnavailableEntitlement,
)
from src.gui.controllers.recurring import RecurringController
from src.gui.views.recurring.dialog import RecurringDialog


@pytest.fixture
def dialog_setup(tmp_path):
    """Construct a native Qt view with fixture-only storage and clock."""
    app = QApplication.instance() or QApplication([])
    folder = tmp_path / "templates"
    shutil.copytree(Path(__file__).parent / "fixtures" / "recurring", folder)
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"priority": {"minimum": "A", "maximum": "E"}})
    )
    workflow = RecurringWorkflow(
        MarkdownTemplates(),
        JsonOccurrences(tmp_path / "state.json"),
        PreviewEntitlement(),
    )
    controller = RecurringController(
        workflow, settings, lambda: date(2026, 9, 28)
    )
    dialog = RecurringDialog(controller)
    dialog.show()
    app.processEvents()
    yield dialog, folder, controller
    dialog.close()
    app.processEvents()


def test_apply_checkbox_refresh_and_reopen(dialog_setup):
    """Use visible controls to opt in, complete early, and retain completion."""
    dialog, folder, controller = dialog_setup
    assert dialog.tasks.count() == 0
    dialog.folder.setText(str(folder))
    QTest.mouseClick(dialog.enabled, Qt.MouseButton.LeftButton)
    apply = next(
        button
        for button in dialog.findChildren(QPushButton)
        if button.text() == "Apply"
    )
    QTest.mouseClick(apply, Qt.MouseButton.LeftButton)
    assert dialog.tasks.count() == 8
    medium = next(
        dialog.tasks.item(i)
        for i in range(dialog.tasks.count())
        if dialog.tasks.item(i).text().startswith("Medium")
    )
    assert "suggested Sunday" in medium.text()
    option = QStyleOptionViewItem()
    option.initFrom(dialog.tasks)
    dialog.tasks.itemDelegate().initStyleOption(
        option,
        dialog.tasks.indexFromItem(medium),
    )
    option.rect = dialog.tasks.visualItemRect(medium)
    rectangle = dialog.tasks.style().subElementRect(
        QStyle.SubElement.SE_ItemViewItemCheckIndicator,
        option,
        dialog.tasks,
    )
    QTest.mouseClick(
        dialog.tasks.viewport(),
        Qt.MouseButton.LeftButton,
        pos=rectangle.center(),
    )
    controller.clock = lambda: date(2026, 10, 4)
    QTest.mouseClick(
        next(
            button
            for button in dialog.findChildren(QPushButton)
            if button.text() == "Refresh"
        ),
        Qt.MouseButton.LeftButton,
    )
    rows = [
        dialog.tasks.item(i)
        for i in range(dialog.tasks.count())
        if dialog.tasks.item(i).text().startswith("Medium")
    ]
    assert len(rows) == 1
    assert rows[0].checkState() == Qt.CheckState.Checked
    assert "completed 2026-09-28" in rows[0].text()
    reopened = RecurringDialog(controller)
    assert "1 of 8 completed" in reopened.summary.text()
    reopened.close()
    controller.clock = lambda: date(2026, 10, 5)
    dialog.refresh()
    assert all(
        dialog.tasks.item(i).checkState() == Qt.CheckState.Unchecked
        for i in range(dialog.tasks.count())
    )


def test_denied_access_is_read_only_and_preserves_state(
    dialog_setup, monkeypatch
):
    """Revoke preview access and block opt-in commands without losing records."""
    dialog, folder, controller = dialog_setup
    controller.save_preferences(str(folder), enabled=True)
    dialog.refresh()
    row = dialog.tasks.item(0)
    row.setCheckState(Qt.CheckState.Checked)
    controller.workflow.entitlement = UnavailableEntitlement()
    dialog.refresh()
    assert "read only" in dialog.summary.text()
    assert not dialog.tasks.item(0).flags() & Qt.ItemFlag.ItemIsUserCheckable
    assert "not connected" in dialog.status.text()
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: warnings.append(args[-1])
    )
    dialog.enabled.setChecked(True)
    dialog.folder.setText(str(folder))
    QTest.mouseClick(
        next(
            button
            for button in dialog.findChildren(QPushButton)
            if button.text() == "Apply"
        ),
        Qt.MouseButton.LeftButton,
    )
    assert warnings and "not connected" in warnings[0]
    assert dialog.tasks.item(0).checkState() == Qt.CheckState.Checked


def test_bad_folder_reports_error_and_disables_stale_rows(dialog_setup):
    """An unavailable template folder leaves persisted state untouched."""
    dialog, folder, controller = dialog_setup
    controller.save_preferences(str(folder), enabled=True)
    dialog.refresh()
    shutil.rmtree(folder)
    dialog.refresh()
    assert not dialog.tasks.isEnabled()
    assert "Could not refresh" in dialog.summary.text()


def test_closed_dialog_stops_refresh(dialog_setup):
    """Closing the optional view stops its timer even if a parent retains it."""
    dialog, _, _ = dialog_setup
    assert dialog._timer.isActive()
    dialog.close()
    assert not dialog._timer.isActive()


def test_existing_app_menu_opens_recurring_dialog(
    dialog_setup, monkeypatch, tmp_path
):
    """Open recurrence through the existing main window's real menu action."""
    from src.adapters.storage.done_text import DoneTextStore
    from src.adapters.storage.todo_text import TodoTextStore
    from src.domains.tasks.models import TaskBoard
    from src.gui.controllers.preferences import ViewPreferences
    from src.gui.views.menu_bar import main_menu
    from src.gui.views.root_window import window

    dialog, folder, controller = dialog_setup
    dialog.close()
    controller.save_preferences(str(folder), enabled=True)
    monkeypatch.setattr(
        main_menu, "build_recurring_controller", lambda: controller
    )
    monkeypatch.setattr(
        window,
        "ViewPreferences",
        lambda: ViewPreferences(controller.settings_path),
    )
    task_path = tmp_path / "todo.txt"
    task_path.write_text("Ordinary task\n")
    store = TodoTextStore(task_path)
    main = window.TodoMainWindow(
        TaskBoard(store.load_todos()),
        store,
        DoneTextStore(tmp_path / "done.txt"),
    )
    main.show()
    opened = []

    def close_dialog():
        active = QApplication.activeModalWidget()
        assert isinstance(active, RecurringDialog)
        opened.append(active.tasks.count())
        active.reject()

    action = next(
        action
        for menu in main.menuBar().actions()
        if menu.menu()
        for action in menu.menu().actions()
        if "Recurring Tasks" in action.text()
    )
    QTimer.singleShot(0, close_dialog)
    action.trigger()
    assert opened == [8]
    assert task_path.read_text() == "Ordinary task\n"
    main.close()
