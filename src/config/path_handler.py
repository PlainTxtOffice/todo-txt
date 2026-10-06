"""Static/base repository path constants.

Keep variable path segments (for example project name, date, or user ID)
out of this module and build those at the usage site.
"""

from __future__ import annotations

import sys
from pathlib import Path

NUITKA_BUILD = globals().get("__compiled__", None)
IS_COMPILED = NUITKA_BUILD is not None


def calc_root_dir(
    *,
    is_compiled: bool,
    original_argv0: str | None,
    argv0: str,
) -> Path:
    """Return the base directory that holds writable application files.

    - An interpreted run anchors at the repository root so development
      keeps using repository-relative paths.
    - A compiled run anchors beside the executable so a portable build
      keeps working from any directory it is copied to.
    - The launch path is the only reliable anchor in a compiled build. A
      onefile build unpacks into a temporary directory that is deleted
      on exit, and both `sys.executable` and `__file__` point inside it.
      `__compiled__.containing_dir` is wrong in the other direction: for
      standalone builds it reports the parent of the distribution
      folder, in abbreviated 8.3 form.
    """
    if not is_compiled:
        return Path(__file__).resolve().parents[2]
    launch_path = original_argv0 or argv0
    return Path(launch_path).resolve().parent


ROOT_DIR = calc_root_dir(
    is_compiled=IS_COMPILED,
    original_argv0=getattr(NUITKA_BUILD, "original_argv0", None),
    argv0=sys.argv[0],
)
LOGS_DIR = ROOT_DIR / "logs"
EXPORTS_DIR = ROOT_DIR / "exports"
BACKUPS_DIR = EXPORTS_DIR / "backups"
DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
NOTES_PATH = DATA_DIR / "notes.json"

# Bundled read-only files anchor at the program code rather than
# ROOT_DIR, because a compiled build unpacks them beside its modules
# instead of beside the executable.
ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
APP_ICON_PATH = ASSETS_DIR / "icon.svg"
