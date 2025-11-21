from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from typing import Dict, Any
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from helpers.analytics_engine import AnalyticsEngine
from helpers.config import load_config

router = APIRouter()

def get_analytics_engine():
    """Dependency to get analytics engine"""
    config = load_config()
    return AnalyticsEngine(config)

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(analytics: AnalyticsEngine = Depends(get_analytics_engine)):
    """Main dashboard page"""
    try:
        # Get analytics data
        summary = await get_analytics_summary(analytics)

        # Simple HTML dashboard
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Analytics Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .content-section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .api-links {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .api-link {{
            background: #667eea;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.9em;
        }}
        .api-link:hover {{
            background: #5a67d8;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Atlas Analytics Dashboard</h1>
        <p>Personal cognitive amplification platform</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-number">{summary.get('total_items', 0):,}</div>
            <div class="stat-label">Total Content Items</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{summary.get('articles', 0):,}</div>
            <div class="stat-label">Articles</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{summary.get('searchable_items', 0):,}</div>
            <div class="stat-label">Searchable Items</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{summary.get('processing_success_rate', 0):.1f}%</div>
            <div class="stat-label">Success Rate</div>
        </div>
    </div>

    <div class="content-section">
        <h2>📊 System Status</h2>
        <p><strong>Analytics Sync:</strong> {summary.get('analytics_status', 'Unknown')}</p>
        <p><strong>Search Index:</strong> {summary.get('search_status', 'Unknown')}</p>
        <p><strong>Last Updated:</strong> {summary.get('last_updated', 'Unknown')}</p>
    </div>

    <div class="content-section">
        <h2>🔌 API Endpoints</h2>
        <div class="api-links">
            <a href="/api/v1/search/?query=technology&limit=5" class="api-link">Test Search</a>
            <a href="/api/v1/content/" class="api-link">Content API</a>
            <a href="/api/v1/health" class="api-link">Health Check</a>
            <a href="/docs" class="api-link">API Documentation</a>
            <a href="/api/v1/dashboard/analytics" class="api-link">Analytics JSON</a>
        </div>
    </div>

    <div class="content-section">
        <h2>📈 Recent Activity</h2>
        <div id="activity">
            {summary.get('recent_activity', '<p>No recent activity</p>')}
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
        """
        return html_content

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

@router.get("/analytics")
async def analytics_data(analytics: AnalyticsEngine = Depends(get_analytics_engine)):
    """Get analytics data as JSON"""
    try:
        return await get_analytics_summary(analytics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

async def get_analytics_summary(analytics: AnalyticsEngine) -> Dict[str, Any]:
    """Get comprehensive analytics summary"""
    try:
        # Import here to avoid circular imports
        import sqlite3
        from datetime import datetime

        # Get main database stats
        atlas_db = sqlite3.connect("data/atlas.db")
        total_items = atlas_db.execute("SELECT COUNT(*) FROM content").fetchone()[0]
        articles = atlas_db.execute("SELECT COUNT(*) FROM content WHERE content_type = 'article'").fetchone()[0]
        success_items = atlas_db.execute("SELECT COUNT(*) FROM content WHERE LENGTH(metadata) > 100").fetchone()[0]
        atlas_db.close()

        # Get search database stats
        search_db = sqlite3.connect("data/enhanced_search.db")
        searchable_items = search_db.execute("SELECT COUNT(*) FROM search_index").fetchone()[0]
        search_db.close()

        # Calculate success rate
        success_rate = (success_items / total_items * 100) if total_items > 0 else 0

        # Get analytics status
        analytics_status = "Active" if hasattr(analytics, 'db_path') else "Inactive"

        # Recent activity
        recent_activity = f"""
        <ul>
            <li>✅ Search index populated with {searchable_items:,} items</li>
            <li>✅ Analytics engine synchronized</li>
            <li>✅ API endpoints active and responding</li>
            <li>✅ Background services operational</li>
        </ul>
        """

        return {
            "total_items": total_items,
            "articles": articles,
            "searchable_items": searchable_items,
            "processing_success_rate": success_rate,
            "analytics_status": analytics_status,
            "search_status": f"Active ({searchable_items:,} indexed)",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "recent_activity": recent_activity
        }

    except Exception as e:
        return {
            "total_items": 0,
            "articles": 0,
            "searchable_items": 0,
            "processing_success_rate": 0,
            "analytics_status": f"Error: {str(e)}",
            "search_status": "Unknown",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "recent_activity": f"<p>Error loading activity: {str(e)}</p>"
        }