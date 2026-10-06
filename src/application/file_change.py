"""Coordinate archive relocation and settings persistence."""

from pathlib import Path

from src.adapters.archive_files import prepare_archive_transfer
from src.config.settings import SETTINGS_PATH, AppSettings, save_settings
from src.domains.tasks.archive import ArchiveAction


def save_file_settings(
    settings: AppSettings,
    previous: AppSettings,
    *,
    archive_action: ArchiveAction = ArchiveAction.KEEP,
    settings_path: Path = SETTINGS_PATH,
) -> str | None:
    """Save settings and apply an explicitly chosen archive action.

    - Retains the source until the destination and settings save succeed.
    - Restores the destination after a settings failure if still unchanged.
    - Returns a warning when the source cannot safely be removed.
    """
    if archive_action == ArchiveAction.KEEP:
        save_settings(settings, settings_path)
        return None
    source = previous.done_file
    destination = settings.todo_file.parent / "done.txt"
    if previous.done_file_explicit or source.resolve() == destination.resolve():
        msg = "Only a default archive can move to a new folder."
        raise ValueError(msg)
    transfer = prepare_archive_transfer(source, destination, archive_action)
    transfer.write()
    try:
        save_settings(settings, settings_path)
    except (OSError, ValueError, TypeError):
        transfer.restore()
        raise
    return transfer.remove_source()
