from fastapi import APIRouter, HTTPException, Query, Depends, File, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from helpers.metadata_manager import MetadataManager, ContentType, ProcessingStatus
from helpers.config import load_config
from ingest.link_dispatcher import process_url_file

router = APIRouter()

# Dependency to get metadata manager
def get_metadata_manager():
    config = load_config()
    return MetadataManager(config)

class ContentItem(BaseModel):
    uid: str
    title: str
    source: str
    content_type: str
    status: str
    created_at: str
    updated_at: str
    tags: List[str]
    content_path: Optional[str] = None

class ContentListResponse(BaseModel):
    items: List[ContentItem]
    total: int

class ContentSubmission(BaseModel):
    url: str

class BookmarkletSave(BaseModel):
    title: str
    url: str
    content: str
    content_type: str = "article"

@router.get("/", response_model=ContentListResponse)
async def list_content(
    skip: int = 0,
    limit: int = 50,
    content_type: Optional[str] = None,
    tags: Optional[List[str]] = Query(None)
):
    """List all content with pagination and filtering"""
    try:
        # Use direct SQLite query to avoid metadata manager issues
        from helpers.simple_database import SimpleDatabase

        db = SimpleDatabase()
        with db.get_connection() as conn:
            # Build query
            where_clauses = []
            params = []

            if content_type:
                where_clauses.append("content_type = ?")
                params.append(content_type)

            where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Get total count
            count_query = f"SELECT COUNT(*) FROM content{where_clause}"
            total = conn.execute(count_query, params).fetchone()[0]

            # Get items
            query = f"""
                SELECT id, title, url, content_type, created_at, updated_at,
                       'completed' as status
                FROM content
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, skip])

            rows = conn.execute(query, params).fetchall()

            # Convert to ContentItem objects
            items = []
            for row in rows:
                items.append(ContentItem(
                    uid=str(row[0]),
                    title=row[1] or "Untitled",
                    source=row[2] or "",
                    content_type=row[3] or "article",
                    status=row[6],
                    created_at=row[4] or "",
                    updated_at=row[5] or "",
                    tags=[],  # Simple implementation without tags for now
                    content_path=None
                ))

        return ContentListResponse(items=items, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing content: {str(e)}")

@router.get("/html", response_class=HTMLResponse)
async def list_content_html(
    skip: int = 0,
    limit: int = 50,
    content_type: Optional[str] = None
):
    """List all content as HTML page"""
    try:
        from helpers.simple_database import SimpleDatabase

        db = SimpleDatabase()
        with db.get_connection() as conn:
            # Build query
            where_clauses = []
            params = []

            if content_type:
                where_clauses.append("content_type = ?")
                params.append(content_type)

            where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Get total count
            count_query = f"SELECT COUNT(*) FROM content{where_clause}"
            total = conn.execute(count_query, params).fetchone()[0]

            # Get items
            query = f"""
                SELECT id, title, url, content_type, created_at,
                       'No summary available' as summary,
                       'completed' as status
                FROM content
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, skip])

            rows = conn.execute(query, params).fetchall()

            # Build HTML
            content_rows = ""
            for row in rows:
                title = (row[1] or "Untitled")[:80]
                url = row[2] or ""
                content_type = row[3] or "article"
                created_at = row[4] or ""
                status = row[6]
                summary = row[5] or "No summary available"

                # Truncate summary for display
                summary_display = summary[:200] + "..." if len(summary) > 200 else summary

                status_color = "#28a745" if status == "completed" else "#ffc107"

                content_rows += f"""
                <tr>
                    <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <strong>{title}</strong><br>
                        <small style="color: #666;">{content_type}</small>
                    </td>
                    <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <a href="{url}" target="_blank" style="color: #007bff; text-decoration: none;">{url}</a>
                    </td>
                    <td>
                        <span style="background-color: {status_color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px;">
                            {status}
                        </span>
                    </td>
                    <td style="max-width: 300px; font-size: 13px; color: #555;">
                        {summary_display}
                    </td>
                    <td style="font-size: 12px; color: #888;">
                        {created_at[:10] if created_at else ""}
                    </td>
                </tr>
                """

            # Pagination
            prev_link = f"?skip={max(0, skip-limit)}&limit={limit}" if skip > 0 else ""
            next_link = f"?skip={skip+limit}&limit={limit}" if skip + limit < total else ""

            pagination = f"""
            <div style="margin: 20px 0; text-align: center;">
                {'<a href="' + prev_link + '" style="margin-right: 10px;">← Previous</a>' if prev_link else ''}
                <span>Showing {skip+1}-{min(skip+limit, total)} of {total} items</span>
                {'<a href="' + next_link + '" style="margin-left: 10px;">Next →</a>' if next_link else ''}
            </div>
            """

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Atlas Content Browser</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; }}
                    .header {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th, td {{ padding: 12px 8px; border-bottom: 1px solid #eee; text-align: left; vertical-align: top; }}
                    th {{ background-color: #f8f9fa; font-weight: 600; }}
                    a {{ color: #007bff; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🗂️ Atlas Content Browser</h1>
                    <p>Browse and manage your content collection</p>
                </div>
                {pagination}
                <table>
                    <thead>
                        <tr>
                            <th>Title & Type</th>
                            <th>Source URL</th>
                            <th>Status</th>
                            <th>Summary</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {content_rows}
                    </tbody>
                </table>
                {pagination}
            </body>
            </html>
            """

            return html_content
    except Exception as e:
        return f"<html><body><h1>Error</h1><p>Error loading content: {str(e)}</p></body></html>"

@router.get("/{content_id}", response_model=ContentItem)
async def get_content(
    content_id: str,
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Get a specific content item by ID"""
    try:
        metadata = manager.load_metadata(content_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Content not found")

        return ContentItem(
            uid=metadata.uid,
            title=metadata.title,
            source=metadata.source,
            content_type=metadata.content_type.value,
            status=metadata.status.value,
            created_at=metadata.created_at,
            updated_at=metadata.updated_at,
            tags=metadata.tags,
            content_path=metadata.content_path
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving content: {str(e)}")

@router.post("/submit-url")
async def submit_url_for_processing(
    submission: ContentSubmission
):
    """Submit a URL for processing via unified ingestion queue"""
    try:
        from helpers.unified_ingestion import submit_url

        # Submit URL to unified queue
        job_id = submit_url(submission.url, priority=50, source="api")

        return {
            "success": True,
            "message": "URL queued for processing",
            "job_id": job_id,
            "url": submission.url,
            "status": "queued"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting URL: {str(e)}")

# Old processing logic removed - now using unified queue system

@router.post("/save", response_model=dict)
async def save_bookmarklet_content(
    save_data: BookmarkletSave,
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Save content directly from browser bookmarklet"""
    try:
        # Save content to database using the simple database helper
        from helpers.simple_database import SimpleDatabase
        db = SimpleDatabase()
        with db.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO content (title, url, content, content_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (save_data.title, save_data.url, save_data.content, save_data.content_type))
            conn.commit()
            content_db_id = cursor.lastrowid

        return {
            "status": "success",
            "message": f"Content saved successfully: {save_data.title}",
            "id": content_db_id,
            "title": save_data.title
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving content: {str(e)}")

@router.post("/upload-file")
async def upload_file_for_processing(
    file: UploadFile = File(...),
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Upload a file for content processing"""
    try:
        # Save uploaded file temporarily
        temp_file = f"/tmp/atlas_file_upload_{uuid.uuid4()}_{file.filename}"
        with open(temp_file, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # For now, just acknowledge the upload
        # In a full implementation, this would trigger processing
        return {"message": f"File {file.filename} uploaded successfully", "temp_path": temp_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Delete a content item"""
    try:
        # Load metadata first to get file paths
        metadata = manager.load_metadata(content_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Content not found")

        # Delete the metadata file
        manager.delete_metadata(content_id)

        # Attempt to delete associated files if they exist
        if metadata.content_path and os.path.exists(metadata.content_path):
            os.remove(metadata.content_path)

        # Delete from any other storage locations based on content type
        # This would be expanded based on the actual file structure

        return {"message": f"Content {content_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting content: {str(e)}")