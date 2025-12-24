"""
Shiori-compatible API endpoints (v1).

This module provides API endpoints that match Shiori's v1 API contract,
allowing the Shiori Vue frontend to work with Atlas storage.

API paths:
- /api/v1/auth/login
- /api/v1/auth/logout
- /api/v1/auth/me
- /api/v1/bookmarks
- /api/v1/bookmarks/{id}/readable
- /api/v1/tags

Shiori API docs: https://github.com/go-shiori/shiori/blob/master/docs/API.md
"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Header, Request, Query, Body, Depends
from pydantic import BaseModel

from modules.storage import FileStore, IndexManager, ContentType
from modules.pipeline.content_pipeline import ContentPipeline

# Create sub-routers for v1 API structure
router = APIRouter(tags=["shiori"])
auth_router = APIRouter(prefix="/v1/auth", tags=["auth"])
bookmarks_router = APIRouter(prefix="/v1/bookmarks", tags=["bookmarks"])
tags_router = APIRouter(prefix="/v1/tags", tags=["tags"])

# Simple in-memory session store (for single-user homelab use)
# In production, you'd use Redis or database sessions
_sessions: Dict[str, Dict[str, Any]] = {}

# Default paths
INDEX_DB = "data/indexes/atlas_index.db"
CONTENT_DIR = "data/content"

# Cache for content items (refreshed on each request for now)
_content_cache: List[Dict[str, Any]] = []
_cache_time: Optional[datetime] = None


def scan_content_directories(limit: int = 100, content_types: List[str] = None) -> List[Dict[str, Any]]:
    """
    Directly scan content directories for metadata.json files.
    Returns list of content items with hasContent properly set.
    """
    global _content_cache, _cache_time
    import glob
    import json

    # Use cache if less than 60 seconds old
    if _cache_time and (datetime.now() - _cache_time).seconds < 60 and _content_cache:
        items = _content_cache
    else:
        content_base = Path(CONTENT_DIR)
        items = []

        # Default to articles and newsletters (most readable content)
        if not content_types:
            content_types = ["article", "newsletter", "youtube"]

        for ct in content_types:
            type_dir = content_base / ct
            if not type_dir.exists():
                continue

            # Find all metadata.json files
            for meta_path in type_dir.glob("**/metadata.json"):
                try:
                    content_dir = meta_path.parent
                    content_id = content_dir.name

                    with open(meta_path) as f:
                        meta = json.load(f)

                    # Check for readable content
                    has_html = (content_dir / "article.html").exists()
                    has_md = (content_dir / "content.md").exists()
                    has_content = has_html or has_md

                    # Add to items with content status
                    meta["content_id"] = content_id
                    meta["content_type"] = ct
                    meta["_has_content"] = has_content
                    meta["_content_dir"] = str(content_dir)
                    items.append(meta)

                except Exception:
                    continue

        # Filter out garbage content
        GARBAGE_PATTERNS = [
            "requires javascript",
            "please turn on javascript",
            "unblock scripts",
            "error occurred",
            "retrieving sharing information",
            "please try again later",
            "| substack",  # Profile pages, not articles
            "access denied",
            "page not found",
            "404",
            "403 forbidden",
            "[no-title]",
            "no title",
            "untitled",
            "sign in",
            "log in",
            "loading...",
            "redirecting",
            "just a moment",
            "bloomberg link",  # Tracking links
            "spotify",  # App redirect pages
        ]

        def is_garbage(item):
            title = (item.get("title") or "").lower()
            desc = (item.get("description") or "").lower()
            combined = title + " " + desc

            # Check for garbage patterns
            for pattern in GARBAGE_PATTERNS:
                if pattern in combined:
                    return True

            # Very short titles that are just URLs or IDs
            if title.startswith("http") or len(title) < 5:
                return True

            # Titles that are just the domain
            source_url = item.get("source_url", "")
            if source_url and title and title.lower() in source_url.lower():
                return True

            return False

        items = [item for item in items if not is_garbage(item)]

        # Sort by date (newest first) - check modified, created_at, created, or extract from path
        def get_sort_date(x):
            date = x.get("modified") or x.get("created_at") or x.get("created")
            if date:
                return date
            # Try to extract date from content directory path (e.g., /youtube/2025/12/22/abc123/)
            content_dir = x.get("_content_dir", "")
            if content_dir:
                import re
                match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', content_dir)
                if match:
                    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}T00:00:00"
            return ""
        items.sort(key=get_sort_date, reverse=True)

        # Update cache
        _content_cache = items
        _cache_time = datetime.now()

    return items[:limit]


# --- Pydantic Models ---

class LoginRequest(BaseModel):
    username: str
    password: str
    remember: bool = True
    owner: bool = True


class LoginResponse(BaseModel):
    token: str
    expires: int  # Unix timestamp in milliseconds


class TagModel(BaseModel):
    name: str


class BookmarkRequest(BaseModel):
    url: str
    title: Optional[str] = None
    excerpt: Optional[str] = None
    tags: Optional[List[TagModel]] = None
    createArchive: bool = True
    public: int = 0


class BookmarkUpdateRequest(BaseModel):
    id: int
    url: Optional[str] = None
    title: Optional[str] = None
    excerpt: Optional[str] = None
    tags: Optional[List[TagModel]] = None
    public: Optional[int] = None


class TagRenameRequest(BaseModel):
    id: int
    name: str


# --- Helper Functions ---

def get_index_manager() -> IndexManager:
    """Get index manager instance."""
    return IndexManager(INDEX_DB)


def get_file_store() -> FileStore:
    """Get file store instance."""
    return FileStore(CONTENT_DIR)


def validate_session(
    x_session_id: Optional[str] = None,
    authorization: Optional[str] = None
) -> Dict[str, Any]:
    """Validate session and return user info.

    Accepts either X-Session-Id header or Authorization: Bearer <token>
    """
    session_id = x_session_id

    # Check Authorization header (Bearer token)
    if not session_id and authorization:
        if authorization.startswith("Bearer "):
            session_id = authorization[7:]  # Remove "Bearer " prefix

    if not session_id or session_id not in _sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    return _sessions[session_id]


def get_session_from_headers(
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Dependency to extract and validate session from headers."""
    return validate_session(x_session_id, authorization)


