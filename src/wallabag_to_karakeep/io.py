"""Read wallabag JSON exports and write Karakeep-compatible output files.

Handles two wallabag export shapes:
- A bare JSON array of entry objects: ``[{...}, {...}]``
- A wrapper object with an ``entries`` key: ``{"entries": [{...}, {...}]}``

Provides URL-based and wallabag-id-based deduplication.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from wallabag_to_karakeep.converter import normalize_url
from wallabag_to_karakeep.models import WallabagEntry

logger = logging.getLogger(__name__)


def read_wallabag_json(path: Path) -> list[WallabagEntry]:
    """Read and parse a wallabag JSON export file.

    Accepts both a top-level array and a wrapper ``{"entries": [...]}``.
    Invalid entries are logged and skipped rather than causing a failure.

    Args:
        path: Path to the wallabag JSON file.

    Returns:
        List of validated ``WallabagEntry`` objects.

    Raises:
        FileNotFoundError: If *path* does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    raw_text = path.read_text(encoding="utf-8")
    data: Any = json.loads(raw_text)

    # Accept both bare array and {entries: [...]} wrapper
    if isinstance(data, dict) and "entries" in data:
        raw_entries: list[dict[str, Any]] = data["entries"]
    elif isinstance(data, list):
        raw_entries = data
    else:
        raise ValueError(
            f"Unexpected JSON structure in {path}: "
            "expected a list or an object with an 'entries' key."
        )

    entries: list[WallabagEntry] = []
    for idx, raw in enumerate(raw_entries):
        try:
            entries.append(WallabagEntry.model_validate(raw))
        except ValidationError as exc:
            logger.warning("Skipping entry %d: validation error: %s", idx, exc)

    return entries


def write_json(data: list[dict[str, Any]], path: Path) -> None:
    """Write a list of dicts as pretty-printed JSON with UTF-8 encoding.

    Args:
        data: Serializable list to write.
        path: Destination file path (parent dirs are created automatically).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def deduplicate_entries(
    entries: list[WallabagEntry],
    mode: str = "url",
) -> list[WallabagEntry]:
    """Remove duplicate entries according to *mode*.

    Args:
        entries: Input entries.
        mode: One of ``"url"`` (normalize and dedup by URL), ``"wallabag-id"``
              (dedup by wallabag ``id`` field), or ``"none"`` (no dedup).

    Returns:
        Deduplicated list preserving original order.
    """
    if mode == "none":
        return entries

    seen: set[str] = set()
    unique: list[WallabagEntry] = []

    for entry in entries:
        if mode == "url":
            if not entry.url:
                continue
            key = normalize_url(entry.url)
        elif mode == "wallabag-id":
            key = str(entry.id) if entry.id is not None else ""
            if not key:
                # No wallabag id; keep the entry
                unique.append(entry)
                continue
        else:
            # Unknown mode, no dedup
            unique.append(entry)
            continue

        if key not in seen:
            seen.add(key)
            unique.append(entry)
        else:
            logger.debug("Duplicate entry skipped (mode=%s): %s", mode, key)

    return unique
