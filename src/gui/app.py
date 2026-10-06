"""Bootstrap the PySide6 todo interface."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.config.path_handler import APP_ICON_PATH
from src.gui.views.root_window.window import TodoMainWindow

if TYPE_CHECKING:
    from src.adapters.storage.done_text import DoneTextStore
    from src.adapters.storage.todo_text import TodoTextStore
    from src.domains.tasks.models import TaskBoard


def run_gui(
    task_board: TaskBoard,
    store: TodoTextStore,
    done_store: DoneTextStore,
) -> int:
    """Launch the desktop application and block until it exits."""
    gui_app = QApplication.instance() or QApplication(sys.argv)
    QApplication.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    window = TodoMainWindow(
        task_board=task_board,
        store=store,
        done_store=done_store,
    )
    window.show()
    return gui_app.exec()
