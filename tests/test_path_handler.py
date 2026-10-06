"""Test base-path resolution for development and compiled builds."""

from __future__ import annotations

from pathlib import Path

from src.config.path_handler import calc_root_dir

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_development_run_anchors_paths_at_repository_root() -> None:
    """An interpreted run should keep using repository-relative paths."""
    root = calc_root_dir(
        is_compiled=False,
        original_argv0=None,
        argv0="C:/python/python.exe",
    )

    assert root == REPO_ROOT


def test_compiled_run_prefers_the_original_launch_path() -> None:
    """Nuitka reports the launch path it was started from; prefer it."""
    root = calc_root_dir(
        is_compiled=True,
        original_argv0="D:/portable/TodoTxt.exe",
        argv0="C:/elsewhere/TodoTxt.exe",
    )

    assert root == Path("D:/portable")


def test_compiled_run_without_an_original_launch_path_uses_argv() -> None:
    """Older Nuitka releases omit original_argv0; argv still names it."""
    root = calc_root_dir(
        is_compiled=True,
        original_argv0=None,
        argv0="D:/portable/TodoTxt.exe",
    )

    assert root == Path("D:/portable")


def test_compiled_run_ignores_a_blank_original_launch_path() -> None:
    """An empty original_argv0 must not resolve to the drive root."""
    root = calc_root_dir(
        is_compiled=True,
        original_argv0="",
        argv0="D:/portable/TodoTxt.exe",
    )

    assert root == Path("D:/portable")


def test_standalone_run_anchors_inside_the_distribution_folder() -> None:
    """The base root holds the executable and is not its parent folder.

    Nuitka's `__compiled__.containing_dir` reports the parent of the
    standalone distribution folder, which would put writable files
    outside the distribution that is meant to be copied.
    """
    root = calc_root_dir(
        is_compiled=True,
        original_argv0="D:/portable/main.dist/TodoTxt.exe",
        argv0="D:/portable/main.dist/TodoTxt.exe",
    )

    assert root == Path("D:/portable/main.dist")
