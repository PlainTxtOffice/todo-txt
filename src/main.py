"""Launch the Todo Txt desktop application."""

from __future__ import annotations

import logging

from src.bootstrap import build_default_done_store, build_default_store
from src.config.logging.log_config import configure_logging
from src.domains.tasks.models import TaskBoard
from src.gui.app import run_gui

logger = logging.getLogger(__name__)


def main() -> int:
    """Configure startup dependencies and launch the GUI."""
    configure_logging(project_name="todo_txt")
    logger.info("Starting Todo Txt application")
    store = build_default_store()
    done_store = build_default_done_store()
    task_board = TaskBoard(todos=store.load_todos())
    return run_gui(task_board=task_board, store=store, done_store=done_store)


if __name__ == "__main__":
    raise SystemExit(main())
