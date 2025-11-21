#!/usr/bin/env python3
"""
Improved Transcript Finder
Actually finds real transcripts from known sources
"""

import sqlite3
import requests
import time
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote_plus, urljoin
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImprovedTranscriptFinder:
    """Better transcript finder that checks real sources"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def check_known_transcript_sources(self, podcast_name, episode_title):
        """Check known high-quality transcript sources"""

        # Build search terms
        search_terms = [
            f"{podcast_name} {episode_title} transcript",
            f"{podcast_name} {episode_title} full transcript",
            f"{episode_title} transcript {podcast_name}"
        ]

        # Known transcript sources to check
        sources = [
            {
                'name': 'TapeSearch',
                'url_template': 'https://www.tapesearch.com/search?q={query}',
                'link_selector': 'a[href*="/transcript/"]'
            },
            {
                'name': 'Podscripts',
                'url_template': 'https://podscripts.co/?q={query}',
                'link_selector': 'a[href*="/episode/"]'
            },
            {
                'name': 'HappyScribe',
                'url_template': 'https://www.happyscribe.com/public/{show_name}',
                'method': 'direct_show'
            }
        ]

        found_transcripts = []

        for search_term in search_terms:
            for source in sources:
                try:
                    result = self._check_source(source, search_term, podcast_name, episode_title)
                    if result:
                        found_transcripts.extend(result)
                        logger.info(f"Found {len(result)} transcripts from {source['name']}")
                except Exception as e:
                    logger.error(f"Error checking {source['name']}: {e}")

        return found_transcripts

    def _check_source(self, source, search_term, podcast_name, episode_title):
        """Check a specific transcript source"""

        if source['method'] == 'direct_show':
            return self._check_direct_show(source, podcast_name, episode_title)
        else:
            return self._check_search_based(source, search_term)

    def _check_search_based(self, source, search_term):
        """Check search-based transcript sources"""
        url = source['url_template'].format(query=quote_plus(search_term))

        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            transcripts = []
            links = soup.select(source['link_selector'])

            for link in links[:5]:  # Limit to first 5 results
                href = link.get('href')
                if href:
                    if href.startswith('/'):
                        href = urljoin(url, href)

                    # Try to extract transcript from this link
                    transcript_content = self._extract_transcript_from_page(href)
                    if transcript_content:
                        transcripts.append({
                            'source': source['name'],
                            'url': href,
                            'content': transcript_content,
                            'title': link.get_text().strip()
                        })

            return transcripts

        except Exception as e:
            logger.error(f"Search failed for {source['name']}: {e}")
            return []

    def _check_direct_show(self, source, podcast_name, episode_title):
        """Check direct show pages like HappyScribe"""

        # Clean podcast name for URL
        clean_name = re.sub(r'[^a-zA-Z0-9\s-]', '', podcast_name).strip().lower()
        clean_name = re.sub(r'\s+', '-', clean_name)

        url = source['url_template'].format(show_name=clean_name)

        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            transcripts = []

            # Look for episode links
            episode_links = soup.find_all('a', href=True)

            for link in episode_links:
                link_text = link.get_text().strip().lower()
                href = link.get('href')

                # Check if this link matches our episode
                if (href and
                    any(word in link_text for word in episode_title.lower().split()[:3]) and
                    len(link_text) > 20):  # Reasonable title length

                    full_url = urljoin(url, href)
                    transcript_content = self._extract_transcript_from_page(full_url)

                    if transcript_content:
                        transcripts.append({
                            'source': source['name'],
                            'url': full_url,
                            'content': transcript_content,
                            'title': link.get_text().strip()
                        })
                        break  # Found our episode

            return transcripts

        except Exception as e:
            logger.error(f"Direct show check failed for {source['name']}: {e}")
            return []

    def _extract_transcript_from_page(self, url):
        """Extract actual transcript content from a page"""

        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script/style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            text = soup.get_text()

            # Clean up text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = ' '.join(lines)

            # Check if this looks like a transcript
            transcript_indicators = [
                len(text) > 2000,  # Reasonable length
                ':' in text,  # Has dialogue format
                any(word in text.lower() for word in ['transcript', 'speaker', 'host', 'guest']),
                text.count('.') > 50  # Has many sentences
            ]

            if sum(transcript_indicators) >= 3:
                return text[:10000]  # Return first 10K characters

            return None

        except Exception as e:
            logger.error(f"Failed to extract transcript from {url}: {e}")
            return None

    def process_episodes(self, limit=10):
        """Process episodes and find transcripts"""

        conn = sqlite3.connect("podcast_processing.db")

        # Get diverse episodes from different podcasts
        cursor = conn.execute("""
            SELECT e.id, e.title, e.link, e.description, e.podcast_id, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'pending'
            GROUP BY e.podcast_id
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))

        episodes = cursor.fetchall()
        conn.close()

        print(f"🎯 Processing {len(episodes)} diverse episodes from different podcasts...")
        print("=" * 60)

        successful = 0

        for episode in episodes:
            episode_id, title, link, description, podcast_id, podcast_name = episode

            print(f"\n🎙️  Podcast: {podcast_name}")
            print(f"📄 Episode: {title[:80]}...")

            # Check for transcripts
            transcripts = self.check_known_transcript_sources(podcast_name, title)

            if transcripts:
                print(f"✅ SUCCESS! Found {len(transcripts)} transcript(s)")

                # Save the best transcript
                best_transcript = max(transcripts, key=lambda x: len(x['content']))

                conn = sqlite3.connect("podcast_processing.db")
                conn.execute("""
                    UPDATE episodes
                    SET processing_status = 'completed',
                        transcript_found = 1,
                        transcript_text = ?,
                        transcript_source = ?,
                        transcript_url = ?,
                        last_attempt = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (best_transcript['content'], best_transcript['source'], best_transcript['url'], episode_id))
                conn.commit()
                conn.close()

                print(f"💾 Saved transcript from {best_transcript['source']}")
                print(f"📊 Length: {len(best_transcript['content'])} characters")
                successful += 1

            else:
                print(f"❌ No transcripts found")

                # Mark as failed
                conn = sqlite3.connect("podcast_processing.db")
                conn.execute("""
                    UPDATE episodes
                    SET processing_status = 'failed',
                        last_attempt = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (episode_id,))
                conn.commit()
                conn.close()

            time.sleep(1)  # Rate limiting

        print(f"\n🏁 Processing complete!")
        print(f"📊 Results: {successful}/{len(episodes)} episodes found transcripts")
        print(f"📈 Success rate: {(successful/len(episodes))*100:.1f}%")

        return successful

if __name__ == "__main__":
    finder = ImprovedTranscriptFinder()
    finder.process_episodes(10)