def content_to_bookmark(item: Dict[str, Any], bookmark_id: int) -> Dict[str, Any]:
    """Convert Atlas content item to Shiori bookmark format."""
    import re

    # Parse created_at for modified timestamp, with fallback to directory path date
    created_at = item.get("modified") or item.get("created_at") or item.get("created", "")
    modified = None

    if isinstance(created_at, str) and created_at:
        try:
            modified = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Fallback: extract date from content directory path
    if not modified:
        content_dir = item.get("_content_dir", "")
        if content_dir:
            match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', content_dir)
            if match:
                try:
                    modified = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                except ValueError:
                    pass

    if not modified:
        modified = datetime.now()

    # Extract domain from URL
    source_url = item.get("source_url", "")
    domain = ""
    if source_url:
        try:
            from urllib.parse import urlparse
            domain = urlparse(source_url).netloc
        except Exception:
            pass

    # Get excerpt from description or generate from title
    excerpt = item.get("description", "") or ""
    if len(excerpt) > 200:
        excerpt = excerpt[:200] + "..."

    timestamp = modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": bookmark_id,
        "url": source_url,
        "title": item.get("title", "Untitled"),
        "excerpt": excerpt,
        "author": item.get("author", ""),
        "public": 0,
        "createdAt": timestamp,
        "modifiedAt": timestamp,
        "imageURL": "",
        "hasContent": item.get("_has_content", item.get("status") == "completed"),
        "hasArchive": item.get("status") == "completed",
        "hasEbook": False,
        "tags": [],  # TODO: Load from tags table
        "createArchive": True,
        # Atlas-specific fields (ignored by Shiori frontend)
        "_content_id": item.get("content_id"),
        "_content_type": item.get("content_type"),
        "_domain": domain,
    }


