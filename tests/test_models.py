"""Tests for Pydantic v2 models in wallabag_to_karakeep.models."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

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
# WallabagEntry
# ---------------------------------------------------------------------------


class TestWallabagEntry:
    """Tests for WallabagEntry model."""

    def test_full_entry(self, full_entry_dict: dict[str, Any]) -> None:
        """Fully-populated entry parses without error."""
        entry = WallabagEntry.model_validate(full_entry_dict)
        assert entry.id == 100
        assert entry.title == "How to Use Docker Compose for Development"
        assert entry.url == "https://docs.docker.com/compose/gettingstarted/"
        assert entry.is_archived == 1
        assert entry.is_starred == 1
        assert len(entry.tags) == 3
        assert len(entry.annotations) == 1
        assert entry.language == "en"
        assert entry.published_by == ["Docker Inc."]

    def test_minimal_entry(self, minimal_entry_dict: dict[str, Any]) -> None:
        """Minimal entry parses with defaults for optional fields."""
        entry = WallabagEntry.model_validate(minimal_entry_dict)
        assert entry.url == "https://example.com"
        assert entry.title is None
        assert entry.is_archived == 0
        assert entry.is_starred == 0
        assert entry.tags == []
        assert entry.annotations == []
        assert entry.content is None

    def test_bool_coercion(self) -> None:
        """is_archived and is_starred accept booleans and coerce to int."""
        entry = WallabagEntry.model_validate(
            {
                "url": "https://example.com",
                "is_archived": True,
                "is_starred": False,
                "created_at": "2025-01-01 00:00:00",
                "tags": [],
            }
        )
        assert entry.is_archived == 1
        assert entry.is_starred == 0

    def test_none_coercion(self) -> None:
        """is_archived and is_starred accept None and default to 0."""
        entry = WallabagEntry.model_validate(
            {
                "url": "https://example.com",
                "is_archived": None,
                "is_starred": None,
                "tags": [],
            }
        )
        assert entry.is_archived == 0
        assert entry.is_starred == 0

    def test_extra_fields_ignored(self) -> None:
        """Unknown fields are silently ignored (extra='ignore')."""
        entry = WallabagEntry.model_validate(
            {
                "url": "https://example.com",
                "tags": [],
                "some_future_field": "value",
                "another_field": 42,
            }
        )
        assert entry.url == "https://example.com"
        assert not hasattr(entry, "some_future_field")

    def test_object_tags(self, entry_with_object_tags_dict: dict[str, Any]) -> None:
        """API-style tag objects parse into WallabagTag instances."""
        entry = WallabagEntry.model_validate(entry_with_object_tags_dict)
        assert len(entry.tags) == 3
        tag = entry.tags[0]
        assert isinstance(tag, WallabagTag)
        assert tag.label == "css"

    def test_annotations_parse(self, full_entry_dict: dict[str, Any]) -> None:
        """Annotations with ranges parse correctly."""
        entry = WallabagEntry.model_validate(full_entry_dict)
        assert len(entry.annotations) == 1
        ann = entry.annotations[0]
        assert isinstance(ann, WallabagAnnotation)
        assert ann.text == "Remember to use volume mounts for hot reload"
        assert ann.quote.startswith("Use volume mounts")
        assert len(ann.ranges) == 1
        assert ann.ranges[0].startOffset == 0


# ---------------------------------------------------------------------------
# KarakeepCreateBookmarkRequest
# ---------------------------------------------------------------------------


class TestKarakeepCreateBookmarkRequest:
    """Tests for KarakeepCreateBookmarkRequest model."""

    def test_basic_creation(self) -> None:
        """Bookmark request with required fields only."""
        req = KarakeepCreateBookmarkRequest(url="https://example.com")
        assert req.type == "link"
        assert req.url == "https://example.com"
        assert req.source == "import"
        assert req.crawlPriority == "low"
        assert req.archived is False
        assert req.favourited is False

    def test_full_creation(self) -> None:
        """Bookmark request with all fields populated."""
        req = KarakeepCreateBookmarkRequest(
            url="https://example.com/article",
            title="Article Title",
            archived=True,
            favourited=True,
            note="Some notes",
            createdAt="2025-01-01T00:00:00.000Z",
        )
        assert req.title == "Article Title"
        assert req.archived is True
        assert req.favourited is True
        assert req.note == "Some notes"

    def test_title_max_length(self) -> None:
        """Title exceeding 1000 characters raises validation error."""
        with pytest.raises(ValidationError):
            KarakeepCreateBookmarkRequest(
                url="https://example.com",
                title="A" * 1001,
            )


# ---------------------------------------------------------------------------
# KarakeepAttachTagsRequest
# ---------------------------------------------------------------------------


class TestKarakeepAttachTagsRequest:
    """Tests for KarakeepAttachTagsRequest model."""

    def test_tag_attachment(self) -> None:
        """Tag attachment payload serializes correctly."""
        req = KarakeepAttachTagsRequest(
            tags=[
                KarakeepTagAttachment(tagName="python"),
                KarakeepTagAttachment(tagName="tutorial"),
            ]
        )
        assert len(req.tags) == 2
        assert req.tags[0].tagName == "python"

    def test_empty_tags(self) -> None:
        """Empty tag list is valid."""
        req = KarakeepAttachTagsRequest(tags=[])
        assert req.tags == []


# ---------------------------------------------------------------------------
# OmnivoreBookmark
# ---------------------------------------------------------------------------


class TestOmnivoreBookmark:
    """Tests for OmnivoreBookmark model."""

    def test_basic_creation(self) -> None:
        """Omnivore bookmark with required fields."""
        bm = OmnivoreBookmark(
            id="wb-100",
            title="Test Article",
            url="https://example.com",
            savedAt="2025-01-01T00:00:00.000Z",
        )
        assert bm.id == "wb-100"
        assert bm.state == "Active"
        assert bm.labels == []
        assert bm.description == ""

    def test_archived_state(self) -> None:
        """Omnivore bookmark with Archived state."""
        bm = OmnivoreBookmark(
            id="wb-200",
            title="Archived Article",
            url="https://example.com",
            savedAt="2025-01-01T00:00:00.000Z",
            state="Archived",
            labels=["tag1", "tag2"],
        )
        assert bm.state == "Archived"
        assert bm.labels == ["tag1", "tag2"]
