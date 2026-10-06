"""Collect recurring preferences and present current calendar occurrences."""

from datetime import timedelta

from PySide6.QtCore import QSignalBlocker, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.domains.recurring.models import Occurrence
from src.gui.controllers.recurring import RecurringController

_ERRORS = (OSError, ValueError, TypeError)


def _format_occurrence(occurrence: Occurrence) -> str:
    """Show the complete availability window and optional weekday guidance."""
    end = occurrence.period.end - timedelta(days=1)
    text = (
        f"{occurrence.title} — {occurrence.cadence.value} "
        f"({occurrence.period.start} to {end})"
    )
    if occurrence.suggested_day:
        text += f" · suggested {occurrence.suggested_day}"
    if occurrence.completed_on:
        text += f" · completed {occurrence.completed_on}"
    return text


class RecurringDialog(QDialog):
    """Display weekly, monthly, and quarterly work with explicit opt-in."""

    def __init__(
        self, controller: RecurringController, parent: QWidget | None = None
    ) -> None:
        """Build the view and refresh current work when opened."""
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Recurring Tasks · Premium")
        self.resize(900, 450)
        layout = QVBoxLayout(self)
        self.status = QLabel(controller.workflow.entitlement.description)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        guidance = QLabel(
            "Tasks are available for the entire calendar period. Suggested "
            "weekdays are guidance. Missed periods are not backfilled. "
            "Templates and todo.txt are never changed."
        )
        guidance.setWordWrap(True)
        layout.addWidget(guidance)
        settings = controller.load_preferences()
        self.enabled = QCheckBox("Enable recurring tasks")
        self.enabled.setChecked(settings.recurring_enabled)
        layout.addWidget(self.enabled)
        self.folder = QLineEdit(str(settings.recurring_folder or ""))
        self.folder.setPlaceholderText(
            "Folder containing weekly.md, monthly.md, quarterly.md"
        )
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.folder)
        row.addWidget(browse)
        layout.addLayout(row)
        buttons = QHBoxLayout()
        apply = QPushButton("Apply")
        apply.clicked.connect(self._apply)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        for button in (apply, refresh, close):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.tasks = QListWidget()
        self.tasks.itemChanged.connect(self._complete)
        layout.addWidget(self.tasks)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        self.refresh()
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self.refresh)
        self.finished.connect(self._timer.stop)
        self._timer.start()

    def _browse(self) -> None:
        """Collect a template folder without changing its contents."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select recurring templates",
            self.folder.text(),
        )
        if folder:
            self.folder.setText(folder)

    def _apply(self) -> None:
        """Persist opt-in and refresh after a successful settings save."""
        try:
            self.controller.save_preferences(
                self.folder.text(),
                enabled=self.enabled.isChecked(),
            )
        except (*_ERRORS, PermissionError) as exc:
            QMessageBox.warning(self, "Recurring Tasks", str(exc))
            return
        self.refresh()

    def refresh(self) -> None:
        """Render retained completion; disable stale rows if refresh fails."""
        self.status.setText(self.controller.workflow.entitlement.description)
        try:
            occurrences = self.controller.refresh()
            editable = self.controller.can_edit()
        except (*_ERRORS, PermissionError) as exc:
            self.tasks.setEnabled(False)
            self.summary.setText(f"Could not refresh recurring tasks: {exc}")
            return
        with QSignalBlocker(self.tasks):
            self.tasks.clear()
            self.tasks.setEnabled(True)
            for occurrence in occurrences:
                row = QListWidgetItem(_format_occurrence(occurrence))
                row.setData(Qt.ItemDataRole.UserRole, occurrence.identifier)
                if editable:
                    row.setFlags(row.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                else:
                    row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                row.setCheckState(
                    Qt.CheckState.Checked
                    if occurrence.completed_on
                    else Qt.CheckState.Unchecked
                )
                self.tasks.addItem(row)
        count = sum(
            occurrence.completed_on is not None for occurrence in occurrences
        )
        mode = "" if editable else " · read only; generation disabled"
        self.summary.setText(f"{count} of {len(occurrences)} completed{mode}")

    def _complete(self, row: QListWidgetItem) -> None:
        """Save a checkbox change through the controller and reload state."""
        try:
            self.controller.complete(
                row.data(Qt.ItemDataRole.UserRole),
                completed=row.checkState() == Qt.CheckState.Checked,
            )
        except (*_ERRORS, PermissionError) as exc:
            QMessageBox.warning(self, "Recurring Tasks", str(exc))
        self.refresh()