def generate_bookmark_id(content_id: str) -> int:
    """Generate a numeric ID from content_id hash (Shiori expects integers)."""
    # Use first 8 chars of hash as hex, convert to int, mod to keep reasonable
    return int(hashlib.md5(content_id.encode()).hexdigest()[:8], 16) % 1000000000


# --- Content ID mapping ---
# Shiori uses integer IDs, Atlas uses string content_ids
# We maintain a mapping for the session
_id_to_content_id: Dict[int, str] = {}
_content_id_to_id: Dict[str, int] = {}


def get_or_create_id(content_id: str) -> int:
    """Get or create a numeric ID for a content_id."""
    if content_id in _content_id_to_id:
        return _content_id_to_id[content_id]

    numeric_id = generate_bookmark_id(content_id)
    _id_to_content_id[numeric_id] = content_id
    _content_id_to_id[content_id] = numeric_id
    return numeric_id


def get_content_id(numeric_id: int) -> Optional[str]:
    """Get content_id from numeric ID."""
    return _id_to_content_id.get(numeric_id)


# --- Auth Endpoints (at /api/v1/auth/*) ---

@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login and get session token.

    For homelab single-user setup, we use simple auth.
    Configure ATLAS_READER_USER and ATLAS_READER_PASS env vars.
    """
    import os
    expected_user = os.environ.get("ATLAS_READER_USER", "atlas")
    expected_pass = os.environ.get("ATLAS_READER_PASS", "atlas")

    if request.username != expected_user or request.password != expected_pass:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create session
    session_id = secrets.token_hex(32)
    _sessions[session_id] = {
        "id": 1,
        "username": request.username,
        "owner": request.owner,
        "created_at": datetime.now().isoformat(),
    }

    # Expires in 7 days (milliseconds for JS)
    expires_ms = int((datetime.now().timestamp() + 7 * 24 * 3600) * 1000)

    return LoginResponse(
        token=session_id,
        expires=expires_ms,
    )


@auth_router.post("/logout")
async def logout(x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None)):
    """Logout and invalidate session."""
    if x_session_id and x_session_id in _sessions:
        del _sessions[x_session_id]
    return {"message": "ok"}


@auth_router.get("/me")
async def get_current_user(x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None)):
    """Get current user info."""
    user = validate_session(x_session_id, authorization)
    return {
        "id": 1,
        "username": user["username"],
        "owner": user.get("owner", True),
    }


@auth_router.get("/account")
async def get_account(x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None)):
    """Get account info (alias for /me)."""
    user = validate_session(x_session_id, authorization)
    return {
        "id": 1,
        "username": user["username"],
        "owner": user.get("owner", True),
    }


@auth_router.post("/refresh")
async def refresh_session(x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None)):
    """Refresh session token."""
    user = validate_session(x_session_id, authorization)

    # Create new session
    new_session_id = secrets.token_hex(32)
    _sessions[new_session_id] = {
        "id": 1,
        "username": user["username"],
        "owner": user.get("owner", True),
        "created_at": datetime.now().isoformat(),
    }

    # Remove old session
    if x_session_id in _sessions:
        del _sessions[x_session_id]

    # Expires in 7 days (milliseconds for JS)
    expires_ms = int((datetime.now().timestamp() + 7 * 24 * 3600) * 1000)

    return {
        "token": new_session_id,
        "expires": expires_ms,
    }


# --- Bookmark Endpoints (at /api/v1/bookmarks/*) ---

@bookmarks_router.get("")
async def list_bookmarks(
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
    page: int = 1,
    keyword: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tag names
    readable_only: bool = True,  # Only show items with readable content
):
    """
    List bookmarks (content items).

    Returns items in Shiori's expected format.
    Uses direct filesystem scanning instead of index for reliability.
    """
    validate_session(x_session_id, authorization)

    limit = 30
    offset = (page - 1) * limit

    # Use direct filesystem scanning (IndexManager indexes don't exist)
    all_items = scan_content_directories(limit=500)  # Get more, then filter

    # Filter to only readable content if requested
    if readable_only:
        all_items = [item for item in all_items if item.get("_has_content")]

    # Apply pagination
    paginated_items = all_items[offset:offset + limit]

    # Convert to Shiori format
    bookmarks = []
    for item in paginated_items:
        content_id = item.get("content_id", "")
        if content_id:
            bookmark_id = get_or_create_id(content_id)
            bookmarks.append(content_to_bookmark(item, bookmark_id))

    # Calculate pagination
    total = len(all_items)
    max_page = (total // limit) + (1 if total % limit else 0)

    return {
        "bookmarks": bookmarks,
        "page": page,
        "maxPage": max_page if max_page > 0 else 1,
    }


@bookmarks_router.post("")
async def add_bookmark(
    request: BookmarkRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
):
    """
    Add a new bookmark (save URL to Atlas).

    This triggers Atlas's content pipeline to fetch and process the URL.
    """
    validate_session(x_session_id, authorization)

    pipeline = ContentPipeline()

    try:
        item = pipeline.process_url(request.url)

        if item:
            bookmark_id = get_or_create_id(item.content_id)

            # Convert to Shiori format for response
            return {
                "id": bookmark_id,
                "url": request.url,
                "title": item.title,
                "excerpt": item.description or "",
                "author": item.author or "",
                "public": request.public,
                "modified": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "imageURL": "",
                "hasContent": True,
                "hasArchive": request.createArchive,
                "tags": request.tags or [],
                "_content_id": item.content_id,
            }
        else:
            # Item already exists or failed to process
            raise HTTPException(
                status_code=409,
                detail="URL already exists or failed to process"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@bookmarks_router.put("")
async def update_bookmark(
    request: BookmarkUpdateRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
):
    """Update a bookmark's metadata."""
    validate_session(x_session_id, authorization)

    content_id = get_content_id(request.id)
    if not content_id:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    store = get_file_store()
    item = store.load(content_id)

    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    # Update fields
    if request.title:
        item.title = request.title
    if request.tags:
        item.tags = [t.name for t in request.tags]

    # Save back
    store.save(item)

    return content_to_bookmark(
        {
            "content_id": item.content_id,
            "title": item.title,
            "description": item.description,
            "author": item.author,
            "source_url": item.source_url,
            "status": item.status.value,
            "created_at": item.created_at.isoformat(),
            "content_type": item.content_type.value,
        },
        request.id
    )


