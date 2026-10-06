"""Apply byte-preserving archive writes and rollback operations."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.domains.tasks.archive import ArchiveAction


def replace_archive(path: Path, contents: bytes, expected: bytes) -> None:
    """Atomically replace an archive unless it changed during preparation."""
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(contents)
        if path.read_bytes() != expected:
            msg = f"Archive changed outside the application: {path}"
            raise OSError(msg)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def merge_archives(existing: bytes, incoming: bytes) -> bytes:
    """Append archive bytes, retaining duplicates and a line boundary."""
    if not existing or not incoming or existing.endswith((b"\n", b"\r")):
        return existing + incoming
    newline = b"\r\n" if b"\r\n" in existing else b"\n"
    return existing + newline + incoming


def write_archive(path: Path, contents: bytes, original: bytes | None) -> None:
    """Create exclusively or replace an unchanged existing archive."""
    if original is not None:
        replace_archive(path, contents, original)
        return
    target = path.open("xb")
    try:
        with target:
            target.write(contents)
    except OSError:
        path.unlink()
        raise


def restore_archive(
    path: Path,
    written: bytes,
    original: bytes | None,
) -> None:
    """Restore destination contents after a failed settings save."""
    if original is not None:
        replace_archive(path, original, written)
    elif path.read_bytes() == written:
        path.unlink()
    else:
        msg = f"Archive changed; retained it for review: {path}"
        raise OSError(msg)


@dataclass(frozen=True)
class ArchiveTransfer:
    """Retain the byte snapshots needed to write or undo a relocation."""

    source: Path
    destination: Path
    incoming: bytes
    original: bytes | None
    contents: bytes

    def write(self) -> None:
        """Write the destination only if the prepared revision still matches."""
        write_archive(self.destination, self.contents, self.original)

    def restore(self) -> None:
        """Undo the destination write if no other writer has changed it."""
        restore_archive(self.destination, self.contents, self.original)

    def remove_source(self) -> str | None:
        """Remove an unchanged source, returning a warning if it must remain."""
        try:
            if self.source.read_bytes() != self.incoming:
                return (
                    "Settings saved, but the old archive changed; "
                    f"retained {self.source}."
                )
            self.source.unlink()
        except OSError as exc:
            return (
                "Settings saved, but the old archive remains at "
                f"{self.source}: {exc}"
            )
        return None


def prepare_archive_transfer(
    source: Path,
    destination: Path,
    action: ArchiveAction,
) -> ArchiveTransfer:
    """Read relocation snapshots and prepare the requested destination bytes."""
    incoming = source.read_bytes()
    original = (
        destination.read_bytes()
        if action in (ArchiveAction.MERGE, ArchiveAction.OVERWRITE)
        else None
    )
    contents = (
        merge_archives(original or b"", incoming)
        if action == ArchiveAction.MERGE
        else incoming
    )
    return ArchiveTransfer(source, destination, incoming, original, contents)
