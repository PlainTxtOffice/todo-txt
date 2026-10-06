"""Provide the task editor pane."""

from __future__ import annotations

from datetime import date
from string import ascii_uppercase
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QDate,
    QLocale,
    QRect,
    QRectF,
    Qt,
    Signal,
    SignalInstance,
)
from PySide6.QtGui import QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QBoxLayout,
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.views.root_window.dates import qt_date_display_pattern

if TYPE_CHECKING:
    from pathlib import Path

    from PySide6.QtGui import QResizeEvent

    from src.config.settings import DateDisplayFormat, PrioritySettings
    from src.domains.tasks.models import Todo


def _parse_projects(text: str) -> tuple[str, ...]:
    """Split typed projects into names, with or without a leading +.

    A repeated name is kept once, in the order it was first typed.
    """
    names = (word.removeprefix("+") for word in text.split())
    return tuple(dict.fromkeys(name for name in names if name))


class _DueCalendar(QCalendarWidget):
    """Outline today's date in the due-date calendar.

    Today is checked on every paint, so the outline moves to the new
    day after midnight without restarting the program.
    """

    def paintCell(
        self,
        painter: QPainter,
        rect: QRect,
        cell_date: QDate,
    ) -> None:
        """Draw the cell, then ring it when it is today."""
        super().paintCell(painter, rect, cell_date)
        if cell_date != QDate.currentDate():
            return
        # On the selected cell the highlight fill would hide a
        # highlight-colored ring, so use the selected text color there.
        ring_role = (
            QPalette.ColorRole.HighlightedText
            if cell_date == self.selectedDate()
            else QPalette.ColorRole.Highlight
        )
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().color(ring_role), 2))
        painter.drawRoundedRect(QRectF(rect).adjusted(2, 2, -2, -2), 4, 4)
        painter.restore()


def _build_due_calendar() -> QCalendarWidget:
    """Build the due-date calendar with a Today button.

    Today pages the calendar to the current month and year without
    selecting a date, so the due date still changes only on a click.
    Today's date is outlined. The button is skipped if Qt's navigation
    bar is not found.
    """
    calendar = _DueCalendar()
    navigation_bar = calendar.findChild(QWidget, "qt_calendar_navigationbar")
    next_month = calendar.findChild(QToolButton, "qt_calendar_nextmonth")
    if navigation_bar is None or next_month is None:
        return calendar
    layout = navigation_bar.layout()
    if not isinstance(layout, QBoxLayout):
        return calendar
    today_button = QToolButton(navigation_bar)
    today_button.setObjectName("dueCalendarToday")
    today_button.setText("Today")
    today_button.setToolTip("Show the current month")
    today_button.setAutoRaise(True)
    today_button.clicked.connect(calendar.showToday)
    layout.insertWidget(layout.indexOf(next_month), today_button)
    return calendar


class _FilePathLabel(QLabel):
    """Show a file path as plain, muted text rather than a field.

    A long path is shortened in the middle to fit the pane, so it never
    widens the editor; the tooltip keeps the full path.
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._full_text = str(path)
        self.setToolTip(self._full_text)
        self.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        self._show_elided()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Re-shorten the path whenever the available width changes."""
        super().resizeEvent(event)
        self._show_elided()

    def _show_elided(self) -> None:
        self.setText(
            self.fontMetrics().elidedText(
                self._full_text,
                Qt.TextElideMode.ElideMiddle,
                self.width(),
            ),
        )


