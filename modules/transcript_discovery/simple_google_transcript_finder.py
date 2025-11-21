#!/usr/bin/env python3
"""
Simple Google Transcript Finder
Just search Google and follow transcript links
"""

import sqlite3
import requests
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleGoogleTranscriptFinder:
    """Simple Google search + follow links approach"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def google_search_and_follow_links(self, episode_title, podcast_name=None):
        """Search Google for transcript and follow promising links"""

        # Build search query
        if podcast_name:
            search_query = f'"{episode_title}" transcript {podcast_name}'
        else:
            search_query = f'"{episode_title}" transcript'

        print(f"🔍 Searching: {search_query}")

        # Search Google
        search_url = f"https://www.google.com/search?q={quote_plus(search_query)}"

        try:
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Get all result links
            result_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Skip Google internal links
                if href.startswith('/url?'):
                    # Extract actual URL from Google redirect
                    match = re.search(r'url=([^&]+)', href)
                    if match:
                        actual_url = match.group(1)
                        result_links.append({
                            'url': actual_url,
                            'title': link.get_text().strip()
                        })
                elif href.startswith('http') and 'google.com' not in href:
                    result_links.append({
                        'url': href,
                        'title': link.get_text().strip()
                    })

            print(f"📊 Found {len(result_links)} potential links")

            # Check first 10 promising links
            for i, link_info in enumerate(result_links[:10]):
                url = link_info['url']
                title = link_info['title']

                print(f"\n🔗 Link {i+1}: {title[:60]}...")
                print(f"   URL: {url[:80]}...")

                # Skip obvious non-transcript sites
                skip_domains = ['spotify.com', 'apple.com/podcasts', 'stitcher.com', 'podbay.fm']
                if any(skip in url.lower() for skip in skip_domains):
                    print(f"   ⏭️  Skipping (podcast platform)")
                    continue

                # Try to get transcript from this page
                transcript = self.extract_transcript_from_page(url)
                if transcript:
                    print(f"   ✅ SUCCESS! Found transcript")
                    return {
                        'url': url,
                        'title': title,
                        'transcript': transcript,
                        'source': 'google_search'
                    }
                else:
                    print(f"   ❌ No transcript found on this page")

                time.sleep(1)  # Be nice to servers

            return None

        except Exception as e:
            print(f"   🚫 Google search failed: {e}")
            return None

    def extract_transcript_from_page(self, url):
        """Extract transcript from a page"""

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                element.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up the text
            lines = []
            for line in text.split('\n'):
                line = line.strip()
                if line and len(line) > 10:  # Skip very short lines
                    lines.append(line)

            clean_text = ' '.join(lines)

            # Check if this looks like a transcript
            if self.looks_like_transcript(clean_text):
                return clean_text[:20000]  # Return first 20K characters

            return None

        except Exception as e:
            logger.error(f"Failed to extract from {url}: {e}")
            return None

    def looks_like_transcript(self, text):
        """Check if text looks like a transcript"""

        # Must have reasonable length
        if len(text) < 1000:
            return False

        # Check for transcript indicators
        indicators = [
            'transcript', 'speaker', 'host', 'guest', 'interview', 'conversation',
            'question:', 'answer:', 'q:', 'a:', '[music]', '[applause]'
        ]

        indicator_count = sum(1 for indicator in indicators if indicator.lower() in text.lower())

        # Check for dialogue format (lots of colons and quotes)
        dialogue_score = text.count(':') + text.count('"') + text.count("'")

        # Check sentence structure (lots of periods = complete sentences)
        sentence_score = text.count('.')

        # Combined score
        score = indicator_count + (dialogue_score / 100) + (sentence_score / 50)

        return score >= 3  # Reasonable threshold

    def process_episodes(self, limit=10):
        """Process episodes and find transcripts"""

        conn = sqlite3.connect("podcast_processing.db")

        # Get diverse episodes
        cursor = conn.execute("""
            SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name
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
        print("=" * 70)

        successful = 0

        for episode in episodes:
            episode_id, title, link, podcast_id, podcast_name = episode

            print(f"\n🎙️  Podcast: {podcast_name}")
            print(f"📄 Episode: {title[:80]}...")

            # Try to find transcript
            result = self.google_search_and_follow_links(title, podcast_name)

            if result:
                print(f"\n💾 SAVING TRANSCRIPT")
                print(f"📊 Source: {result['url']}")
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
                print(f"\n❌ No transcript found")

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
    finder = SimpleGoogleTranscriptFinder()
    finder.process_episodes(10)