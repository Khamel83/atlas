import datetime
import json
import os
import sys
from urllib.parse import urlencode

# Add parent directory to Python path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import zipfile
import magic
import mimetypes

# Cognitive Features
try:
    from ask.insights.pattern_detector import PatternDetector
    from ask.proactive.surfacer import ProactiveSurfacer
    from ask.recall.recall_engine import RecallEngine
    from ask.socratic.question_engine import QuestionEngine
    from ask.temporal.temporal_engine import TemporalEngine
    ASK_AVAILABLE = True
except ImportError:
    ASK_AVAILABLE = False

from helpers.metadata_manager import MetadataManager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# For demo: instantiate with default config (replace with real config/manager in production)
def get_metadata_manager():
    try:
        from helpers.config import load_config

        config = load_config()
    except Exception:
        config = {}
    return MetadataManager(config)


app = FastAPI(title="Atlas Cognitive Platform")

templates = Jinja2Templates(directory="web/templates")

# Path to the scheduler's SQLite job store (should match Atlas scheduler)
JOBSTORE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scheduler.db"
)  # Unified job store for persistence

# Simple in-memory log for job runs (MVP)
job_logs = {}


def log_job_run(job_id, message):
    """Append a log entry for a job (in-memory, last 50 entries)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    job_logs.setdefault(job_id, []).append(f"[{now}] {message}")
    job_logs[job_id] = job_logs[job_id][-50:]


# APScheduler instance (paused, for inspection and management only)
scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{JOBSTORE_PATH}")}
)
scheduler.start(paused=True)


# Dummy function for new jobs (MVP)
def dummy_job():
    """A placeholder job function for demonstration purposes."""
    log_job_run("dummy", "Dummy job executed.")
    print("Dummy job executed.")


# Map job IDs to their log file paths for ingestion jobs
INGESTION_LOG_PATHS = {
    "weekly_article_ingestion": os.path.join(
        os.path.dirname(__file__), "..", "output", "articles", "ingest.log"
    ),
    "weekly_podcast_ingestion": os.path.join(
        os.path.dirname(__file__), "..", "output", "podcasts", "ingest.log"
    ),
    "weekly_youtube_ingestion": os.path.join(
        os.path.dirname(__file__), "..", "output", "youtube", "ingest.log"
    ),
}


def read_log_tail(log_path, n=50):
    """Read the last n lines from a log file."""
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
        return lines[-n:]
    except Exception:
        return ["No log file found or unable to read log."]


@app.get("/", response_class=HTMLResponse)
def root():
    """Atlas main dashboard with navigation to all features."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Atlas - Personal AI Dashboard</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 2rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 {
                font-size: 3rem;
                text-align: center;
                margin-bottom: 1rem;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .subtitle {
                text-align: center;
                font-size: 1.2rem;
                margin-bottom: 3rem;
                opacity: 0.9;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 2rem;
                margin-bottom: 3rem;
            }
            .dashboard-card {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 2rem;
                text-decoration: none;
                color: white;
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .dashboard-card:hover {
                transform: translateY(-5px);
                background: rgba(255, 255, 255, 0.2);
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            .dashboard-icon {
                font-size: 3rem;
                text-align: center;
                margin-bottom: 1rem;
            }
            .dashboard-title {
                font-size: 1.5rem;
                font-weight: 600;
                text-align: center;
                margin-bottom: 1rem;
            }
            .dashboard-description {
                text-align: center;
                opacity: 0.8;
                font-size: 0.9rem;
            }
            .quick-links {
                text-align: center;
                margin-top: 2rem;
            }
            .quick-link {
                display: inline-block;
                margin: 0 1rem;
                padding: 0.5rem 1rem;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 25px;
                text-decoration: none;
                color: white;
                font-size: 0.9rem;
                transition: all 0.3s ease;
            }
            .quick-link:hover {
                background: rgba(255, 255, 255, 0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 Atlas</h1>
            <p class="subtitle">Your Personal AI Knowledge System</p>

            <div class="dashboard-grid">
                <a href="/mobile" class="dashboard-card">
                    <div class="dashboard-icon">📱</div>
                    <div class="dashboard-title">Mobile Dashboard</div>
                    <div class="dashboard-description">Touch-optimized interface with content management, search filters, and all cognitive features</div>
                </a>

                <a href="/ask/html" class="dashboard-card">
                    <div class="dashboard-icon">🧠</div>
                    <div class="dashboard-title">Cognitive AI</div>
                    <div class="dashboard-description">6 AI-powered features: proactive surfacing, temporal analysis, Socratic questions, active recall</div>
                </a>

                <a href="/system" class="dashboard-card">
                    <div class="dashboard-icon">📊</div>
                    <div class="dashboard-title">System Overview</div>
                    <div class="dashboard-description">Content statistics, recent activity, system health, and quick actions</div>
                </a>

                <a href="/upload" class="dashboard-card">
                    <div class="dashboard-icon">📁</div>
                    <div class="dashboard-title">File Import</div>
                    <div class="dashboard-description">Upload and process files safely - CSV, JSON, TXT, ZIP archives with automatic content detection</div>
                </a>
            </div>

            <div class="quick-links">
                <a href="/ask/proactive" class="quick-link">🔄 Proactive API</a>
                <a href="/ask/temporal" class="quick-link">⏰ Temporal API</a>
                <a href="/ask/patterns" class="quick-link">🔍 Patterns API</a>
                <a href="/ask/recall" class="quick-link">🧠 Recall API</a>
                <a href="/jobs" class="quick-link">📊 Jobs API</a>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/jobs", response_class=JSONResponse)
def list_jobs():
    """Return all jobs as JSON (API endpoint)."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time),
                "trigger": str(job.trigger),
                "func": str(job.func_ref),
                "args": job.args,
                "kwargs": job.kwargs,
                "enabled": not job.paused if hasattr(job, "paused") else True,
            }
        )
    return {"jobs": jobs}


# Enhance jobs_html to show last run status and timestamp for ingestion jobs
@app.get("/jobs/html", response_class=HTMLResponse)
def jobs_html(request: Request, msg: str = "", error: str = ""):
    """Main jobs UI: list jobs, show messages/errors."""
    jobs = []
    for job in scheduler.get_jobs():
        job_info = {
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time),
            "trigger": str(job.trigger),
            "func": str(job.func_ref),
            "args": job.args,
            "kwargs": job.kwargs,
            "enabled": not job.paused if hasattr(job, "paused") else True,
        }
        # For ingestion jobs, try to get last run status and timestamp from log file
        if job.id in INGESTION_LOG_PATHS:
            log_path = INGESTION_LOG_PATHS[job.id]
            try:
                with open(log_path, "r") as f:
                    lines = f.readlines()
                # Look for last status line
                last_status = None
                last_time = None
                for line in reversed(lines):
                    if "ingestion complete" in line.lower() or "error" in line.lower():
                        last_status = (
                            "Success" if "complete" in line.lower() else "Error"
                        )
                        # Try to extract timestamp if present
                        if line.startswith("["):
                            last_time = line.split("]")[0].strip("[]")
                        break
                job_info["last_status"] = last_status or "Unknown"
                job_info["last_time"] = last_time or "-"
            except Exception:
                job_info["last_status"] = "-"
                job_info["last_time"] = "-"
        else:
            job_info["last_status"] = "-"
            job_info["last_time"] = "-"
        jobs.append(job_info)
    return templates.TemplateResponse(
        "jobs.html", {"request": request, "jobs": jobs, "msg": msg, "error": error}
    )


@app.get("/jobs/{job_id}/edit", response_class=HTMLResponse)
def edit_job_form(request: Request, job_id: str, msg: str = "", error: str = ""):
    """Render the edit form for a job (cron string only)."""
    job = scheduler.get_job(job_id)
    if not job:
        return RedirectResponse(url="/jobs/html?error=Job+not+found", status_code=303)
    cron_str = (
        job.trigger.cronspec if hasattr(job.trigger, "cronspec") else str(job.trigger)
    )
    return templates.TemplateResponse(
        "edit_job.html",
        {
            "request": request,
            "job": {"id": job.id, "name": job.name, "cron": cron_str},
            "msg": msg,
            "error": error,
        },
    )


@app.post("/jobs/{job_id}/edit")
def edit_job(job_id: str, cron: str = Form(...)):
    """Update a job's cron schedule."""
    job = scheduler.get_job(job_id)
    if job:
        try:
            trigger = CronTrigger.from_crontab(cron)
            scheduler.reschedule_job(job_id, trigger=trigger)
            log_job_run(job_id, f"Job rescheduled to cron: {cron}")
            params = urlencode({"msg": "Job updated."})
            return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
        except Exception as e:
            print(f"Error editing job: {e}")
            params = urlencode({"error": f"Invalid cron string: {cron}"})
            return RedirectResponse(
                url=f"/jobs/{job_id}/edit?{params}", status_code=303
            )
    return RedirectResponse(url="/jobs/html", status_code=303)


@app.post("/jobs/{job_id}/trigger")
def trigger_job(job_id: str):
    """Manually trigger a job to run immediately."""
    job = scheduler.get_job(job_id)
    if job:
        try:
            job.modify(next_run_time=None)
            scheduler.wakeup()
            log_job_run(job_id, "Job manually triggered.")
            params = urlencode({"msg": "Job triggered."})
            return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
        except Exception as e:
            print(f"Error triggering job: {e}")
            params = urlencode({"error": "Failed to trigger job."})
            return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
    return RedirectResponse(url="/jobs/html", status_code=303)





@app.post("/jobs/{job_id}/enable")
def enable_job(job_id: str):
    """Enable (resume) a paused job."""
    job = scheduler.get_job(job_id)
    if job:
        scheduler.resume_job(job_id)
        log_job_run(job_id, "Job enabled.")
        params = urlencode({"msg": "Job enabled."})
        return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
    return RedirectResponse(url="/jobs/html", status_code=303)


@app.post("/jobs/{job_id}/disable")
def disable_job(job_id: str):
    """Disable (pause) a job."""
    job = scheduler.get_job(job_id)
    if job:
        scheduler.pause_job(job_id)
        log_job_run(job_id, "Job disabled.")
        params = urlencode({"msg": "Job disabled."})
        return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
    return RedirectResponse(url="/jobs/html", status_code=303)


@app.post("/jobs/{job_id}/delete")
def delete_job(job_id: str):
    """Delete a job from the scheduler."""
    scheduler.remove_job(job_id)
    log_job_run(job_id, "Job deleted.")
    params = urlencode({"msg": "Job deleted."})
    return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)


@app.post("/jobs/add")
def add_job(name: str = Form(...), cron: str = Form(...)):
    """Add a new job with the given name and cron string (dummy function)."""
    try:
        trigger = CronTrigger.from_crontab(cron)
        scheduler.add_job(dummy_job, trigger, id=name, name=name, replace_existing=True)
        log_job_run(name, f"Job added with cron: {cron}")
        params = urlencode({"msg": "Job added."})
        return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
    except Exception as e:
        print(f"Error adding job: {e}")
        params = urlencode({"error": f"Invalid cron string: {cron}"})
        return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)


# Future endpoints:
# - GET /jobs/{job_id}/logs (view logs)


@app.get("/ask/proactive", response_class=JSONResponse)
def ask_proactive():
    """Surface forgotten/stale content (top 5)."""
    mgr = get_metadata_manager()
    surfacer = ProactiveSurfacer(mgr)
    items = surfacer.surface_forgotten_content(n=5)
    return {
        "forgotten": [
            {
                "title": getattr(i, "title", None),
                "updated_at": getattr(i, "updated_at", None),
            }
            for i in items
        ]
    }


@app.get("/ask/temporal", response_class=JSONResponse)
def ask_temporal():
    """Show time-aware content relationships (max 10)."""
    mgr = get_metadata_manager()
    engine = TemporalEngine(mgr)
    rels = engine.get_time_aware_relationships(max_delta_days=2)
    return {
        "relationships": [
            {
                "from": getattr(a, "title", None),
                "to": getattr(b, "title", None),
                "days": d,
            }
            for a, b, d in rels[:10]
        ]
    }


@app.post("/ask/socratic", response_class=JSONResponse)
def ask_socratic(content: str = Form(...)):
    """Generate Socratic questions from content."""
    engine = QuestionEngine()
    questions = engine.generate_questions(content)
    return {"questions": questions}


@app.get("/ask/recall", response_class=JSONResponse)
def ask_recall():
    """Show most overdue items for spaced repetition (top 5)."""
    mgr = get_metadata_manager()
    engine = RecallEngine(mgr)
    items = engine.schedule_spaced_repetition(n=5)
    return {
        "due_for_review": [
            {
                "title": getattr(i, "title", None),
                "last_reviewed": getattr(i, "type_specific", {}).get(
                    "last_reviewed", None
                ),
            }
            for i in items
        ]
    }


@app.get("/ask/patterns", response_class=JSONResponse)
def ask_patterns():
    """Show top tags and sources (top 5)."""
    mgr = get_metadata_manager()
    detector = PatternDetector(mgr)
    patterns = detector.find_patterns(n=5)
    return {"top_tags": patterns["top_tags"], "top_sources": patterns["top_sources"]}


@app.get("/ask/html", response_class=HTMLResponse)
async def ask_dashboard(request: Request, feature: str = ""):
    """Render the cognitive amplification dashboard with the selected feature."""
    mgr = get_metadata_manager()
    data = None
    if feature == "proactive":
        surfacer = ProactiveSurfacer(mgr)
        data = {
            "forgotten": [
                {
                    "title": getattr(i, "title", None),
                    "updated_at": getattr(i, "updated_at", None),
                }
                for i in surfacer.surface_forgotten_content(n=5)
            ]
        }
    elif feature == "temporal":
        engine = TemporalEngine(mgr)
        rels = engine.get_time_aware_relationships(max_delta_days=2)
        data = {
            "relationships": [
                {
                    "from": getattr(a, "title", None),
                    "to": getattr(b, "title", None),
                    "days": d,
                }
                for a, b, d in rels[:10]
            ]
        }
    elif feature == "recall":
        engine = RecallEngine(mgr)
        items = engine.schedule_spaced_repetition(n=5)
        data = {
            "due_for_review": [
                {
                    "title": getattr(i, "title", None),
                    "last_reviewed": getattr(i, "type_specific", {}).get(
                        "last_reviewed", None
                    ),
                }
                for i in items
            ]
        }
    elif feature == "patterns":
        detector = PatternDetector(mgr)
        patterns = detector.find_patterns(n=5)
        data = {
            "top_tags": patterns["top_tags"],
            "top_sources": patterns["top_sources"],
        }
    # Socratic handled by POST
    return templates.TemplateResponse(
        "ask_dashboard.html", {"request": request, "feature": feature, "data": data}
    )


@app.post("/ask/html", response_class=HTMLResponse)
async def ask_dashboard_post(
    request: Request, feature: str = Form(""), content: str = Form("")
):
    """Handle Socratic question form submission."""
    data = None
    if feature == "socratic" and content:
        engine = QuestionEngine()
        questions = engine.generate_questions(content)
        data = {"questions": questions}
    return templates.TemplateResponse(
        "ask_dashboard.html", {"request": request, "feature": feature, "data": data}
    )


# Mobile-optimized routes
@app.get("/mobile", response_class=HTMLResponse)
async def mobile_dashboard(request: Request, feature: str = "", search: str = "",
                          date_filter: str = "", type_filter: str = "", source_filter: str = ""):
    """Mobile-optimized cognitive dashboard."""
    data = None
    recent_content = None

    if not ASK_AVAILABLE:
        return templates.TemplateResponse(
            "mobile_dashboard.html",
            {"request": request, "feature": feature, "data": {"error": "Cognitive features not available"}}
        )

    mgr = get_metadata_manager()

    # Handle content browsing
    if feature == "browse" or not feature:
        import sqlite3
        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        # Build WHERE conditions based on filters
        where_conditions = ["title IS NOT NULL AND title != ''"]
        params = []

        if search:
            where_conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%'])

        if type_filter:
            where_conditions.append("content_type LIKE ?")
            params.append(f'%{type_filter}%')

        if date_filter:
            import datetime
            today = datetime.date.today()
            if date_filter == "today":
                where_conditions.append("DATE(created_at) = ?")
                params.append(today.isoformat())
            elif date_filter == "week":
                week_ago = today - datetime.timedelta(days=7)
                where_conditions.append("DATE(created_at) >= ?")
                params.append(week_ago.isoformat())
            elif date_filter == "month":
                month_ago = today - datetime.timedelta(days=30)
                where_conditions.append("DATE(created_at) >= ?")
                params.append(month_ago.isoformat())
            elif date_filter == "year":
                year_ago = today - datetime.timedelta(days=365)
                where_conditions.append("DATE(created_at) >= ?")
                params.append(year_ago.isoformat())

        where_clause = " AND ".join(where_conditions)

        cursor.execute(f"""
            SELECT id, title, content, content_type, created_at
            FROM content
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT 20
        """, params)

        recent_content = [
            {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "content_type": row[3],
                "created_at": row[4]
            }
            for row in cursor.fetchall()
        ]
        conn.close()

    # Handle cognitive features (same logic as desktop)
    elif feature == "proactive":
        # Get real old content that user might have forgotten
        import sqlite3
        import random
        from datetime import datetime, timedelta

        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        # Find content older than 2 days that user might want to revisit
        days_ago = (datetime.now() - timedelta(days=2)).isoformat()
        cursor.execute("""
            SELECT id, title, created_at, content_type
            FROM content
            WHERE created_at < ? AND title IS NOT NULL AND title != ''
            ORDER BY RANDOM()
            LIMIT 10
        """, (days_ago,))

        results = cursor.fetchall()
        conn.close()


        if results:
            data = {
                "forgotten": [
                    {
                        "id": row[0],
                        "title": row[1][:80] + "..." if len(row[1]) > 80 else row[1],
                        "updated_at": row[2][:10],
                        "type": row[3] or "article"
                    }
                    for row in results
                ]
            }
        else:
            data = {"forgotten": [{"title": "No older content found - try refreshing!", "updated_at": "Debug", "type": "info"}]}
    elif feature == "temporal":
        engine = TemporalEngine(mgr)
        rels = engine.identify_temporal_relationships(n=10)
        data = {
            "relationships": [
                {
                    "from": getattr(a, "title", None),
                    "to": getattr(b, "title", None),
                    "days": d,
                }
                for a, b, d in rels[:10]
            ]
        }
    elif feature == "recall":
        # Get content from 1-4 weeks ago for spaced repetition review
        import sqlite3
        from datetime import datetime, timedelta

        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        # Find content from 1-3 days ago for review
        start_date = (datetime.now() - timedelta(days=3)).isoformat()
        end_date = (datetime.now() - timedelta(days=1)).isoformat()

        cursor.execute("""
            SELECT title, created_at, content_type, url
            FROM content
            WHERE created_at BETWEEN ? AND ?
              AND title IS NOT NULL AND title != ''
            ORDER BY RANDOM()
            LIMIT 10
        """, (start_date, end_date))

        results = cursor.fetchall()
        conn.close()

        if results:
            data = {
                "due_for_review": [
                    {
                        "title": row[0][:60] + "..." if len(row[0]) > 60 else row[0],
                        "last_reviewed": f"Saved {row[1][:10]}",
                        "type": row[2] or "article",
                        "url": row[3]
                    }
                    for row in results
                ]
            }
        else:
            data = {"due_for_review": [{"title": "No content ready for review yet", "last_reviewed": "Check back later", "type": "info"}]}
    elif feature == "patterns":
        # Get real patterns from user's content
        import sqlite3
        from collections import Counter

        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        # Analyze content types
        cursor.execute("""
            SELECT content_type, COUNT(*) as count
            FROM content
            WHERE content_type IS NOT NULL AND content_type != ''
            GROUP BY content_type
            ORDER BY count DESC
            LIMIT 10
        """)
        content_types = cursor.fetchall()

        # Analyze domains from URLs
        cursor.execute("""
            SELECT substr(url, instr(url, '://') + 3,
                         CASE WHEN instr(substr(url, instr(url, '://') + 3), '/') > 0
                              THEN instr(substr(url, instr(url, '://') + 3), '/') - 1
                              ELSE length(substr(url, instr(url, '://') + 3)) END) as domain,
                   COUNT(*) as count
            FROM content
            WHERE url IS NOT NULL AND url LIKE 'http%'
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 10
        """)
        sources = cursor.fetchall()

        # Analyze creation patterns by day of week
        cursor.execute("""
            SELECT strftime('%w', created_at) as dow, COUNT(*) as count
            FROM content
            WHERE created_at IS NOT NULL
            GROUP BY dow
            ORDER BY count DESC
        """)
        day_patterns = cursor.fetchall()

        conn.close()

        # Convert day numbers to names
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        day_stats = [(days[int(row[0])], row[1]) for row in day_patterns if row[0].isdigit()]

        data = {
            "top_tags": [(f"{row[0]} ({row[1]} items)", row[1]) for row in content_types],
            "top_sources": [(row[0], row[1]) for row in sources if row[0]],
            "day_patterns": day_stats
        }

    return templates.TemplateResponse(
        "mobile_dashboard.html",
        {
            "request": request,
            "feature": feature,
            "data": data,
            "recent_content": recent_content,
            "search": search,
            "date_filter": date_filter,
            "type_filter": type_filter,
            "source_filter": source_filter
        }
    )


@app.post("/mobile", response_class=HTMLResponse)
async def mobile_dashboard_post(request: Request, feature: str = Form(""), content: str = Form("")):
    """Handle mobile form submissions."""
    data = None
    if feature == "socratic" and content:
        engine = QuestionEngine()
        questions = engine.generate_questions(content)
        data = {"questions": questions}

    return templates.TemplateResponse(
        "mobile_dashboard.html",
        {"request": request, "feature": feature, "data": data}
    )


# Content Management API Endpoints
@app.delete("/mobile/content/{content_id}")
async def delete_content(content_id: int):
    """Delete content item"""
    try:
        import sqlite3
        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        cursor.execute("DELETE FROM content WHERE id = ?", (content_id,))
        if cursor.rowcount == 0:
            conn.close()
            return {"success": False, "error": "Content not found"}

        conn.commit()
        conn.close()
        return {"success": True, "message": "Content deleted successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/mobile/content/{content_id}/tags")
async def tag_content(content_id: int, tags: str = Form(...)):
    """Add tags to content item"""
    try:
        import sqlite3
        import json
        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        # Check if content exists
        cursor.execute("SELECT tags FROM content WHERE id = ?", (content_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return {"success": False, "error": "Content not found"}

        # Parse existing tags
        existing_tags = json.loads(result[0] or "[]")
        new_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # Merge tags (avoid duplicates)
        all_tags = list(set(existing_tags + new_tags))

        cursor.execute("UPDATE content SET tags = ? WHERE id = ?",
                      (json.dumps(all_tags), content_id))
        conn.commit()
        conn.close()

        return {"success": True, "message": f"Tags added: {', '.join(new_tags)}", "tags": all_tags}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/mobile/content/{content_id}/archive")
async def archive_content(content_id: int):
    """Archive content item"""
    try:
        import sqlite3
        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        cursor.execute("UPDATE content SET archived = 1 WHERE id = ?", (content_id,))
        if cursor.rowcount == 0:
            conn.close()
            return {"success": False, "error": "Content not found"}

        conn.commit()
        conn.close()
        return {"success": True, "message": "Content archived successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/metrics", response_class=JSONResponse)
async def metrics():
    """System metrics endpoint for monitoring."""
    import sqlite3
    import psutil
    from datetime import datetime

    try:
        # Database metrics
        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        # Count total content items
        cursor.execute("SELECT COUNT(*) FROM content")
        total_content = cursor.fetchone()[0]

        # Count recent content (last 24 hours)
        from datetime import timedelta
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM content WHERE created_at > ?", (yesterday,))
        recent_content = cursor.fetchone()[0]

        conn.close()

        # System metrics
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')

        return {
            "timestamp": datetime.now().isoformat(),
            "service": "atlas-web",
            "status": "healthy",
            "metrics": {
                "content_total": total_content,
                "content_recent_24h": recent_content,
                "memory_used_percent": memory_info.percent,
                "disk_used_percent": disk_info.percent,
                "uptime_seconds": psutil.boot_time()
            }
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "service": "atlas-web",
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/content/{content_id}", response_class=HTMLResponse)
async def view_content(content_id: int):
    """Display full content for reading."""
    try:
        import sqlite3
        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, content, url, content_type, created_at, quality_score, quality_issues
            FROM content
            WHERE id = ?
        """, (content_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return "<h1>Content not found</h1>"

        content_data = {
            'id': row[0],
            'title': row[1] or 'Untitled',
            'content': row[2] or 'No content available',
            'url': row[3],
            'content_type': row[4] or 'unknown',
            'created_at': row[5][:10] if row[5] else 'Unknown',
            'quality_score': row[6] if row[6] is not None else 0.5,
            'quality_issues': row[7] or ''
        }

        # Determine quality classification
        score = content_data['quality_score']
        if score < 0.2:
            quality_class = 'failed'
            quality_label = 'FAILED'
            quality_color = '#dc2626'  # red
        elif score < 0.4:
            quality_class = 'stub'
            quality_label = 'STUB'
            quality_color = '#ea580c'  # orange
        elif score < 0.6:
            quality_class = 'low-quality'
            quality_label = 'LOW QUALITY'
            quality_color = '#ca8a04'  # yellow
        elif score < 0.8:
            quality_class = 'good'
            quality_label = 'GOOD'
            quality_color = '#16a34a'  # green
        else:
            quality_class = 'excellent'
            quality_label = 'EXCELLENT'
            quality_color = '#0d9488'  # teal

        # Format content for better reading
        content = content_data['content']
        podcast_metadata = {}

        if content_data['content_type'] == 'podcast':
            # Parse podcast metadata from content
            import re
            lines = content.split('\n')

            for line in lines[:10]:  # Check first 10 lines for metadata
                if line.startswith('Title: '):
                    podcast_metadata['show_title'] = line[7:].strip()
                elif line.startswith('Author: '):
                    podcast_metadata['author'] = line[8:].strip()
                elif line.startswith('Published: '):
                    podcast_metadata['published'] = line[11:].strip()
                elif line.startswith('Summary: '):
                    podcast_metadata['summary'] = line[9:].strip()

            # Skip metadata section and format transcript
            transcript_start = 0
            for i, line in enumerate(lines):
                if line.strip() == '' and i > 5:  # First empty line after metadata
                    transcript_start = i + 1
                    break

            transcript_content = '\n'.join(lines[transcript_start:])
            content = transcript_content.replace('\n\n', '<br><br>').replace('\n', '<br>')
        else:
            # For articles, preserve paragraphs
            paragraphs = content.split('\n\n')
            content = '<p>' + '</p><p>'.join([p.replace('\n', '<br>') for p in paragraphs if p.strip()]) + '</p>'

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{content_data['title']} - Atlas</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .header {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .content {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    font-size: 16px;
                    line-height: 1.8;
                }}
                .meta {{
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 10px;
                }}
                .back-link {{
                    color: #007AFF;
                    text-decoration: none;
                    font-weight: 500;
                    margin-bottom: 15px;
                    display: inline-block;
                }}
                .back-link:hover {{
                    text-decoration: underline;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 10px;
                }}
                p {{
                    margin-bottom: 15px;
                }}
                .transcript-marker {{
                    color: #007AFF;
                    font-weight: bold;
                    background: #f0f8ff;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <a href="/mobile" class="back-link">← Back to Atlas</a>
                <h1>{podcast_metadata.get('show_title', content_data['title'])}</h1>

                <div class="quality-indicator">
                    <span class="quality-badge" style="background-color: {quality_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">
                        {quality_label} ({content_data['quality_score']:.2f})
                    </span>
                    {f'<span style="margin-left: 10px; font-size: 12px; color: #666;">Issues: {content_data["quality_issues"]}</span>' if content_data['quality_issues'] else ''}
                </div>

                <div class="meta">
                    {'<span class="transcript-marker">PODCAST TRANSCRIPT</span>' if content_data['content_type'] == 'podcast' else ''}
                    {f'<br><strong>Host:</strong> {podcast_metadata["author"]}' if podcast_metadata.get('author') else ''}
                    {f'<br><strong>Published:</strong> {podcast_metadata["published"][:16]}' if podcast_metadata.get('published') else f'<br><strong>Added:</strong> {content_data["created_at"]}'}
                    {f'<br><strong>Summary:</strong> {podcast_metadata["summary"][:200]}{"..." if len(podcast_metadata.get("summary", "")) > 200 else ""}' if podcast_metadata.get('summary') else ''}
                    {f' • <a href="{content_data["url"]}" target="_blank">Original Source</a>' if content_data['url'] and not content_data['url'].startswith('inputs/') else ''}
                </div>

                {'<div class="reprocess-actions" style="margin-top: 15px;">' if quality_class in ['failed', 'stub', 'low-quality'] else ''}
                {'<button onclick="reprocessContent()" style="background: #f59e0b; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-right: 10px;">🔄 Reprocess Content</button>' if quality_class in ['failed', 'stub', 'low-quality'] else ''}
                {'<button onclick="markAsStub()" style="background: #dc2626; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">🗑️ Mark as Stub</button>' if quality_class in ['failed', 'stub', 'low-quality'] else ''}
                {'</div>' if quality_class in ['failed', 'stub', 'low-quality'] else ''}
            </div>
            <div class="content">
                {content[:50000]}
                {'<br><br><em>[Content truncated at 50,000 characters for performance]</em>' if len(content) > 50000 else ''}
            </div>

            <script>
                async function reprocessContent() {{
                    const contentId = {content_data['id']};
                    const button = event.target;

                    button.disabled = true;
                    button.textContent = '🔄 Processing...';

                    try {{
                        const response = await fetch(`/content/${{contentId}}/reprocess`, {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}}
                        }});

                        const result = await response.json();

                        if (result.success) {{
                            button.textContent = '✅ Queued for Reprocessing';
                            button.style.background = '#16a34a';
                            setTimeout(() => location.reload(), 2000);
                        }} else {{
                            button.textContent = '❌ Failed';
                            button.style.background = '#dc2626';
                            console.error('Reprocess failed:', result.error);
                        }}
                    }} catch (error) {{
                        button.textContent = '❌ Error';
                        button.style.background = '#dc2626';
                        console.error('Request failed:', error);
                    }}
                }}

                async function markAsStub() {{
                    const contentId = {content_data['id']};
                    const button = event.target;

                    if (!confirm('Mark this content as a stub? This will flag it as low quality.')) {{
                        return;
                    }}

                    button.disabled = true;
                    button.textContent = '🗑️ Marking...';

                    try {{
                        const response = await fetch(`/content/${{contentId}}/mark-stub`, {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}}
                        }});

                        const result = await response.json();

                        if (result.success) {{
                            button.textContent = '✅ Marked as Stub';
                            button.style.background = '#16a34a';
                            setTimeout(() => location.reload(), 2000);
                        }} else {{
                            button.textContent = '❌ Failed';
                            console.error('Mark stub failed:', result.error);
                        }}
                    }} catch (error) {{
                        button.textContent = '❌ Error';
                        console.error('Request failed:', error);
                    }}
                }}
            </script>
        </body>
        </html>
        """

    except Exception as e:
        return f"<h1>Error loading content: {e}</h1>"

@app.get("/system", response_class=HTMLResponse)
async def system_overview():
    """Useful system overview dashboard for users."""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        import psutil

        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        # Get content statistics
        cursor.execute("SELECT COUNT(*) FROM content")
        total_content = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'podcast'")
        podcast_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM content WHERE (content_type IS NULL OR content_type = '')")
        article_count = cursor.fetchone()[0]

        # Recent activity (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM content WHERE created_at > ?", (week_ago,))
        recent_additions = cursor.fetchone()[0]

        # Get latest additions with titles
        cursor.execute("""
            SELECT title, created_at, content_type
            FROM content
            WHERE title IS NOT NULL AND title != ''
            ORDER BY created_at DESC
            LIMIT 5
        """)
        latest_content = cursor.fetchall()

        # Get quality breakdown instead of just content types
        cursor.execute("""
            SELECT
                CASE
                    WHEN quality_score < 0.2 THEN 'Failed Content'
                    WHEN quality_score < 0.4 THEN 'Stub Content'
                    WHEN quality_score < 0.6 THEN 'Low Quality'
                    WHEN quality_score < 0.8 THEN 'Good Content'
                    ELSE 'Excellent Content'
                END as quality_display,
                COUNT(*) as count
            FROM content
            WHERE quality_score IS NOT NULL
            GROUP BY
                CASE
                    WHEN quality_score < 0.2 THEN 1
                    WHEN quality_score < 0.4 THEN 2
                    WHEN quality_score < 0.6 THEN 3
                    WHEN quality_score < 0.8 THEN 4
                    ELSE 5
                END
            ORDER BY
                CASE
                    WHEN quality_score < 0.2 THEN 1
                    WHEN quality_score < 0.4 THEN 2
                    WHEN quality_score < 0.6 THEN 3
                    WHEN quality_score < 0.8 THEN 4
                    ELSE 5
                END
        """)
        quality_breakdown = cursor.fetchall()

        # Get most problematic items count
        cursor.execute("SELECT COUNT(*) FROM content WHERE quality_score < 0.4")
        problematic_count = cursor.fetchone()[0]

        conn.close()

        # System info
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Atlas System Overview</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 1000px;
                    margin: 0 auto;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 2rem;
                }}
                .back-link {{
                    color: rgba(255,255,255,0.8);
                    text-decoration: none;
                    display: inline-block;
                    margin-bottom: 1rem;
                }}
                .back-link:hover {{
                    color: white;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1rem;
                    margin-bottom: 2rem;
                }}
                .stat-card {{
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    padding: 1.5rem;
                    text-align: center;
                    backdrop-filter: blur(10px);
                }}
                .stat-number {{
                    font-size: 2rem;
                    font-weight: bold;
                    margin-bottom: 0.5rem;
                }}
                .stat-label {{
                    opacity: 0.8;
                    font-size: 0.9rem;
                }}
                .section {{
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 15px;
                    padding: 2rem;
                    margin-bottom: 2rem;
                    backdrop-filter: blur(10px);
                }}
                .section h2 {{
                    margin-top: 0;
                    border-bottom: 2px solid rgba(255,255,255,0.2);
                    padding-bottom: 0.5rem;
                }}
                .recent-item {{
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                    padding: 1rem;
                    margin-bottom: 0.5rem;
                    border-left: 3px solid rgba(255,255,255,0.3);
                }}
                .item-title {{
                    font-weight: 600;
                    margin-bottom: 0.25rem;
                }}
                .item-meta {{
                    font-size: 0.85rem;
                    opacity: 0.7;
                }}
                .breakdown-item {{
                    display: flex;
                    justify-content: space-between;
                    padding: 0.5rem 0;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                }}
                .breakdown-item:last-child {{
                    border-bottom: none;
                }}
                .health-indicator {{
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    background: #4ade80;
                    margin-right: 0.5rem;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <a href="/" class="back-link">← Back to Atlas Dashboard</a>
                    <h1>📊 System Overview</h1>
                    <p><span class="health-indicator"></span>Atlas is running smoothly</p>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total_content:,}</div>
                        <div class="stat-label">Total Items</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{recent_additions}</div>
                        <div class="stat-label">Added This Week</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" style="color: #f59e0b;">{problematic_count:,}</div>
                        <div class="stat-label">Needs Reprocessing</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{memory_info.percent:.1f}%</div>
                        <div class="stat-label">Memory Usage</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{disk_info.percent:.1f}%</div>
                        <div class="stat-label">Disk Usage</div>
                    </div>
                </div>

                <div class="section">
                    <h2>⭐ Content Quality Breakdown</h2>
                    {''.join([f'<div class="breakdown-item"><span>{row[0]}</span><span>{row[1]:,}</span></div>' for row in quality_breakdown])}
                    {f'<div class="breakdown-item" style="border-top: 2px solid rgba(255,255,255,0.2); margin-top: 10px; padding-top: 10px;"><span><strong>Items Needing Attention</strong></span><span style="color: #f59e0b;"><strong>{problematic_count:,}</strong></span></div>' if problematic_count > 0 else ''}
                </div>

                <div class="section">
                    <h2>🆕 Recently Added</h2>
                    {''.join([f'''
                    <div class="recent-item">
                        <div class="item-title">{row[0][:80]}{"..." if len(row[0]) > 80 else ""}</div>
                        <div class="item-meta">{row[2] or "article"} • Added {row[1][:10]}</div>
                    </div>
                    ''' for row in latest_content])}
                </div>

                <div class="section">
                    <h2>🔗 Quick Actions</h2>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                        <a href="/mobile" style="display: block; background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; text-decoration: none; color: white; text-align: center;">
                            📱 Browse Content
                        </a>
                        <a href="/ask/html" style="display: block; background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; text-decoration: none; color: white; text-align: center;">
                            🧠 Cognitive Features
                        </a>
                        <a href="/metrics" style="display: block; background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; text-decoration: none; color: white; text-align: center;">
                            📈 System Metrics
                        </a>
                        <a href="https://github.com/Khamel83/atlas" target="_blank" style="display: block; background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; text-decoration: none; color: white; text-align: center;">
                            🔗 GitHub Repository
                        </a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    except Exception as e:
        return f"<h1>Error loading system overview: {e}</h1>"

@app.post("/content/{content_id}/reprocess")
async def reprocess_content(content_id: int):
    """Reprocess content to improve quality."""
    try:
        import sqlite3
        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        # Get current content info
        cursor.execute("SELECT title, url, content_type FROM content WHERE id = ?", (content_id,))
        row = cursor.fetchone()
        if not row:
            return {"success": False, "error": "Content not found"}

        title, url, content_type = row

        # Mark as reprocessing
        cursor.execute(
            "UPDATE content SET quality_score = 0.0, quality_issues = 'reprocessing' WHERE id = ?",
            (content_id,)
        )
        conn.commit()
        conn.close()

        # Use actual reprocessing pipeline
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from helpers.content_reprocessor import ContentReprocessor

            reprocessor = ContentReprocessor()
            result = reprocessor.reprocess_item(content_id)

            if result.success:
                improvement = result.new_quality - result.old_quality
                return {
                    "success": True,
                    "message": f"Content #{content_id} reprocessed successfully",
                    "old_quality": result.old_quality,
                    "new_quality": result.new_quality,
                    "improvement": improvement,
                    "method": result.method_used
                }
            else:
                return {
                    "success": False,
                    "error": result.error or "Reprocessing failed",
                    "message": f"Failed to reprocess content #{content_id}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error reprocessing content #{content_id}: {str(e)}"
            }

        return {
            "success": True,
            "message": f"Content #{content_id} reprocessing completed",
            "content_id": content_id,
            "status": "queued"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/reprocessing-status")
async def get_reprocessing_status():
    """Get current reprocessing status and progress."""
    try:
        import sqlite3
        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        # Quality distribution
        cursor.execute("""
            SELECT
                CASE
                    WHEN quality_score < 0.2 THEN 'Failed'
                    WHEN quality_score < 0.4 THEN 'Stub'
                    WHEN quality_score < 0.6 THEN 'Low Quality'
                    WHEN quality_score < 0.8 THEN 'Good'
                    ELSE 'Excellent'
                END as category,
                COUNT(*) as count
            FROM content
            WHERE quality_score IS NOT NULL AND quality_score > 0
            GROUP BY category
        """)

        quality_dist = dict(cursor.fetchall())

        # Reprocessing stats
        cursor.execute('SELECT COUNT(*) FROM content WHERE quality_issues = "reprocessing"')
        currently_processing = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM content WHERE quality_score < 0.4 AND quality_score > 0 AND quality_issues NOT LIKE "%reprocessing%"')
        remaining_problematic = cursor.fetchone()[0]

        # Recent improvements
        cursor.execute("""
            SELECT id, title, quality_score
            FROM content
            WHERE quality_score BETWEEN 0.3 AND 0.8
            AND quality_issues NOT LIKE '%reprocessing%'
            AND updated_at > datetime('now', '-1 hour')
            ORDER BY updated_at DESC
            LIMIT 10
        """)

        recent_improvements = [
            {"id": cid, "title": title[:60] + "..." if len(title) > 60 else title, "score": score}
            for cid, title, score in cursor.fetchall()
        ]

        conn.close()

        # Calculate progress
        original_problematic = 956  # From initial assessment
        processed = original_problematic - remaining_problematic - currently_processing
        progress_percentage = (processed / original_problematic) * 100 if original_problematic > 0 else 0

        return {
            "status": "running" if currently_processing > 0 else "idle",
            "progress": {
                "total_items": original_problematic,
                "processed": processed,
                "remaining": remaining_problematic,
                "currently_processing": currently_processing,
                "percentage": round(progress_percentage, 1)
            },
            "quality_distribution": quality_dist,
            "recent_improvements": recent_improvements,
            "summary": f"Processed {processed}/{original_problematic} items ({progress_percentage:.1f}% complete)"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/content/{content_id}/mark-stub")
async def mark_as_stub(content_id: int):
    """Mark content as a stub (low quality, not worth reprocessing)."""
    try:
        import sqlite3
        conn = sqlite3.connect('atlas.db')
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE content SET quality_score = 0.1, quality_issues = 'marked_as_stub' WHERE id = ?",
            (content_id,)
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Content #{content_id} marked as stub",
            "content_id": content_id
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug/proactive")
async def debug_proactive():
    """Debug proactive content surfacing."""
    import sqlite3
    from datetime import datetime, timedelta

    days_ago = (datetime.now() - timedelta(days=2)).isoformat()

    conn = sqlite3.connect('atlas.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM content")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM content WHERE title IS NOT NULL AND title != ''")
    titled_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM content WHERE created_at < ?", (days_ago,))
    old_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT title, created_at, content_type
        FROM content
        WHERE created_at < ? AND title IS NOT NULL AND title != ''
        ORDER BY RANDOM()
        LIMIT 3
    """, (days_ago,))

    sample_results = cursor.fetchall()
    conn.close()

    return {
        "cutoff_date": days_ago,
        "total_content": total_count,
        "with_titles": titled_count,
        "older_than_cutoff": old_count,
        "sample_results": [{"title": r[0], "date": r[1], "type": r[2]} for r in sample_results]
    }


# File upload and processing routes
ALLOWED_EXTENSIONS = {'.txt', '.csv', '.json', '.md', '.zip', '.log'}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads')

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

def is_safe_file(filename: str, content: bytes) -> tuple[bool, str]:
    """Check if file is safe to process."""
    _, ext = os.path.splitext(filename.lower())

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension '{ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    # Use python-magic to detect actual file type
    try:
        mime_type = magic.from_buffer(content, mime=True)

        # Check for executable files
        if 'executable' in mime_type or 'application/x-' in mime_type:
            if mime_type not in ['application/x-zip-compressed', 'application/zip']:
                return False, f"Potentially executable file detected: {mime_type}"

        # Additional safety checks
        dangerous_patterns = [b'\x00', b'<?php', b'<script', b'#!/bin/']
        for pattern in dangerous_patterns:
            if pattern in content[:1024]:  # Check first 1KB
                return False, "Potentially dangerous content detected"

    except Exception as e:
        return False, f"Could not analyze file: {str(e)}"

    return True, "File appears safe"

def process_uploaded_file(filepath: str, filename: str) -> dict:
    """Process uploaded file based on type."""
    _, ext = os.path.splitext(filename.lower())
    results = {"filename": filename, "type": ext, "processed": False, "data": None, "error": None}

    try:
        if ext == '.csv':
            import pandas as pd
            df = pd.read_csv(filepath)
            results["data"] = {
                "rows": len(df),
                "columns": list(df.columns),
                "sample": df.head(3).to_dict('records') if len(df) > 0 else []
            }
            results["processed"] = True

        elif ext == '.json':
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            results["data"] = {
                "type": type(data).__name__,
                "size": len(str(data)),
                "keys": list(data.keys()) if isinstance(data, dict) else "Not a dict",
                "sample": str(data)[:500] + "..." if len(str(data)) > 500 else str(data)
            }
            results["processed"] = True

        elif ext in ['.txt', '.md', '.log']:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            results["data"] = {
                "size": len(content),
                "lines": len(content.splitlines()),
                "sample": content[:500] + "..." if len(content) > 500 else content
            }
            results["processed"] = True

        elif ext == '.zip':
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                results["data"] = {
                    "files": len(file_list),
                    "file_list": file_list[:10],  # First 10 files
                    "total_size": sum(info.file_size for info in zip_ref.filelist)
                }
                results["processed"] = True

    except Exception as e:
        results["error"] = str(e)

    return results

@app.get("/upload", response_class=HTMLResponse)
def upload_form():
    """File upload form."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Atlas File Import</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 2rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            .upload-card {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 2rem;
                margin-bottom: 2rem;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .upload-zone {
                border: 2px dashed rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                padding: 2rem;
                text-align: center;
                margin: 1rem 0;
                transition: all 0.3s ease;
            }
            .upload-zone:hover {
                border-color: rgba(255, 255, 255, 0.6);
                background: rgba(255, 255, 255, 0.05);
            }
            input[type="file"] {
                display: none;
            }
            .file-input-label {
                cursor: pointer;
                background: rgba(255, 255, 255, 0.2);
                padding: 1rem 2rem;
                border-radius: 25px;
                border: none;
                color: white;
                font-size: 1rem;
                transition: all 0.3s ease;
                display: inline-block;
            }
            .file-input-label:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            .submit-btn {
                background: #4CAF50;
                color: white;
                padding: 1rem 2rem;
                border: none;
                border-radius: 25px;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .submit-btn:hover {
                background: #45a049;
            }
            .back-link {
                display: inline-block;
                margin-bottom: 2rem;
                color: white;
                text-decoration: none;
                opacity: 0.8;
            }
            .back-link:hover {
                opacity: 1;
            }
            .allowed-files {
                margin-top: 1rem;
                opacity: 0.8;
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-link">← Back to Dashboard</a>
            <h1>📁 File Import</h1>

            <div class="upload-card">
                <h2>Upload File</h2>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <div class="upload-zone">
                        <label for="file" class="file-input-label">
                            Choose File
                        </label>
                        <input type="file" id="file" name="file" required>
                        <p>Drag and drop or click to select</p>
                    </div>
                    <button type="submit" class="submit-btn">Upload & Process</button>
                </form>

                <div class="allowed-files">
                    <strong>Allowed file types:</strong> TXT, CSV, JSON, MD, ZIP, LOG
                    <br>
                    <strong>Max size:</strong> 50MB
                    <br>
                    <strong>Security:</strong> Files are scanned for safety before processing
                </div>
            </div>
        </div>

        <script>
            const fileInput = document.getElementById('file');
            const label = document.querySelector('.file-input-label');

            fileInput.addEventListener('change', function(e) {
                const fileName = e.target.files[0]?.name || 'Choose File';
                label.textContent = fileName;
            });
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Process uploaded file."""
    try:
        # Check file size (50MB limit)
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={"error": "File too large. Maximum size is 50MB."}
            )

        # Check if file is safe
        is_safe, safety_msg = is_safe_file(file.filename, content)
        if not is_safe:
            return JSONResponse(
                status_code=400,
                content={"error": f"File rejected: {safety_msg}"}
            )

        # Save file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, safe_filename)

        with open(filepath, 'wb') as f:
            f.write(content)

        # Process file
        results = process_uploaded_file(filepath, file.filename)

        # Generate HTML response
        status_color = "#4CAF50" if results["processed"] else "#f44336"
        status_text = "Success" if results["processed"] else "Error"

        data_html = ""
        if results["processed"] and results["data"]:
            data_html = f"<pre>{json.dumps(results['data'], indent=2)}</pre>"
        elif results["error"]:
            data_html = f"<div style='color: #f44336;'>Error: {results['error']}</div>"

        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Upload Results - Atlas</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 2rem;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                }}
                .result-card {{
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 15px;
                    padding: 2rem;
                    margin-bottom: 2rem;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }}
                .status {{
                    display: inline-block;
                    padding: 0.5rem 1rem;
                    border-radius: 15px;
                    background: {status_color};
                    color: white;
                    font-weight: bold;
                }}
                pre {{
                    background: rgba(0, 0, 0, 0.3);
                    padding: 1rem;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                .back-link {{
                    display: inline-block;
                    margin: 1rem 0;
                    padding: 0.5rem 1rem;
                    background: rgba(255, 255, 255, 0.2);
                    color: white;
                    text-decoration: none;
                    border-radius: 15px;
                }}
                .back-link:hover {{
                    background: rgba(255, 255, 255, 0.3);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📁 Upload Results</h1>

                <div class="result-card">
                    <h2>File: {results['filename']}</h2>
                    <p><strong>Status:</strong> <span class="status">{status_text}</span></p>
                    <p><strong>Type:</strong> {results['type']}</p>
                    <p><strong>Safety Check:</strong> {safety_msg}</p>

                    <h3>Processing Results:</h3>
                    {data_html}
                </div>

                <a href="/upload" class="back-link">← Upload Another File</a>
                <a href="/" class="back-link">← Back to Dashboard</a>
            </div>
        </body>
        </html>
        """)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Upload failed: {str(e)}"}
        )


if __name__ == "__main__":
    import uvicorn
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_port = int(os.getenv('API_PORT', 7444))
    print("🚀 Starting Atlas Mobile Web Interface...")
    print(f"📱 Mobile dashboard: http://localhost:{api_port}/mobile")
    print(f"🖥️  Desktop dashboard: http://localhost:{api_port}/ask/html")
    uvicorn.run(app, host="0.0.0.0", port=api_port)

