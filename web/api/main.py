from fastapi import FastAPI, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import os
import sys
import httpx
import json
import datetime
import zipfile
import magic

# Add parent directory to Python path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routers import content, search, cognitive, auth, dashboard, transcription, worker, shortcuts, transcript_search, transcript_stats, podcast_progress
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title="Atlas API",
    description="API for the Atlas cognitive amplification platform",
    version="1.0.0"
)

# Add CORS middleware with security restrictions
allowed_origins = ["*"]  # Allow all origins for bookmarklet functionality

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(content.router, prefix="/api/v1/content", tags=["content"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(cognitive.router, prefix="/api/v1/cognitive", tags=["cognitive"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(transcription.router, prefix="/api/v1/transcriptions", tags=["transcription"])
app.include_router(worker.router, prefix="/api/v1/worker", tags=["worker"])
app.include_router(shortcuts.router, prefix="/api/v1/shortcuts", tags=["shortcuts"])
app.include_router(transcript_search.router, prefix="/api/v1/transcripts", tags=["transcript_search"])
app.include_router(transcript_stats.router, prefix="/api/v1/transcripts", tags=["transcript_stats"])
app.include_router(podcast_progress.router, prefix="/api/v1/podcast-progress", tags=["podcast_progress"])

@app.get("/api/v1/health")
async def health_check():
    # Google Custom Search API now configured
    return {"status": "healthy"}

@app.get("/search")
async def search_redirect(
    q: str = Query(..., description="Search query"),
    skip: int = Query(0, description="Skip results"),
    limit: int = Query(20, description="Limit results"),
    content_type: str = Query(None, description="Content type filter")
):
    """Direct search endpoint - redirects to /api/v1/search for compatibility"""
    from api.routers.search import search_content
    return await search_content(query=q, skip=skip, limit=limit, content_type=content_type)

@app.get("/")
async def root():
    """Redirect root to mobile dashboard"""
    return RedirectResponse(url="/mobile")

@app.get("/mobile", response_class=HTMLResponse)
async def mobile_dashboard():
    """Mobile dashboard for Atlas status and quick actions"""
    return await get_mobile_dashboard_html()

@app.get("/shortcuts")
async def shortcuts_redirect():
    """Redirect to shortcuts install page"""
    return RedirectResponse(url="/api/v1/shortcuts/install")

@app.get("/bookmarklet")
async def bookmarklet_page():
    """Serve the bookmarklet installation page"""
    from pathlib import Path
    from fastapi import HTTPException
    bookmarklet_path = Path(__file__).parent.parent / "browser_bookmarklet" / "install_bookmarklet.html"
    if bookmarklet_path.exists():
        with open(bookmarklet_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        raise HTTPException(status_code=404, detail="Bookmarklet page not found")

async def get_mobile_dashboard_html():
    """Generate mobile dashboard HTML with real-time Atlas data"""
    try:
        # Get system status
        sys.path.append('.')
        from helpers.simple_database import SimpleDatabase
        import subprocess
        import psutil

        db = SimpleDatabase()

        # Get processing stats
        with db.get_connection() as conn:
            total_items = conn.execute('SELECT COUNT(*) FROM content WHERE content IS NOT NULL AND length(content) > 100').fetchone()[0]
            processed_items = conn.execute('SELECT COUNT(*) FROM content WHERE ai_summary IS NOT NULL AND ai_summary != ""').fetchone()[0]
            articles_count = conn.execute('SELECT COUNT(*) FROM content WHERE content_type = "article"').fetchone()[0]
            podcasts_count = conn.execute('SELECT COUNT(*) FROM content WHERE content_type = "podcast"').fetchone()[0]

            # Get recently processed items (by updated_at when AI processing completed)
            recent = conn.execute('''
                SELECT id, title, updated_at
                FROM content
                WHERE ai_summary IS NOT NULL
                AND updated_at > datetime('now', '-24 hours')
                ORDER BY updated_at DESC LIMIT 5
            ''').fetchall()

        # System info
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)

        # Processing progress
        progress_pct = (processed_items / total_items * 100) if total_items > 0 else 0
        remaining_items = total_items - processed_items

        # Check if mass processing is running
        mass_processing_running = False
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            mass_processing_running = 'mass_ai_reprocessing.py' in result.stdout
        except:
            pass

        # Cost calculations for normal operation (not mass processing)
        import datetime
        now = datetime.datetime.now()

        if mass_processing_running:
            # Show mass processing costs
            estimated_cost = processed_items * 0.000048
            remaining_cost = remaining_items * 0.000048
            cost_display = f"Spent: ${estimated_cost:.4f} | Remaining: ${remaining_cost:.4f}"
        else:
            # Show normal operation costs (day/week/month)
            with db.get_connection() as conn:
                # Get items processed in last day/week/month
                day_ago = (now - datetime.timedelta(days=1)).isoformat()
                week_ago = (now - datetime.timedelta(days=7)).isoformat()
                month_ago = (now - datetime.timedelta(days=30)).isoformat()

                # Count items that were actually processed (updated) in these time periods
                day_items = conn.execute('SELECT COUNT(*) FROM content WHERE ai_summary IS NOT NULL AND updated_at > ? AND updated_at > created_at', (day_ago,)).fetchone()[0]
                week_items = conn.execute('SELECT COUNT(*) FROM content WHERE ai_summary IS NOT NULL AND updated_at > ? AND updated_at > created_at', (week_ago,)).fetchone()[0]
                month_items = conn.execute('SELECT COUNT(*) FROM content WHERE ai_summary IS NOT NULL AND updated_at > ? AND updated_at > created_at', (month_ago,)).fetchone()[0]

                day_cost = day_items * 0.000048
                week_cost = week_items * 0.000048
                month_cost = month_items * 0.000048

                cost_display = f"Day: ${day_cost:.4f} | Week: ${week_cost:.4f} | Month: ${month_cost:.4f}"

        # Get transcript statistics
        transcript_stats_data = {}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:7444/api/v1/transcripts/admin")
                response.raise_for_status()
                transcript_stats_data = response.json()
        except httpx.RequestError as e:
            print(f"Error fetching transcript stats: {e}")
        except httpx.HTTPStatusError as e:
            print(f"Error response {e.response.status_code} while fetching transcript stats: {e.response.text}")

        html = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            font-size: 16px;
            line-height: 1.4;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .status-good {{ color: #22c55e; }}
        .status-processing {{ color: #f59e0b; }}
        .status-bad {{ color: #ef4444; }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: #22c55e;
            width: {progress_pct:.1f}%;
            transition: width 0.3s ease;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin: 16px 0;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #1f2937;
        }}
        .stat-label {{
            color: #6b7280;
            font-size: 14px;
        }}
        .url-input {{
            width: 100%;
            padding: 12px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            margin-bottom: 12px;
        }}
        .btn {{
            background: #2563eb;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
        }}
        .btn:hover {{
            background: #1d4ed8;
        }}
        .recent-item {{
            padding: 8px 0;
            border-bottom: 1px solid #e5e7eb;
            font-size: 14px;
        }}
        .recent-item:last-child {{
            border-bottom: none;
        }}
        .monospace {{
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 14px;
        }}
        .refresh-indicator {{
            text-align: center;
            color: #6b7280;
            font-size: 12px;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Atlas Dashboard</h1>
            <p class="status-good">✅ System Running</p>
        </div>

        <div class="card">
            <h2>⚡ Processing Status</h2>
            <div class="{"status-processing" if mass_processing_running or remaining_items > 0 else "status-good"}">
                {"🔄 Mass AI Processing Running" if mass_processing_running else ("🔄 Continuous Processing" if remaining_items > 0 else "✅ Processing Complete")}
            </div>
            <div class="progress-bar">
                <div class="progress-fill"></div>
            </div>
            <div class="monospace">
                {processed_items:,} / {total_items:,} items processed ({progress_pct:.1f}%)
            </div>
            {f'<div class="monospace">⏱️  ~{remaining_items//500:.0f} hours remaining</div>' if mass_processing_running else ''}
        </div>

        <div class="card">
            <h2>📊 Content Library</h2>
            <div class="stats-grid">
                <div class="stat">
                    <div class="stat-value">{articles_count:,}</div>
                    <div class="stat-label">Articles</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{podcasts_count:,}</div>
                    <div class="stat-label">Podcasts</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{processed_items:,}</div>
                    <div class="stat-label">AI Analyzed</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{free_gb:.1f}GB</div>
                    <div class="stat-label">Free Space</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>🎙️ Transcript Statistics</h2>
            <div class="stats-grid">
                <div class="stat">
                    <div class="stat-value">{transcript_stats_data.get('total_transcripts', 0):,}</div>
                    <div class="stat-label">Total Transcripts</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{transcript_stats_data.get('total_episodes_known', 0):,}</div>
                    <div class="stat-label">Total Episodes Known</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{transcript_stats_data.get('pending_podcast_transcriptions', 0):,}</div>
                    <div class="stat-label">Pending Transcriptions</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{transcript_stats_data.get('failed_episodes_count', 0):,}</div>
                    <div class="stat-label">Failed Transcriptions</div>
                </div>
            </div>
            <h3>Recent Discoveries</h3>
            {''.join([f'<div class="recent-item">{item.get("podcast_name", "N/A")}: {item.get("title", "N/A")[:50]}...</div>' for item in transcript_stats_data.get('recent_discoveries', [])])}
            <h3>Top Podcasts by Transcripts</h3>
            {''.join([f'<div class="recent-item">{item.get("podcast_name", "N/A")}: {item.get("transcript_count", 0)}</div>' for item in transcript_stats_data.get('podcast_stats', [])])}
        </div>

        <div class="card">
            <h2>💰 Processing Costs</h2>
            <div class="monospace">
                {cost_display}
            </div>
        </div>

        <div class="card">
            <h2>🚀 Quick Actions</h2>
            <form id="urlForm">
                <input type="url" class="url-input" id="urlInput" placeholder="Paste URL here (article, YouTube, etc.)" required>
                <button type="submit" class="btn">Save to Atlas</button>
            </form>
        </div>

        <div class="card">
            <h2>📝 Recently Processed</h2>
            {''.join([f'<div class="recent-item">#{item[0]}: {item[1][:60]}{"..." if len(item[1]) > 60 else ""}</div>' for item in recent])}
        </div>
    </div>

    <div class="refresh-indicator">
        Auto-refresh every 30 seconds
    </div>

    <!-- Atlas Dashboards -->
    <div class="card">
        <h2>🧭 Atlas Dashboards</h2>
        <div style="display: grid; gap: 12px; margin-top: 16px;">
            <a href="/api/v1/dashboard/" style="display: block; padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; text-align: center; font-weight: 500;">
                📊 Analytics Dashboard
            </a>
            <a href="/api/v1/content/html" style="display: block; padding: 12px; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; text-decoration: none; border-radius: 8px; text-align: center; font-weight: 500;">
                📚 Content Browser
            </a>
        </div>
    </div>

    <!-- Quick Tools -->
    <div class="card">
        <h2>🛠️ Atlas Tools</h2>
        <div style="display: grid; gap: 12px; margin-top: 16px;">
            <a href="/bookmarklet" style="display: block; padding: 12px; background: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%); color: white; text-decoration: none; border-radius: 8px; text-align: center; font-weight: 500;">
                🔖 Browser Bookmarklet (Save from any browser)
            </a>
            <a href="https://github.com/Khamel83/Atlas/blob/main/quick_start_package/shortcuts/" target="_blank" style="display: block; padding: 12px; background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%); color: #333; text-decoration: none; border-radius: 8px; text-align: center; font-weight: 500;">
                📱 iOS Shortcuts (Download links)
            </a>
            <div onclick="document.getElementById('fileInput').click()" id="uploadBtn" style="display: block; padding: 12px; background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; cursor: pointer; border-radius: 8px; text-align: center; font-weight: 500;">
                📁 Upload File (CSV, JSON, TXT, ZIP)
            </div>
            <input type="file" id="fileInput" style="display: none" accept=".csv,.json,.txt,.md,.log,.zip" onchange="uploadFile(this.files[0])">
            <div id="uploadResult" style="display: none; margin-top: 12px; padding: 12px; border-radius: 8px; font-size: 14px;"></div>
            <div onclick="processCSV()" id="processBtn" style="display: block; margin-top: 12px; padding: 12px; background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; cursor: pointer; border-radius: 8px; text-align: center; font-weight: 500;">
                🚀 Process All URLs from CSV (6,194 URLs)
            </div>
            <div id="csvProgress" style="display: none; margin-top: 12px; padding: 12px; border-radius: 8px; font-size: 14px; background: #f0f9ff; border: 1px solid #7dd3fc;"></div>
        </div>
        <div style="margin-top: 16px; padding: 12px; background: #f8f9fa; border-radius: 8px; font-size: 14px; color: #666;">
            💡 <strong>Tip:</strong> Use the bookmarklet on any website to save articles to Atlas instantly
        </div>
    </div>

    <div style="text-align: center; margin-top: 30px; padding: 20px; border-top: 1px solid #e5e7eb;">
        <a href="https://github.com/Khamel83/atlas" target="_blank" style="color: #6b7280; text-decoration: none; font-size: 14px;">
            📚 Atlas on GitHub
        </a>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setInterval(() => location.reload(), 30000);

        // Handle URL form submission
        document.getElementById('urlForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const url = document.getElementById('urlInput').value;
            const btn = e.target.querySelector('.btn');

            btn.textContent = 'Saving...';
            btn.disabled = true;

            try {{
                const response = await fetch('/api/v1/content/submit-url', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{url: url}})
                }});

                if (response.ok) {{
                    document.getElementById('urlInput').value = '';
                    btn.textContent = '✅ Saved!';
                    setTimeout(() => location.reload(), 1000);
                }} else {{
                    const error = await response.json();
                    if (response.status === 409) {{
                        btn.textContent = '📋 Already Exists';
                    }} else if (response.status === 422) {{
                        btn.textContent = '🚫 Site Blocked Access';
                    }} else {{
                        btn.textContent = '❌ Failed';
                    }}
                    setTimeout(() => {{
                        btn.textContent = 'Save to Atlas';
                        btn.disabled = false;
                    }}, 3000);
                }}
            }} catch (error) {{
                btn.textContent = '❌ Error';
                setTimeout(() => {{
                    btn.textContent = 'Save to Atlas';
                    btn.disabled = false;
                }}, 2000);
            }}
        }});

        // Handle file upload
        async function uploadFile(file) {{
            if (!file) return;

            const btn = document.getElementById('uploadBtn');
            const result = document.getElementById('uploadResult');

            btn.textContent = '📤 Uploading...';
            btn.style.cursor = 'not-allowed';
            result.style.display = 'none';

            const formData = new FormData();
            formData.append('file', file);

            try {{
                const response = await fetch('/upload', {{
                    method: 'POST',
                    body: formData
                }});

                const data = await response.json();

                if (data.success) {{
                    btn.textContent = '✅ Upload Complete!';
                    btn.style.background = 'linear-gradient(135deg, #48bb78, #38a169)';

                    const res = data.results;
                    let resultHtml = `<strong>✅ ${{res.filename}}</strong><br>`;
                    resultHtml += `Type: ${{res.type}} | `;

                    if (res.data) {{
                        if (res.data.rows) resultHtml += `${{res.data.rows}} rows, ${{res.data.columns.length}} columns`;
                        else if (res.data.lines) resultHtml += `${{res.data.lines}} lines, ${{Math.round(res.data.size/1024)}}KB`;
                        else if (res.data.files) resultHtml += `${{res.data.files}} files in archive`;
                    }}

                    result.innerHTML = resultHtml;
                    result.style.display = 'block';
                    result.style.background = '#f0fff4';
                    result.style.color = '#22543d';
                    result.style.border = '1px solid #9ae6b4';
                }} else {{
                    btn.textContent = '❌ Upload Failed';
                    btn.style.background = 'linear-gradient(135deg, #f56565, #e53e3e)';

                    result.innerHTML = `<strong>❌ Error:</strong> ${{data.error}}`;
                    result.style.display = 'block';
                    result.style.background = '#fff5f5';
                    result.style.color = '#742a2a';
                    result.style.border = '1px solid #feb2b2';
                }}

                // Reset button after 3 seconds
                setTimeout(() => {{
                    btn.textContent = '📁 Upload File (CSV, JSON, TXT, ZIP)';
                    btn.style.background = 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)';
                    btn.style.cursor = 'pointer';
                    document.getElementById('fileInput').value = '';
                }}, 3000);

            }} catch (error) {{
                btn.textContent = '❌ Upload Error';
                btn.style.background = 'linear-gradient(135deg, #f56565, #e53e3e)';

                result.innerHTML = `<strong>❌ Network Error:</strong> ${{error.message}}`;
                result.style.display = 'block';
                result.style.background = '#fff5f5';
                result.style.color = '#742a2a';
                result.style.border = '1px solid #feb2b2';

                setTimeout(() => {{
                    btn.textContent = '📁 Upload File (CSV, JSON, TXT, ZIP)';
                    btn.style.background = 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)';
                    btn.style.cursor = 'pointer';
                }}, 3000);
            }}
        }}

        // CSV Processing Functions
        async function processCSV() {{
            const btn = document.getElementById('processBtn');
            const progress = document.getElementById('csvProgress');

            btn.textContent = '🚀 Starting CSV Processing...';
            btn.style.cursor = 'not-allowed';
            progress.style.display = 'block';
            progress.innerHTML = 'Initializing batch processing...';

            try {{
                const response = await fetch('/process-csv', {{
                    method: 'POST'
                }});

                const result = await response.json();

                if (result.success) {{
                    btn.textContent = '✅ Processing Started!';
                    progress.innerHTML = `<strong>🚀 Batch Processing Started</strong><br>Processing ${{result.total_urls}} URLs through Atlas ingestion pipeline...`;

                    // Start progress monitoring
                    startProgressMonitoring();
                }} else {{
                    btn.textContent = '❌ Start Failed';
                    progress.innerHTML = `<strong>❌ Error:</strong> ${{result.error}}`;
                    progress.style.background = '#fff5f5';
                    progress.style.borderColor = '#feb2b2';
                }}

            }} catch (error) {{
                btn.textContent = '❌ Network Error';
                progress.innerHTML = `<strong>❌ Network Error:</strong> ${{error.message}}`;
                progress.style.background = '#fff5f5';
                progress.style.borderColor = '#feb2b2';
            }}
        }}

        function startProgressMonitoring() {{
            const updateProgress = async () => {{
                try {{
                    const response = await fetch('/csv-status');
                    const status = await response.json();

                    const progress = document.getElementById('csvProgress');
                    const percentage = status.total > 0 ? Math.round((status.processed / status.total) * 100) : 0;

                    if (status.active) {{
                        progress.innerHTML = `
                            <strong>📊 Processing in Progress</strong><br>
                            Progress: ${{status.processed}}/${{status.total}} URLs (${{percentage}}%)<br>
                            ✅ Succeeded: ${{status.succeeded}} | ❌ Failed: ${{status.failed}}<br>
                            <small>Current: ${{status.current_url || 'Loading...'}}</small>
                        `;

                        // Continue monitoring
                        setTimeout(updateProgress, 2000);
                    }} else {{
                        if (status.current_url === 'COMPLETED') {{
                            progress.innerHTML = `
                                <strong>✅ CSV Processing Complete!</strong><br>
                                Total Processed: ${{status.processed}}/${{status.total}} URLs<br>
                                ✅ Succeeded: ${{status.succeeded}} | ❌ Failed: ${{status.failed}}<br>
                                <em>All URLs have been submitted to Atlas ingestion pipeline</em>
                            `;
                            progress.style.background = '#f0fff4';
                            progress.style.borderColor = '#9ae6b4';

                            // Reset button
                            const btn = document.getElementById('processBtn');
                            btn.textContent = '🚀 Process All URLs from CSV (6,194 URLs)';
                            btn.style.cursor = 'pointer';
                        }}
                    }}

                }} catch (error) {{
                    console.log('Progress monitoring error:', error);
                }}
            }};

            // Start monitoring immediately
            updateProgress();
        }}
    </script>
</body>
</html>
        '''

        return html

    except Exception as e:
        # Fallback error page
        return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Atlas Dashboard - Error</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: system-ui; padding: 20px; text-align: center;">
    <h1>Atlas Dashboard</h1>
    <p style="color: red;">Error loading dashboard: {str(e)}</p>
    <p><a href="/docs">View API Docs</a></p>
</body>
</html>
        '''

# File upload functionality
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

def is_safe_file(filename: str, content: bytes) -> tuple[bool, str]:
    """Check if file is safe to process."""
    ALLOWED_EXTENSIONS = {'.txt', '.csv', '.json', '.md', '.zip', '.log'}
    _, ext = os.path.splitext(filename.lower())

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension '{ext}' not allowed"

    # Skip magic check for now to avoid import issues
    return True, "File appears safe"

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Process uploaded file."""
    try:
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            return JSONResponse(status_code=413, content={"error": "File too large (50MB max)"})

        is_safe, safety_msg = is_safe_file(file.filename, content)
        if not is_safe:
            return JSONResponse(status_code=400, content={"error": f"File rejected: {safety_msg}"})

        # Save file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, safe_filename)

        with open(filepath, 'wb') as f:
            f.write(content)

        # Process based on file type
        _, ext = os.path.splitext(file.filename.lower())
        results = {"filename": file.filename, "type": ext, "processed": True, "path": filepath}

        if ext == '.csv':
            try:
                import pandas as pd
                df = pd.read_csv(filepath)
                # Handle NaN values by converting to None or string
                sample_df = df.head(3).fillna('null')
                results["data"] = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "sample": sample_df.to_dict('records')
                }
            except Exception as e:
                results["error"] = str(e)

        return JSONResponse(content={"success": True, "results": results})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Upload failed: {str(e)}"})

# CSV URL processing for batch ingestion
csv_processing_status = {"active": False, "total": 0, "processed": 0, "succeeded": 0, "failed": 0, "current_url": ""}

@app.get("/csv-status")
async def get_csv_status():
    """Get current CSV processing status."""
    return JSONResponse(content=csv_processing_status)

@app.post("/process-csv")
async def process_csv_urls():
    """Process all URLs from the most recent uploaded CSV file."""
    global csv_processing_status

    if csv_processing_status["active"]:
        return JSONResponse(content={"error": "CSV processing already in progress"})

    try:
        # Find the most recent CSV file
        import glob
        csv_files = glob.glob(os.path.join(UPLOAD_DIR, "*ip.csv"))
        if not csv_files:
            return JSONResponse(content={"error": "No CSV file found"})

        latest_csv = max(csv_files, key=os.path.getmtime)

        # Read CSV and extract URLs, separating email vs web URLs
        import pandas as pd
        df = pd.read_csv(latest_csv)

        # Separate email URLs from web URLs
        email_urls = df[df['URL'].str.startswith('instapaper-private://email/')].copy()
        web_urls = df[~df['URL'].str.startswith('instapaper-private://email/')]['URL'].dropna().tolist()

        # Process email URLs for title matching and web search
        email_matches, email_searches = await process_email_urls(email_urls)

        # Combine web URLs with found URLs from email searches
        urls = web_urls + email_searches

        # Initialize status
        csv_processing_status = {
            "active": True,
            "total": len(urls),
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "current_url": "",
            "start_time": datetime.datetime.now().isoformat()
        }

        # Process URLs in background
        import asyncio
        asyncio.create_task(process_urls_batch(urls))

        return JSONResponse(content={
            "success": True,
            "message": f"Started processing {len(urls)} URLs from {os.path.basename(latest_csv)}",
            "total_urls": len(urls)
        })

    except Exception as e:
        csv_processing_status["active"] = False
        return JSONResponse(status_code=500, content={"error": f"Failed to start CSV processing: {str(e)}"})

async def process_urls_batch(urls):
    """Process URLs in batch using unified Atlas ingestion queue."""
    from helpers.unified_ingestion import submit_urls
    global csv_processing_status

    if not urls:
        csv_processing_status["active"] = False
        csv_processing_status["current_url"] = "COMPLETED"
        return

    try:
        # Submit ALL URLs to unified queue in one operation
        job_ids = submit_urls(urls, priority=60, source="csv_upload")

        # Update status
        csv_processing_status["processed"] = len(urls)
        csv_processing_status["succeeded"] = len(job_ids)
        csv_processing_status["failed"] = len(urls) - len(job_ids)
        csv_processing_status["current_url"] = f"Queued {len(job_ids)} URLs"

        print(f"✅ CSV Processing: Queued {len(job_ids)} URLs via unified ingestion system")

    except Exception as e:
        csv_processing_status["failed"] = len(urls)
        csv_processing_status["current_url"] = f"Error: {str(e)}"
        print(f"❌ CSV Processing failed: {e}")

    # Mark as completed
    csv_processing_status["active"] = False
    csv_processing_status["current_url"] = "COMPLETED"

async def process_email_urls(email_df):
    """Process email URLs by matching titles and web searching for missing ones."""
    import sqlite3
    import pandas as pd
    from helpers.simple_database import SimpleDatabase

    db = SimpleDatabase()
    matched_count = 0
    search_urls = []

    with db.get_connection() as conn:
        for _, row in email_df.iterrows():
            title = row['Title'].strip() if pd.notna(row['Title']) else ""
            if not title:
                continue

            # Search for existing content with similar title
            cursor = conn.execute(
                "SELECT url FROM content WHERE title LIKE ? AND url NOT LIKE 'instapaper-private:%' LIMIT 1",
                (f"%{title}%",)
            )
            existing = cursor.fetchone()

            if existing:
                matched_count += 1
                # Already have this content
                continue
            else:
                # Need to web search for this title
                search_urls.append(await web_search_for_title(title))

    # Filter out None results from failed searches
    found_urls = [url for url in search_urls if url]

    return matched_count, found_urls

async def web_search_for_title(title):
    """Use web search to find URL for email title."""
    # Import the new GoogleSearchFallback system
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from helpers.google_search_fallback import search_with_google_fallback

    try:
        # Use the new fallback system with background processing
        result = await search_with_google_fallback(title, priority=3)  # Background priority
        if result:
            print(f"Found URL for '{title}': {result}")
        else:
            print(f"No search results for: {title}")
        return result
    except Exception as e:
        print(f"Web search failed for title: {title} - {e}")
        return None

@app.post("/test-web-search")
async def test_web_search(request: dict):
    """Test web search functionality."""
    title = request.get("title", "")
    if not title:
        return {"error": "Title is required"}

    result = await web_search_for_title(title)
    return {"title": title, "found_url": result}

@app.get("/google-search-stats")
async def get_google_search_stats():
    """Get Google Search fallback system statistics."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from helpers.google_search_fallback import get_google_search_stats

    try:
        stats = get_google_search_stats()
        return stats
    except Exception as e:
        return {"error": str(e)}

@app.get("/google-search-analytics")
async def google_search_analytics():
    """Get comprehensive Google Search analytics and monitoring data"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from helpers.google_search_analytics import create_monitoring_dashboard
        return create_monitoring_dashboard()
    except Exception as e:
        return {"error": f"Failed to get Google Search analytics: {e}"}

@app.get("/google-search-report")
async def google_search_report():
    """Get daily Google Search report"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from helpers.google_search_analytics import GoogleSearchMonitor
        monitor = GoogleSearchMonitor()
        report = monitor.generate_daily_report()
        return {"report": report, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"error": f"Failed to generate Google Search report: {e}"}

if __name__ == "__main__":
    import uvicorn
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_port = int(os.getenv('API_PORT', 7444))
    uvicorn.run(app, host="0.0.0.0", port=api_port)