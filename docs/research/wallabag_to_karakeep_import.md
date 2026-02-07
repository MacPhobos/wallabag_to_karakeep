# Wallabag to Karakeep Import: Comprehensive Conversion Specification

**Date**: 2026-02-07
**Status**: Research Complete
**Target**: Python 3.12+, pydantic v2

---

## Table of Contents

1. [Part 1: Wallabag JSON Export Format](#part-1-wallabag-json-export-format)
2. [Part 2: Karakeep Import Format](#part-2-karakeep-import-format)
3. [Part 3: Field Mapping Specification](#part-3-field-mapping-specification)
4. [Part 4: Tool Design](#part-4-tool-design)
5. [Part 5: Implementation Plan](#part-5-implementation-plan)
6. [Part 6: Code Skeleton Description](#part-6-code-skeleton-description)
7. [Sources](#sources)

---

## Part 1: Wallabag JSON Export Format

### 1.1 Export Mechanism

Wallabag v2 exports bookmarks as a JSON array of entry objects. The export is
triggered from the web UI via "All articles" then choosing JSON export format.
The serialization uses JMS Serializer with annotation groups `entries_for_user`
and `export_all` defined on the `Entry` entity.

> Source: The Entry entity defines serialization groups `['entries_for_user', 'export_all']`
> on all exported fields.
> -- [wallabag/wallabag Entry.php](https://github.com/wallabag/wallabag/blob/master/src/Entity/Entry.php)

The wallabag config supports export formats including "epub, pdf, txt, csv, and json".
> -- [wallabag/wallabag config.yml](https://github.com/wallabag/wallabag/blob/master/app/config/config.yml)

### 1.2 Complete Field Reference

The following table lists ALL fields present in a wallabag v2 JSON export, derived
from the `Entry.php` entity ORM column definitions and JMS Serializer annotations.

| Field | Type | Nullable | Serialization Group | Description |
|-------|------|----------|---------------------|-------------|
| `id` | integer | No | `entries_for_user`, `export_all` | Primary key |
| `uid` | string(23) | Yes | `entries_for_user`, `export_all` | Unique identifier for public sharing |
| `title` | text | Yes | `entries_for_user`, `export_all` | Article title |
| `url` | text | Yes | `entries_for_user`, `export_all` | Canonical URL of the article |
| `hashed_url` | string(40) | Yes | -- | SHA1 hash of `url` (auto-computed) |
| `origin_url` | text | Yes | `entries_for_user`, `export_all` | Original/source URL if different |
| `given_url` | text | Yes | `entries_for_user`, `export_all` | URL as originally provided by user |
| `hashed_given_url` | string(40) | Yes | -- | SHA1 hash of `given_url` (auto-computed) |
| `content` | text | Yes | `entries_for_user`, `export_all` | Full HTML content of the article |
| `domain_name` | text | Yes | `entries_for_user`, `export_all` | Domain of the article URL |
| `language` | string(20) | Yes | `entries_for_user`, `export_all` | Language code (e.g., `en`, `fr`) |
| `mimetype` | text | Yes | `entries_for_user`, `export_all` | MIME type (e.g., `text/html`) |
| `reading_time` | integer | No (default 0) | `entries_for_user`, `export_all` | Estimated reading time in minutes |
| `preview_picture` | text | Yes | `entries_for_user`, `export_all` | URL of the preview/hero image |
| `http_status` | string(3) | Yes | `entries_for_user`, `export_all` | HTTP status code when fetched |
| `headers` | array | Yes | `entries_for_user`, `export_all` | HTTP response headers (JSON object) |
| `is_archived` | integer (0/1) | No (default 0) | `entries_for_user`, `export_all` | 1 if read/archived, 0 otherwise |
| `archived_at` | datetime | Yes | `entries_for_user`, `export_all` | Timestamp when archived |
| `is_starred` | integer (0/1) | No (default 0) | `entries_for_user`, `export_all` | 1 if starred/favorited, 0 otherwise |
| `starred_at` | datetime | Yes | `entries_for_user`, `export_all` | Timestamp when starred |
| `is_public` | boolean | No | `entries_for_user`, `export_all` | Virtual property: `uid !== null` |
| `is_not_parsed` | boolean | No (default false) | `entries_for_user`, `export_all` | True if content extraction failed |
| `created_at` | datetime | No | `entries_for_user`, `export_all` | When entry was saved to wallabag |
| `updated_at` | datetime | No | `entries_for_user`, `export_all` | When entry was last modified |
| `published_at` | datetime | Yes | `entries_for_user`, `export_all` | Original publication date |
| `published_by` | array | Yes | `entries_for_user`, `export_all` | Author name(s) as JSON array |
| `tags` | array of Tag | No | `entries_for_user`, `export_all` | Associated tags (see 1.3) |
| `annotations` | array of Annotation | No | `entries_for_user`, `export_all` | Highlights/annotations (see 1.4) |
| `user_name` | string | No | `export_all` | Virtual: wallabag username |
| `user_email` | string | No | `export_all` | Virtual: wallabag user email |
| `user_id` | integer | No | `export_all` | Virtual: wallabag user ID |

> NOTE: The `is_archived` and `is_starred` fields are serialized as integers (0 or 1),
> not booleans, despite being stored as booleans internally.
> -- [wallabag Entry.php virtual property annotations](https://github.com/wallabag/wallabag/blob/master/src/Entity/Entry.php)

### 1.3 Tag Object Structure

Each tag in the `tags` array is a JSON object with three fields:

```json
{
  "id": 42,
  "label": "python",
  "slug": "python"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Tag primary key |
| `label` | string | Human-readable tag name |
| `slug` | string | URL-friendly version of label |

> Tags are associated with entries via a ManyToMany relation. The API supports
> adding tags via `/api/entries/{entry}/tags`.
> -- [wallabag API methods documentation](https://doc.wallabag.org/developer/api/methods/)

**IMPORTANT**: In the `export_all` serialization group (used for full JSON export),
the `tags` field is a virtual property that returns an array of **tag label strings**,
not tag objects. When accessed via the API (`entries_for_user` group), tags are
returned as full objects with `id`, `label`, and `slug`.

Implementers should handle BOTH formats:
- API format: `"tags": [{"id": 42, "label": "python", "slug": "python"}]`
- Export format: `"tags": ["python", "programming"]`

### 1.4 Annotation Object Structure

Annotations represent highlights and notes on article content.

```json
{
  "id": 1,
  "annotator_schema_version": "v1.0",
  "created_at": "2024-01-15T10:30:00+0000",
  "updated_at": "2024-01-15T10:30:00+0000",
  "text": "This is my note on the highlight",
  "quote": "The highlighted text passage",
  "ranges": [
    {
      "start": "/div[1]/p[2]",
      "startOffset": 0,
      "end": "/div[1]/p[2]",
      "endOffset": 42
    }
  ],
  "user": "wallabag_user"
}
```

> CAVEAT: Annotations may NOT be included in the JSON export due to a known bug.
> "Annotations aren't exported at all in JSON file" was reported as issue #5160.
> -- [wallabag/wallabag#5160](https://github.com/wallabag/wallabag/issues/5160)

### 1.5 Datetime Format

Wallabag uses the format `"YYYY-MM-DD HH:MM:SS"` or ISO 8601 with timezone
`"YYYY-MM-DDTHH:MM:SS+0000"` depending on the version and field.

Examples observed in the wild:
- `"2017-02-14 17:50:31"` (common in exports)
- `"2024-01-15T10:30:00+0000"` (API responses, annotations)

Implementers MUST handle both formats.

### 1.6 Essential vs Optional Fields

**Essential fields** (always present, needed for meaningful import):
- `url` -- the bookmark URL (the only truly required field)
- `title` -- article title (may be null but always present as key)
- `is_archived` -- read status
- `is_starred` -- favorite status
- `created_at` -- save timestamp
- `updated_at` -- modification timestamp
- `tags` -- tag array (may be empty `[]`)

**Optional fields** (may be null or absent):
- `content`, `domain_name`, `language`, `mimetype`, `reading_time`
- `preview_picture`, `http_status`, `headers`
- `archived_at`, `starred_at`, `published_at`, `published_by`
- `origin_url`, `given_url`, `uid`
- `annotations` (often empty or missing entirely per bug #5160)
- `user_name`, `user_email`, `user_id` (only in `export_all` group)

### 1.7 Synthetic Sample Objects

**Sample 1: A fully-populated archived article with tags**

```json
{
  "id": 2847,
  "uid": null,
  "title": "Understanding Python Decorators: A Complete Guide",
  "url": "https://realpython.com/primer-on-python-decorators/",
  "hashed_url": "sample_hash_123",
  "origin_url": null,
  "given_url": null,
  "hashed_given_url": null,
  "content": "<div class=\"article-body\"><p>Decorators provide a simple syntax for calling higher-order functions...</p></div>",
  "domain_name": "realpython.com",
  "language": "en",
  "mimetype": "text/html",
  "reading_time": 12,
  "preview_picture": "https://realpython.com/images/decorators-hero.jpg",
  "http_status": "200",
  "headers": null,
  "is_archived": 1,
  "archived_at": "2025-03-20 14:22:10",
  "is_starred": 1,
  "starred_at": "2025-03-15 09:10:00",
  "is_public": false,
  "is_not_parsed": false,
  "created_at": "2025-03-15 09:08:33",
  "updated_at": "2025-03-20 14:22:10",
  "published_at": "2024-11-01 00:00:00",
  "published_by": ["Real Python", "Geir Arne Hjelle"],
  "tags": ["python", "programming", "tutorial"],
  "annotations": [],
  "user_name": "myuser",
  "user_email": "user@example.com",
  "user_id": 1
}
```

**Sample 2: A minimal unread article (no tags, no metadata)**

```json
{
  "id": 3102,
  "uid": null,
  "title": null,
  "url": "https://news.ycombinator.com/item?id=39012345",
  "hashed_url": "sample_hash_456",
  "origin_url": null,
  "given_url": "https://news.ycombinator.com/item?id=39012345",
  "hashed_given_url": "sample_hash_456",
  "content": null,
  "domain_name": "news.ycombinator.com",
  "language": null,
  "mimetype": null,
  "reading_time": 0,
  "preview_picture": null,
  "http_status": null,
  "headers": null,
  "is_archived": 0,
  "archived_at": null,
  "is_starred": 0,
  "starred_at": null,
  "is_public": false,
  "is_not_parsed": true,
  "created_at": "2025-06-10 22:15:44",
  "updated_at": "2025-06-10 22:15:44",
  "published_at": null,
  "published_by": null,
  "tags": [],
  "annotations": [],
  "user_name": "myuser",
  "user_email": "user@example.com",
  "user_id": 1
}
```

**Sample 3: An article with rich tags (object format from API)**

```json
{
  "id": 1455,
  "uid": "uid_789",
  "title": "The State of CSS 2025",
  "url": "https://2025.stateofcss.com/en-US/",
  "content": "<article><h1>The State of CSS 2025</h1><p>...</p></article>",
  "domain_name": "2025.stateofcss.com",
  "language": "en",
  "mimetype": "text/html",
  "reading_time": 8,
  "preview_picture": "https://2025.stateofcss.com/og-image.png",
  "http_status": "200",
  "headers": {"content-type": "text/html; charset=utf-8"},
  "is_archived": 1,
  "archived_at": "2025-07-01 11:00:00",
  "is_starred": 0,
  "starred_at": null,
  "is_public": true,
  "created_at": "2025-06-28 16:45:12",
  "updated_at": "2025-07-01 11:00:00",
  "published_at": "2025-06-25 00:00:00",
  "published_by": ["Sacha Greif"],
  "tags": [
    {"id": 10, "label": "css", "slug": "css"},
    {"id": 15, "label": "web-development", "slug": "web-development"},
    {"id": 22, "label": "survey", "slug": "survey"}
  ],
  "annotations": [
    {
      "id": 5,
      "text": "Key finding: CSS nesting adoption at 78%",
      "quote": "CSS nesting has seen the fastest adoption of any CSS feature in recent history",
      "ranges": [{"start": "/article/p[3]", "startOffset": 0, "end": "/article/p[3]", "endOffset": 72}],
      "created_at": "2025-06-29T10:20:00+0000",
      "updated_at": "2025-06-29T10:20:00+0000"
    }
  ],
  "user_name": "myuser",
  "user_email": "user@example.com",
  "user_id": 1
}
```

---

## Part 2: Karakeep Import Format

### 2.1 Overview of Import Paths

Karakeep (formerly known as Hoarder) offers multiple import paths:

| Path | Format | Preserves Tags | Preserves Dates | Preserves Archived |
|------|--------|---------------|-----------------|-------------------|
| Web UI: Netscape HTML | `<!DOCTYPE NETSCAPE-Bookmark-file-1>` | Yes | Yes (`ADD_DATE`) | Yes (via folders) |
| Web UI: Omnivore JSON | JSON array | Yes (`labels`) | Yes (`savedAt`) | Yes (`state`) |
| Web UI: Pocket CSV | CSV | Yes | Yes | Yes |
| REST API: POST | `{"type":"link","url":"..."}` | Via separate call | Yes (`createdAt`) | Yes (`archived`) |
| CLI | `bookmarks add --link` | No | No | No |

> "Titles, tags and addition date will be preserved during the import."
> -- [Karakeep import documentation](https://docs.karakeep.app/using-karakeep/import/)

> "The benefit of importing from the web app (over the CLI) is that Karakeep
> will carry forward your tags, titles, and created-at dates."
> -- [Karakeep import docs](https://docs.karakeep.app/using-karakeep/import/)

### 2.2 Recommended Import Strategy

There are **three viable approaches** for importing wallabag data into Karakeep,
ranked by data fidelity:

**Strategy A: REST API (POST /api/v1/bookmarks) -- BEST fidelity**
- Create each bookmark individually via API
- Can set: `title`, `archived`, `favourited`, `note`, `createdAt`, `source`
- Tags added via separate `POST /api/v1/bookmarks/{id}/tags`
- Allows setting `createdAt` to preserve original wallabag timestamps
- Requires API key and running Karakeep instance
- Most fields preserved, but requires multiple API calls per bookmark

**Strategy B: Omnivore JSON format -- GOOD fidelity, simplest**
- Convert wallabag JSON to Omnivore-compatible JSON
- Upload via web UI import
- Preserves: title, url, tags (labels), creation date (savedAt), archived state
- No API key needed
- Single file upload

**Strategy C: Netscape HTML -- GOOD fidelity, well-tested**
- Convert wallabag JSON to Netscape bookmark HTML
- Upload via web UI import
- Preserves: title, url, tags, creation date, modified date
- Lists/folders preserved in v0.25.0+
- Well-tested path (existing Ruby scripts available)

This specification targets **Strategy A (REST API)** as the primary approach and
**Strategy B (Omnivore JSON)** as a fallback, since the API approach preserves the
most metadata.

### 2.3 Karakeep REST API: Create Bookmark

**Endpoint**: `POST /api/v1/bookmarks`
**Auth**: Bearer token (API key from Settings > API Keys)

> The API base endpoint follows: `https://karakeep.example.com/api/v1/bookmarks`.
> -- [Karakeep API docs](https://docs.karakeep.app/api/karakeep-api/)

**Request body** (for link bookmarks):

```json
{
  "type": "link",
  "url": "https://example.com/article",
  "title": "Article Title",
  "archived": true,
  "favourited": false,
  "note": "My notes about this article",
  "summary": "Brief summary text",
  "createdAt": "2025-03-15T09:08:33.000Z",
  "source": "import",
  "crawlPriority": "low"
}
```

**Request body schema** (from the OpenAPI spec):

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `type` | `"link"` | Yes | -- | Discriminator for link bookmarks |
| `url` | string (URI) | Yes | -- | The bookmark URL |
| `title` | string | No | 1000 | Bookmark title |
| `archived` | boolean | No | -- | Archive/read status |
| `favourited` | boolean | No | -- | Favorite status |
| `note` | string | No | -- | User notes |
| `summary` | string | No | -- | Summary text |
| `createdAt` | string (ISO 8601) | No | -- | Creation timestamp |
| `source` | enum | No | -- | One of: `api`, `web`, `cli`, `mobile`, `extension`, `singlefile`, `rss`, `import` |
| `crawlPriority` | enum | No | -- | `"low"` or `"normal"` |
| `precrawledArchiveId` | string | No | -- | Pre-crawled archive reference |
| `importSessionId` | string | No | -- | Links bookmark to an import session |

> Source: OpenAPI spec at `packages/open-api/karakeep-openapi-spec.json`
> -- [Karakeep OpenAPI spec](https://github.com/karakeep-app/karakeep/blob/main/packages/open-api/karakeep-openapi-spec.json)

**Response** (201 Created):

```json
{
  "id": "bookmark_id_123",
  "createdAt": "2025-03-15T09:08:33.000Z",
  "modifiedAt": null,
  "userId": "user_abc123",
  "archived": true,
  "favourited": false,
  "taggingStatus": "pending",
  "summarizationStatus": null,
  "title": "Article Title",
  "note": "My notes about this article",
  "summary": null,
  "source": "import",
  "tags": [],
  "content": {
    "type": "link",
    "url": "https://example.com/article",
    "title": null,
    "description": null,
    "imageUrl": null,
    "favicon": null,
    "htmlContent": null,
    "crawlStatus": "pending"
  },
  "assets": []
}
```

**Status codes**:
- `201`: Bookmark created successfully
- `200`: Bookmark already exists (same URL)
- `400`: Invalid request

### 2.4 Karakeep REST API: Attach Tags

**Endpoint**: `POST /api/v1/bookmarks/{bookmarkId}/tags`

```json
{
  "tags": [
    {"tagName": "python"},
    {"tagName": "programming"},
    {"tagName": "tutorial"}
  ]
}
```

Each tag object uses `tagName` (string). Tags are created on-the-fly if they
do not already exist.

### 2.5 Karakeep REST API: Update Bookmark

**Endpoint**: `PATCH /api/v1/bookmarks/{bookmarkId}`

As of v0.24.0, nearly all bookmark fields are editable:

> "You can now edit almost all the details of bookmarks -- the URL, summary,
> creation date, everything."
> -- [Karakeep v0.24.0 release notes](https://github.com/karakeep-app/karakeep/discussions/1320)

Updatable fields: `title`, `archived`, `favourited`, `note`, `summary`, `createdAt`.

### 2.6 Omnivore JSON Format (Fallback Import)

The Omnivore JSON format that Karakeep natively imports is an array of objects:

```json
[
  {
    "id": "unique-id-string",
    "title": "Article Title",
    "url": "https://example.com/article",
    "description": "Article description",
    "savedAt": "2025-03-15T09:08:33.000Z",
    "slug": "article-title",
    "labels": ["python", "tutorial"],
    "state": "Active"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `title` | string | Article title |
| `url` | string | Article URL |
| `description` | string | Article description/excerpt |
| `savedAt` | ISO 8601 datetime | When article was saved |
| `slug` | string | URL-friendly title |
| `labels` | string[] | Tag labels |
| `state` | `"Active"` or `"Archived"` | Archive status |

> The `parseOmnivoreBookmark` function reads `bookmark.title`, `bookmark.url`,
> `bookmark.labels`, `bookmark.savedAt`, and `bookmark.State`.
> -- [hoarder-app/hoarder#703](https://github.com/hoarder-app/hoarder/issues/703)

### 2.7 Netscape HTML Format (Alternative Fallback)

```html
<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
  <DT><A HREF="https://example.com/article"
         ADD_DATE="1710493713"
         LAST_MODIFIED="1711015330"
         TAGS="python,tutorial">Article Title</A>
</DL><p>
```

| Attribute | Source | Format |
|-----------|--------|--------|
| `HREF` | wallabag `url` | URL string |
| `ADD_DATE` | wallabag `created_at` | Unix timestamp (seconds) |
| `LAST_MODIFIED` | wallabag `updated_at` | Unix timestamp (seconds) |
| `TAGS` | wallabag `tags` | Comma-separated string |
| Inner text | wallabag `title` | Plain text |

> The Ruby script maps `item['url']`, `Time.parse(item['created_at'])`,
> `Time.parse(item['updated_at'])`, and `item['tags'].join(',')`.
> -- [karakeep-app/karakeep Discussion #581](https://github.com/karakeep-app/karakeep/discussions/581)

### 2.8 Synthetic Karakeep Sample Objects

**Sample 1: API POST request body for a link bookmark**

```json
{
  "type": "link",
  "url": "https://realpython.com/primer-on-python-decorators/",
  "title": "Understanding Python Decorators: A Complete Guide",
  "archived": true,
  "favourited": true,
  "note": "",
  "createdAt": "2025-03-15T09:08:33.000Z",
  "source": "import",
  "crawlPriority": "low"
}
```

**Sample 2: Omnivore-compatible JSON (for web UI import)**

```json
[
  {
    "id": "wb-2847",
    "title": "Understanding Python Decorators: A Complete Guide",
    "url": "https://realpython.com/primer-on-python-decorators/",
    "description": "",
    "savedAt": "2025-03-15T09:08:33.000Z",
    "slug": "understanding-python-decorators",
    "labels": ["python", "programming", "tutorial"],
    "state": "Archived"
  },
  {
    "id": "wb-3102",
    "title": "",
    "url": "https://news.ycombinator.com/item?id=39012345",
    "description": "",
    "savedAt": "2025-06-10T22:15:44.000Z",
    "slug": "hacker-news-39012345",
    "labels": [],
    "state": "Active"
  }
]
```

**Sample 3: Netscape HTML output**

```html
<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Wallabag Export</TITLE>
<H1>Wallabag Export</H1>
<DL><p>
  <DT><A HREF="https://realpython.com/primer-on-python-decorators/"
         ADD_DATE="1710493713"
         LAST_MODIFIED="1711015330"
         TAGS="python,programming,tutorial">Understanding Python Decorators: A Complete Guide</A>
  <DT><A HREF="https://news.ycombinator.com/item?id=39012345"
         ADD_DATE="1718057744"
         LAST_MODIFIED="1718057744"
         TAGS="">https://news.ycombinator.com/item?id=39012345</A>
</DL><p>
```

---

## Part 3: Field Mapping Specification

### 3.1 Direct Field Mapping Table

| # | Wallabag Field | Wallabag Type | Karakeep Field (API) | Karakeep Type | Transform | Notes |
|---|---------------|---------------|---------------------|---------------|-----------|-------|
| 1 | `url` | string | `url` | string (URI) | None | **Required**. Validate URL format |
| 2 | `title` | string/null | `title` | string (max 1000) | Truncate if >1000 chars; use URL as fallback if null | |
| 3 | `is_archived` | int (0/1) | `archived` | boolean | `bool(is_archived)` | |
| 4 | `is_starred` | int (0/1) | `favourited` | boolean | `bool(is_starred)` | |
| 5 | `created_at` | datetime string | `createdAt` | ISO 8601 string | Parse wallabag format, emit ISO 8601 with `Z` suffix | See 3.2 |
| 6 | `tags` | string[] or Tag[] | Tags via POST `.../tags` | `{"tagName": str}[]` | Extract label strings | See 3.3 |
| 7 | `content` | HTML string/null | -- (not directly settable) | -- | Dropped for API import; available via SingleFile endpoint | See 3.6 |
| 8 | `annotations` | Annotation[]/null | `note` | string | Concatenate annotation quotes + text into note | See 3.4 |
| 9 | `preview_picture` | URL string/null | -- | -- | Dropped; Karakeep re-fetches images | |
| 10 | `reading_time` | int | -- | -- | Dropped; Karakeep computes its own | |
| 11 | `language` | string/null | -- | -- | Dropped; no equivalent field | Could be added to note |
| 12 | `domain_name` | string/null | -- | -- | Dropped; Karakeep extracts from URL | |
| 13 | `published_at` | datetime/null | `note` (appended) | string | Append `"Published: {date}"` to note if present | |
| 14 | `published_by` | string[]/null | `note` (appended) | string | Append `"Author: {names}"` to note if present | |
| 15 | `origin_url` | string/null | `note` (appended) | string | Append `"Origin: {url}"` to note if present | |
| 16 | `archived_at` | datetime/null | -- | -- | Dropped; approximated by `archived` boolean | |
| 17 | `starred_at` | datetime/null | -- | -- | Dropped; approximated by `favourited` boolean | |
| 18 | `mimetype` | string/null | -- | -- | Dropped | |
| 19 | `http_status` | string/null | -- | -- | Dropped | |
| 20 | `headers` | object/null | -- | -- | Dropped | |
| 21 | `uid` | string/null | -- | -- | Dropped | |
| 22 | `id` | int | -- | -- | Used for dedup tracking only | |
| 23 | -- | -- | `source` | `"import"` | Always set to `"import"` | |
| 24 | -- | -- | `type` | `"link"` | Always set to `"link"` | |
| 25 | -- | -- | `crawlPriority` | `"low"` | Set to `"low"` to avoid overloading server | |

### 3.2 Timestamp Transforms

Wallabag datetimes appear in two formats:

1. **Format A**: `"2025-03-15 09:08:33"` (space-separated, no timezone)
2. **Format B**: `"2025-03-15T09:08:33+0000"` (ISO 8601 with timezone)

Karakeep expects ISO 8601 with UTC timezone: `"2025-03-15T09:08:33.000Z"`

**Transform logic**:

```python
from datetime import datetime, timezone

WALLABAG_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",     # ISO 8601 with timezone
    "%Y-%m-%d %H:%M:%S",        # Space-separated, no TZ (assume UTC)
    "%Y-%m-%dT%H:%M:%S",        # ISO 8601 without timezone
]

def parse_wallabag_datetime(value: str | None) -> datetime | None:
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

def to_karakeep_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
```

### 3.3 Tag Transforms

Wallabag tags may appear in two formats depending on export method:

**Format 1 (Full export)**: Array of strings
```json
"tags": ["python", "tutorial"]
```

**Format 2 (API export)**: Array of tag objects
```json
"tags": [{"id": 10, "label": "python", "slug": "python"}]
```

**Transform logic**:

```python
def extract_tag_labels(tags: list) -> list[str]:
    labels = []
    for tag in tags:
        if isinstance(tag, str):
            labels.append(tag.strip())
        elif isinstance(tag, dict) and "label" in tag:
            labels.append(tag["label"].strip())
        elif isinstance(tag, dict) and "slug" in tag:
            labels.append(tag["slug"].strip())
    return [label for label in labels if label]
```

**Karakeep tag attachment** (separate API call per bookmark):

```python
def build_tag_payload(labels: list[str]) -> dict:
    return {"tags": [{"tagName": label} for label in labels]}
```

### 3.4 Annotation-to-Note Transform

Since Karakeep does not have an annotations feature equivalent to wallabag,
annotations are converted to a structured note string:

```python
def annotations_to_note(annotations: list[dict] | None) -> str:
    if not annotations:
        return ""

    parts = []
    for ann in annotations:
        quote = ann.get("quote", "").strip()
        text = ann.get("text", "").strip()
        if quote:
            parts.append(f"> {quote}")
        if text:
            parts.append(f"  Note: {text}")
        if quote or text:
            parts.append("")  # blank line separator

    return "\n".join(parts).strip()
```

### 3.5 Building the Note Field

The `note` field in Karakeep is assembled from multiple wallabag fields:

```python
def build_note(entry: dict) -> str:
    sections = []

    # 1. Annotations (highest priority)
    ann_text = annotations_to_note(entry.get("annotations"))
    if ann_text:
        sections.append(ann_text)

    # 2. Metadata
    metadata_lines = []
    if entry.get("published_by"):
        authors = entry["published_by"]
        if isinstance(authors, list):
            authors = ", ".join(authors)
        metadata_lines.append(f"Author: {authors}")

    if entry.get("published_at"):
        metadata_lines.append(f"Published: {entry['published_at']}")

    if entry.get("language"):
        metadata_lines.append(f"Language: {entry['language']}")

    if entry.get("origin_url"):
        metadata_lines.append(f"Origin URL: {entry['origin_url']}")

    if metadata_lines:
        sections.append("\n".join(metadata_lines))

    return "\n\n---\n\n".join(sections) if sections else ""
```

### 3.6 Handling HTML Content

Wallabag stores the full HTML content of articles in the `content` field.
Karakeep's REST API does NOT accept `htmlContent` directly when creating
a bookmark. Instead, Karakeep crawls the URL itself.

> "The workaround uses the SingleFile endpoint at `/api/v1/bookmarks/singlefile`
> with FormData containing: `file` (HTML content as a Blob) and `url`."
> -- [karakeep-app/karakeep#1260](https://github.com/karakeep-app/karakeep/issues/1260)

**Options for content handling**:

1. **Drop content** (default) -- Let Karakeep re-crawl. Works if the original
   URL is still accessible.
2. **SingleFile endpoint** (optional) -- Upload the wallabag HTML content as a
   SingleFile archive. Requires wrapping in a valid HTML document.
3. **Store content in note** (optional) -- For very important articles, append
   a plain-text extract of the content to the note field. Not recommended for
   large articles.

### 3.7 Handling Duplicates

**By URL (primary dedup strategy)**:

```python
def normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
    parsed = urlparse(url.strip().rstrip("/"))
    # Remove tracking parameters
    params = parse_qs(parsed.query)
    tracking_params = {"utm_source", "utm_medium", "utm_campaign",
                       "utm_term", "utm_content", "ref", "source"}
    clean_params = {k: v for k, v in params.items()
                    if k.lower() not in tracking_params}
    clean_query = urlencode(clean_params, doseq=True)
    return urlunparse(parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        query=clean_query,
    ))
```

**Dedup modes**:
- `--dedup=url` (default): Skip entries with duplicate normalized URLs
- `--dedup=none`: Import all entries, let Karakeep handle duplicates (returns 200 instead of 201)
- `--dedup=wallabag-id`: Skip entries with duplicate wallabag `id` fields

### 3.8 Handling Invalid URLs

```python
from urllib.parse import urlparse

def is_valid_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False
```

Entries with invalid URLs are logged and skipped (not silently dropped).

### 3.9 HTML Sanitization and Character Encoding

The wallabag `content` field contains HTML that may include:
- Malformed HTML
- Non-UTF-8 characters
- Embedded scripts/styles

If content is used (e.g., for the note field or SingleFile upload):

```python
import html

def sanitize_for_note(html_content: str, max_length: int = 5000) -> str:
    """Strip HTML tags and limit length for note field."""
    from html.parser import HTMLParser
    from io import StringIO

    class MLStripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.result = StringIO()
        def handle_data(self, d):
            self.result.write(d)
        def get_data(self):
            return self.result.getvalue()

    s = MLStripper()
    s.feed(html_content)
    text = s.get_data().strip()
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text
```

### 3.10 Omnivore JSON Mapping (Fallback Strategy B)

If using the Omnivore JSON import path instead of the API:

| Wallabag Field | Omnivore Field | Transform |
|---------------|---------------|-----------|
| `url` | `url` | Direct |
| `title` | `title` | Use URL as fallback if null |
| `created_at` | `savedAt` | Parse and emit ISO 8601 |
| `tags` (labels) | `labels` | Extract label strings to string array |
| `is_archived` | `state` | `"Archived"` if `is_archived == 1`, else `"Active"` |
| `id` | `id` | Prefix with `"wb-"` to create unique ID |
| `title` (slug) | `slug` | Slugify the title |
| -- | `description` | Empty string (wallabag has no description field) |

---

## Part 4: Tool Design

### 4.1 CLI Interface

```
wallabag-to-karakeep [OPTIONS] COMMAND

Commands:
  convert    Convert wallabag JSON to Karakeep-compatible format
  push       Push bookmarks to a Karakeep instance via API
  validate   Validate a wallabag JSON export file

Options:
  --verbose, -v     Enable verbose logging (repeat for debug: -vv)
  --quiet, -q       Suppress non-error output

Convert options:
  --in PATH          Input wallabag JSON file (required)
  --out PATH         Output file path (required)
  --format FORMAT    Output format: omnivore | netscape | api-json
                     (default: omnivore)
  --dedup MODE       Dedup mode: url | none | wallabag-id (default: url)
  --tags-mode MODE   Tag handling: preserve | lowercase | strip (default: preserve)
  --dry-run          Show conversion plan without writing output
  --include-notes    Include annotations/metadata as notes (default: true)
  --max-note-length  Maximum note length in characters (default: 5000)

Push options:
  --in PATH          Input wallabag JSON file (required)
  --server URL       Karakeep server address (required)
  --api-key KEY      Karakeep API key (required, or env KARAKEEP_API_KEY)
  --dedup MODE       Dedup mode: url | none (default: url)
  --tags-mode MODE   Tag handling: preserve | lowercase | strip (default: preserve)
  --dry-run          Show what would be pushed without making API calls
  --batch-size N     Bookmarks per batch (default: 10)
  --delay SECONDS    Delay between batches (default: 1.0)
  --crawl-priority   Crawl priority: low | normal (default: low)
  --include-notes    Include annotations/metadata as notes (default: true)

Validate options:
  --in PATH          Input wallabag JSON file (required)
```

**Example usage**:

```bash
# Convert wallabag JSON to Omnivore format for web UI import
wallabag-to-karakeep convert \
  --in wallabag-export.json \
  --out karakeep-import.json \
  --format omnivore \
  --tags-mode lowercase

# Push directly to Karakeep via API
wallabag-to-karakeep push \
  --in wallabag-export.json \
  --server https://karakeep.example.com \
  --api-key "your-api-key" \
  --dry-run

# Validate an export file
wallabag-to-karakeep validate --in wallabag-export.json
```

### 4.2 Project Structure

```
wallabag_to_karakeep/
  pyproject.toml
  src/
    wallabag_to_karakeep/
      __init__.py
      main.py                 # CLI entrypoint (click/typer)
      cli.py                  # CLI command definitions
      models/
        __init__.py
        wallabag.py            # Pydantic models for wallabag JSON
        karakeep.py            # Pydantic models for Karakeep API
        omnivore.py            # Pydantic models for Omnivore JSON
      converters/
        __init__.py
        base.py                # Abstract converter interface
        omnivore_converter.py  # Wallabag -> Omnivore JSON
        netscape_converter.py  # Wallabag -> Netscape HTML
        api_converter.py       # Wallabag -> Karakeep API payloads
      transforms/
        __init__.py
        timestamps.py          # Datetime parsing and formatting
        tags.py                # Tag extraction and normalization
        urls.py                # URL validation and normalization
        notes.py               # Annotation/metadata -> note assembly
        html.py                # HTML sanitization utilities
      api/
        __init__.py
        client.py              # Karakeep API client (httpx)
        push.py                # Batch push logic with retry/backoff
      io/
        __init__.py
        reader.py              # Wallabag JSON file reader with validation
        writer.py              # Output file writers (JSON, HTML)
  tests/
    __init__.py
    conftest.py                # Shared fixtures
    fixtures/
      wallabag_full.json       # Full-featured wallabag export sample
      wallabag_minimal.json    # Minimal wallabag export sample
      wallabag_edge_cases.json # Edge cases (null URLs, huge content, etc.)
    test_models/
      test_wallabag_model.py
      test_karakeep_model.py
    test_converters/
      test_omnivore_converter.py
      test_netscape_converter.py
      test_api_converter.py
    test_transforms/
      test_timestamps.py
      test_tags.py
      test_urls.py
      test_notes.py
    test_api/
      test_client.py
      test_push.py
    test_cli.py                # Integration tests for CLI commands
    test_e2e.py                # End-to-end conversion tests
```

### 4.3 Key Dependencies

```toml
[project]
name = "wallabag-to-karakeep"
version = "0.1.0"
description = "Migrate bookmarks from Wallabag to Karakeep"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = [
    "pydantic>=2.0,<3.0",
    "httpx>=0.27,<1.0",
    "typer>=0.12,<1.0",
    "rich>=13.0,<14.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "mypy>=1.10",
    "ruff>=0.4",
]

[project.scripts]
wallabag-to-karakeep = "wallabag_to_karakeep.cli:app"
```

### 4.4 Key Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `models/wallabag.py` | Pydantic v2 models to validate/parse wallabag JSON input |
| `models/karakeep.py` | Pydantic v2 models for Karakeep API request/response payloads |
| `models/omnivore.py` | Pydantic v2 models for Omnivore-compatible JSON output |
| `converters/base.py` | `Converter` protocol with `convert(entry) -> output` method |
| `converters/omnivore_converter.py` | Implements wallabag Entry -> Omnivore JSON object |
| `converters/netscape_converter.py` | Implements wallabag Entry -> Netscape HTML `<DT>` element |
| `converters/api_converter.py` | Implements wallabag Entry -> Karakeep API payload |
| `transforms/timestamps.py` | `parse_wallabag_datetime()`, `to_karakeep_iso()`, `to_unix_timestamp()` |
| `transforms/tags.py` | `extract_tag_labels()`, `normalize_tags()` |
| `transforms/urls.py` | `normalize_url()`, `is_valid_url()` |
| `transforms/notes.py` | `annotations_to_note()`, `build_note()` |
| `transforms/html.py` | `strip_html_tags()`, `sanitize_for_note()` |
| `api/client.py` | `KarakeepClient` with `create_bookmark()`, `attach_tags()`, `update_bookmark()` |
| `api/push.py` | `PushManager` with batching, rate limiting, progress bar |
| `io/reader.py` | `read_wallabag_export()` with streaming support for large files |
| `io/writer.py` | `write_omnivore_json()`, `write_netscape_html()` |
| `cli.py` | Typer app with `convert`, `push`, `validate` commands |

---

## Part 5: Implementation Plan

### 5.1 Step-by-Step Implementation Order

**Phase 1: Foundation (Days 1-2)**

1. Set up project structure with `pyproject.toml`, `src/` layout, dev dependencies
2. Implement `models/wallabag.py` -- pydantic v2 models for wallabag JSON
3. Implement `transforms/timestamps.py` -- datetime parsing
4. Implement `transforms/tags.py` -- tag extraction
5. Implement `transforms/urls.py` -- URL validation and normalization
6. Write unit tests for all transforms

**Phase 2: Converters (Days 3-4)**

7. Implement `models/omnivore.py` -- pydantic v2 models for Omnivore JSON
8. Implement `models/karakeep.py` -- pydantic v2 models for API payloads
9. Implement `converters/omnivore_converter.py`
10. Implement `converters/netscape_converter.py`
11. Implement `converters/api_converter.py`
12. Implement `transforms/notes.py` -- annotation/metadata to note conversion
13. Write unit tests for all converters

**Phase 3: I/O and CLI (Days 5-6)**

14. Implement `io/reader.py` -- wallabag JSON file reader with validation
15. Implement `io/writer.py` -- output file writers
16. Implement `cli.py` -- Typer CLI with `convert` and `validate` commands
17. Write integration tests for `convert` command
18. Write edge case fixtures and tests

**Phase 4: API Client (Days 7-8)**

19. Implement `api/client.py` -- httpx-based Karakeep API client
20. Implement `api/push.py` -- batch push with progress tracking
21. Add `push` command to CLI
22. Write API client tests with `respx` mocking
23. Write push integration tests

**Phase 5: Polish (Days 9-10)**

24. Add `--dry-run` mode to all commands
25. Add rich progress bars and summary output
26. Add comprehensive error handling and recovery
27. Write end-to-end tests
28. Documentation and README
29. Pre-commit hooks (ruff, mypy)

### 5.2 Test Plan

**Unit test targets** (minimum coverage: 95% for transforms, 90% for converters):

| Module | Test Count | Key Assertions |
|--------|-----------|----------------|
| `transforms/timestamps.py` | 8 | Parses Format A, Format B, null, invalid, timezone handling |
| `transforms/tags.py` | 6 | String tags, object tags, mixed, empty, whitespace, duplicate |
| `transforms/urls.py` | 10 | Valid URLs, invalid URLs, normalization, tracking param removal |
| `transforms/notes.py` | 6 | Empty annotations, single annotation, multiple, metadata assembly |
| `converters/omnivore_converter.py` | 5 | Full entry, minimal entry, null fields, archived mapping |
| `converters/netscape_converter.py` | 4 | Full entry, escaped HTML in title, empty tags |
| `converters/api_converter.py` | 5 | Full entry, minimal entry, title truncation |
| `models/wallabag.py` | 6 | Valid full, valid minimal, missing required, extra fields |
| `api/client.py` | 6 | Create success, create duplicate, 400 error, attach tags, timeout |
| `api/push.py` | 4 | Batch processing, retry on error, dry-run mode, progress |
| `cli.py` | 4 | Convert happy path, push dry-run, validate valid, validate invalid |

### 5.3 Edge Case Fixtures

**Fixture 1: `wallabag_edge_cases.json` -- Entries with problematic data**

```json
[
  {
    "id": 9001,
    "title": null,
    "url": null,
    "content": null,
    "is_archived": 0,
    "is_starred": 0,
    "created_at": "2025-01-01 00:00:00",
    "updated_at": "2025-01-01 00:00:00",
    "tags": [],
    "annotations": []
  },
  {
    "id": 9002,
    "title": "A" ,
    "url": "not-a-valid-url",
    "content": "<script>alert('xss')</script><p>Content</p>",
    "is_archived": 1,
    "is_starred": 1,
    "created_at": "invalid-date",
    "updated_at": "2025-01-01T00:00:00+0200",
    "tags": ["", " ", "valid-tag", {"id": 1, "label": "obj-tag", "slug": "obj-tag"}],
    "annotations": [
      {"quote": "", "text": "", "ranges": []},
      {"quote": "Some highlighted text", "text": "My note", "ranges": [{"start": "/p[1]", "startOffset": 0, "end": "/p[1]", "endOffset": 20}]}
    ]
  },
  {
    "id": 9003,
    "title": "Title with \u00e9m\u00f6ji \ud83d\ude00 and\nnewlines\tand\ttabs",
    "url": "https://example.com/article?utm_source=twitter&utm_medium=social&real_param=keep",
    "content": "<p>Normal content</p>",
    "is_archived": 0,
    "is_starred": 0,
    "created_at": "2025-06-15T12:30:00",
    "updated_at": "2025-06-15T12:30:00",
    "tags": ["tag1", "tag1", "TAG1", "tag2"],
    "annotations": []
  }
]
```

**Test expectations for Fixture 1**:

| Entry | Expected Behavior |
|-------|------------------|
| id=9001 | **SKIP**: null URL is invalid, log warning |
| id=9002 | **SKIP**: `"not-a-valid-url"` is not a valid http/https URL; log warning. If URL were valid: title truncation at 1000 chars not needed (1 char), tags = `["valid-tag", "obj-tag"]` (empty/whitespace stripped), only second annotation produces note text, `created_at` parse failure falls back to `updated_at` |
| id=9003 | **CONVERT**: URL normalized to `https://example.com/article?real_param=keep` (tracking params removed), duplicate tags `["tag1", "TAG1", "tag2"]` with `--tags-mode=lowercase` becomes `["tag1", "tag2"]`, Unicode preserved in title |

**Fixture 2: `wallabag_minimal.json` -- Smallest valid export**

```json
[
  {
    "url": "https://example.com",
    "is_archived": 0,
    "is_starred": 0,
    "created_at": "2025-01-01 00:00:00",
    "updated_at": "2025-01-01 00:00:00",
    "tags": []
  }
]
```

**Fixture 3: `wallabag_full.json` -- Realistic export with 3 entries**

```json
[
  {
    "id": 100,
    "uid": null,
    "title": "How to Use Docker Compose for Development",
    "url": "https://docs.docker.com/compose/gettingstarted/",
    "content": "<article><h1>Get started with Docker Compose</h1><p>Docker Compose is a tool...</p></article>",
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
    "is_public": false,
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
        "ranges": [{"start": "/article/p[3]", "startOffset": 0, "end": "/article/p[3]", "endOffset": 60}],
        "created_at": "2025-01-20T09:15:00+0000",
        "updated_at": "2025-01-20T09:15:00+0000"
      }
    ],
    "user_name": "testuser",
    "user_email": "test@example.com",
    "user_id": 1
  },
  {
    "id": 101,
    "title": "Understanding Rust Ownership",
    "url": "https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html",
    "content": "<main><h1>What Is Ownership?</h1><p>Rust's central feature...</p></main>",
    "domain_name": "doc.rust-lang.org",
    "language": "en",
    "reading_time": 15,
    "is_archived": 0,
    "is_starred": 0,
    "created_at": "2025-03-10 14:22:00",
    "updated_at": "2025-03-10 14:22:00",
    "tags": ["rust", "programming"],
    "annotations": []
  },
  {
    "id": 102,
    "title": "Les recettes de grand-mere",
    "url": "https://cuisine.example.fr/recettes/tarte-tatin",
    "content": "<div><p>La tarte Tatin est un dessert traditionnel...</p></div>",
    "domain_name": "cuisine.example.fr",
    "language": "fr",
    "reading_time": 3,
    "is_archived": 1,
    "is_starred": 0,
    "created_at": "2025-04-05 18:00:00",
    "updated_at": "2025-04-10 12:30:00",
    "published_at": "2025-03-20 00:00:00",
    "published_by": ["Marie Dupont"],
    "tags": ["cuisine", "recettes", "dessert"],
    "annotations": []
  }
]
```

### 5.4 Validation Plan

1. **Static validation**: Run `mypy --strict` on all source files
2. **Lint validation**: Run `ruff check` and `ruff format --check`
3. **Unit tests**: `pytest tests/ --cov=wallabag_to_karakeep --cov-report=term-missing`
4. **Integration test**: Convert `wallabag_full.json` to all three output formats,
   validate each output against its respective schema
5. **Manual validation**: Import the Omnivore JSON output into a test Karakeep
   instance and verify tags, dates, and archived status are preserved

---

## Part 6: Code Skeleton Description

### 6.1 Pydantic Models

#### `models/wallabag.py`

```python
"""Pydantic v2 models for wallabag JSON export entries."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class WallabagTag(BaseModel):
    """Tag object as returned by wallabag API (not always present in exports)."""
    id: int
    label: str
    slug: str


class WallabagAnnotationRange(BaseModel):
    """XPath range for an annotation highlight."""
    start: str
    startOffset: int
    end: str
    endOffset: int


class WallabagAnnotation(BaseModel):
    """Annotation/highlight on an entry."""
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
        if isinstance(v, bool):
            return int(v)
        return int(v) if v is not None else 0
```

#### `models/karakeep.py`

```python
"""Pydantic v2 models for Karakeep REST API payloads."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class KarakeepCreateBookmarkRequest(BaseModel):
    """POST /api/v1/bookmarks request body for link bookmarks."""
    type: Literal["link"] = "link"
    url: str
    title: str | None = Field(default=None, max_length=1000)
    archived: bool = False
    favourited: bool = False
    note: str | None = None
    summary: str | None = None
    createdAt: str | None = None  # ISO 8601
    source: Literal["import"] = "import"
    crawlPriority: Literal["low", "normal"] = "low"


class KarakeepTagAttachment(BaseModel):
    """A single tag to attach to a bookmark."""
    tagName: str


class KarakeepAttachTagsRequest(BaseModel):
    """POST /api/v1/bookmarks/{id}/tags request body."""
    tags: list[KarakeepTagAttachment]


class KarakeepBookmarkResponse(BaseModel):
    """Response from POST /api/v1/bookmarks."""
    id: str
    createdAt: str
    archived: bool
    favourited: bool
    title: str | None = None
    note: str | None = None
    tags: list[dict] = Field(default_factory=list)

    model_config = {"extra": "ignore"}
```

#### `models/omnivore.py`

```python
"""Pydantic v2 models for Omnivore-compatible JSON format."""
from __future__ import annotations

from pydantic import BaseModel


class OmnivoreBookmark(BaseModel):
    """A bookmark in Omnivore export format, compatible with Karakeep import."""
    id: str
    title: str
    url: str
    description: str = ""
    savedAt: str  # ISO 8601
    slug: str = ""
    labels: list[str] = []
    state: str = "Active"  # "Active" or "Archived"
```

### 6.2 Mapping Functions

#### `converters/omnivore_converter.py`

```python
"""Convert wallabag entries to Omnivore-compatible JSON for Karakeep import."""
from __future__ import annotations

import re

from wallabag_to_karakeep.models.omnivore import OmnivoreBookmark
from wallabag_to_karakeep.models.wallabag import WallabagEntry
from wallabag_to_karakeep.transforms.tags import extract_tag_labels
from wallabag_to_karakeep.transforms.timestamps import (
    parse_wallabag_datetime,
    to_karakeep_iso,
)
from wallabag_to_karakeep.transforms.urls import is_valid_url


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80].strip("-")


def convert_to_omnivore(
    entry: WallabagEntry,
    tags_mode: str = "preserve",
) -> OmnivoreBookmark | None:
    """Convert a wallabag entry to Omnivore format.

    Returns None if the entry is invalid (e.g., missing/invalid URL).
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

    # Build title
    title = entry.title or entry.url or ""

    return OmnivoreBookmark(
        id=f"wb-{entry.id}" if entry.id else f"wb-{hash(entry.url)}",
        title=title,
        url=entry.url,
        description="",
        savedAt=saved_at,
        slug=slugify(title),
        labels=labels,
        state=state,
    )
```

#### `converters/api_converter.py`

```python
"""Convert wallabag entries to Karakeep API payloads."""
from __future__ import annotations

from wallabag_to_karakeep.models.karakeep import (
    KarakeepAttachTagsRequest,
    KarakeepCreateBookmarkRequest,
    KarakeepTagAttachment,
)
from wallabag_to_karakeep.models.wallabag import WallabagEntry
from wallabag_to_karakeep.transforms.notes import build_note
from wallabag_to_karakeep.transforms.tags import extract_tag_labels
from wallabag_to_karakeep.transforms.timestamps import (
    parse_wallabag_datetime,
    to_karakeep_iso,
)
from wallabag_to_karakeep.transforms.urls import is_valid_url


def convert_to_api_payload(
    entry: WallabagEntry,
    tags_mode: str = "preserve",
    include_notes: bool = True,
    max_note_length: int = 5000,
) -> tuple[KarakeepCreateBookmarkRequest, KarakeepAttachTagsRequest | None] | None:
    """Convert a wallabag entry to Karakeep API request payloads.

    Returns a tuple of (create_request, tag_request) or None if invalid.
    The tag_request may be None if there are no tags.
    """
    if not is_valid_url(entry.url):
        return None

    # Parse timestamp
    dt = parse_wallabag_datetime(entry.created_at)
    created_at = to_karakeep_iso(dt) if dt else None

    # Build note
    note = build_note(entry) if include_notes else None
    if note and len(note) > max_note_length:
        note = note[:max_note_length] + "..."

    # Build title
    title = entry.title
    if title and len(title) > 1000:
        title = title[:997] + "..."

    # Create bookmark request
    bookmark_req = KarakeepCreateBookmarkRequest(
        url=entry.url,
        title=title,
        archived=bool(entry.is_archived),
        favourited=bool(entry.is_starred),
        note=note or None,
        createdAt=created_at,
    )

    # Create tag request
    labels = extract_tag_labels(entry.tags, mode=tags_mode)
    tag_req = None
    if labels:
        tag_req = KarakeepAttachTagsRequest(
            tags=[KarakeepTagAttachment(tagName=label) for label in labels]
        )

    return bookmark_req, tag_req
```

### 6.3 CLI Entrypoint

#### `cli.py`

```python
"""CLI interface for wallabag-to-karakeep converter."""
from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="wallabag-to-karakeep",
    help="Convert Wallabag JSON exports to Karakeep import formats.",
)
console = Console()


class OutputFormat(str, Enum):
    omnivore = "omnivore"
    netscape = "netscape"
    api_json = "api-json"


class DedupMode(str, Enum):
    url = "url"
    none = "none"
    wallabag_id = "wallabag-id"


class TagsMode(str, Enum):
    preserve = "preserve"
    lowercase = "lowercase"
    strip = "strip"


@app.command()
def convert(
    input_file: Annotated[Path, typer.Option("--in", help="Input wallabag JSON")],
    output_file: Annotated[Path, typer.Option("--out", help="Output file path")],
    format: Annotated[OutputFormat, typer.Option(help="Output format")] = OutputFormat.omnivore,
    dedup: Annotated[DedupMode, typer.Option(help="Dedup mode")] = DedupMode.url,
    tags_mode: Annotated[TagsMode, typer.Option("--tags-mode")] = TagsMode.preserve,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    include_notes: Annotated[bool, typer.Option("--include-notes")] = True,
    max_note_length: Annotated[int, typer.Option("--max-note-length")] = 5000,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0,
) -> None:
    """Convert wallabag JSON export to a Karakeep-compatible format."""
    # Implementation: read, validate, convert, dedup, write
    ...


@app.command()
def push(
    input_file: Annotated[Path, typer.Option("--in", help="Input wallabag JSON")],
    server: Annotated[str, typer.Option(help="Karakeep server URL")],
    api_key: Annotated[Optional[str], typer.Option(help="API key")] = None,
    dedup: Annotated[DedupMode, typer.Option()] = DedupMode.url,
    tags_mode: Annotated[TagsMode, typer.Option("--tags-mode")] = TagsMode.preserve,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    batch_size: Annotated[int, typer.Option("--batch-size")] = 10,
    delay: Annotated[float, typer.Option()] = 1.0,
    crawl_priority: Annotated[str, typer.Option("--crawl-priority")] = "low",
    include_notes: Annotated[bool, typer.Option("--include-notes")] = True,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0,
) -> None:
    """Push wallabag bookmarks directly to a Karakeep instance via API."""
    # Implementation: read, validate, convert, push with progress bar
    ...


@app.command()
def validate(
    input_file: Annotated[Path, typer.Option("--in", help="Input wallabag JSON")],
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0,
) -> None:
    """Validate a wallabag JSON export file."""
    # Implementation: read, parse with pydantic, report errors
    ...


if __name__ == "__main__":
    app()
```

### 6.4 API Client

#### `api/client.py`

```python
"""Karakeep REST API client."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from wallabag_to_karakeep.models.karakeep import (
    KarakeepAttachTagsRequest,
    KarakeepBookmarkResponse,
    KarakeepCreateBookmarkRequest,
)


@dataclass
class KarakeepClient:
    """HTTP client for Karakeep REST API."""
    server_url: str
    api_key: str
    timeout: float = 30.0

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=f"{self.server_url.rstrip('/')}/api/v1",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

    def create_bookmark(
        self, request: KarakeepCreateBookmarkRequest
    ) -> tuple[KarakeepBookmarkResponse, bool]:
        """Create a bookmark. Returns (response, is_new).

        is_new is True if 201 (created), False if 200 (already exists).
        """
        with self._client() as client:
            resp = client.post(
                "/bookmarks",
                content=request.model_dump_json(exclude_none=True),
            )
            resp.raise_for_status()
            is_new = resp.status_code == 201
            return KarakeepBookmarkResponse.model_validate(resp.json()), is_new

    def attach_tags(
        self, bookmark_id: str, request: KarakeepAttachTagsRequest
    ) -> None:
        """Attach tags to a bookmark."""
        with self._client() as client:
            resp = client.post(
                f"/bookmarks/{bookmark_id}/tags",
                content=request.model_dump_json(),
            )
            resp.raise_for_status()
```

---

## Sources

### Wallabag

- [wallabag Entry.php entity (field definitions, serialization groups)](https://github.com/wallabag/wallabag/blob/master/src/Entity/Entry.php)
- [wallabag API methods documentation](https://doc.wallabag.org/developer/api/methods/)
- [wallabag v2 import documentation](https://doc.wallabag.org/user/import/wallabagv2/)
- [wallabag JSON export gist sample](https://gist.github.com/tcitworld/c7b7e963b579a27240b2)
- [wallabag annotations not exported (issue #5160)](https://github.com/wallabag/wallabag/issues/5160)
- [wallabag API additional fields PR #3106](https://github.com/wallabag/wallabag/pull/3106)
- [wallabago Go client (tag/entry structure)](https://pkg.go.dev/github.com/Strubbl/wallabago/v8)
- [wallabag-to-html converter by KillianKemps](https://github.com/KillianKemps/wallabag-to-html)
- [wallabag API documentation (live)](https://app.wallabag.it/api/doc/)

### Karakeep (formerly Hoarder)

- [Karakeep import documentation](https://docs.karakeep.app/using-karakeep/import/)
- [Karakeep API documentation](https://docs.karakeep.app/api/karakeep-api/)
- [Karakeep OpenAPI spec (source)](https://github.com/karakeep-app/karakeep/blob/main/packages/open-api/karakeep-openapi-spec.json)
- [Karakeep GitHub repository](https://github.com/karakeep-app/karakeep)
- [Discussion: HOWTO import from Wallabag (#581)](https://github.com/karakeep-app/karakeep/discussions/581)
- [Issue: Omnivore import improvement - archived (#703)](https://github.com/hoarder-app/hoarder/issues/703)
- [Issue: Import bookmarks with other services (#322)](https://github.com/karakeep-app/karakeep/issues/322)
- [Issue: Setting full page content via API (#1260)](https://github.com/karakeep-app/karakeep/issues/1260)
- [Karakeep v0.24.0 release (edit all bookmark details)](https://github.com/karakeep-app/karakeep/discussions/1320)
- [Karakeep v0.25.0 release (list preservation on import)](https://github.com/karakeep-app/karakeep/discussions/1561)
- [Karakeep bookmark management system (DeepWiki)](https://deepwiki.com/karakeep-app/karakeep/3.1-bookmark-management-system)
- [Karakeep import/export system (DeepWiki)](https://deepwiki.com/karakeep-app/karakeep/6.3-importexport-system)
- [Karakeep Python API client](https://github.com/thiswillbeyourgithub/karakeep_python_api)
- [Karakeep CLI documentation](https://docs.karakeep.app/command-line/)

### Community Tools

- [wallabag-to-karakeep Python converter](https://git.theorangeone.net/tools/wallabag-to-karakeep)
- [Blog: Migrating from Wallabag to Karakeep](https://nikokultalahti.com/2025/08/28/migrating-from-wallabag-to-karakeep/)
- [Karakeep Miniflux integration](https://miniflux.app/docs/karakeep.html)

### Omnivore

- [Omnivore schema.ts (API types)](https://github.com/omnivore-app/omnivore/blob/main/packages/api/src/schema.ts)
- [Omnivore export JQ commands (issue #4493)](https://github.com/omnivore-app/omnivore/issues/4493)
