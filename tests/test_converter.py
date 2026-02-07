"""Tests for wallabag_to_karakeep.converter."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wallabag_to_karakeep.converter import (
    annotations_to_note,
    build_note,
    convert_to_api,
    convert_to_omnivore,
    extract_tag_labels,
    is_valid_url,
    normalize_url,
    parse_wallabag_datetime,
    slugify,
    to_karakeep_iso,
)
from wallabag_to_karakeep.models import WallabagAnnotation, WallabagEntry, WallabagTag


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------


class TestParseWallabagDatetime:
    """Tests for parse_wallabag_datetime."""

    def test_format_a_space_separated(self) -> None:
        """Parse 'YYYY-MM-DD HH:MM:SS' (no timezone, assume UTC)."""
        dt = parse_wallabag_datetime("2025-03-15 09:08:33")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 3
        assert dt.day == 15
        assert dt.hour == 9
        assert dt.minute == 8
        assert dt.second == 33
        assert dt.tzinfo == timezone.utc

    def test_format_b_iso_with_tz(self) -> None:
        """Parse ISO 8601 with timezone offset."""
        dt = parse_wallabag_datetime("2025-01-20T09:15:00+0000")
        assert dt is not None
        assert dt.year == 2025
        assert dt.tzinfo is not None

    def test_format_c_iso_no_tz(self) -> None:
        """Parse ISO 8601 without timezone (assume UTC)."""
        dt = parse_wallabag_datetime("2025-06-15T12:30:00")
        assert dt is not None
        assert dt.tzinfo == timezone.utc

    def test_none_returns_none(self) -> None:
        """None or empty string returns None."""
        assert parse_wallabag_datetime(None) is None
        assert parse_wallabag_datetime("") is None

    def test_invalid_raises(self) -> None:
        """Invalid datetime string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse datetime"):
            parse_wallabag_datetime("not-a-date")

    def test_whitespace_stripped(self) -> None:
        """Leading/trailing whitespace is handled."""
        dt = parse_wallabag_datetime("  2025-01-01 00:00:00  ")
        assert dt is not None
        assert dt.year == 2025


class TestToKarakeepIso:
    """Tests for to_karakeep_iso."""

    def test_basic_conversion(self) -> None:
        """UTC datetime formats to ISO 8601 with .000Z suffix."""
        dt = datetime(2025, 3, 15, 9, 8, 33, tzinfo=timezone.utc)
        assert to_karakeep_iso(dt) == "2025-03-15T09:08:33.000Z"

    def test_none_returns_empty(self) -> None:
        """None returns empty string."""
        assert to_karakeep_iso(None) == ""


# ---------------------------------------------------------------------------
# Tag helpers
# ---------------------------------------------------------------------------


class TestExtractTagLabels:
    """Tests for extract_tag_labels."""

    def test_string_tags(self) -> None:
        """Extract labels from string array."""
        tags: list[str | WallabagTag] = ["python", "tutorial"]
        assert extract_tag_labels(tags) == ["python", "tutorial"]

    def test_object_tags(self) -> None:
        """Extract labels from WallabagTag objects."""
        tags: list[str | WallabagTag] = [
            WallabagTag(id=1, label="css", slug="css"),
            WallabagTag(id=2, label="web-dev", slug="web-dev"),
        ]
        assert extract_tag_labels(tags) == ["css", "web-dev"]

    def test_mixed_tags(self) -> None:
        """Handle mix of string and object tags."""
        tags: list[str | WallabagTag] = [
            "python",
            WallabagTag(id=1, label="tutorial", slug="tutorial"),
        ]
        assert extract_tag_labels(tags) == ["python", "tutorial"]

    def test_empty_and_whitespace_stripped(self) -> None:
        """Empty strings and whitespace-only tags are dropped."""
        tags: list[str | WallabagTag] = ["", " ", "valid-tag"]
        assert extract_tag_labels(tags) == ["valid-tag"]

    def test_dedup_preserves_order(self) -> None:
        """Duplicate labels are removed; first occurrence wins."""
        tags: list[str | WallabagTag] = ["tag1", "tag2", "tag1"]
        assert extract_tag_labels(tags) == ["tag1", "tag2"]

    def test_lowercase_mode(self) -> None:
        """Lowercase mode lowercases and deduplicates."""
        tags: list[str | WallabagTag] = ["Python", "PYTHON", "tutorial"]
        result = extract_tag_labels(tags, mode="lowercase")
        assert result == ["python", "tutorial"]

    def test_strip_mode(self) -> None:
        """Strip mode returns empty list."""
        tags: list[str | WallabagTag] = ["python", "tutorial"]
        assert extract_tag_labels(tags, mode="strip") == []


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


class TestIsValidUrl:
    """Tests for is_valid_url."""

    def test_valid_http(self) -> None:
        assert is_valid_url("http://example.com") is True

    def test_valid_https(self) -> None:
        assert is_valid_url("https://example.com/path") is True

    def test_none(self) -> None:
        assert is_valid_url(None) is False

    def test_empty_string(self) -> None:
        assert is_valid_url("") is False

    def test_invalid_scheme(self) -> None:
        assert is_valid_url("ftp://example.com") is False

    def test_no_scheme(self) -> None:
        assert is_valid_url("not-a-valid-url") is False


class TestNormalizeUrl:
    """Tests for normalize_url."""

    def test_removes_tracking_params(self) -> None:
        """UTM and ref parameters are stripped."""
        url = (
            "https://example.com/article?utm_source=twitter&utm_medium=social&real=keep"
        )
        normalized = normalize_url(url)
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized
        assert "real=keep" in normalized

    def test_lowercase_scheme_and_host(self) -> None:
        """Scheme and netloc are lowercased."""
        assert normalize_url("HTTPS://EXAMPLE.COM/Path") == "https://example.com/Path"

    def test_trailing_slash_stripped(self) -> None:
        """Trailing slash is removed."""
        assert normalize_url("https://example.com/") == "https://example.com"

    def test_preserves_path(self) -> None:
        """Path component is preserved unchanged."""
        url = "https://example.com/some/path"
        assert normalize_url(url) == url


# ---------------------------------------------------------------------------
# Note/annotation helpers
# ---------------------------------------------------------------------------


class TestAnnotationsToNote:
    """Tests for annotations_to_note."""

    def test_empty_annotations(self) -> None:
        """Empty or None annotations return empty string."""
        assert annotations_to_note(None) == ""
        assert annotations_to_note([]) == ""

    def test_single_annotation(self) -> None:
        """Single annotation with quote and text."""
        ann = WallabagAnnotation(
            quote="Highlighted text",
            text="My note about it",
        )
        result = annotations_to_note([ann])
        assert "> Highlighted text" in result
        assert "Note: My note about it" in result

    def test_quote_only(self) -> None:
        """Annotation with quote but no text."""
        ann = WallabagAnnotation(quote="Just a highlight")
        result = annotations_to_note([ann])
        assert "> Just a highlight" in result
        assert "Note:" not in result

    def test_empty_annotation_skipped(self) -> None:
        """Annotation with empty quote and text produces nothing."""
        ann = WallabagAnnotation(quote="", text="")
        assert annotations_to_note([ann]) == ""


class TestBuildNote:
    """Tests for build_note."""

    def test_full_entry_note(self, full_entry: WallabagEntry) -> None:
        """Full entry produces note with annotations and metadata."""
        note = build_note(full_entry)
        # Should contain annotation
        assert "Use volume mounts" in note
        assert "Remember to use volume mounts" in note
        # Should contain metadata
        assert "Author: Docker Inc." in note
        assert "Published: 2024-12-01 00:00:00" in note
        assert "Language: en" in note
        # Sections separated by ---
        assert "---" in note

    def test_minimal_entry_note(self, minimal_entry: WallabagEntry) -> None:
        """Minimal entry produces empty note."""
        assert build_note(minimal_entry) == ""

    def test_metadata_only(self) -> None:
        """Entry with metadata but no annotations."""
        entry = WallabagEntry(
            url="https://example.com",
            published_by=["Author Name"],
            language="fr",
            tags=[],
        )
        note = build_note(entry)
        assert "Author: Author Name" in note
        assert "Language: fr" in note
        assert "---" not in note  # Only one section, no separator


# ---------------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    """Tests for slugify."""

    def test_basic(self) -> None:
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self) -> None:
        assert slugify("Python's Guide!") == "pythons-guide"

    def test_truncation(self) -> None:
        """Slug is truncated to 80 characters."""
        long_title = "a" * 200
        assert len(slugify(long_title)) <= 80


