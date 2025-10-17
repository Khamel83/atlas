#!/usr/bin/env python3
"""
Podcast Transcript Orchestrator

Universal system that finds and extracts transcripts for ANY podcast.
Integrates with Atlas database and processing pipeline.
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from helpers.universal_transcript_finder import UniversalTranscriptFinder, TranscriptSource
from helpers.database_config import get_database_connection
from helpers.content_transactions import TransactionTimer

logger = logging.getLogger(__name__)

class PodcastTranscriptOrchestrator:
    """Main orchestrator for podcast transcript discovery and extraction"""

    def __init__(self, atlas_config):
        self.config = atlas_config
        self.finder = UniversalTranscriptFinder()
        self.transcript_cache = {}

        # Episode processing stages
        self.STAGES = {
            100: "EPISODE_DISCOVERED",
            200: "TRANSCRIPT_SOURCES_FOUND",
            300: "TRANSCRIPT_EXTRACTED",
            400: "TRANSCRIPT_STORED",
            500: "TRANSCRIPT_PROCESSED"
        }

    def process_all_podcasts(self):
        """Process all configured podcasts for transcript discovery"""

        # Get podcast list from config
        podcasts = self._load_podcast_config()

        for podcast in podcasts:
            try:
                logger.info(f"Processing podcast: {podcast['name']}")
                self.process_podcast(podcast)
                time.sleep(2)  # Rate limiting

            except Exception as e:
                logger.error(f"Failed to process podcast {podcast['name']}: {e}")

    def process_podcast(self, podcast_config: Dict):
        """Process a single podcast for transcript discovery"""

        podcast_name = podcast_config.get('name')
        expected_count = podcast_config.get('expected_episodes', 0)

        logger.info(f"=== Processing {podcast_name} (expecting {expected_count} episodes) ===")

        # Step 1: Find all transcript sources for this podcast
        transcript_sources = self.finder.find_transcript_sources(podcast_name)

        if not transcript_sources:
            logger.warning(f"No transcript sources found for {podcast_name}")
            return

        logger.info(f"Found {len(transcript_sources)} potential transcript sources")

        # Step 2: Test each source and extract episodes
        for source in transcript_sources[:3]:  # Top 3 sources
            try:
                episodes = self._extract_episodes_from_source(source, podcast_name)

                if episodes:
                    logger.info(f"Found {len(episodes)} episodes from {source.site_name}")

                    # Step 3: Store episodes in Atlas database
                    self._store_episodes_in_atlas(episodes, podcast_name, source)
                    break  # Use first working source

            except Exception as e:
                logger.warning(f"Failed to extract from {source.url}: {e}")

    def _load_podcast_config(self) -> List[Dict]:
        """Load podcast configuration from CSV"""
        podcasts = []

        config_file = Path(self.config.get('project_root', '.')) / "config" / "podcast_config.csv"

        try:
            import csv
            with open(config_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Exclude') == '1':
                        continue

                    podcasts.append({
                        'name': row.get('Podcast Name'),
                        'category': row.get('Category'),
                        'expected_episodes': int(row.get('Count', 0)),
                        'transcript_only': row.get('Transcript_Only') == '1',
                        'future': row.get('Future') == '1'
                    })

        except Exception as e:
            logger.error(f"Failed to load podcast config: {e}")

        return [p for p in podcasts if p['expected_episodes'] > 0]

    def _extract_episodes_from_source(self, source: TranscriptSource, podcast_name: str) -> List[Dict]:
        """Extract episode information and transcripts from a source"""
        episodes = []

        if source.coverage_type == "official":
            # Handle official podcast websites
            episodes = self._extract_from_official_site(source, podcast_name)

        elif source.site_name == "github.com":
            # Handle GitHub transcript repositories
            episodes = self._extract_from_github(source, podcast_name)

        elif source.site_name in ["medium.com", "substack.com"]:
            # Handle community transcript articles
            episodes = self._extract_from_articles(source, podcast_name)

        elif source.site_name in ["reddit.com"]:
            # Handle Reddit transcript discussions
            episodes = self._extract_from_reddit(source, podcast_name)

        else:
            # Generic extraction for unknown sources
            episodes = self._extract_generic(source, podcast_name)

        return episodes

    def _extract_from_official_site(self, source: TranscriptSource, podcast_name: str) -> List[Dict]:
        """Extract episodes from official podcast website"""
        episodes = []

        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(source.url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for episode lists
            episode_links = []

            # Common patterns for episode pages
            selectors = [
                'a[href*="episode"]',
                'a[href*="/episodes/"]',
                '.episode-link a',
                '.episode-title a',
                'h2 a', 'h3 a'
            ]

            for selector in selectors:
                links = soup.select(selector)
                episode_links.extend(links)

            # Process each episode link
            for link in episode_links[:50]:  # Limit to avoid overwhelming
                episode_url = requests.compat.urljoin(source.url, link.get('href', ''))
                episode_title = link.get_text(strip=True)

                if episode_title and len(episode_title) > 5:
                    # Try to extract transcript from episode page
                    transcript = self._extract_transcript_from_url(episode_url)

                    if transcript:
                        episodes.append({
                            'title': episode_title,
                            'url': episode_url,
                            'transcript': transcript,
                            'source': source.site_name,
                            'podcast_name': podcast_name
                        })

                time.sleep(0.5)  # Rate limiting

        except Exception as e:
            logger.warning(f"Failed to extract from official site {source.url}: {e}")

        return episodes

    def _extract_from_github(self, source: TranscriptSource, podcast_name: str) -> List[Dict]:
        """Extract transcripts from GitHub repository"""
        episodes = []

        try:
            # Convert GitHub URL to API URL for file listing
            if "github.com" in source.url:
                api_url = source.url.replace("github.com", "api.github.com/repos") + "/contents"

                import requests
                response = requests.get(api_url, timeout=10)

                if response.status_code == 200:
                    files = response.json()

                    for file_info in files:
                        if file_info['type'] == 'file' and file_info['name'].endswith(('.md', '.txt')):
                            # Download and process transcript file
                            content_response = requests.get(file_info['download_url'])

                            if content_response.status_code == 200:
                                transcript = content_response.text

                                episodes.append({
                                    'title': file_info['name'].replace('.md', '').replace('.txt', ''),
                                    'url': file_info['html_url'],
                                    'transcript': transcript,
                                    'source': 'github.com',
                                    'podcast_name': podcast_name
                                })

        except Exception as e:
            logger.warning(f"Failed to extract from GitHub {source.url}: {e}")

        return episodes

    def _extract_from_articles(self, source: TranscriptSource, podcast_name: str) -> List[Dict]:
        """Extract transcripts from Medium/Substack articles"""
        episodes = []

        try:
            transcript = self._extract_transcript_from_url(source.url)

            if transcript:
                # Try to extract episode title from article
                import requests
                from bs4 import BeautifulSoup

                response = requests.get(source.url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')

                title_element = soup.find('h1') or soup.find('title')
                title = title_element.get_text(strip=True) if title_element else "Unknown Episode"

                episodes.append({
                    'title': title,
                    'url': source.url,
                    'transcript': transcript,
                    'source': source.site_name,
                    'podcast_name': podcast_name
                })

        except Exception as e:
            logger.warning(f"Failed to extract from article {source.url}: {e}")

        return episodes

    def _extract_from_reddit(self, source: TranscriptSource, podcast_name: str) -> List[Dict]:
        """Extract transcripts from Reddit discussions"""
        # Implementation would depend on Reddit API access
        return []

    def _extract_generic(self, source: TranscriptSource, podcast_name: str) -> List[Dict]:
        """Generic extraction for unknown sources"""
        episodes = []

        try:
            transcript = self._extract_transcript_from_url(source.url)

            if transcript and len(transcript) > 1000:  # Reasonable transcript length
                episodes.append({
                    'title': f"Episode from {source.site_name}",
                    'url': source.url,
                    'transcript': transcript,
                    'source': source.site_name,
                    'podcast_name': podcast_name
                })

        except Exception as e:
            logger.warning(f"Failed generic extraction from {source.url}: {e}")

        return episodes

    def _extract_transcript_from_url(self, url: str) -> Optional[str]:
        """Extract transcript text from any URL"""
        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Try multiple selectors for transcript content
            selectors = [
                '.transcript',
                '#transcript',
                '.episode-transcript',
                '.full-text',
                '.verbatim',
                'article',
                '.content',
                '.entry-content',
                '.post-content',
                '.episode-content',
                'main'
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)

                    # Basic quality checks
                    if len(text) > 1000 and self._looks_like_transcript(text):
                        return text

            # Fallback: get all text and filter
            all_text = soup.get_text(separator=' ', strip=True)
            if len(all_text) > 1000 and self._looks_like_transcript(all_text):
                return all_text

        except Exception as e:
            logger.debug(f"Failed to extract transcript from {url}: {e}")

        return None

    def _looks_like_transcript(self, text: str) -> bool:
        """Check if text looks like a podcast transcript"""
        transcript_indicators = [
            'transcript',
            'speaker:',
            'host:',
            'guest:',
            'interviewer:',
            'interviewee:',
            '[music]',
            '[applause]',
            'yeah, so',
            'um, you know',
            'like, I think'
        ]

        text_lower = text.lower()
        indicator_count = sum(1 for indicator in transcript_indicators if indicator in text_lower)

        # Should have some conversational indicators
        return indicator_count >= 2

    def _store_episodes_in_atlas(self, episodes: List[Dict], podcast_name: str, source: TranscriptSource):
        """Store extracted episodes in Atlas database"""

        stored_count = 0

        with get_database_connection() as conn:
            for episode in episodes:
                try:
                    # Check if episode already exists
                    existing = conn.execute(
                        "SELECT id FROM content WHERE url = ?",
                        (episode['url'],)
                    ).fetchone()

                    if existing:
                        # Update existing with transcript
                        conn.execute("""
                            UPDATE content
                            SET content = ?,
                                content_type = 'podcast_transcript',
                                stage = ?,
                                updated_at = ?
                            WHERE url = ?
                        """, (
                            episode['transcript'],
                            self.STAGES[400],  # TRANSCRIPT_STORED
                            datetime.now().isoformat(),
                            episode['url']
                        ))
                    else:
                        # Insert new episode
                        conn.execute("""
                            INSERT INTO content (
                                title, url, content, content_type, stage,
                                created_at, updated_at, metadata
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            f"[PODCAST] {episode['title']}",
                            episode['url'],
                            episode['transcript'],
                            'podcast_transcript',
                            self.STAGES[400],  # TRANSCRIPT_STORED
                            datetime.now().isoformat(),
                            datetime.now().isoformat(),
                            json.dumps({
                                'podcast_name': podcast_name,
                                'transcript_source': source.site_name,
                                'source_reliability': source.reliability_score
                            })
                        ))

                    stored_count += 1

                except Exception as e:
                    logger.error(f"Failed to store episode {episode['title']}: {e}")

            conn.commit()

        logger.info(f"Stored {stored_count} episodes for {podcast_name}")

    def generate_transcript_report(self) -> str:
        """Generate a report of transcript discovery status"""

        with get_database_connection() as conn:
            # Get transcript counts by podcast
            results = conn.execute("""
                SELECT
                    JSON_EXTRACT(metadata, '$.podcast_name') as podcast_name,
                    COUNT(*) as transcript_count,
                    JSON_EXTRACT(metadata, '$.transcript_source') as source
                FROM content
                WHERE content_type = 'podcast_transcript'
                AND JSON_EXTRACT(metadata, '$.podcast_name') IS NOT NULL
                GROUP BY podcast_name, source
                ORDER BY transcript_count DESC
            """).fetchall()

        report = "\n=== PODCAST TRANSCRIPT DISCOVERY REPORT ===\n\n"

        for row in results:
            podcast_name = row[0] or "Unknown"
            count = row[1]
            source = row[2] or "Unknown"

            report += f"{podcast_name}: {count} transcripts from {source}\n"

        return report

# Main execution
def main():
    """Main function for running transcript discovery"""

    # Basic config
    config = {
        'project_root': Path(__file__).parent.parent,
        'database_path': 'data/atlas.db'
    }

    orchestrator = PodcastTranscriptOrchestrator(config)

    # Process all podcasts
    orchestrator.process_all_podcasts()

    # Generate report
    report = orchestrator.generate_transcript_report()
    print(report)

if __name__ == "__main__":
    main()