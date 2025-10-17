from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import json
from datetime import datetime
import os
import sys

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from helpers.simple_database import SimpleDatabase

router = APIRouter()

class WorkerRegistration(BaseModel):
    worker_id: str
    capabilities: List[str]
    platform: str
    whisper_available: bool = False
    ytdlp_available: bool = False
    metadata: Optional[Dict[str, Any]] = None

class JobResult(BaseModel):
    job_id: str
    worker_id: str
    status: str  # 'completed', 'failed'
    result: Dict[str, Any]
    timestamp: float

class TranscriptionJob(BaseModel):
    type: str  # 'transcribe_url', 'transcribe_podcast', 'transcribe_youtube'
    data: Dict[str, Any]
    priority: int = 5
    created_by: str = "system"

@router.post("/register")
async def register_worker(registration: WorkerRegistration):
    """Register a new worker with Atlas"""
    try:
        db = SimpleDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()

        # Create workers table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                worker_id TEXT PRIMARY KEY,
                capabilities TEXT,
                platform TEXT,
                whisper_available INTEGER,
                ytdlp_available INTEGER,
                metadata TEXT,
                registered_at TEXT,
                last_seen TEXT,
                status TEXT DEFAULT 'active'
            )
        """)

        # Insert or update worker
        cursor.execute("""
            INSERT OR REPLACE INTO workers
            (worker_id, capabilities, platform, whisper_available, ytdlp_available,
             metadata, registered_at, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """, (
            registration.worker_id,
            json.dumps(registration.capabilities),
            registration.platform,
            1 if registration.whisper_available else 0,
            1 if registration.ytdlp_available else 0,
            json.dumps(registration.metadata or {}),
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        return {"success": True, "message": f"Worker {registration.worker_id} registered"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Worker registration failed: {str(e)}")

@router.get("/jobs")
async def get_jobs(worker_id: str, capabilities: str = ""):
    """Get available jobs for a worker"""
    try:
        db = SimpleDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()

        # Update worker last_seen
        cursor.execute("""
            UPDATE workers SET last_seen = ? WHERE worker_id = ?
        """, (datetime.utcnow().isoformat(), worker_id))

        # Create jobs table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_jobs (
                id TEXT PRIMARY KEY,
                type TEXT,
                data TEXT,
                priority INTEGER,
                status TEXT DEFAULT 'pending',
                assigned_worker TEXT,
                created_at TEXT,
                assigned_at TEXT,
                completed_at TEXT,
                result TEXT
            )
        """)

        # Get pending jobs that match worker capabilities
        worker_caps = [cap.strip() for cap in capabilities.split(',') if cap.strip()]

        if worker_caps:
            placeholders = ','.join(['?' for _ in worker_caps])
            cursor.execute(f"""
                SELECT id, type, data, priority, created_at
                FROM worker_jobs
                WHERE status = 'pending' AND type IN ({placeholders})
                ORDER BY priority DESC, created_at ASC
                LIMIT 5
            """, worker_caps)
        else:
            cursor.execute("""
                SELECT id, type, data, priority, created_at
                FROM worker_jobs
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 5
            """)

        job_rows = cursor.fetchall()

        # Assign jobs to worker
        jobs = []
        for job_row in job_rows:
            job_id, job_type, data_json, priority, created_at = job_row

            # Mark as assigned
            cursor.execute("""
                UPDATE worker_jobs
                SET status = 'assigned', assigned_worker = ?, assigned_at = ?
                WHERE id = ?
            """, (worker_id, datetime.utcnow().isoformat(), job_id))

            jobs.append({
                'id': job_id,
                'type': job_type,
                'data': json.loads(data_json),
                'priority': priority,
                'created_at': created_at
            })

        conn.commit()
        conn.close()

        return {"jobs": jobs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get jobs: {str(e)}")

@router.post("/results")
async def submit_job_result(result: JobResult):
    """Receive job results from workers"""
    try:
        db = SimpleDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()

        # Update job status
        cursor.execute("""
            UPDATE worker_jobs
            SET status = ?, result = ?, completed_at = ?
            WHERE id = ?
        """, (
            result.status,
            json.dumps(result.result),
            datetime.utcnow().isoformat(),
            result.job_id
        ))

        # If completed successfully, process the transcript
        if result.status == 'completed' and 'transcript' in result.result:
            transcript_data = {
                'filename': result.result.get('filename', f"worker_job_{result.job_id}"),
                'transcript': result.result['transcript'],
                'source': f'worker_{result.worker_id}',
                'metadata': json.dumps({
                    'job_id': result.job_id,
                    'worker_id': result.worker_id,
                    'source_url': result.result.get('source_url', result.result.get('video_url', '')),
                    'title': result.result.get('title', ''),
                    'length': result.result.get('length', 0)
                }),
                'created_at': datetime.utcnow().isoformat(),
                'processed': False
            }

            # Store transcript for Atlas processing
            transcript_id = db.store_transcription(transcript_data)

            # Add to content pipeline
            content_id = db.store_content(
                content=transcript_data['transcript'],
                title=transcript_data['filename'],
                url=result.result.get('source_url', f"worker://{result.job_id}"),
                content_type="transcription",
                metadata=transcript_data
            )

        conn.commit()
        conn.close()

        return {"success": True, "message": "Job result received"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process job result: {str(e)}")

@router.post("/jobs")
async def create_job(job: TranscriptionJob):
    """Create a new transcription job for workers"""
    try:
        import uuid

        db = SimpleDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()

        # Create jobs table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_jobs (
                id TEXT PRIMARY KEY,
                type TEXT,
                data TEXT,
                priority INTEGER,
                status TEXT DEFAULT 'pending',
                assigned_worker TEXT,
                created_at TEXT,
                assigned_at TEXT,
                completed_at TEXT,
                result TEXT
            )
        """)

        job_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO worker_jobs (id, type, data, priority, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            job_id,
            job.type,
            json.dumps(job.data),
            job.priority,
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        return {"success": True, "job_id": job_id, "message": "Job created"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

@router.get("/status")
async def worker_status():
    """Get worker and job status"""
    try:
        db = SimpleDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()

        # Get worker counts
        cursor.execute("SELECT COUNT(*) FROM workers WHERE status = 'active'")
        result = cursor.fetchone()
        active_workers = result[0] if result else 0

        cursor.execute("SELECT COUNT(*) FROM workers")
        result = cursor.fetchone()
        total_workers = result[0] if result else 0

        # Get job counts
        cursor.execute("SELECT status, COUNT(*) FROM worker_jobs GROUP BY status")
        job_counts = dict(cursor.fetchall())

        # Get recent workers
        cursor.execute("""
            SELECT worker_id, platform, capabilities, last_seen
            FROM workers
            WHERE status = 'active'
            ORDER BY last_seen DESC
            LIMIT 10
        """)
        recent_workers = []
        for row in cursor.fetchall():
            recent_workers.append({
                'worker_id': row[0],
                'platform': row[1],
                'capabilities': json.loads(row[2]),
                'last_seen': row[3]
            })

        conn.close()

        return {
            'workers': {
                'active': active_workers,
                'total': total_workers,
                'recent': recent_workers
            },
            'jobs': {
                'pending': job_counts.get('pending', 0),
                'assigned': job_counts.get('assigned', 0),
                'completed': job_counts.get('completed', 0),
                'failed': job_counts.get('failed', 0),
                'total': sum(job_counts.values())
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get worker status: {str(e)}")