@bookmarks_router.delete("")
async def delete_bookmarks(
    ids: List[int] = Query(...),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
):
    """Delete bookmarks by ID."""
    validate_session(x_session_id, authorization)

    store = get_file_store()
    index = get_index_manager()
    deleted = []

    for bookmark_id in ids:
        content_id = get_content_id(bookmark_id)
        if content_id:
            try:
                # Remove from index
                index.remove_item(content_id)
                # Note: We don't delete files, just remove from index
                # Files can be cleaned up later if needed
                deleted.append(bookmark_id)
            except Exception:
                continue

    return {"deleted": deleted}


@bookmarks_router.put("/cache")
async def update_cache(
    ids: List[int] = Body(..., embed=True),
    keep_metadata: bool = Body(False, embed=True),
    create_archive: bool = Body(True, embed=True),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
):
    """Re-cache/archive bookmarks (re-fetch content)."""
    validate_session(x_session_id, authorization)
    # For now, just acknowledge - actual re-caching would need pipeline integration
    return {"message": "ok", "processed": ids}


@bookmarks_router.put("/bulk/tags")
async def bulk_update_tags(
    ids: List[int] = Body(..., embed=True),
    tags: List[TagModel] = Body(..., embed=True),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
):
    """Update tags for multiple bookmarks."""
    validate_session(x_session_id, authorization)

    store = get_file_store()
    updated = []

    for bookmark_id in ids:
        content_id = get_content_id(bookmark_id)
        if content_id:
            try:
                item = store.load(content_id)
                if item:
                    item.tags = [t.name for t in tags]
                    store.save(item)
                    updated.append(bookmark_id)
            except Exception:
                continue

    return {"message": "ok", "updated": updated}