class TaskEditorPane(QWidget):
    """Collect task details and expose editor commands."""

    new_requested = Signal()
    save_requested = Signal()
    complete_requested = Signal()
    delete_requested = Signal()
    export_requested = Signal()

    def __init__(
        self,
        date_display_format: DateDisplayFormat,
        priority_settings: PrioritySettings,
        todo_file_path: Path,
    ) -> None:
        """Initialize the task editing controls."""
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addLayout(self._build_file_path_row(todo_file_path))
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Task title")
        layout.addWidget(self._title_edit)
        layout.addLayout(self._build_projects_row())
        self._priority_box = QComboBox()
        self.set_priority_range(priority_settings)
        layout.addWidget(self._priority_box)
        layout.addLayout(self._build_due_grid(date_display_format))
        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText("Optional notes")
        layout.addWidget(self._notes_edit)
        self._add_command_buttons(layout)
        layout.addStretch(1)
        self.set_completion_state(is_completed=None)
        self._mark_clean()

    def _build_file_path_row(self, todo_file_path: Path) -> QFormLayout:
        """Build the read-only todo.txt path row."""
        self._file_path_label = _FilePathLabel(todo_file_path)
        self._file_path_label.setObjectName("todoFilePath")
        file_path_form = QFormLayout()
        file_path_form.addRow("File Path", self._file_path_label)
        return file_path_form

    def _build_projects_row(self) -> QHBoxLayout:
        """Build the projects field beside the known-projects dropdown."""
        self._projects_edit = QLineEdit()
        self._projects_edit.setObjectName("taskProjects")
        self._projects_edit.setPlaceholderText("Projects, e.g. +Home +Work")
        self._project_box = QComboBox()
        self._project_box.setObjectName("knownProjects")
        self._project_box.setToolTip("Add a project already in todo.txt")
        self._project_box.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon,
        )
        self._project_box.setMinimumContentsLength(12)
        self._project_box.activated.connect(self._add_chosen_project)
        self.set_known_projects([])
        projects_row = QHBoxLayout()
        projects_row.addWidget(self._projects_edit, 1)
        projects_row.addWidget(self._project_box)
        return projects_row

    def _build_due_grid(
        self,
        date_display_format: DateDisplayFormat,
    ) -> QGridLayout:
        """Build the due-date toggle, date picker, and weekday line."""
        self._has_due_box = QCheckBox("Due date")
        self._due_edit = QDateEdit(QDate.currentDate())
        self._due_edit.setCalendarPopup(True)
        self._due_edit.setCalendarWidget(_build_due_calendar())
        self._due_edit.setEnabled(False)
        self._has_due_box.toggled.connect(self._due_edit.setEnabled)
        self._due_weekday_label = QLabel()
        self._due_weekday_label.setObjectName("dueWeekday")
        self._due_weekday_label.setForegroundRole(
            QPalette.ColorRole.PlaceholderText,
        )
        self._due_weekday_label.setEnabled(False)
        self._has_due_box.toggled.connect(self._due_weekday_label.setEnabled)
        self._due_edit.dateChanged.connect(self._show_due_weekday)
        self._show_due_weekday()
        self.set_date_display_format(date_display_format)
        due_grid = QGridLayout()
        due_grid.addWidget(self._has_due_box, 0, 0)
        due_grid.addWidget(self._due_edit, 0, 1)
        due_grid.addWidget(self._due_weekday_label, 1, 1)
        due_grid.setColumnStretch(1, 1)
        return due_grid

    def _add_command_buttons(self, layout: QVBoxLayout) -> None:
        """Add the task command buttons in display order."""
        layout.addWidget(self._build_button("New", self.new_requested))
        layout.addWidget(self._build_button("Save", self.save_requested))
        self._complete_button = self._build_button(
            "Complete",
            self.complete_requested,
        )
        layout.addWidget(self._complete_button)
        self._delete_button = self._build_button(
            "Delete",
            self.delete_requested,
        )
        layout.addWidget(self._delete_button)
        layout.addWidget(self._build_button("Export", self.export_requested))

    def set_date_display_format(
        self,
        display_format: DateDisplayFormat,
    ) -> None:
        """Apply the selected format to the due-date control.

        The weekday line is hidden when the format already shows the day.
        """
        pattern = qt_date_display_pattern(display_format)
        self._due_edit.setDisplayFormat(pattern)
        self._due_weekday_label.setVisible("ddd" not in pattern)

    def _show_due_weekday(self) -> None:
        """Name the weekday of the date in the due-date control."""
        self._due_weekday_label.setText(
            self._due_edit.locale().dayName(
                self._due_edit.date().dayOfWeek(),
                QLocale.FormatType.LongFormat,
            ),
        )

    def set_known_projects(self, projects: list[str]) -> None:
        """List the projects offered in the Add project dropdown.

        The dropdown is disabled when no task has a project yet.
        """
        self._project_box.clear()
        self._project_box.addItem("Add project", None)
        for project in projects:
            self._project_box.addItem(f"+{project}", project)
        self._project_box.setEnabled(bool(projects))

    def _add_chosen_project(self, index: int) -> None:
        """Append the chosen project unless the task already has it.

        The dropdown returns to Add project so the next choice is
        always a fresh pick.
        """
        project = self._project_box.itemData(index)
        self._project_box.setCurrentIndex(0)
        if not isinstance(project, str):
            return
        text = self._projects_edit.text()
        if project in _parse_projects(text):
            return
        self._projects_edit.setText(f"{text.rstrip()} +{project}".lstrip())

    def set_priority_range(
        self,
        priority_settings: PrioritySettings,
        existing_priority: str | None = None,
    ) -> None:
        """Populate priority choices while preserving an existing value."""
        self._priority_settings = priority_settings
        self._priority_box.clear()
        self._priority_box.addItem("No priority", None)
        minimum_index = ascii_uppercase.index(priority_settings.minimum)
        maximum_index = ascii_uppercase.index(priority_settings.maximum)
        priorities = list(ascii_uppercase[minimum_index : maximum_index + 1])
        if (
            existing_priority is not None
            and existing_priority not in priorities
        ):
            priorities.append(existing_priority)
            priorities.sort()
        for priority in priorities:
            self._priority_box.addItem(f"({priority})", priority)
        self._priority_box.setCurrentIndex(
            self._priority_box.findData(existing_priority),
        )

    def selected_priority(self) -> str | None:
        """Return the priority currently selected in the editor."""
        priority = self._priority_box.currentData()
        return priority if isinstance(priority, str) else None

    def reset(self) -> None:
        """Reset controls for a new task."""
        self._title_edit.clear()
        self._projects_edit.clear()
        self.set_priority_range(self._priority_settings)
        self._show_due_date(None)
        self._notes_edit.clear()
        self.set_completion_state(is_completed=None)
        self._mark_clean()
        self._title_edit.setFocus()

    def show_todo(self, todo: Todo) -> None:
        """Display one task in the editor controls."""
        self._title_edit.setText(todo.title)
        self._projects_edit.setText(
            " ".join(f"+{project}" for project in todo.projects),
        )
        self.set_priority_range(self._priority_settings, todo.priority)
        self._show_due_date(todo.due_on)
        self._notes_edit.setPlainText(todo.notes)
        self.set_completion_state(is_completed=todo.is_completed)
        self._mark_clean()

    def has_unsaved_changes(self) -> bool:
        """Return whether the editor differs from what it last loaded.

        Values are compared rather than edits tracked, so changing a
        field and changing it back leaves nothing to save.
        """
        return self._comparable_values() != self._loaded_values

    def _mark_clean(self) -> None:
        self._loaded_values = self._comparable_values()

    def _comparable_values(
        self,
    ) -> tuple[str, date | None, str, str | None, tuple[str, ...]]:
        """Return editor values as they would be saved.

        Title and notes are stripped because saving strips them.
        """
        title, due_on, notes, priority, projects = self.task_values()
        return title.strip(), due_on, notes.strip(), priority, projects

    def set_completion_state(self, *, is_completed: bool | None) -> None:
        """Match the task commands to the selected task.

        None means no task is selected, which disables Complete and
        Delete; otherwise Complete reads Reopen for a finished task.
        """
        has_task = is_completed is not None
        self._complete_button.setEnabled(has_task)
        self._delete_button.setEnabled(has_task)
        self._complete_button.setText("Reopen" if is_completed else "Complete")

    def _show_due_date(self, due_on: date | None) -> None:
        """Show a due date, or an unticked box starting from today."""
        self._has_due_box.setChecked(due_on is not None)
        if due_on is None:
            self._due_edit.setDate(QDate.currentDate())
        else:
            self._due_edit.setDate(
                QDate(due_on.year, due_on.month, due_on.day),
            )

    def task_values(
        self,
    ) -> tuple[str, date | None, str, str | None, tuple[str, ...]]:
        """Return the task values currently shown in the editor.

        The due date is None unless the Due date box is ticked.
        Projects are split on spaces, and a leading + is optional.
        """
        due_on: date | None = None
        if self._has_due_box.isChecked():
            selected_date = self._due_edit.date()
            due_on = date(
                selected_date.year(),
                selected_date.month(),
                selected_date.day(),
            )
        return (
            self._title_edit.text(),
            due_on,
            self._notes_edit.toPlainText(),
            self.selected_priority(),
            _parse_projects(self._projects_edit.text()),
        )

    def _build_button(
        self,
        label: str,
        signal: SignalInstance,
    ) -> QPushButton:
        button = QPushButton(label)
        button.clicked.connect(signal.emit)
        return button
