"""Build the main application menu bar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMenuBar, QMessageBox

from src.bootstrap import build_recurring_controller
from src.config.settings import load_settings
from src.gui.views.menu_bar.view_menu import build_view_menu
from src.gui.views.recurring.dialog import RecurringDialog
from src.gui.views.settings.settings_dialog import show_settings_dialog

if TYPE_CHECKING:
    from src.gui.views.root_window.panes.task_view import TaskView


def build_menu_bar(window: QMainWindow, task_view: TaskView) -> QMenuBar:
    """Create and populate the application menu bar."""
    menu_bar = window.menuBar()
    file_menu = menu_bar.addMenu("&File")
    export_action = QAction("&Export...", window)
    export_action.setShortcut(QKeySequence("Ctrl+E"))
    export_action.triggered.connect(task_view.export_tasks)
    file_menu.addAction(export_action)
    archive_action = QAction("&Archive Completed", window)
    archive_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
    archive_action.triggered.connect(task_view.archive_completed)
    file_menu.addAction(archive_action)
    file_menu.addSeparator()
    exit_action = QAction("E&xit", window)
    exit_action.setShortcut(QKeySequence("Ctrl+Q"))
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)

    edit_menu = menu_bar.addMenu("&Edit")
    new_action = QAction("&New Task", window)
    new_action.setShortcut(QKeySequence("Ctrl+N"))
    new_action.triggered.connect(task_view.new_task)
    edit_menu.addAction(new_action)
    complete_action = QAction("Toggle &Complete", window)
    complete_action.setShortcut(QKeySequence("Ctrl+Return"))
    complete_action.triggered.connect(task_view.complete_selected)
    edit_menu.addAction(complete_action)
    delete_action = QAction("&Delete Task", window)
    delete_action.setShortcut(QKeySequence("Delete"))
    delete_action.triggered.connect(task_view.delete_selected)
    edit_menu.addAction(delete_action)
    edit_menu.addSeparator()
    settings_action = QAction("&Settings...", window)
    settings_action.setShortcut(QKeySequence("Ctrl+,"))
    settings_action.triggered.connect(
        lambda: _edit_settings(window, task_view),
    )
    edit_menu.addAction(settings_action)

    build_view_menu(window, menu_bar, task_view)

    recurring_action = QAction("&Recurring Tasks...", window)
    recurring_action.triggered.connect(lambda: _show_recurring(window))
    edit_menu.addAction(recurring_action)

    help_menu = menu_bar.addMenu("&Help")
    about_action = QAction("&About", window)
    about_action.triggered.connect(lambda: _show_about(window))
    help_menu.addAction(about_action)
    return menu_bar


def _show_about(window: QMainWindow) -> None:
    QMessageBox.about(
        window,
        "About Todo Txt",
        "Todo Txt\n\nA simple app for managing one-time tasks.",
    )


def _show_recurring(window: QMainWindow) -> None:
    """Open the optional recurring feature and report initialization errors."""
    try:
        dialog = RecurringDialog(build_recurring_controller(), window)
        dialog.exec()
        dialog.deleteLater()
    except (OSError, ValueError, TypeError) as exc:
        QMessageBox.warning(window, "Recurring Tasks", str(exc))


def _edit_settings(window: QMainWindow, task_view: TaskView) -> None:
    previous_path = load_settings().todo_file.resolve()
    if show_settings_dialog(window):
        if load_settings().todo_file.resolve() != previous_path:
            window.close()
        else:
            task_view.reload_display_settings()
