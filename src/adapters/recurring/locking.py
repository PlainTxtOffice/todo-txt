"""Serialize cooperating app instances with a bounded operating-system lock."""

import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def _lock(stream: BinaryIO) -> None:
    """Attempt a non-blocking exclusive file lock."""
    stream.seek(0)
    if sys.platform == "win32":
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(stream: BinaryIO) -> None:
    """Release the operating-system lock held by this open file."""
    stream.seek(0)
    if sys.platform == "win32":
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def lock_state(path: Path, *, timeout: float = 2.0) -> Generator[None]:
    """Lock a read-modify-write operation, timing out instead of guessing.

    A one-byte sidecar stays in place so concurrent processes always lock the
    same file. Locks release on process exit; no stale-lock deletion is needed.
    This coordinates local app instances, not other devices or manual editors.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"\0")
            stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                _lock(stream)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    msg = (
                        "Another app instance is updating recurring state. "
                        "Retry."
                    )
                    raise OSError(msg) from exc
                time.sleep(0.02)
        try:
            yield
        finally:
            _unlock(stream)
