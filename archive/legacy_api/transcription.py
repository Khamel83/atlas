from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import sqlite3
import json
from datetime import datetime
import os
import sys

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from helpers.simple_database import SimpleDatabase

router = APIRouter()

class TranscriptionRequest(BaseModel):
    filename: str
    transcript: str
    source: str = "external"
    metadata: Optional[dict] = None

class TranscriptionResponse(BaseModel):
    success: bool
    message: str
    transcription_id: Optional[int] = None

@router.post("/", response_model=TranscriptionResponse)
async def create_transcription(request: TranscriptionRequest):
    """
    Receive transcription from Mac Mini client or other sources
    """
    try:
        # Initialize database
        db = SimpleDatabase()

        # Prepare transcription data
        transcription_data = {
            'filename': request.filename,
            'transcript': request.transcript,
            'source': request.source,
            'metadata': json.dumps(request.metadata or {}),
            'created_at': datetime.utcnow().isoformat(),
            'processed': False
        }

        # Store in database
        transcription_id = db.store_transcription(transcription_data)

        # Queue for processing (add to processing queue)
        processing_data = {
            'type': 'transcription',
            'content': request.transcript,
            'title': request.filename,
            'url': f"transcription://{request.filename}",
            'source': request.source,
            'metadata': request.metadata or {}
        }

        # Add to content processing queue
        content_id = db.store_content(
            content=request.transcript,
            title=request.filename,
            url=f"transcription://{request.filename}",
            content_type="transcription",
            metadata=processing_data
        )

        return TranscriptionResponse(
            success=True,
            message=f"Transcription received and queued for processing",
            transcription_id=transcription_id
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process transcription: {str(e)}"
        )

@router.get("/status")
async def transcription_status():
    """
    Get transcription processing status
    """
    try:
        db_manager = DatabaseManager()

        # Get transcription counts
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM transcriptions")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transcriptions WHERE processed = 1")
        processed = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transcriptions WHERE source = 'mac_mini_client'")
        mac_mini = cursor.fetchone()[0]

        conn.close()

        return {
            "total_transcriptions": total,
            "processed": processed,
            "pending": total - processed,
            "mac_mini_submissions": mac_mini,
            "success_rate": f"{(processed/total*100):.1f}%" if total > 0 else "0%"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get transcription status: {str(e)}"
        )

@router.get("/recent")
async def recent_transcriptions(limit: int = 10):
    """
    Get recent transcriptions
    """
    try:
        db = SimpleDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT filename, source, created_at, processed, LENGTH(transcript) as length
            FROM transcriptions
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        results = cursor.fetchall()
        conn.close()

        transcriptions = []
        for row in results:
            transcriptions.append({
                "filename": row[0],
                "source": row[1],
                "created_at": row[2],
                "processed": bool(row[3]),
                "transcript_length": row[4]
            })

        return {"transcriptions": transcriptions}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recent transcriptions: {str(e)}"
        )