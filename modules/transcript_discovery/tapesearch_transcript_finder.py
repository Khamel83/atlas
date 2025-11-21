#!/usr/bin/env python3
"""
TapeSearch Transcript Finder
Access the 4.2M transcripts from TapeSearch
"""

import sqlite3
import requests
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TapeSearchTranscriptFinder:
    """Find transcripts from TapeSearch"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def search_tapesearch(self, podcast_name, episode_title):
        """Search TapeSearch for transcripts"""

        # Try different search queries
        search_queries = [
            f"{podcast_name} {episode_title}",
            f"{episode_title}",
            podcast_name
        ]

        for query in search_queries:
            print(f"🔍 TapeSearch query: {query}")

            url = f"https://www.tapesearch.com/search?q={quote_plus(query)}"

            try:
                response = self.session.get(url, timeout=15)

                if response.status_code == 200:
                    # Look for transcript links in the page
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Find all links that might be transcripts
                    transcript_links = []

                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        text = link.get_text().strip()

                        # Look for transcript episode links
                        if (href.startswith('/transcript/') or
                            'transcript' in href.lower() or
                            len(text) > 50):  # Likely episode titles

                            transcript_links.append({
                                'url': f"https://www.tapesearch.com{href}",
                                'title': text,
                                'search_query': query
                            })

                    print(f"📊 Found {len(transcript_links)} potential transcript links")

                    # Try to extract transcript from each link
                    for i, link_info in enumerate(transcript_links[:3]):  # Try first 3
                        print(f"  📄 Checking link {i+1}: {link_info['title'][:60]}...")

                        transcript = self.extract_transcript_from_tapesearch_page(link_info['url'])
                        if transcript:
                            print(f"  ✅ SUCCESS! Found transcript")
                            return {
                                'url': link_info['url'],
                                'title': link_info['title'],
                                'transcript': transcript,
                                'source': 'tapesearch',
                                'search_query': query
                            }
                        else:
                            print(f"  ❌ No transcript content found")

                        time.sleep(1)  # Rate limiting

                else:
                    print(f"   🚫 TapeSearch returned status {response.status_code}")

            except Exception as e:
                print(f"   🚫 TapeSearch error: {e}")

        return None

    def extract_transcript_from_tapesearch_page(self, url):
        """Extract transcript content from TapeSearch page"""

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up the text
            lines = []
            for line in text.split('\n'):
                line = line.strip()
                if line and len(line) > 5:
                    lines.append(line)

            clean_text = ' '.join(lines)

            # Check if this looks like a transcript
            if self.looks_like_transcript(clean_text):
                return clean_text[:15000]  # Return first 15K characters

            return None

        except Exception as e:
            logger.error(f"Failed to extract from {url}: {e}")
            return None

    def looks_like_transcript(self, text):
        """Check if text looks like a transcript"""

        if len(text) < 500:
            return False

        # Transcript indicators
        indicators = [
            'transcript', 'speaker', 'host', 'guest', 'interview', 'conversation',
            'question:', 'answer:', 'q:', 'a:', '[music]', '[applause]', 'laughs'
        ]

        indicator_count = sum(1 for indicator in indicators if indicator.lower() in text.lower())

        # Check for dialogue format
        dialogue_score = text.count(':') + text.count('"') + text.count("'")

        # Check sentence structure
        sentence_score = text.count('.')

        # Combined score
        score = indicator_count + (dialogue_score / 50) + (sentence_score / 100)

        return score >= 2

    def process_episodes(self, limit=10):
        """Process episodes and find transcripts"""

        conn = sqlite3.connect("podcast_processing.db")

        # Get diverse episodes from popular podcasts
        cursor = conn.execute("""
            SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'pending'
            AND p.name IN (
                'Lex Fridman Podcast', 'Acquired', 'This American Life',
                'The Ezra Klein Show', 'Conversations with Tyler',
                'Stratechery', 'The Knowledge Project', 'Huberman Lab'
            )
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))

        episodes = cursor.fetchall()
        conn.close()

        if not episodes:
            # Fall back to any episodes
            conn = sqlite3.connect("podcast_processing.db")
            cursor = conn.execute("""
                SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name
                FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE e.processing_status = 'pending'
                ORDER BY RANDOM()
                LIMIT ?
            """, (limit,))
            episodes = cursor.fetchall()
            conn.close()

        print(f"🎯 Processing {len(episodes)} episodes...")
        print("=" * 70)

        successful = 0

        for episode in episodes:
            episode_id, title, link, podcast_id, podcast_name = episode

            print(f"\n🎙️  Podcast: {podcast_name}")
            print(f"📄 Episode: {title[:80]}...")

            # Search TapeSearch
            result = self.search_tapesearch(podcast_name, title)

            if result:
                print(f"\n💾 SAVING TRANSCRIPT")
                print(f"📊 Source: {result['url']}")
                print(f"🔍 Found with: {result['search_query']}")
                print(f"📏 Length: {len(result['transcript'])} characters")

                # Save to database
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
                """, (result['transcript'], result['source'], result['url'], episode_id))
                conn.commit()
                conn.close()

                successful += 1
            else:
                print(f"\n❌ No transcript found on TapeSearch")

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

            print("-" * 70)
            time.sleep(2)  # Rate limiting

        print(f"\n🏁 Processing complete!")
        print(f"📊 Results: {successful}/{len(episodes)} episodes found transcripts")
        print(f"📈 Success rate: {(successful/len(episodes))*100:.1f}%")

        return successful

if __name__ == "__main__":
    finder = TapeSearchTranscriptFinder()
    finder.process_episodes(10)