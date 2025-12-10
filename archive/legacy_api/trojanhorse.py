"""Atlas router for TrojanHorse integration."""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
ATLAS_API_KEY = os.getenv('ATLAS_API_KEY')


class IngestNote(BaseModel):
    """Note payload from TrojanHorse for Atlas ingestion."""
    id: str = Field(..., description="Unique identifier from TrojanHorse")
    path: str = Field(..., description="File path in TrojanHorse")
    title: str = Field(..., description="Note title")
    source: Optional[str] = Field(None, description="Source system (e.g., 'drafts', 'macwhisper')")
    raw_type: Optional[str] = Field(None, description="Raw content type (e.g., 'email_dump', 'voice_note')")
    class_type: Optional[str] = Field(None, description="Classification (work/personal)")
    category: Optional[str] = Field(None, description="Content category (email/meeting/idea/etc.)")
    project: Optional[str] = Field(None, description="Project identifier")
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    created_at: Optional[str] = Field(None, description="ISO creation timestamp")
    updated_at: Optional[str] = Field(None, description="ISO update timestamp")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    body: str = Field(..., description="Main content body")
    frontmatter: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class IngestResponse(BaseModel):
    """Response for ingest operations."""
    status: str
    message: str
    count: Optional[int] = None


def validate_api_key(x_api_key: str = Header(default=None)) -> bool:
    """Validate API key if authentication is configured."""
    if ATLAS_API_KEY and x_api_key != ATLAS_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return True


