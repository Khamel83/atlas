from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any, List
import sqlite3
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter()

class PodcastProgressTracker:
    """Tracks progress for the 37 prioritized podcasts"""

    def __init__(self, db_path="atlas.db", prioritized_csv_path="config/podcasts_prioritized_updated.csv"):
        self.db_path = db_path
        self.prioritized_csv_path = prioritized_csv_path
        self.prioritized_podcasts = self.load_prioritized_podcasts()

    def load_prioritized_podcasts(self) -> List[Dict[str, Any]]:
        """Load prioritized podcasts from CSV"""
        podcasts = []

        try:
            # Get absolute path relative to project root
            project_root = Path(__file__).parent.parent.parent
            csv_path = project_root / self.prioritized_csv_path

            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    podcasts.append({
                        'category': row['Category'],
                        'name': row['Podcast Name'],
                        'target_count': int(row['Count']),
                        'future_episodes': bool(int(row['Future'])),
                        'transcript_only': bool(int(row['Transcript_Only'])),
                        'excluded': bool(int(row.get('Exclude', 0)))
                    })
        except Exception as e:
            print(f"Error loading prioritized podcasts: {e}")

        return [p for p in podcasts if not p['excluded']]

    def get_podcast_database_stats(self, podcast_name: str) -> Dict[str, Any]:
        """Get current stats for a podcast from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get podcast info
            cursor.execute("SELECT id, name FROM podcasts WHERE name = ?", (podcast_name,))
            podcast_row = cursor.fetchone()

            if not podcast_row:
                return {
                    'podcast_id': None,
                    'total_episodes': 0,
                    'transcripts_found': 0,
                    'transcripts_processed': 0,
                    'last_updated': None,
                    'processing_status': 'not_found'
                }

            podcast_id = podcast_row[0]

            # Count total episodes in content table
            cursor.execute("""
                SELECT COUNT(*) FROM content
                WHERE content_type = 'podcast_episode'
                AND metadata LIKE ?
            """, (f'%"{podcast_name}"%',))
            total_episodes = cursor.fetchone()[0] or 0

            # Count transcripts found
            cursor.execute("""
                SELECT COUNT(*) FROM content
                WHERE content_type = 'podcast_transcript'
                AND title LIKE ?
            """, (f'%[TRANSCRIPT]%{podcast_name}%',))
            transcripts_found = cursor.fetchone()[0] or 0

            # Check processing queue status
            cursor.execute("""
                SELECT COUNT(*) FROM worker_jobs
                WHERE data LIKE ? AND status = 'pending'
            """, (f'%"{podcast_name}"%',))
            pending_jobs = cursor.fetchone()[0] or 0

            # Get last update
            cursor.execute("""
                SELECT MAX(created_at) FROM content
                WHERE (content_type = 'podcast_episode' OR content_type = 'podcast_transcript')
                AND (title LIKE ? OR metadata LIKE ?)
            """, (f'%{podcast_name}%', f'%"{podcast_name}"%'))
            last_updated = cursor.fetchone()[0]

            return {
                'podcast_id': podcast_id,
                'total_episodes': total_episodes,
                'transcripts_found': transcripts_found,
                'pending_jobs': pending_jobs,
                'last_updated': last_updated,
                'processing_status': 'active' if pending_jobs > 0 else 'idle'
            }

    def get_universal_queue_stats(self) -> Dict[str, Any]:
        """Get universal processing queue statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total jobs by status
            cursor.execute("""
                SELECT status, COUNT(*) FROM worker_jobs
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())

            # Jobs by type
            cursor.execute("""
                SELECT type, COUNT(*) FROM worker_jobs
                WHERE status = 'pending'
                GROUP BY type
            """)
            pending_by_type = dict(cursor.fetchall())

            # Recent completions
            cursor.execute("""
                SELECT COUNT(*) FROM worker_jobs
                WHERE status = 'completed'
                AND datetime(completed_at) > datetime('now', '-24 hours')
            """)
            completed_24h = cursor.fetchone()[0] or 0

            return {
                'status_counts': status_counts,
                'pending_by_type': pending_by_type,
                'completed_24h': completed_24h
            }

    def calculate_progress_percentage(self, current: int, target: int) -> float:
        """Calculate progress percentage"""
        if target == 0:
            return 100.0 if current > 0 else 0.0
        return min((current / target) * 100, 100.0)

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get complete progress summary for all prioritized podcasts"""
        summary = {
            'total_podcasts': len(self.prioritized_podcasts),
            'podcasts_with_content': 0,
            'total_target_episodes': 0,
            'total_current_episodes': 0,
            'total_transcripts_found': 0,
            'podcasts': [],
            'categories': {},
            'queue_stats': self.get_universal_queue_stats(),
            'last_updated': datetime.now().isoformat()
        }

        for podcast in self.prioritized_podcasts:
            stats = self.get_podcast_database_stats(podcast['name'])

            # Calculate progress
            progress_pct = self.calculate_progress_percentage(
                stats['total_episodes'],
                podcast['target_count']
            )

            podcast_summary = {
                **podcast,
                **stats,
                'progress_percentage': progress_pct,
                'status': self.get_podcast_status(podcast, stats)
            }

            summary['podcasts'].append(podcast_summary)

            # Update totals
            if stats['total_episodes'] > 0:
                summary['podcasts_with_content'] += 1

            summary['total_target_episodes'] += podcast['target_count']
            summary['total_current_episodes'] += stats['total_episodes']
            summary['total_transcripts_found'] += stats['transcripts_found']

            # Group by category
            category = podcast['category']
            if category not in summary['categories']:
                summary['categories'][category] = {
                    'name': category,
                    'podcasts': 0,
                    'target_episodes': 0,
                    'current_episodes': 0,
                    'transcripts_found': 0
                }

            summary['categories'][category]['podcasts'] += 1
            summary['categories'][category]['target_episodes'] += podcast['target_count']
            summary['categories'][category]['current_episodes'] += stats['total_episodes']
            summary['categories'][category]['transcripts_found'] += stats['transcripts_found']

        # Calculate overall progress
        summary['overall_progress'] = self.calculate_progress_percentage(
            summary['total_current_episodes'],
            summary['total_target_episodes']
        )

        # Sort podcasts by progress (lowest first to highlight what needs work)
        summary['podcasts'].sort(key=lambda x: (x['progress_percentage'], x['total_episodes']))

        return summary

    def get_podcast_status(self, podcast: Dict[str, Any], stats: Dict[str, Any]) -> str:
        """Determine podcast status"""
        if stats['podcast_id'] is None:
            return 'not_found'
        elif stats['pending_jobs'] > 0:
            return 'processing'
        elif stats['total_episodes'] >= podcast['target_count']:
            return 'complete'
        elif stats['total_episodes'] > 0:
            return 'partial'
        else:
            return 'not_started'

@router.get("/", response_class=HTMLResponse)
async def podcast_progress_dashboard():
    """Main podcast progress dashboard"""
    try:
        tracker = PodcastProgressTracker()
        summary = tracker.get_progress_summary()

        # Generate status color
        def get_status_color(status: str) -> str:
            colors = {
                'complete': '#4CAF50',
                'processing': '#2196F3',
                'partial': '#FF9800',
                'not_started': '#f44336',
                'not_found': '#9E9E9E'
            }
            return colors.get(status, '#9E9E9E')

        # Generate category cards HTML
        category_cards = ""
        for category_name, category_data in summary['categories'].items():
            progress = tracker.calculate_progress_percentage(
                category_data['current_episodes'],
                category_data['target_episodes']
            )
            category_cards += f"""
            <div class="category-card">
                <h3>{category_name}</h3>
                <div class="category-stats">
                    <div>📊 {category_data['podcasts']} podcasts</div>
                    <div>🎯 {category_data['current_episodes']}/{category_data['target_episodes']} episodes</div>
                    <div>📝 {category_data['transcripts_found']} transcripts</div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {progress}%"></div>
                </div>
                <div class="progress-text">{progress:.1f}% Complete</div>
            </div>
            """

        # Generate podcast rows HTML
        podcast_rows = ""
        for podcast in summary['podcasts']:
            status_color = get_status_color(podcast['status'])
            transcript_badge = "📝" if podcast['transcript_only'] else "🎵"

            podcast_rows += f"""
            <tr>
                <td>
                    <div class="podcast-name">{transcript_badge} {podcast['name']}</div>
                    <div class="podcast-category">{podcast['category']}</div>
                </td>
                <td>{podcast['total_episodes']}/{podcast['target_count']}</td>
                <td>{podcast['transcripts_found']}</td>
                <td>
                    <span class="status-badge" style="background-color: {status_color}">
                        {podcast['status'].replace('_', ' ').title()}
                    </span>
                </td>
                <td>
                    <div class="progress-bar small">
                        <div class="progress-fill" style="width: {podcast['progress_percentage']}%"></div>
                    </div>
                    <div class="progress-text">{podcast['progress_percentage']:.1f}%</div>
                </td>
                <td>{podcast['pending_jobs']}</td>
            </tr>
            """

        # Generate queue stats
        queue_stats = summary['queue_stats']
        total_pending = sum(queue_stats['status_counts'].get(status, 0) for status in ['pending'])
        total_running = sum(queue_stats['status_counts'].get(status, 0) for status in ['running'])

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Podcast Progress Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .overview-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .categories-section {{
            margin-bottom: 30px;
        }}
        .categories-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .category-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .category-card h3 {{
            margin: 0 0 15px 0;
            color: #333;
        }}
        .category-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
            font-size: 0.9em;
        }}
        .progress-bar {{
            background-color: #e0e0e0;
            border-radius: 20px;
            height: 8px;
            overflow: hidden;
            margin-bottom: 5px;
        }}
        .progress-bar.small {{
            height: 6px;
        }}
        .progress-fill {{
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 100%;
            transition: width 0.3s ease;
        }}
        .progress-text {{
            font-size: 0.8em;
            color: #666;
            text-align: center;
        }}
        .detailed-table {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
            margin-bottom: 30px;
        }}
        .table-header {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #dee2e6;
        }}
        .table-header h2 {{
            margin: 0;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        .podcast-name {{
            font-weight: 600;
            color: #333;
        }}
        .podcast-category {{
            font-size: 0.85em;
            color: #666;
            margin-top: 5px;
        }}
        .status-badge {{
            padding: 4px 8px;
            border-radius: 4px;
            color: white;
            font-size: 0.8em;
            font-weight: 500;
        }}
        .queue-stats {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .queue-stats h3 {{
            margin: 0 0 15px 0;
            color: #333;
        }}
        .queue-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        .queue-item {{
            text-align: center;
        }}
        .queue-number {{
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .queue-label {{
            font-size: 0.8em;
            color: #666;
        }}
        .section-title {{
            font-size: 1.5em;
            color: #333;
            margin: 30px 0 20px 0;
            font-weight: 300;
        }}
        .last-updated {{
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-top: 30px;
        }}
        @media (max-width: 768px) {{
            .overview-stats {{
                grid-template-columns: 1fr 1fr;
            }}
            .categories-grid {{
                grid-template-columns: 1fr;
            }}
            .category-stats {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎙️ Atlas Podcast Progress</h1>
        <p>Tracking {summary['total_podcasts']} prioritized podcasts • {summary['overall_progress']:.1f}% complete</p>
    </div>

    <div class="overview-stats">
        <div class="stat-card">
            <div class="stat-number">{summary['total_current_episodes']}</div>
            <div class="stat-label">Total Episodes</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{summary['total_target_episodes']}</div>
            <div class="stat-label">Target Episodes</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{summary['total_transcripts_found']}</div>
            <div class="stat-label">Transcripts Found</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{summary['podcasts_with_content']}</div>
            <div class="stat-label">Active Podcasts</div>
        </div>
    </div>

    <div class="queue-stats">
        <h3>⚡ Universal Processing Queue Status</h3>
        <div class="queue-grid">
            <div class="queue-item">
                <div class="queue-number">{total_pending}</div>
                <div class="queue-label">Pending Jobs</div>
            </div>
            <div class="queue-item">
                <div class="queue-number">{total_running}</div>
                <div class="queue-label">Running Jobs</div>
            </div>
            <div class="queue-item">
                <div class="queue-number">{queue_stats['completed_24h']}</div>
                <div class="queue-label">Completed (24h)</div>
            </div>
        </div>
    </div>

    <div class="section-title">📊 Progress by Category</div>
    <div class="categories-grid">
        {category_cards}
    </div>

    <div class="detailed-table">
        <div class="table-header">
            <h2>📋 Detailed Podcast Status</h2>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Podcast</th>
                    <th>Episodes</th>
                    <th>Transcripts</th>
                    <th>Status</th>
                    <th>Progress</th>
                    <th>Queue Jobs</th>
                </tr>
            </thead>
            <tbody>
                {podcast_rows}
            </tbody>
        </table>
    </div>

    <div class="last-updated">
        Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>
        """

        return HTMLResponse(content=html_content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

@router.get("/api/progress", response_class=JSONResponse)
async def get_progress_api():
    """Get podcast progress data as JSON API"""
    try:
        tracker = PodcastProgressTracker()
        summary = tracker.get_progress_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.get("/api/podcast/{podcast_name}", response_class=JSONResponse)
async def get_podcast_details(podcast_name: str):
    """Get detailed stats for a specific podcast"""
    try:
        tracker = PodcastProgressTracker()
        stats = tracker.get_podcast_database_stats(podcast_name)

        # Find the podcast in prioritized list
        podcast_config = None
        for p in tracker.prioritized_podcasts:
            if p['name'] == podcast_name:
                podcast_config = p
                break

        if not podcast_config:
            raise HTTPException(status_code=404, detail="Podcast not found in prioritized list")

        return {
            'podcast': podcast_config,
            'stats': stats,
            'progress_percentage': tracker.calculate_progress_percentage(
                stats['total_episodes'],
                podcast_config['target_count']
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")