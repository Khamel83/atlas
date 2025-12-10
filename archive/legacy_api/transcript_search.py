"""Enhanced Transcript Search API Router
Provides comprehensive transcript search, discovery, and analytics
for the Atlas platform with modern UI integration.
"""

import json
import os
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from helpers.simple_database import SimpleDatabase
from helpers.semantic_search_ranker import SemanticSearchRanker

router = APIRouter()

class TranscriptSearchQuery(BaseModel):
    """Model for transcript search queries."""
    query: str = Field(..., min_length=1, description="Search query")
    podcasts: Optional[List[str]] = Field(None, description="Filter by podcast names")
    speakers: Optional[List[str]] = Field(None, description="Filter by speaker names")
    content_type: Optional[str] = Field(None, description="Filter by content type")
    limit: int = Field(20, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")

class TranscriptResult(BaseModel):
    """Model for transcript search results."""
    id: str
    title: str
    podcast_name: Optional[str] = None
    speaker: Optional[str] = None
    content_excerpt: str
    content_type: str
    score: float
    timestamp: Optional[str] = None
    word_count: int
    source_url: Optional[str] = None
    created_at: str

class TranscriptSearchResponse(BaseModel):
    """Response model for transcript searches."""
    results: List[TranscriptResult]
    total_count: int
    query: str
    processing_time_ms: float
    suggestions: Optional[List[str]] = None
    facets: Optional[Dict[str, Any]] = None

class TranscriptStats(BaseModel):
    """Statistics about the transcript collection."""
    total_transcripts: int
    unique_podcasts: int
    unique_speakers: int
    total_words: int
    latest_transcript: Optional[str] = None
    coverage_by_podcast: Dict[str, int]

def get_database():
    """Get database connection."""
    return SimpleDatabase("data/atlas.db")

def search_transcripts_in_content(query: str, db: SimpleDatabase, limit: int = 20, offset: int = 0) -> tuple:
    """Search for transcripts in the content table."""

    # Simple full-text search on content table
    search_sql = """
    SELECT
        id,
        title,
        content,
        content_type,
        url,
        created_at,
        LENGTH(content) as word_count
    FROM content
    WHERE (content_type = 'podcast_transcript' OR content_type LIKE '%transcript%')
    AND (
        content LIKE ? OR
        title LIKE ? OR
        url LIKE ?
    )
    ORDER BY
        CASE
            WHEN title LIKE ? THEN 1
            WHEN content LIKE ? THEN 2
            ELSE 3
        END,
        created_at DESC
    LIMIT ? OFFSET ?
    """

    # Count total matching results
    count_sql = """
    SELECT COUNT(*)
    FROM content
    WHERE (content_type = 'podcast_transcript' OR content_type LIKE '%transcript%')
    AND (
        content LIKE ? OR
        title LIKE ? OR
        url LIKE ?
    )
    """

    search_pattern = f"%{query}%"
    title_pattern = f"%{query}%"

    with db.get_connection() as conn:
        # Get total count
        total_count = conn.execute(count_sql, (search_pattern, title_pattern, search_pattern)).fetchone()[0]

        # Get results
        results = conn.execute(search_sql, (
            search_pattern, title_pattern, search_pattern,  # WHERE clause
            title_pattern, search_pattern,  # ORDER BY clause
            limit, offset
        )).fetchall()

    return results, total_count

def extract_content_excerpt(content: str, query: str, max_length: int = 200) -> str:
    """Extract relevant excerpt from content based on query."""
    if not content:
        return ""

    query_lower = query.lower()
    content_lower = content.lower()

    # Find first occurrence of query terms
    query_words = query_lower.split()
    best_position = 0

    for word in query_words:
        pos = content_lower.find(word)
        if pos != -1:
            best_position = max(0, pos - 50)  # Start 50 chars before match
            break

    # Extract excerpt around the best position
    start = max(0, best_position)
    excerpt = content[start:start + max_length]

    # Clean up excerpt
    if start > 0:
        excerpt = "..." + excerpt
    if len(content) > start + max_length:
        excerpt = excerpt + "..."

    return excerpt.strip()

@router.get("/search", response_model=TranscriptSearchResponse)
async def search_transcripts(
    q: str = Query(..., description="Search query"),
    podcasts: Optional[str] = Query(None, description="Comma-separated podcast names"),
    speakers: Optional[str] = Query(None, description="Comma-separated speaker names"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    db: SimpleDatabase = Depends(get_database)
):
    """Search transcripts with filtering and ranking."""

    start_time = time.time()

    try:
        # Parse filters
        podcast_filters = [p.strip() for p in podcasts.split(',')] if podcasts else None
        speaker_filters = [s.strip() for s in speakers.split(',')] if speakers else None

        # Perform search
        results, total_count = search_transcripts_in_content(q, db, limit, offset)

        # Format results
        formatted_results = []
        for row in results:
            id_val, title, content, content_type, url, created_at, word_count = row

            # Extract podcast name from title or source
            podcast_name = None
            if title and '[' in title and ']' in title:
                # Extract from title like "[TRANSCRIPT] Podcast Name - Episode"
                try:
                    podcast_name = title.split('[TRANSCRIPT]')[1].split(' - ')[0].strip()
                except:
                    pass

            # Calculate simple relevance score
            score = calculate_relevance_score(q, title, content)

            # Create result
            result = TranscriptResult(
                id=str(id_val),
                title=title,
                podcast_name=podcast_name,
                content_excerpt=extract_content_excerpt(content, q),
                content_type=content_type,
                score=score,
                word_count=word_count or 0,
                source_url=url,
                created_at=created_at
            )

            formatted_results.append(result)

        # Sort by relevance score
        formatted_results.sort(key=lambda x: x.score, reverse=True)

        processing_time = (time.time() - start_time) * 1000

        # Generate suggestions (simple implementation)
        suggestions = generate_search_suggestions(q, db) if len(formatted_results) < 5 else None

        return TranscriptSearchResponse(
            results=formatted_results,
            total_count=total_count,
            query=q,
            processing_time_ms=round(processing_time, 2),
            suggestions=suggestions
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

def calculate_relevance_score(query: str, title: str, content: str) -> float:
    """Calculate relevance score for search result."""
    score = 0.0
    query_lower = query.lower()
    title_lower = (title or "").lower()
    content_lower = (content or "").lower()

    query_words = query_lower.split()

    # Title matches (higher weight)
    for word in query_words:
        if word in title_lower:
            score += 2.0

    # Content matches
    for word in query_words:
        content_count = content_lower.count(word)
        score += min(content_count * 0.1, 1.0)  # Cap at 1.0 per word

    # Exact phrase bonus
    if query_lower in title_lower:
        score += 5.0
    elif query_lower in content_lower:
        score += 2.0

    # Normalize to 0-1 range
    return min(score / 10.0, 1.0)

def generate_search_suggestions(query: str, db: SimpleDatabase) -> List[str]:
    """Generate search suggestions based on available content."""
    suggestions = []

    try:
        with db.get_connection() as conn:
            # Get common words from transcript titles
            titles_sql = """
            SELECT title FROM content
            WHERE content_type LIKE '%transcript%'
            AND title IS NOT NULL
            LIMIT 50
            """

            titles = conn.execute(titles_sql).fetchall()

            # Extract keywords from titles
            keywords = set()
            for (title,) in titles:
                if title:
                    words = title.lower().split()
                    keywords.update(word.strip('[]().,!?') for word in words if len(word) > 3)

            # Find related keywords
            query_words = set(query.lower().split())
            related_keywords = keywords - query_words

            suggestions = list(related_keywords)[:5]

    except Exception as e:
        print(f"Error generating suggestions: {e}")

    return suggestions

@router.get("/stats", response_model=TranscriptStats)
async def get_transcript_stats(db: SimpleDatabase = Depends(get_database)):
    """Get comprehensive transcript collection statistics."""

    try:
        with db.get_connection() as conn:
            # Basic counts
            total_transcripts = conn.execute(
                "SELECT COUNT(*) FROM content WHERE (content_type = 'podcast_transcript' OR content_type LIKE '%transcript%')"
            ).fetchone()[0]

            # Get podcast names from titles
            podcast_sql = """
            SELECT title FROM content
            WHERE (content_type = 'podcast_transcript' OR content_type LIKE '%transcript%')
            AND (title LIKE '[TRANSCRIPT]%' OR title IS NOT NULL)
            """

            podcasts = conn.execute(podcast_sql).fetchall()
            podcast_names = set()
            coverage_by_podcast = {}

            for (title,) in podcasts:
                if title and '[TRANSCRIPT]' in title:
                    try:
                        podcast_name = title.split('[TRANSCRIPT]')[1].split(' - ')[0].strip()
                        podcast_names.add(podcast_name)
                        coverage_by_podcast[podcast_name] = coverage_by_podcast.get(podcast_name, 0) + 1
                    except:
                        pass

            # Latest transcript
            latest_sql = """
            SELECT title, created_at FROM content
            WHERE content_type LIKE '%transcript%'
            ORDER BY created_at DESC LIMIT 1
            """
            latest_result = conn.execute(latest_sql).fetchone()
            latest_transcript = latest_result[0] if latest_result else None

            # Total word count approximation
            word_count_sql = """
            SELECT SUM(LENGTH(content) / 5) FROM content
            WHERE content_type LIKE '%transcript%'
            AND content IS NOT NULL
            """
            total_words = conn.execute(word_count_sql).fetchone()[0] or 0

        return TranscriptStats(
            total_transcripts=total_transcripts,
            unique_podcasts=len(podcast_names),
            unique_speakers=0,  # Would need speaker extraction
            total_words=int(total_words),
            latest_transcript=latest_transcript,
            coverage_by_podcast=coverage_by_podcast
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")

@router.get("/discovery", response_class=HTMLResponse)
async def transcript_discovery_ui():
    """Serve the transcript discovery web interface."""

    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Transcript Discovery</title>
    <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --background: #f8f9fa;
            --text-color: #333;
            --border-color: #e9ecef;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }

        .header p {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        .search-section {
            padding: 30px;
            border-bottom: 1px solid var(--border-color);
        }

        .search-form {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .search-input {
            flex: 1;
            min-width: 300px;
            padding: 15px 20px;
            font-size: 16px;
            border: 2px solid var(--border-color);
            border-radius: 8px;
            outline: none;
            transition: border-color 0.3s;
        }

        .search-input:focus {
            border-color: var(--primary-color);
        }

        .search-btn {
            padding: 15px 30px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .search-btn:hover {
            transform: translateY(-2px);
        }

        .search-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .filters {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }

        .filter-input {
            padding: 10px 15px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-size: 14px;
        }

        .stats-section {
            padding: 30px;
            background: var(--background);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 5px;
        }

        .stat-label {
            color: #666;
            font-size: 14px;
        }

        .results-section {
            padding: 30px;
        }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .result-item {
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: box-shadow 0.2s;
        }

        .result-item:hover {
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        .result-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--primary-color);
            margin-bottom: 10px;
        }

        .result-meta {
            display: flex;
            gap: 15px;
            margin-bottom: 10px;
            font-size: 14px;
            color: #666;
        }

        .result-excerpt {
            color: var(--text-color);
            line-height: 1.6;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }

        .no-results {
            text-align: center;
            padding: 40px;
            color: #666;
        }

        .suggestions {
            margin-top: 20px;
        }

        .suggestion-chip {
            display: inline-block;
            background: var(--primary-color);
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            margin: 5px;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        .suggestion-chip:hover {
            background: var(--secondary-color);
        }

        @media (max-width: 768px) {
            .search-form {
                flex-direction: column;
            }

            .search-input {
                min-width: unset;
            }

            .filters {
                flex-direction: column;
            }

            .stats-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎙️ Atlas Transcript Discovery</h1>
            <p>Search and explore podcast transcripts with intelligent ranking</p>
        </div>

        <div class="search-section">
            <div class="search-form">
                <input type="text" id="searchInput" class="search-input" placeholder="Search transcripts..." />
                <button id="searchBtn" class="search-btn">Search</button>
            </div>

            <div class="filters">
                <input type="text" id="podcastFilter" class="filter-input" placeholder="Filter by podcast..." />
                <input type="text" id="speakerFilter" class="filter-input" placeholder="Filter by speaker..." />
                <select id="limitSelect" class="filter-input">
                    <option value="20">20 results</option>
                    <option value="50">50 results</option>
                    <option value="100">100 results</option>
                </select>
            </div>
        </div>

        <div class="stats-section" id="statsSection">
            <div class="stats-grid" id="statsGrid">
                <!-- Stats will be loaded here -->
            </div>
        </div>

        <div class="results-section">
            <div class="results-header">
                <h2 id="resultsTitle">Welcome to Transcript Search</h2>
                <span id="resultsCount"></span>
            </div>

            <div id="resultsContainer">
                <div class="no-results">
                    <h3>🔍 Ready to Search</h3>
                    <p>Enter your search query above to find relevant transcript content.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        class TranscriptSearch {
            constructor() {
                this.searchInput = document.getElementById('searchInput');
                this.searchBtn = document.getElementById('searchBtn');
                this.resultsContainer = document.getElementById('resultsContainer');
                this.resultsTitle = document.getElementById('resultsTitle');
                this.resultsCount = document.getElementById('resultsCount');
                this.statsGrid = document.getElementById('statsGrid');

                this.bindEvents();
                this.loadStats();
            }

            bindEvents() {
                this.searchBtn.addEventListener('click', () => this.performSearch());
                this.searchInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') this.performSearch();
                });

                // Auto-search with debounce
                let debounceTimer;
                this.searchInput.addEventListener('input', () => {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(() => {
                        if (this.searchInput.value.length > 2) {
                            this.performSearch();
                        }
                    }, 500);
                });
            }

            async loadStats() {
                try {
                    const response = await fetch('/api/v1/transcriptions/stats');
                    const stats = await response.json();

                    this.statsGrid.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-value">${stats.total_transcripts}</div>
                            <div class="stat-label">Total Transcripts</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.unique_podcasts}</div>
                            <div class="stat-label">Unique Podcasts</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${Math.floor(stats.total_words / 1000)}K</div>
                            <div class="stat-label">Total Words</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.unique_speakers || 0}</div>
                            <div class="stat-label">Speakers</div>
                        </div>
                    `;
                } catch (error) {
                    console.error('Error loading stats:', error);
                    this.statsGrid.innerHTML = '<div class="stat-card">Unable to load statistics</div>';
                }
            }

            async performSearch() {
                const query = this.searchInput.value.trim();
                if (!query) {
                    this.showMessage('Please enter a search query');
                    return;
                }

                this.showLoading();

                try {
                    const params = new URLSearchParams({
                        q: query,
                        limit: document.getElementById('limitSelect').value || '20'
                    });

                    const podcastFilter = document.getElementById('podcastFilter').value.trim();
                    if (podcastFilter) params.append('podcasts', podcastFilter);

                    const speakerFilter = document.getElementById('speakerFilter').value.trim();
                    if (speakerFilter) params.append('speakers', speakerFilter);

                    const response = await fetch(`/api/v1/transcriptions/search?${params}`);
                    const data = await response.json();

                    this.displayResults(data);

                } catch (error) {
                    console.error('Search error:', error);
                    this.showMessage('Search failed. Please try again.');
                }
            }

            displayResults(data) {
                this.resultsTitle.textContent = `Search Results for "${data.query}"`;
                this.resultsCount.textContent = `${data.total_count} results (${data.processing_time_ms}ms)`;

                if (data.results.length === 0) {
                    this.resultsContainer.innerHTML = `
                        <div class="no-results">
                            <h3>No transcripts found</h3>
                            <p>Try different search terms or check the suggestions below.</p>
                            ${this.renderSuggestions(data.suggestions)}
                        </div>
                    `;
                    return;
                }

                const resultsHtml = data.results.map(result => `
                    <div class="result-item">
                        <div class="result-title">${this.escapeHtml(result.title)}</div>
                        <div class="result-meta">
                            ${result.podcast_name ? `<span>📻 ${this.escapeHtml(result.podcast_name)}</span>` : ''}
                            ${result.speaker ? `<span>🎤 ${this.escapeHtml(result.speaker)}</span>` : ''}
                            <span>📊 Score: ${result.score.toFixed(2)}</span>
                            <span>📝 ${result.word_count} words</span>
                            <span>📅 ${new Date(result.created_at).toLocaleDateString()}</span>
                        </div>
                        <div class="result-excerpt">${this.escapeHtml(result.content_excerpt)}</div>
                    </div>
                `).join('');

                this.resultsContainer.innerHTML = resultsHtml + this.renderSuggestions(data.suggestions);
            }

            renderSuggestions(suggestions) {
                if (!suggestions || suggestions.length === 0) return '';

                return `
                    <div class="suggestions">
                        <h4>Try these suggestions:</h4>
                        ${suggestions.map(suggestion =>
                            `<span class="suggestion-chip" onclick="document.getElementById('searchInput').value='${suggestion}'; transcriptSearch.performSearch()">${suggestion}</span>`
                        ).join('')}
                    </div>
                `;
            }

            showLoading() {
                this.resultsContainer.innerHTML = '<div class="loading">🔍 Searching transcripts...</div>';
                this.searchBtn.disabled = true;
                this.searchBtn.textContent = 'Searching...';
            }

            showMessage(message) {
                this.resultsContainer.innerHTML = `<div class="no-results"><p>${message}</p></div>`;
                this.searchBtn.disabled = false;
                this.searchBtn.textContent = 'Search';
            }

            escapeHtml(text) {
                const map = {
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                };
                return text.replace(/[&<>"']/g, (m) => map[m]);
            }
        }

        // Initialize the search interface
        const transcriptSearch = new TranscriptSearch();
    </script>
</body>
</html>
    """

    return HTMLResponse(content=html_content)

@router.post("/process", response_class=JSONResponse)
async def process_transcripts(
    background_tasks: BackgroundTasks,
    limit: int = Query(10, ge=1, le=100, description="Number of episodes to process")
):
    """Start transcript processing in background."""

    def process_transcripts_task():
        """Background task to process transcripts."""
        try:
            # Import and run transcript processing
            sys.path.append('.')
            from scalable_transcript_system import process_all_podcasts
            process_all_podcasts()
        except Exception as e:
            print(f"Background transcript processing error: {e}")

    background_tasks.add_task(process_transcripts_task)

    return JSONResponse({
        "status": "started",
        "message": f"Started processing up to {limit} transcript episodes in background",
        "task": "transcript_processing"
    })