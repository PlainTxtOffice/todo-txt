"""Translate checkbox templates without importing historical completion."""

import hashlib
import re
from pathlib import Path

from src.domains.recurring.models import Cadence, Template

_DAYS = {
    day.casefold(): day
    for day in (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )
}
_CHECKBOX = re.compile(r"^\s*[-*+]\s+\[[ xX]\]\s*(.*?)\s*$")
_IDENTIFIER = re.compile(r"\s*<!--\s*recurring-id:\s*([\w-]+)\s*-->\s*$")


def parse_templates(text: str, cadence: Cadence) -> list[Template]:
    """Parse named Markdown checkboxes, optional IDs, and weekday headings.

    Ignore YAML front matter, empty placeholders, and checkbox checked state.
    Explicit IDs must be unique within a cadence; implicit IDs use normalized
    title and cadence, so renames intentionally create a new template.
    """
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        end = next(
            (i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"),
            None,
        )
        if end is None:
            msg = "Template front matter must end with ---."
            raise ValueError(msg)
        lines = lines[end + 1 :]
    templates: list[Template] = []
    identifiers: set[str] = set()
    suggested_day = None
    for line in lines:
        if line.lstrip().startswith("#"):
            heading = line.lstrip().lstrip("#").strip().casefold()
            suggested_day = _DAYS.get(heading)
        match = _CHECKBOX.match(line)
        if not match:
            continue
        title = match[1]
        explicit = _IDENTIFIER.search(title)
        if explicit:
            title = title[: explicit.start()].strip()
        if not title:
            continue
        key = (
            explicit[1]
            if explicit
            else hashlib.sha256(
                " ".join(title.casefold().split()).encode("utf-8")
            ).hexdigest()
        )
        identifier = f"{cadence.value}:{key}"
        if identifier in identifiers:
            msg = f"Duplicate recurring template: {title}"
            raise ValueError(msg)
        identifiers.add(identifier)
        templates.append(
            Template(
                identifier,
                title,
                cadence,
                suggested_day if cadence == Cadence.WEEKLY else None,
            )
        )
    return templates


class MarkdownTemplates:
    """Read weekly.md, monthly.md, and quarterly.md from a chosen folder."""

    def load(self, folder: Path) -> list[Template]:
        """Read existing supported files; reject missing or unrelated folders.

        Missing individual cadences are allowed. All parsing finishes before
        occurrence persistence begins, so malformed input cannot partly import.
        """
        if not folder.is_dir():
            msg = "Select an existing recurring template folder."
            raise ValueError(msg)
        templates = []
        found = False
        for cadence in Cadence:
            path = folder / f"{cadence.value}.md"
            if path.is_file():
                found = True
                templates.extend(
                    parse_templates(
                        path.read_text(encoding="utf-8-sig"),
                        cadence,
                    )
                )
        if not found:
            msg = "Folder needs weekly.md, monthly.md, or quarterly.md."
            raise ValueError(msg)
        return templates
