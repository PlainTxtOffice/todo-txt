"""Build the View menu with sort, group, and line display choices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup

from src.domains.tasks.arrangement import GroupBy, SortOrder

if TYPE_CHECKING:
    from collections.abc import Callable
    from enum import StrEnum

    from PySide6.QtWidgets import QMainWindow, QMenu, QMenuBar

    from src.gui.views.root_window.panes.task_view import TaskView

_SORT_LABELS: dict[SortOrder, str] = {
    SortOrder.COMPLETION: "&Completion",
    SortOrder.DUE_DATE: "&Due Date",
    SortOrder.PRIORITY: "&Priority",
    SortOrder.CREATED: "C&reated Date",
    SortOrder.ALPHABETICAL: "&Alphabetical",
    SortOrder.PROJECT: "Pro&ject",
    SortOrder.CONTEXT: "Con&text",
}

_GROUP_LABELS: dict[GroupBy, str] = {
    GroupBy.NONE: "&None",
    GroupBy.COMPLETION: "&Completion",
    GroupBy.DUE_DATE: "&Due Date",
    GroupBy.PRIORITY: "&Priority",
    GroupBy.PROJECT: "Pro&ject",
    GroupBy.CONTEXT: "Con&text",
}


def _add_choice_actions[Choice: StrEnum](
    window: QMainWindow,
    menu: QMenu,
    labels: dict[Choice, str],
    selected: Choice,
    apply_choice: Callable[[Choice], None],
) -> None:
    """Add one checkable action per choice, allowing a single selection."""
    action_group = QActionGroup(window)
    action_group.setExclusive(True)
    for choice, label in labels.items():
        action = QAction(label, window)
        action.setCheckable(True)
        action.setChecked(choice == selected)
        action.triggered.connect(
            lambda _checked, value=choice: apply_choice(value),
        )
        action_group.addAction(action)
        menu.addAction(action)


def build_view_menu(
    window: QMainWindow,
    menu_bar: QMenuBar,
    task_view: TaskView,
) -> QMenu:
    """Create the View menu and wire it to the task list."""
    view_menu = menu_bar.addMenu("&View")
    sort_menu = view_menu.addMenu("&Sort By")
    _add_choice_actions(
        window,
        sort_menu,
        _SORT_LABELS,
        task_view.sort_order,
        task_view.set_sort_order,
    )
    group_menu = view_menu.addMenu("&Group By")
    _add_choice_actions(
        window,
        group_menu,
        _GROUP_LABELS,
        task_view.group_by,
        task_view.set_group_by,
    )
    view_menu.addSeparator()
    file_lines_action = QAction("Show todo.txt &Lines", window)
    file_lines_action.setCheckable(True)
    file_lines_action.setChecked(task_view.show_file_lines)
    file_lines_action.toggled.connect(
        lambda checked: task_view.set_show_file_lines(show_file_lines=checked),
    )
    view_menu.addAction(file_lines_action)
    return view_menu
