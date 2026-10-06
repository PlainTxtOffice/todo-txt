"""Display and edit the todo list."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QWidget,
)

from src.adapters.export import format_todo_line
from src.domains.tasks.arrangement import (
    GroupBy,
    SortOrder,
    group_todos,
    sort_todos,
)
from src.domains.tasks.models import TaskEdits
from src.gui.views.root_window.panes.task_editor import TaskEditorPane
from src.gui.views.root_window.task_labels import format_task_label
from src.ports.tasks import TodoFileChangedError

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.domains.tasks.models import Todo
    from src.gui.controllers.preferences import ViewPreferences
    from src.gui.controllers.tasks import TaskController

logger = logging.getLogger(__name__)


def _build_group_header(label: str) -> QListWidgetItem:
    header = QListWidgetItem(label)
    font = header.font()
    font.setBold(True)
    header.setFont(font)
    header.setFlags(Qt.ItemFlag.ItemIsEnabled)
    return header


class TaskView(QWidget):
    """Present the todo list alongside its task editor pane."""

    def __init__(
        self,
        controller: TaskController,
        preferences: ViewPreferences,
    ) -> None:
        """Initialize the task list and editing controls."""
        super().__init__()
        self._controller = controller
        self._preferences = preferences
        settings = preferences.load()
        self._date_display_format = settings.date_display_format
        self.sort_order = settings.sort_order
        self.group_by = settings.group_by
        self.show_file_lines = settings.show_file_lines
        self._selected_id: str | None = None
        layout = QHBoxLayout(self)
        self.todo_list = QListWidget()
        # Wrap long rows at the pane edge for display only; each item's
        # text stays the full, unbroken todo.txt line.
        self.todo_list.setWordWrap(True)
        self.todo_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.todo_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self.todo_list.currentItemChanged.connect(self._select_task)
        self.todo_list.itemChanged.connect(self._toggle_task)
        layout.addWidget(self.todo_list, 3)
        self.task_editor = TaskEditorPane(
            self._date_display_format,
            settings.priority,
            controller.storage_path,
        )
        self.task_editor.new_requested.connect(self.new_task)
        self.task_editor.save_requested.connect(self.save_task)
        self.task_editor.complete_requested.connect(self.complete_selected)
        self.task_editor.delete_requested.connect(self.delete_selected)
        self.task_editor.export_requested.connect(self.export_tasks)
        layout.addWidget(self.task_editor, 2)
        self.refresh_list()

    def refresh_list(self, focus_id: str | None = None) -> None:
        """Rebuild the task list from domain state.

        Tasks follow the selected sort order, and a bold header row
        precedes each group when a grouping is selected. The editor's
        project choices are refreshed to match the tasks. The scroll
        position survives the rebuild, and the task named by
        ``focus_id`` is scrolled into view if it moved off screen.
        """
        self.task_editor.set_known_projects(self._controller.list_projects())
        scroll_bar = self.todo_list.verticalScrollBar()
        scroll_position = scroll_bar.value()
        with QSignalBlocker(self.todo_list):
            self.todo_list.clear()
            todos = sort_todos(
                self._controller.list_todos(),
                self.sort_order,
            )
            if self.group_by is GroupBy.NONE:
                for todo in todos:
                    self.todo_list.addItem(self._build_task_entry(todo))
            else:
                today = datetime.now().astimezone().date()
                for group in group_todos(todos, self.group_by, today):
                    self.todo_list.addItem(_build_group_header(group.label))
                    for todo in group.todos:
                        self.todo_list.addItem(self._build_task_entry(todo))
        self.todo_list.doItemsLayout()
        scroll_bar.setValue(scroll_position)
        if focus_id is not None:
            self._scroll_to_task(focus_id)

    def _scroll_to_task(self, identifier: str) -> None:
        for row in range(self.todo_list.count()):
            entry = self.todo_list.item(row)
            if entry.data(Qt.ItemDataRole.UserRole) == identifier:
                self.todo_list.scrollToItem(
                    entry,
                    QListWidget.ScrollHint.EnsureVisible,
                )
                return

    def _build_task_entry(self, todo: Todo) -> QListWidgetItem:
        label = (
            format_todo_line(todo)
            if self.show_file_lines
            else format_task_label(
                todo.title,
                todo.due_on,
                todo.priority,
                self._date_display_format,
            )
        )
        entry = QListWidgetItem(label)
        entry.setData(Qt.ItemDataRole.UserRole, todo.identifier)
        entry.setFlags(entry.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        state = (
            Qt.CheckState.Checked
            if todo.is_completed
            else Qt.CheckState.Unchecked
        )
        entry.setCheckState(state)
        return entry

    def set_sort_order(self, sort_order: SortOrder) -> None:
        """Apply and remember a task list sort order."""
        self.sort_order = sort_order
        self.refresh_list()
        self._write_view_settings()

    def set_group_by(self, group_by: GroupBy) -> None:
        """Apply and remember a task list grouping."""
        self.group_by = group_by
        self.refresh_list()
        self._write_view_settings()

    def set_show_file_lines(self, *, show_file_lines: bool) -> None:
        """Show tasks as todo.txt lines or as formatted labels."""
        self.show_file_lines = show_file_lines
        self.refresh_list()
        self._write_view_settings()

    def _write_view_settings(self) -> None:
        try:
            self._preferences.save(
                self.sort_order,
                self.group_by,
                show_file_lines=self.show_file_lines,
            )
        except (OSError, TypeError, ValueError):
            logger.exception("Could not save view settings")

    def reload_display_settings(self) -> None:
        """Reload presentation settings and refresh the task list."""
        settings = self._preferences.load()
        self._date_display_format = settings.date_display_format
        self.task_editor.set_date_display_format(self._date_display_format)
        self.task_editor.set_priority_range(
            settings.priority,
            self.task_editor.selected_priority(),
        )
        self.refresh_list()

    def new_task(self) -> None:
        """Reset the task editor pane to create a task.

        Unsaved editor changes are resolved first; nothing happens if
        the user cancels.
        """
        if self.resolve_unsaved_changes():
            self._reset_editor()

    def _reset_editor(self) -> None:
        self._selected_id = None
        self.todo_list.clearSelection()
        self.task_editor.reset()

    def resolve_unsaved_changes(self) -> bool:
        """Offer to save editor changes before the editor moves on.

        Returns True when it is safe to continue: there were no changes,
        they were saved, or the user chose to discard them. Returns
        False when the user cancels or the save fails.
        """
        if not self.task_editor.has_unsaved_changes():
            return True
        todo = self._look_todo(self._selected_id)
        name = f'"{todo.title}"' if todo is not None else "the new task"
        answer = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"Save changes to {name}?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self._save_editor()
        return answer == QMessageBox.StandardButton.Discard

    def save_task(self) -> None:
        """Create or update a task from the task editor pane."""
        if self._save_editor():
            self._reset_editor()

    def _save_editor(self) -> bool:
        """Save the editor's task and report whether it reached the file."""
        edits = TaskEdits(*self.task_editor.task_values())
        return self._run_command(
            lambda: self._controller.save_task(self._selected_id, edits),
        )

    def complete_selected(self) -> None:
        """Save editor changes and toggle the selected task's completion."""
        if self._selected_id is None:
            QMessageBox.information(self, "Complete", "Select a task first.")
            return
        identifier = self._selected_id
        edits = TaskEdits(*self.task_editor.task_values())
        if self._run_command(
            lambda: self._controller.complete_task(identifier, edits),
        ):
            self._reset_editor()

    def delete_selected(self) -> None:
        """Delete the selected task."""
        if self._selected_id is None:
            QMessageBox.information(self, "Delete", "Select a task first.")
            return
        identifier = self._selected_id
        if self._run_command(lambda: self._controller.delete_task(identifier)):
            self._reset_editor()

    def export_tasks(self) -> None:
        """Write the current tasks to a selected todo.txt file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export",
            "todo.txt",
            "Text files (*.txt)",
        )
        if file_path:
            try:
                self._controller.export_tasks(Path(file_path))
            except OSError as exc:
                QMessageBox.warning(self, "File Error", str(exc))

    def _select_task(self, current: QListWidgetItem | None) -> None:
        if current is None:
            return
        todo = self._look_todo(current.data(Qt.ItemDataRole.UserRole))
        if todo is None or todo.identifier == self._selected_id:
            return
        if not self.resolve_unsaved_changes():
            self._select_row(self._selected_id)
            return
        self._selected_id = todo.identifier
        self.task_editor.show_todo(todo)
        # A save may have rebuilt the list, dropping the clicked row.
        self._select_row(todo.identifier)

    def _select_row(self, identifier: str | None) -> None:
        """Highlight a task's row without triggering selection handling."""
        with QSignalBlocker(self.todo_list):
            self.todo_list.setCurrentRow(-1)
            self.todo_list.clearSelection()
            for row in range(self.todo_list.count()):
                entry = self.todo_list.item(row)
                if entry.data(Qt.ItemDataRole.UserRole) == identifier:
                    self.todo_list.setCurrentItem(entry)
                    return

    def _toggle_task(self, entry: QListWidgetItem) -> None:
        identifier = entry.data(Qt.ItemDataRole.UserRole)
        if not isinstance(identifier, str):
            return
        is_completed = entry.checkState() == Qt.CheckState.Checked
        succeeded = self._run_command(
            lambda: self._controller.set_completed(
                identifier,
                is_completed=is_completed,
            ),
        )
        if not succeeded:
            self.refresh_list()
        if identifier == self._selected_id:
            todo = self._controller.look_todo(identifier)
            if todo is not None:
                self.task_editor.set_completion_state(
                    is_completed=todo.is_completed,
                )

    def archive_completed(self) -> None:
        """Move completed tasks from todo.txt into done.txt."""
        count = self._controller.completed_count()
        if not count:
            QMessageBox.information(
                self,
                "Archive Completed",
                "There are no completed tasks to archive.",
            )
            return
        if not self._confirm_archive(count):
            return
        if not self._run_command(self._controller.archive_completed):
            return
        if (
            self._selected_id is not None
            and self._look_todo(self._selected_id) is None
        ):
            self._reset_editor()
        self.refresh_list()

    def _confirm_archive(self, count: int) -> bool:
        answer = QMessageBox.question(
            self,
            "Archive Completed",
            f"Move {count} completed task(s) to "
            f"{self._controller.archive_path.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _offer_reload(self) -> None:
        answer = QMessageBox.question(
            self,
            "Todo File Changed",
            "todo.txt changed in another application. Reload it and "
            "discard unsaved Windows changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.reload_tasks()

    def reload_tasks(self) -> None:
        """Reload the shared file and replace current task state."""
        self._controller.reload_tasks()
        self._reset_editor()
        self.refresh_list()

    def _run_command(self, command: Callable[[], str | None]) -> bool:
        """Present command failures and refresh after a successful save."""
        try:
            focus_id = command()
        except TodoFileChangedError:
            self._offer_reload()
            return False
        except ValueError as exc:
            QMessageBox.warning(self, "Validation", str(exc))
            return False
        except OSError as exc:
            QMessageBox.warning(self, "File Error", str(exc))
            return False
        self.refresh_list(focus_id)
        return True

    def _look_todo(self, identifier: object) -> Todo | None:
        if not isinstance(identifier, str):
            return None
        return self._controller.look_todo(identifier)
