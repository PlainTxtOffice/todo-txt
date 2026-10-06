"""Build the task stores from application settings."""

import sys

from src.adapters.recurring.json_state import JsonOccurrences
from src.adapters.recurring.markdown import MarkdownTemplates
from src.adapters.storage.done_text import DoneTextStore
from src.adapters.storage.notes import NotesStore
from src.adapters.storage.todo_text import TodoTextStore
from src.application.recurring import RecurringWorkflow
from src.config.path_handler import DATA_DIR, IS_COMPILED, NOTES_PATH
from src.config.settings import load_settings
from src.domains.premium.access import (
    PreviewEntitlement,
    RecurringEntitlement,
    UnavailableEntitlement,
)
from src.gui.controllers.recurring import RecurringController


def build_default_store() -> TodoTextStore:
    """Create the todo.txt store configured for the application."""
    return TodoTextStore(
        storage_path=load_settings().todo_file,
        notes_store=NotesStore(NOTES_PATH),
    )


def build_default_done_store() -> DoneTextStore:
    """Create the done.txt store configured for the application."""
    return DoneTextStore(storage_path=load_settings().done_file)


def build_recurring_controller(
    entitlement: RecurringEntitlement | None = None,
) -> RecurringController:
    """Construct optional recurrence with default-deny premium access.

    A production subscription adapter can be injected here. Interpreted runs
    may explicitly select --premium-preview; compiled releases ignore that
    switch. No entitlement is persisted in editable application settings.
    """
    if entitlement is None:
        entitlement = (
            PreviewEntitlement()
            if not IS_COMPILED and "--premium-preview" in sys.argv
            else UnavailableEntitlement()
        )
    return RecurringController(
        RecurringWorkflow(
            MarkdownTemplates(),
            JsonOccurrences(
                DATA_DIR / "recurring.json",
                DATA_DIR / "recurring.sqlite3",
            ),
            entitlement,
        ),
    )
