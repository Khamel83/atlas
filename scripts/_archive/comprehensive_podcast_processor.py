#!/usr/bin/env python3
"""
Comprehensive Podcast Transcript Processor

Builds specialized scrapers for major podcast networks and expands successful sources.
Priority: NPR Network (8 podcasts), This American Life (1), Lex Fridman (1)
"""

import requests
import sqlite3
import json
import time
import re
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

class PodcastNetworkScrapers:
    """Specialized scrapers for different podcast networks"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.db_path = "atlas.db"

    def get_rss_episodes(self, feed_url, limit=10):
        """Get episodes from RSS feed"""
        try:
            response = self.session.get(feed_url, timeout=30)
            root = ET.fromstring(response.content)

            episodes = []
            for item in root.findall('.//item')[:limit]:
                title_elem = item.find('title')
                link_elem = item.find('link')
                description_elem = item.find('description')

                if title_elem is not None and link_elem is not None:
                    episodes.append({
                        'title': title_elem.text,
                        'link': link_elem.text,
                        'description': description_elem.text if description_elem is not None else ""
                    })

            return episodes

        except Exception as e:
            print(f"❌ RSS fetch failed for {feed_url}: {e}")
            return []

    def scrape_npr_transcript(self, episode_url):
        """Enhanced NPR transcript scraper (Planet Money, Indicator, etc.)"""
        try:
            response = self.session.get(episode_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            # NPR transcript patterns
            transcript_selectors = [
                '.transcript-container',
                '[data-testid="transcript"]',
                '.episode-transcript',
                '.storytext',
                '#transcript',
                '.transcript'
            ]

            for selector in transcript_selectors:
                element = soup.select_one(selector)
                if element:
                    # Clean up
                    for tag in element.find_all(['script', 'style', 'nav', 'aside', 'footer']):
                        tag.decompose()

                    text = element.get_text(separator=' ', strip=True)

                    # NPR transcripts are usually long
                    if len(text) > 2000:
                        return self.clean_transcript_text(text)

            # Fallback: look for transcript link
            transcript_link = soup.find('a', href=lambda x: x and 'transcript' in x.lower())
            if transcript_link:
                transcript_url = urljoin(episode_url, transcript_link['href'])
                return self.scrape_transcript_page(transcript_url)

            return None

        except Exception as e:
            print(f"❌ NPR scraping failed for {episode_url}: {e}")
            return None

    def scrape_this_american_life_transcript(self, episode_url):
        """Enhanced This American Life scraper"""
        try:
            response = self.session.get(episode_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for transcript link
            transcript_links = soup.find_all('a', href=lambda x: x and ('transcript' in x.lower() or 'full-episode' in x.lower()))

            for link in transcript_links:
                transcript_url = urljoin(episode_url, link['href'])
                transcript_text = self.scrape_transcript_page(transcript_url)
                if transcript_text:
                    return transcript_text

            # Direct transcript extraction
            transcript_selectors = [
                '.transcript',
                '.story-text',
                '.episode-transcript',
                '#transcript-content'
            ]

            for selector in transcript_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 3000:  # TAL transcripts are very long
                        return self.clean_transcript_text(text)

            return None

        except Exception as e:
            print(f"❌ TAL scraping failed for {episode_url}: {e}")
            return None

    def scrape_lex_fridman_transcript(self, episode_url):
        """Enhanced Lex Fridman scraper"""
        try:
            # Convert to lexfridman.com if needed
            if 'lexfridman.com' not in episode_url:
                # Extract episode number from URL or title
                episode_match = re.search(r'#(\d+)', episode_url)
                if episode_match:
                    episode_num = episode_match.group(1)
                    episode_url = f"https://lexfridman.com/{episode_num}/"

            response = self.session.get(episode_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Lex Fridman transcript patterns
            transcript_selectors = [
                'section#transcript',
                '.transcript-section',
                '#transcript',
                '.episode-transcript',
                '.transcript'
            ]

            for selector in transcript_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 5000:  # Lex episodes are very long
                        return self.clean_transcript_text(text)

            # Look for transcript link
            transcript_link = soup.find('a', string=lambda x: x and 'transcript' in x.lower())
            if transcript_link and transcript_link.get('href'):
                transcript_url = urljoin(episode_url, transcript_link['href'])
                return self.scrape_transcript_page(transcript_url)

            return None

        except Exception as e:
            print(f"❌ Lex Fridman scraping failed for {episode_url}: {e}")
            return None

    def scrape_transcript_page(self, url):
        """Generic transcript page scraper"""
        try:
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements
            for tag in soup.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header']):
                tag.decompose()

            # Try main content areas
            content_selectors = [
                'main',
                'article',
                '.content',
                '.post-content',
                '.entry-content',
                '.transcript',
                'body'
            ]

            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 1000:
                        return self.clean_transcript_text(text)

            return None

        except Exception as e:
            print(f"❌ Generic scraping failed for {url}: {e}")
            return None

    def clean_transcript_text(self, text):
        """Clean transcript text"""
        if not text:
            return ""

        # Remove common podcast/web artifacts
        cleaning_patterns = [
            r'This episode is brought to you by.*?(?=\\n|$)',
            r'Support for this podcast.*?(?=\\n|$)',
            r'Subscribe to.*?(?=\\n|$)',
            r'Follow us on.*?(?=\\n|$)',
            r'Visit our website.*?(?=\\n|$)',
            r'Copyright \d{4}.*?(?=\\n|$)'
        ]

        for pattern in cleaning_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def save_transcript_to_db(self, episode_data, transcript_text, podcast_title):
        """Save transcript to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            title = f"[TRANSCRIPT] {episode_data['title']}"
            content = f"Podcast: {podcast_title}\\nEpisode: {episode_data['title']}\\n\\n{transcript_text}"

            cursor.execute("""
                INSERT OR IGNORE INTO content
                (url, title, content, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                episode_data['link'],
                title[:500],
                content,  # No length limit!
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            print(f"❌ Database save failed: {e}")
            return False

    def process_podcast_by_network(self, podcast_data):
        """Process podcast based on network type"""

        feed_url = podcast_data['feed_url']
        title = podcast_data['title']
        network = self.identify_network(feed_url)

        print(f"\\n🎙️ Processing: {title}")
        print(f"   🌐 Network: {network}")

        # Get recent episodes
        episodes = self.get_rss_episodes(feed_url, limit=5)  # Process 5 recent episodes

        if not episodes:
            print(f"   ❌ No episodes found")
            return 0

        processed = 0

        for episode in episodes:
            print(f"   📻 Processing: {episode['title'][:50]}...")

            # Choose scraper based on network
            transcript_text = None

            if 'npr.org' in feed_url.lower():
                transcript_text = self.scrape_npr_transcript(episode['link'])
            elif 'thisamericanlife.org' in feed_url.lower():
                transcript_text = self.scrape_this_american_life_transcript(episode['link'])
            elif 'lexfridman.com' in feed_url.lower():
                transcript_text = self.scrape_lex_fridman_transcript(episode['link'])
            else:
                # Generic scraper for other networks
                transcript_text = self.scrape_transcript_page(episode['link'])

            if transcript_text and len(transcript_text) > 1000:
                if self.save_transcript_to_db(episode, transcript_text, title):
                    processed += 1
                    print(f"     ✅ Saved transcript ({len(transcript_text)} chars)")
                else:
                    print(f"     ❌ Failed to save")
            else:
                print(f"     ⚠️  No transcript found or too short")

            time.sleep(3)  # Be respectful to servers

        return processed

    def identify_network(self, feed_url):
        """Identify podcast network from feed URL"""
        domain = urlparse(feed_url).netloc.lower()

        if 'npr.org' in domain:
            return 'NPR Network'
        elif 'thisamericanlife.org' in domain:
            return 'This American Life'
        elif 'lexfridman.com' in domain:
            return 'Lex Fridman'
        elif 'gimletmedia.com' in domain:
            return 'Gimlet/Spotify'
        elif 'nytimes.com' in domain:
            return 'New York Times'
        else:
            return 'Other'

def main():
    """Process all high-potential podcasts"""

    print("🚀 COMPREHENSIVE PODCAST TRANSCRIPT PROCESSOR")
    print("=" * 60)

    # Load podcast analysis
    if not Path('podcast_transcript_analysis.json').exists():
        print("❌ Run find_podcast_transcripts.py first")
        return False

    with open('podcast_transcript_analysis.json') as f:
        analysis = json.load(f)

    # Filter for high-potential networks
    high_potential_domains = ['npr.org', 'thisamericanlife.org', 'lexfridman.com']

    high_potential_podcasts = []
    for podcast in analysis['podcasts']:
        feed_url = podcast['feed_url'].lower()
        if any(domain in feed_url for domain in high_potential_domains):
            high_potential_podcasts.append(podcast)

    print(f"📊 Found {len(high_potential_podcasts)} high-potential podcasts to process")

    if len(high_potential_podcasts) == 0:
        print("❌ No high-potential podcasts found")
        return False

    # Process each podcast
    processor = PodcastNetworkScrapers()
    total_processed = 0

    for podcast in high_potential_podcasts:
        try:
            processed = processor.process_podcast_by_network(podcast)
            total_processed += processed

            if processed > 0:
                print(f"   ✅ Success: {processed} transcripts processed")
            else:
                print(f"   ❌ No transcripts extracted")

        except Exception as e:
            print(f"   ❌ Processing failed: {e}")

    print(f"\\n🎉 PROCESSING COMPLETE!")
    print(f"✅ Total new transcripts: {total_processed}")
    print(f"📊 Networks processed: NPR, This American Life, Lex Fridman")

    # Final database stats
    conn = sqlite3.connect(processor.db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM content WHERE title LIKE '%TRANSCRIPT%'")
    total_transcripts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM content")
    total_content = cursor.fetchone()[0]

    conn.close()

    print(f"\\n📈 UPDATED DATABASE:")
    print(f"   🎙️ Total transcripts: {total_transcripts}")
    print(f"   📊 Total content: {total_content}")

    return total_processed > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)