"""Pydantic v2 models for wallabag, Karakeep, and Omnivore data structures."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Wallabag models (permissive input)
# ---------------------------------------------------------------------------


class WallabagTag(BaseModel):
    """Tag object as returned by wallabag API (not always present in exports)."""

    id: int
    label: str
    slug: str


class WallabagAnnotationRange(BaseModel):
    """XPath range for an annotation highlight."""

    start: str
    startOffset: int  # noqa: N815
    end: str
    endOffset: int  # noqa: N815


class WallabagAnnotation(BaseModel):
    """Annotation/highlight on a wallabag entry."""

    id: int | None = None
    annotator_schema_version: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    text: str = ""
    quote: str = ""
    ranges: list[WallabagAnnotationRange] = Field(default_factory=list)
    user: str | None = None


class WallabagEntry(BaseModel):
    """A single entry from a wallabag JSON export.

    Handles both full export format (export_all group) and API format
    (entries_for_user group). All fields except url are optional to
    handle variations between wallabag versions.
    """

    id: int | None = None
    uid: str | None = None
    title: str | None = None
    url: str | None = None
    content: str | None = None
    domain_name: str | None = None
    language: str | None = None
    mimetype: str | None = None
    reading_time: int = 0
    preview_picture: str | None = None
    http_status: str | None = None
    headers: dict[str, Any] | None = None

    is_archived: int = 0
    archived_at: str | None = None
    is_starred: int = 0
    starred_at: str | None = None
    is_public: bool = False
    is_not_parsed: bool = False

    created_at: str | None = None
    updated_at: str | None = None
    published_at: str | None = None
    published_by: list[str] | None = None

    origin_url: str | None = None
    given_url: str | None = None
    hashed_url: str | None = None
    hashed_given_url: str | None = None

    tags: list[str | WallabagTag] = Field(default_factory=list)
    annotations: list[WallabagAnnotation] = Field(default_factory=list)

    user_name: str | None = None
    user_email: str | None = None
    user_id: int | None = None

    model_config = {"extra": "ignore"}

    @field_validator("is_archived", "is_starred", mode="before")
    @classmethod
    def coerce_int_bool(cls, v: Any) -> int:
        """Coerce boolean or None values to int (0 or 1)."""
        if isinstance(v, bool):
            return int(v)
        return int(v) if v is not None else 0


# ---------------------------------------------------------------------------
# Karakeep models (strict API output)
# ---------------------------------------------------------------------------


class KarakeepCreateBookmarkRequest(BaseModel):
    """POST /api/v1/bookmarks request body for link bookmarks."""

    type: Literal["link"] = "link"
    url: str
    title: str | None = Field(default=None, max_length=1000)
    archived: bool = False
    favourited: bool = False
    note: str | None = None
    summary: str | None = None
    createdAt: str | None = None  # noqa: N815
    source: Literal["import"] = "import"
    crawlPriority: Literal["low", "normal"] = "low"  # noqa: N815


class KarakeepTagAttachment(BaseModel):
    """A single tag to attach to a bookmark."""

    tagName: str  # noqa: N815


class KarakeepAttachTagsRequest(BaseModel):
    """POST /api/v1/bookmarks/{id}/tags request body."""

    tags: list[KarakeepTagAttachment]


class KarakeepBookmarkResponse(BaseModel):
    """Response from POST /api/v1/bookmarks."""

    id: str
    createdAt: str  # noqa: N815
    archived: bool
    favourited: bool
    title: str | None = None
    note: str | None = None
    tags: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


# ---------------------------------------------------------------------------
# Omnivore models (output for Omnivore JSON import)
# ---------------------------------------------------------------------------


class OmnivoreBookmark(BaseModel):
    """A bookmark in Omnivore export format, compatible with Karakeep import."""

    id: str
    title: str
    url: str
    description: str = ""
    savedAt: str  # noqa: N815
    slug: str = ""
    labels: list[str] = Field(default_factory=list)
    state: str = "Active"  # "Active" or "Archived"