@bookmarks_router.get("/{bookmark_id}/readable")
async def get_bookmark_content(
    bookmark_id: str,  # Accept string to handle both numeric IDs and content_ids
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
):
    """Get the readable content for a bookmark."""
    validate_session(x_session_id, authorization)

    # Try to get content_id from mapping (for numeric IDs)
    # Or use the bookmark_id directly if it looks like a content_id (hex string)
    if bookmark_id.isdigit():
        content_id = get_content_id(int(bookmark_id))
    else:
        content_id = bookmark_id  # Assume it's already a content_id

    if not content_id:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    # Find content directory by searching for content_id folder
    import glob
    content_base = Path(CONTENT_DIR)
    pattern = str(content_base / "**" / content_id)
    matches = glob.glob(pattern, recursive=True)

    if not matches:
        raise HTTPException(status_code=404, detail="Content directory not found")

    content_dir = Path(matches[0])

    # Read metadata
    metadata_file = content_dir / "metadata.json"
    metadata = {}
    if metadata_file.exists():
        import json
        metadata = json.loads(metadata_file.read_text())

    # Try to read content in order of preference: article.html (pre-rendered), content.md (raw markdown)
    content = None
    html = None
    is_markdown = False

    # Check for pre-rendered HTML first
    article_html = content_dir / "article.html"
    if article_html.exists():
        html = article_html.read_text()

    # Check for markdown content
    content_md = content_dir / "content.md"
    if content_md.exists():
        content = content_md.read_text()
        is_markdown = True
        # If no HTML, client will render markdown
        if not html:
            html = None  # Let client handle markdown rendering

    if not content and not html:
        raise HTTPException(status_code=404, detail="No readable content found")

    return {
        "id": bookmark_id,
        "title": metadata.get("title", "Untitled"),
        "content": content or "",  # Raw markdown content for client-side rendering
        "html": html or "",  # Pre-rendered HTML if available
        "isMarkdown": is_markdown,  # Flag for client to know to parse markdown
        "author": metadata.get("author") or "",
        "url": metadata.get("source_url") or metadata.get("url", ""),
    }


@bookmarks_router.put("/{bookmark_id}/tags")
async def update_bookmark_tags(
    bookmark_id: int,
    tags: List[TagModel] = Body(...),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
):
    """Update tags for a bookmark."""
    validate_session(x_session_id, authorization)

    content_id = get_content_id(bookmark_id)
    if not content_id:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    store = get_file_store()
    item = store.load(content_id)

    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    item.tags = [t.name for t in tags]
    store.save(item)

    return {"message": "ok"}


# --- Tag Endpoints (at /api/v1/tags/*) ---

@tags_router.get("")
async def list_tags(
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
):
    """List all unique tags."""
    validate_session(x_session_id, authorization)

    index = get_index_manager()

    # Query unique tags from the tags table
    try:
        with index._get_conn() as conn:
            rows = conn.execute("""
                SELECT tag, COUNT(*) as count
                FROM tags
                GROUP BY tag
                ORDER BY count DESC
            """).fetchall()

        return [
            {"id": i + 1, "name": row["tag"], "nBookmarks": row["count"]}
            for i, row in enumerate(rows)
        ]
    except Exception:
        # If tags table doesn't exist yet, return empty list
        return []


@tags_router.put("")
async def rename_tag(
    request: TagRenameRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(None),
):
    """Rename a tag."""
    validate_session(x_session_id, authorization)

    index = get_index_manager()

    # Get the old tag name by ID (we'd need to track this)
    # For now, we'll just update based on the request
    # This is a simplified implementation

    with index._get_conn() as conn:
        # Get tags ordered by count (same as list)
        rows = conn.execute("""
            SELECT DISTINCT tag FROM tags ORDER BY tag
        """).fetchall()

        if request.id <= len(rows):
            old_name = rows[request.id - 1]["tag"]

            # Update all occurrences
            conn.execute("""
                UPDATE tags SET tag = ? WHERE tag = ?
            """, (request.name, old_name))

            return {"id": request.id, "name": request.name}

    raise HTTPException(status_code=404, detail="Tag not found")


# --- Include sub-routers into main router ---
router.include_router(auth_router)
router.include_router(bookmarks_router)
router.include_router(tags_router)
