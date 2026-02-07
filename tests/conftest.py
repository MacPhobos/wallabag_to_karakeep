"""Shared test fixtures for wallabag_to_karakeep tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wallabag_to_karakeep.models import WallabagEntry


@pytest.fixture()
def full_entry_dict() -> dict[str, Any]:
    """A fully-populated wallabag entry with tags, annotations, metadata."""
    return {
        "id": 100,
        "uid": None,
        "title": "How to Use Docker Compose for Development",
        "url": "https://docs.docker.com/compose/gettingstarted/",
        "content": "<article><h1>Get started</h1><p>Docker Compose is a tool...</p></article>",
        "domain_name": "docs.docker.com",
        "language": "en",
        "mimetype": "text/html",
        "reading_time": 7,
        "preview_picture": "https://docs.docker.com/compose/images/compose.png",
        "http_status": "200",
        "is_archived": 1,
        "archived_at": "2025-02-01 10:00:00",
        "is_starred": 1,
        "starred_at": "2025-01-20 09:00:00",
        "is_public": False,
        "created_at": "2025-01-15 08:30:00",
        "updated_at": "2025-02-01 10:00:00",
        "published_at": "2024-12-01 00:00:00",
        "published_by": ["Docker Inc."],
        "tags": ["docker", "devops", "containers"],
        "annotations": [
            {
                "id": 10,
                "text": "Remember to use volume mounts for hot reload",
                "quote": "Use volume mounts to share code between your host and container",
                "ranges": [
                    {
                        "start": "/article/p[3]",
                        "startOffset": 0,
                        "end": "/article/p[3]",
                        "endOffset": 60,
                    }
                ],
                "created_at": "2025-01-20T09:15:00+0000",
                "updated_at": "2025-01-20T09:15:00+0000",
            }
        ],
        "user_name": "testuser",
        "user_email": "test@example.com",
        "user_id": 1,
    }


@pytest.fixture()
def minimal_entry_dict() -> dict[str, Any]:
    """A minimal wallabag entry with only essential fields."""
    return {
        "url": "https://example.com",
        "is_archived": 0,
        "is_starred": 0,
        "created_at": "2025-01-01 00:00:00",
        "updated_at": "2025-01-01 00:00:00",
        "tags": [],
    }


@pytest.fixture()
def entry_with_object_tags_dict() -> dict[str, Any]:
    """A wallabag entry with API-style tag objects."""
    return {
        "id": 1455,
        "title": "The State of CSS 2025",
        "url": "https://2025.stateofcss.com/en-US/",
        "is_archived": 1,
        "is_starred": 0,
        "created_at": "2025-06-28 16:45:12",
        "updated_at": "2025-07-01 11:00:00",
        "tags": [
            {"id": 10, "label": "css", "slug": "css"},
            {"id": 15, "label": "web-development", "slug": "web-development"},
            {"id": 22, "label": "survey", "slug": "survey"},
        ],
        "annotations": [
            {
                "id": 5,
                "text": "Key finding: CSS nesting adoption at 78%",
                "quote": "CSS nesting has seen the fastest adoption of any CSS feature in recent history",
                "ranges": [
                    {
                        "start": "/article/p[3]",
                        "startOffset": 0,
                        "end": "/article/p[3]",
                        "endOffset": 72,
                    }
                ],
            }
        ],
    }


@pytest.fixture()
def full_entry(full_entry_dict: dict[str, Any]) -> WallabagEntry:
    """Parsed WallabagEntry from full_entry_dict."""
    return WallabagEntry.model_validate(full_entry_dict)


@pytest.fixture()
def minimal_entry(minimal_entry_dict: dict[str, Any]) -> WallabagEntry:
    """Parsed WallabagEntry from minimal_entry_dict."""
    return WallabagEntry.model_validate(minimal_entry_dict)


@pytest.fixture()
def tmp_wallabag_json(
    tmp_path: Path,
    full_entry_dict: dict[str, Any],
    minimal_entry_dict: dict[str, Any],
) -> Path:
    """Write a temporary wallabag JSON export file with two entries."""
    data = [full_entry_dict, minimal_entry_dict]
    path = tmp_path / "wallabag_export.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture()
def tmp_wallabag_wrapped_json(
    tmp_path: Path,
    full_entry_dict: dict[str, Any],
) -> Path:
    """Wallabag JSON with {entries: [...]} wrapper."""
    data = {"entries": [full_entry_dict]}
    path = tmp_path / "wallabag_wrapped.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path