async def ingest_note_to_atlas(note: IngestNote) -> bool:
    """
    Ingest a single TrojanHorse note into Atlas.

    Args:
        note: Note payload from TrojanHorse

    Returns:
        True if successful, False otherwise
    """
    try:
        # Import Atlas content system
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

        from helpers.simple_database import SimpleDatabase

        db = SimpleDatabase()

        # Prepare content for Atlas
        content = {
            'title': note.title,
            'url': note.path,  # Use TrojanHorse path as URL reference
            'content': note.body,
            'content_type': 'note',  # Mark as note content type
            'ai_summary': note.summary,
            'source': f"TrojanHorse:{note.source or 'unknown'}",
            'created_at': datetime.now().isoformat(),
            'metadata': {
                'trojanhorse_id': note.id,
                'trojanhorse_path': note.path,
                'class_type': note.class_type,
                'category': note.category,
                'project': note.project,
                'tags': note.tags,
                'raw_type': note.raw_type,
                'frontmatter': note.frontmatter,
                'source_system': 'TrojanHorse'
            }
        }

        # Add to Atlas database
        with db.get_connection() as conn:
            # Check if already exists
            existing = conn.execute(
                'SELECT id FROM content WHERE url = ? AND metadata LIKE ?',
                (note.path, f'%trojanhorse_id": "{note.id}"%')
            ).fetchone()

            if existing:
                logger.info(f"Note {note.id} already exists in Atlas, updating")
                # Update existing record
                conn.execute('''
                    UPDATE content SET
                        title = ?,
                        content = ?,
                        ai_summary = ?,
                        updated_at = ?,
                        metadata = ?
                    WHERE id = ?
                ''', (
                    note.title,
                    note.body,
                    note.summary,
                    datetime.now().isoformat(),
                    str(content['metadata']),
                    existing[0]
                ))
            else:
                logger.info(f"Ingesting new note {note.id} to Atlas")
                # Insert new record
                conn.execute('''
                    INSERT INTO content (
                        title, url, content, content_type, ai_summary,
                        source, created_at, updated_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    note.title,
                    note.path,
                    note.body,
                    'note',
                    note.summary,
                    content['source'],
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    str(content['metadata'])
                ))

        logger.info(f"Successfully ingested note {note.id} to Atlas")
        return True

    except Exception as e:
        logger.error(f"Failed to ingest note {note.id} to Atlas: {e}")
        return False


@router.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint for TrojanHorse integration."""
    return {
        "status": "ok",
        "service": "Atlas TrojanHorse Integration",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/ingest", response_model=IngestResponse)
async def ingest_single_note(
    note: IngestNote,
    x_api_key: str = Header(default=None)
):
    """
    Ingest a single note from TrojanHorse.

    This endpoint accepts a single TrojanHorse note and adds it to Atlas
    for long-term storage and integration with the broader knowledge base.
    """
    # Validate API key if configured
    validate_api_key(x_api_key)

    try:
        logger.info(f"Receiving single note from TrojanHorse: {note.id}")

        success = await ingest_note_to_atlas(note)

        if success:
            return IngestResponse(
                status="ok",
                message=f"Note '{note.title}' successfully ingested",
                count=1
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to ingest note"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting single note: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


@router.post("/ingest/batch", response_model=IngestResponse)
async def ingest_batch_notes(
    notes: List[IngestNote],
    x_api_key: str = Header(default=None)
):
    """
    Ingest multiple notes from TrojanHorse in batch.

    This endpoint accepts multiple TrojanHorse notes and adds them to Atlas
    efficiently. This is the recommended endpoint for promotion workflows.
    """
    # Validate API key if configured
    validate_api_key(x_api_key)

    if not notes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No notes provided in batch"
        )

    if len(notes) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size too large (max 100 notes per request)"
        )

    try:
        logger.info(f"Receiving batch of {len(notes)} notes from TrojanHorse")

        success_count = 0
        failed_notes = []

        for note in notes:
            if await ingest_note_to_atlas(note):
                success_count += 1
            else:
                failed_notes.append(note.id)

        if success_count > 0:
            message = f"Successfully ingested {success_count} notes"
            if failed_notes:
                message += f", failed to ingest {len(failed_notes)} notes"

            return IngestResponse(
                status="ok",
                message=message,
                count=success_count
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to ingest any notes"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting batch notes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_trojanhorse_stats(x_api_key: str = Header(default=None)):
    """Get statistics about TrojanHorse content in Atlas."""
    # Validate API key if configured
    validate_api_key(x_api_key)

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

        from helpers.simple_database import SimpleDatabase

        db = SimpleDatabase()

        with db.get_connection() as conn:
            # Get TrojanHorse content statistics
            th_stats = conn.execute('''
                SELECT
                    COUNT(*) as total_notes,
                    COUNT(CASE WHEN metadata LIKE '%class_type":"work"%' THEN 1 END) as work_notes,
                    COUNT(CASE WHEN metadata LIKE '%class_type":"personal"%' THEN 1 END) as personal_notes,
                    COUNT(CASE WHEN metadata LIKE '%"category": "meeting"%' THEN 1 END) as meeting_notes,
                    COUNT(CASE WHEN metadata LIKE '%"category": "idea"%' THEN 1 END) as idea_notes,
                    COUNT(CASE WHEN metadata LIKE '%"category": "task"%' THEN 1 END) as task_notes,
                    COUNT(DISTINCT json_extract(metadata, '$.project')) as unique_projects
                FROM content
                WHERE metadata LIKE '%source_system":"TrojanHorse"%'
            ''').fetchone()

            # Get recent activity
            recent_notes = conn.execute('''
                SELECT title, created_at, json_extract(metadata, '$.category') as category
                FROM content
                WHERE metadata LIKE '%source_system":"TrojanHorse"%'
                ORDER BY created_at DESC
                LIMIT 10
            ''').fetchall()

            # Get project breakdown
            project_stats = conn.execute('''
                SELECT
                    json_extract(metadata, '$.project') as project,
                    COUNT(*) as count
                FROM content
                WHERE metadata LIKE '%source_system":"TrojanHorse"%'
                    AND json_extract(metadata, '$.project') IS NOT NULL
                    AND json_extract(metadata, '$.project') != '""'
                GROUP BY json_extract(metadata, '$.project')
                ORDER BY count DESC
                LIMIT 20
            ''').fetchall()

        return {
            "trojanhorse_stats": {
                "total_notes": th_stats['total_notes'],
                "work_notes": th_stats['work_notes'],
                "personal_notes": th_stats['personal_notes'],
                "meeting_notes": th_stats['meeting_notes'],
                "idea_notes": th_stats['idea_notes'],
                "task_notes": th_stats['task_notes'],
                "unique_projects": th_stats['unique_projects']
            },
            "recent_activity": [
                {
                    "title": note['title'],
                    "created_at": note['created_at'],
                    "category": note['category']
                }
                for note in recent_notes
            ],
            "project_breakdown": [
                {
                    "project": stat['project'],
                    "count": stat['count']
                }
                for stat in project_stats if stat['project']
            ]
        }

    except Exception as e:
        logger.error(f"Error getting TrojanHorse stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )