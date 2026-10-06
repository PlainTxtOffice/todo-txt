"""Ask how to handle the archive when selecting another todo folder."""

from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from src.config.settings import AppSettings
from src.domains.tasks.archive import ArchiveAction


def _ask_existing_archive(
    parent: QWidget | None,
    source: Path,
    destination: Path,
) -> ArchiveAction | None:
    """Offer merge, confirmed overwrite, existing archive, or cancellation."""
    dialog = QMessageBox(parent)
    dialog.setWindowTitle("Archive Already Exists")
    dialog.setText(
        f"An archive already exists at:\n{destination}\n\n"
        f"Old archive: {source}\n\n"
        "Merge appends the old archive and keeps duplicate lines. "
        "Overwrite replaces the destination contents with the old archive. "
        "Use Existing leaves both files in place.",
    )
    merge = dialog.addButton("Merge", QMessageBox.ButtonRole.AcceptRole)
    overwrite = dialog.addButton(
        "Overwrite...",
        QMessageBox.ButtonRole.DestructiveRole,
    )
    keep = dialog.addButton("Use Existing", QMessageBox.ButtonRole.ActionRole)
    cancel = dialog.addButton(QMessageBox.StandardButton.Cancel)
    dialog.setDefaultButton(cancel)
    dialog.setEscapeButton(cancel)
    dialog.exec()
    clicked = dialog.clickedButton()
    if clicked == merge:
        return ArchiveAction.MERGE
    if clicked == keep:
        return ArchiveAction.KEEP
    if clicked == overwrite:
        answer = QMessageBox.warning(
            parent,
            "Overwrite Completed-Task Archive",
            f"Replace all contents of {destination} with {source}?\n\n"
            "The destination's existing completed tasks will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            return ArchiveAction.OVERWRITE
    return None


def ask_archive_move(
    parent: QWidget | None,
    previous: AppSettings,
    todo_file: Path,
) -> ArchiveAction | None:
    """Return move, leave in place, or cancellation for the archive."""
    source = previous.done_file
    destination = todo_file.parent / "done.txt"
    if (
        previous.done_file_explicit
        or source.resolve() == destination.resolve()
        or not source.is_file()
    ):
        return ArchiveAction.KEEP
    if destination.exists():
        return _ask_existing_archive(parent, source, destination)
    answer = QMessageBox.question(
        parent,
        "Move Completed-Task Archive",
        f"Move your existing completed-task archive to the new folder?\n\n"
        f"From: {source}\nTo: {destination}\n\n"
        "Choose No to leave the old archive in place and use a new done.txt "
        "in the selected folder for future completed tasks.",
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No
        | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Yes,
    )
    if answer == QMessageBox.StandardButton.Cancel:
        return None
    return (
        ArchiveAction.MOVE
        if answer == QMessageBox.StandardButton.Yes
        else ArchiveAction.KEEP
    )
