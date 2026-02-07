"""Convert wallabag entries to Karakeep-compatible formats.

Provides two conversion targets:
- Omnivore JSON (for web UI import via Strategy B)
- Karakeep API payload (for direct push via Strategy A)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from wallabag_to_karakeep.models import (
    KarakeepAttachTagsRequest,
    KarakeepCreateBookmarkRequest,
    KarakeepTagAttachment,
    OmnivoreBookmark,
    WallabagAnnotation,
    WallabagEntry,
    WallabagTag,
)

# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

WALLABAG_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
    "%Y-%m-%d %H:%M:%S",  # Space-separated, no TZ (assume UTC)
    "%Y-%m-%dT%H:%M:%S",  # ISO 8601 without timezone
]


def parse_wallabag_datetime(value: str | None) -> datetime | None:
    """Parse a wallabag datetime string into a timezone-aware datetime.

    Supports both ``2025-03-15 09:08:33`` (no TZ, assumed UTC) and
    ``2025-03-15T09:08:33+0000`` (ISO 8601 with TZ).

    Returns ``None`` if *value* is falsy.  Raises ``ValueError`` if *value*
    cannot be parsed by any known format.
    """
    if not value:
        return None
    for fmt in WALLABAG_FORMATS:
        try:
            dt = datetime.strptime(value.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {value!r}")


def to_karakeep_iso(dt: datetime | None) -> str:
    """Format a datetime as ISO 8601 with milliseconds and ``Z`` suffix."""
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# ---------------------------------------------------------------------------
# Tag helpers
# ---------------------------------------------------------------------------


def extract_tag_labels(
    tags: list[str | WallabagTag],
    mode: str = "preserve",
) -> list[str]:
    """Extract tag label strings from wallabag's dual tag format.

    Handles both string arrays (full export) and object arrays (API export).

    Args:
        tags: Raw tag list from wallabag entry.
        mode: ``"preserve"`` keeps original case, ``"lowercase"`` lowercases,
              ``"strip"`` returns an empty list.

    Returns:
        Deduplicated list of non-empty tag labels.
    """
    if mode == "strip":
        return []

    labels: list[str] = []
    for tag in tags:
        if isinstance(tag, str):
            label = tag.strip()
        elif isinstance(tag, WallabagTag):
            label = tag.label.strip()
        elif isinstance(tag, dict):
            label = str(tag.get("label", tag.get("slug", ""))).strip()
        else:
            continue
        if label:
            labels.append(label)

    if mode == "lowercase":
        labels = [lb.lower() for lb in labels]

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for lb in labels:
        if lb not in seen:
            seen.add(lb)
            unique.append(lb)
    return unique


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "source",
    }
)


def is_valid_url(url: str | None) -> bool:
    """Return ``True`` if *url* is a valid HTTP(S) URL."""
    if not url:
        return False
    try:
        result = urlparse(url)
        return bool(result.scheme in ("http", "https") and result.netloc)
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication.

    Removes tracking parameters (utm_*, ref, source), lowercases
    scheme/netloc, and strips trailing slashes.
    """
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    parsed = urlparse(url.strip().rstrip("/"))
    params = parse_qs(parsed.query)
    clean_params = {
        k: v for k, v in params.items() if k.lower() not in _TRACKING_PARAMS
    }
    clean_query = urlencode(clean_params, doseq=True)
    return urlunparse(
        parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            query=clean_query,
        )
    )


# ---------------------------------------------------------------------------
# Note/annotation helpers
# ---------------------------------------------------------------------------


def annotations_to_note(annotations: list[WallabagAnnotation] | None) -> str:
    """Convert wallabag annotations to a plain-text note string.

    Each annotation is rendered as a blockquote (the highlighted text)
    followed by the user's note.
    """
    if not annotations:
        return ""

    parts: list[str] = []
    for ann in annotations:
        quote = ann.quote.strip() if ann.quote else ""
        text = ann.text.strip() if ann.text else ""
        if quote:
            parts.append(f"> {quote}")
        if text:
            parts.append(f"  Note: {text}")
        if quote or text:
            parts.append("")  # blank line separator

    return "\n".join(parts).strip()


