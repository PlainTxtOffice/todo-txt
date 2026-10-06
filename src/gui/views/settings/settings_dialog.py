"""Edit application settings."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from string import ascii_uppercase

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.application.file_change import save_file_settings
from src.config.settings import (
    DateDisplayFormat,
    PrioritySettings,
    load_settings,
)
from src.gui.views.settings.archive_prompt import ask_archive_move


class SettingsDialog(QDialog):
    """Let users edit application settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the settings dialog."""
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._settings = load_settings()
        self.minimum_priority = _build_priority_box(
            self._settings.priority.minimum,
        )
        self.maximum_priority = _build_priority_box(
            self._settings.priority.maximum,
        )
        self.date_display_format = _build_date_display_box(
            self._settings.date_display_format,
        )
        self.todo_file = QLineEdit(str(self._settings.todo_file))
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._select_todo_file)
        todo_file_row = QHBoxLayout()
        todo_file_row.addWidget(self.todo_file)
        todo_file_row.addWidget(browse_button)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Minimum priority", self.minimum_priority)
        form.addRow("Maximum priority", self.maximum_priority)
        form.addRow("Date display", self.date_display_format)
        form.addRow("Todo file", todo_file_row)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        minimum = self.minimum_priority.currentText()
        maximum = self.maximum_priority.currentText()
        try:
            priority = PrioritySettings(minimum=minimum, maximum=maximum)
        except ValueError as exc:
            QMessageBox.warning(self, "Settings", str(exc))
            return
        todo_file_text = self.todo_file.text().strip()
        if not todo_file_text:
            QMessageBox.warning(
                self,
                "Settings",
                "Select a todo.txt file.",
            )
            return
        todo_file = Path(todo_file_text).expanduser().resolve()
        todo_file_changed = todo_file != self._settings.todo_file.resolve()
        if todo_file_changed and not todo_file.is_file():
            QMessageBox.warning(
                self,
                "Settings",
                "Select an existing todo.txt file.",
            )
            return
        archive_action = ask_archive_move(self, self._settings, todo_file)
        if archive_action is None:
            return
        settings = replace(
            self._settings,
            priority=priority,
            todo_file=todo_file,
            date_display_format=DateDisplayFormat(
                self.date_display_format.currentData(),
            ),
        )
        try:
            warning = save_file_settings(
                settings,
                self._settings,
                archive_action=archive_action,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Settings",
                f"Could not save settings: {exc}",
            )
            return
        if warning:
            QMessageBox.warning(self, "Archive Move", warning)
        if todo_file_changed:
            QMessageBox.information(
                self,
                "Settings",
                "Todo Txt will close. Restart it to use the selected file.",
            )
        self.accept()

    def _select_todo_file(self) -> None:
        selected_path = Path(self.todo_file.text())
        initial_directory = (
            selected_path.parent if selected_path.name else selected_path
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select todo.txt",
            str(initial_directory),
            "Text files (*.txt)",
        )
        if file_path:
            self.todo_file.setText(file_path)


def show_settings_dialog(parent: QWidget | None = None) -> bool:
    """Open the application settings dialog."""
    dialog = SettingsDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted


def _build_priority_box(selected_value: str) -> QComboBox:
    box = QComboBox()
    box.addItems(list(ascii_uppercase))
    box.setCurrentText(selected_value)
    return box


def _build_date_display_box(
    selected_value: DateDisplayFormat,
) -> QComboBox:
    box = QComboBox()
    box.addItem("2026-01-14", DateDisplayFormat.ISO.value)
    box.addItem(
        "Wed, Jan 14, 2026",
        DateDisplayFormat.WEEKDAY_SHORT.value,
    )
    box.setCurrentIndex(box.findData(selected_value.value))
    return box
