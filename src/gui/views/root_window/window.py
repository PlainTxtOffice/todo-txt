"""Provide the main todo application window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QFileSystemWatcher, QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox

from src.config.settings import load_settings
from src.gui.controllers.preferences import ViewPreferences
from src.gui.controllers.tasks import TaskController
from src.gui.views.menu_bar.main_menu import build_menu_bar
from src.gui.views.root_window.panes.task_view import TaskView
from src.gui.views.settings.settings_dialog import show_settings_dialog

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

    from src.adapters.storage.done_text import DoneTextStore
    from src.adapters.storage.todo_text import TodoTextStore
    from src.domains.tasks.models import TaskBoard


class TodoMainWindow(QMainWindow):
    """Host the one-time todo list and editing form."""

    def __init__(
        self,
        task_board: TaskBoard,
        store: TodoTextStore,
        done_store: DoneTextStore,
    ) -> None:
        """Initialize the main window and task view."""
        super().__init__()
        self._store = store
        self._external_change_pending = False
        self.setWindowTitle("Todo Txt")
        self.resize(900, 600)
        self._task_view = TaskView(
            TaskController(task_board, store, done_store),
            ViewPreferences(),
        )
        self.setCentralWidget(self._task_view)
        build_menu_bar(self, self._task_view)
        self._file_watcher = QFileSystemWatcher(self)
        self._file_watcher.fileChanged.connect(self._shared_file_changed)
        self._file_watcher.directoryChanged.connect(self._shared_file_changed)
        self._watch_shared_file()
        QTimer.singleShot(0, self._show_conflicted_copy_alert)
        QTimer.singleShot(0, self._locate_missing_file)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Offer to save editor changes before the window closes."""
        if self._task_view.resolve_unsaved_changes():
            event.accept()
        else:
            event.ignore()

    def _watch_shared_file(self) -> None:
        paths = [str(self._store.storage_path.parent)]
        if self._store.storage_path.exists():
            paths.append(str(self._store.storage_path))
        watched_paths = set(self._file_watcher.files()) | set(
            self._file_watcher.directories(),
        )
        new_paths = [path for path in paths if path not in watched_paths]
        if new_paths:
            self._file_watcher.addPaths(new_paths)

    def _shared_file_changed(self, _path: str) -> None:
        self._watch_shared_file()
        if self._external_change_pending:
            return
        if not self._store.storage_path.exists():
            self._locate_missing_file()
            return
        if not self._store.has_external_changes():
            return
        self._external_change_pending = True
        answer = QMessageBox.question(
            self,
            "Todo File Changed",
            "todo.txt changed in another application. Reload it now? "
            "Unsaved Windows changes will be discarded.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._task_view.reload_tasks()
        self._external_change_pending = False

    def _locate_missing_file(self) -> None:
        """Offer file selection when the configured todo file is missing."""
        if self._store.storage_path.exists() or self._external_change_pending:
            return
        self._external_change_pending = True
        try:
            answer = QMessageBox.question(
                self,
                "Todo File Missing",
                f"Cannot find {self._store.storage_path}. "
                "If you moved it, locate it in Settings now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if (
                answer == QMessageBox.StandardButton.Yes
                and show_settings_dialog(self)
                and load_settings().todo_file.resolve()
                != self._store.storage_path.resolve()
            ):
                self.close()
        finally:
            self._external_change_pending = False

    def _show_conflicted_copy_alert(self) -> None:
        conflicted_copies = self._store.find_conflicted_copies()
        if not conflicted_copies:
            return
        names = "\n".join(path.name for path in conflicted_copies)
        QMessageBox.warning(
            self,
            "Dropbox Conflicted Copies",
            "Dropbox conflicted copies were found beside todo.txt:\n\n"
            f"{names}\n\nReview them before deleting them.",
        )