def build_note(entry: WallabagEntry) -> str:
    """Assemble the Karakeep ``note`` field from annotations and metadata.

    Sections are separated by horizontal rules (``---``).
    """
    sections: list[str] = []

    # 1. Annotations (highest priority)
    ann_text = annotations_to_note(entry.annotations)
    if ann_text:
        sections.append(ann_text)

    # 2. Metadata
    metadata_lines: list[str] = []
    if entry.published_by:
        authors = ", ".join(entry.published_by)
        metadata_lines.append(f"Author: {authors}")
    if entry.published_at:
        metadata_lines.append(f"Published: {entry.published_at}")
    if entry.language:
        metadata_lines.append(f"Language: {entry.language}")
    if entry.origin_url:
        metadata_lines.append(f"Origin URL: {entry.origin_url}")

    if metadata_lines:
        sections.append("\n".join(metadata_lines))

    return "\n\n---\n\n".join(sections) if sections else ""


# ---------------------------------------------------------------------------
# Slugify helper
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80].strip("-")


# ---------------------------------------------------------------------------
# Conversion functions
# ---------------------------------------------------------------------------


def convert_to_omnivore(
    entry: WallabagEntry,
    tags_mode: str = "preserve",
) -> OmnivoreBookmark | None:
    """Convert a wallabag entry to Omnivore JSON format.

    Returns ``None`` if the entry has an invalid or missing URL.
    """
    if not is_valid_url(entry.url):
        return None

    # Parse timestamp
    dt = parse_wallabag_datetime(entry.created_at)
    saved_at = to_karakeep_iso(dt) if dt else ""

    # Extract tags
    labels = extract_tag_labels(entry.tags, mode=tags_mode)

    # Determine state
    state = "Archived" if entry.is_archived else "Active"

    # Build title (fall back to URL)
    title = entry.title or entry.url or ""

    return OmnivoreBookmark(
        id=f"wb-{entry.id}" if entry.id is not None else f"wb-{hash(entry.url)}",
        title=title,
        url=entry.url,  # type: ignore[arg-type]
        description="",
        savedAt=saved_at,
        slug=slugify(title),
        labels=labels,
        state=state,
    )


def convert_to_api(
    entry: WallabagEntry,
    tags_mode: str = "preserve",
    include_notes: bool = True,
    max_note_length: int = 5000,
) -> tuple[KarakeepCreateBookmarkRequest, KarakeepAttachTagsRequest | None] | None:
    """Convert a wallabag entry to Karakeep API request payloads.

    Returns a ``(bookmark_request, tag_request)`` tuple, or ``None`` if
    the entry is invalid.  ``tag_request`` is ``None`` when there are no
    tags.
    """
    if not is_valid_url(entry.url):
        return None

    # Parse timestamp
    dt = parse_wallabag_datetime(entry.created_at)
    created_at = to_karakeep_iso(dt) if dt else None

    # Build note
    note: str | None = build_note(entry) if include_notes else None
    if note and len(note) > max_note_length:
        note = note[:max_note_length] + "..."
    if not note:
        note = None

    # Build title (truncate to Karakeep's 1000 char limit)
    title = entry.title
    if title and len(title) > 1000:
        title = title[:997] + "..."

    # Create bookmark request
    bookmark_req = KarakeepCreateBookmarkRequest(
        url=entry.url,  # type: ignore[arg-type]
        title=title,
        archived=bool(entry.is_archived),
        favourited=bool(entry.is_starred),
        note=note,
        createdAt=created_at,
    )

    # Create tag request
    labels = extract_tag_labels(entry.tags, mode=tags_mode)
    tag_req: KarakeepAttachTagsRequest | None = None
    if labels:
        tag_req = KarakeepAttachTagsRequest(
            tags=[KarakeepTagAttachment(tagName=label) for label in labels]
        )

    return bookmark_req, tag_req
