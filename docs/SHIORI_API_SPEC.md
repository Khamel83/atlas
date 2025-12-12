# Shiori API v1 Specification

Reference: https://github.com/go-shiori/shiori/blob/master/docs/swagger/swagger.json

## Authentication

### POST /api/v1/auth/login
Login with username/password.

**Request:**
```json
{
  "username": "string",
  "password": "string",
  "remember_me": true
}
```

**Response:**
```json
{
  "token": "string",
  "expires": 1234567890  // Unix timestamp in milliseconds
}
```

### POST /api/v1/auth/logout
Logout current session.

### GET /api/v1/auth/me
Get current user info.

**Response:**
```json
{
  "id": 1,
  "username": "string",
  "owner": true,
  "config": { ... }
}
```

### POST /api/v1/auth/refresh
Refresh JWT token.

**Response:** Same as login.

## Bookmarks

**NOTE:** The v1 API does NOT have a GET /api/v1/bookmarks endpoint for listing!
The legacy API uses GET /api/bookmarks for listing.

### BookmarkDTO Model
```json
{
  "id": 123,
  "url": "https://example.com",
  "title": "Page Title",
  "excerpt": "Short description...",
  "author": "Author Name",
  "public": 0,
  "createdAt": "2025-01-01T00:00:00Z",
  "modifiedAt": "2025-01-01T00:00:00Z",
  "imageURL": "https://...",
  "hasContent": true,
  "hasArchive": true,
  "hasEbook": false,
  "tags": [{"id": 1, "name": "tag1"}],
  "html": "<html>...</html>"
}
```

### GET /api/v1/bookmarks/{id}/readable
Get readable content for a bookmark.

**Response:**
```json
{
  "content": "Plain text content",
  "html": "<html>Formatted content</html>"
}
```

### PUT /api/v1/bookmarks/cache
Update cache/archive for bookmarks.

**Request:**
```json
{
  "ids": [1, 2, 3],
  "create_archive": true,
  "create_ebook": false,
  "keep_metadata": true,
  "skip_exist": false
}
```

### PUT /api/v1/bookmarks/bulk/tags
Bulk update tags for bookmarks.

**Request:**
```json
{
  "bookmark_ids": [1, 2, 3],
  "tag_ids": [10, 20]
}
```

### GET/POST/DELETE /api/v1/bookmarks/{id}/tags
Manage tags for a specific bookmark.

## Tags

### GET /api/v1/tags
List all tags.

**Query params:**
- `with_bookmark_count` - Include count
- `bookmark_id` - Filter by bookmark
- `search` - Search by name

**Response:**
```json
[
  {"id": 1, "name": "tag1", "bookmark_count": 5},
  {"id": 2, "name": "tag2", "bookmark_count": 3}
]
```

### POST /api/v1/tags
Create a new tag.

### GET/PUT/DELETE /api/v1/tags/{id}
Get, update, or delete a tag.

## Legacy API (Still Used)

### GET /api/bookmarks
List bookmarks (NOT in v1 API yet).

**Response:**
```json
{
  "bookmarks": [BookmarkDTO, ...]
}
```

### POST /api/bookmarks
Add a bookmark.

### PUT /api/bookmarks
Update a bookmark.

### DELETE /api/bookmarks
Delete bookmarks.

---

## Atlas Implementation Notes

Our shiori_compat.py implements:
- All /api/v1/auth/* endpoints
- GET /api/v1/bookmarks (added, not in official v1)
- GET /api/v1/bookmarks/{id}/readable
- GET /api/v1/tags

The frontend uses demo data on HomeView - need to either:
1. Build Shiori frontend from source with proper API calls
2. Create custom frontend
3. Patch the minified JS (fragile)