# ---------------------------------------------------------------------------
# convert_to_omnivore
# ---------------------------------------------------------------------------


class TestConvertToOmnivore:
    """Tests for convert_to_omnivore."""

    def test_full_entry(self, full_entry: WallabagEntry) -> None:
        """Full entry converts to Omnivore format."""
        result = convert_to_omnivore(full_entry)
        assert result is not None
        assert result.id == "wb-100"
        assert result.title == "How to Use Docker Compose for Development"
        assert result.url == "https://docs.docker.com/compose/gettingstarted/"
        assert result.state == "Archived"
        assert result.labels == ["docker", "devops", "containers"]
        assert result.savedAt == "2025-01-15T08:30:00.000Z"
        assert result.slug != ""

    def test_minimal_entry(self, minimal_entry: WallabagEntry) -> None:
        """Minimal entry converts with defaults."""
        result = convert_to_omnivore(minimal_entry)
        assert result is not None
        assert result.title == "https://example.com"  # URL fallback
        assert result.state == "Active"
        assert result.labels == []

    def test_null_url_returns_none(self) -> None:
        """Entry with no URL returns None."""
        entry = WallabagEntry(url=None, tags=[])
        assert convert_to_omnivore(entry) is None

    def test_invalid_url_returns_none(self) -> None:
        """Entry with invalid URL returns None."""
        entry = WallabagEntry(url="not-a-url", tags=[])
        assert convert_to_omnivore(entry) is None

    def test_lowercase_tags(self, full_entry: WallabagEntry) -> None:
        """Lowercase tag mode lowercases all labels."""
        result = convert_to_omnivore(full_entry, tags_mode="lowercase")
        assert result is not None
        assert all(lb == lb.lower() for lb in result.labels)


# ---------------------------------------------------------------------------
# convert_to_api
# ---------------------------------------------------------------------------


class TestConvertToApi:
    """Tests for convert_to_api."""

    def test_full_entry(self, full_entry: WallabagEntry) -> None:
        """Full entry converts to API payload."""
        result = convert_to_api(full_entry)
        assert result is not None
        bookmark_req, tag_req = result
        assert bookmark_req.url == "https://docs.docker.com/compose/gettingstarted/"
        assert bookmark_req.archived is True
        assert bookmark_req.favourited is True
        assert bookmark_req.type == "link"
        assert bookmark_req.source == "import"
        assert bookmark_req.createdAt == "2025-01-15T08:30:00.000Z"
        assert bookmark_req.note is not None
        assert "Use volume mounts" in bookmark_req.note

        assert tag_req is not None
        assert len(tag_req.tags) == 3
        assert tag_req.tags[0].tagName == "docker"

    def test_minimal_entry(self, minimal_entry: WallabagEntry) -> None:
        """Minimal entry converts without note or tags."""
        result = convert_to_api(minimal_entry)
        assert result is not None
        bookmark_req, tag_req = result
        assert bookmark_req.archived is False
        assert bookmark_req.favourited is False
        assert bookmark_req.note is None
        assert tag_req is None

    def test_invalid_url_returns_none(self) -> None:
        """Entry with invalid URL returns None."""
        entry = WallabagEntry(url="bad", tags=[])
        assert convert_to_api(entry) is None

    def test_title_truncation(self) -> None:
        """Long title is truncated to 1000 characters."""
        entry = WallabagEntry(
            url="https://example.com",
            title="A" * 1500,
            tags=[],
        )
        result = convert_to_api(entry)
        assert result is not None
        bookmark_req, _ = result
        assert bookmark_req.title is not None
        assert len(bookmark_req.title) == 1000

    def test_note_truncation(self) -> None:
        """Note exceeding max_note_length is truncated."""
        entry = WallabagEntry(
            url="https://example.com",
            published_by=["A" * 6000],
            tags=[],
        )
        result = convert_to_api(entry, max_note_length=100)
        assert result is not None
        bookmark_req, _ = result
        assert bookmark_req.note is not None
        assert bookmark_req.note.endswith("...")
        assert len(bookmark_req.note) <= 104  # 100 + "..."

    def test_no_notes_mode(self, full_entry: WallabagEntry) -> None:
        """Notes disabled returns None for note field."""
        result = convert_to_api(full_entry, include_notes=False)
        assert result is not None
        bookmark_req, _ = result
        assert bookmark_req.note is None
