#!/usr/bin/env python3
"""
Focused mass extraction targeting high-success podcast sources
"""

import csv
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import time
import random
import feedparser
from urllib.parse import urljoin

class FocusedMassExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # High-success podcasts based on previous results
        self.priority_feeds = {
            "Lex Fridman Podcast": "https://lexfridman.com/feed/podcast/",
            "EconTalk": "https://feeds.simplecast.com/wgl4xEgL",
            "Conversations with Tyler": "https://cowenconvos.libsyn.com/rss",
            "This American Life": "https://www.thisamericanlife.org/podcast/rss.xml",
            "99% Invisible": "https://feeds.simplecast.com/BqbsxVfO",
            "Radiolab": "https://feeds.simplecast.com/EmVW7VGp",
            "Planet Money": "https://feeds.npr.org/510289/podcast.xml",
            "The Knowledge Project with Shane Parrish": "https://feeds.megaphone.fm/FSMI7575968096",
            "Practical AI": "https://feeds.transistor.fm/practical-ai-machine-learning-data-science-llm",
            "Acquired": "https://feeds.transistor.fm/acquired",
            "Hard Fork": "https://feeds.simplecast.com/l2i9YnTd",
            "The Ezra Klein Show": "https://feeds.simplecast.com/82FI35Px",
            "ACQ2 by Acquired": "https://feeds.transistor.fm/acq2",
            "Accidental Tech Podcast": "https://cdn.atp.fm/rss/public?wtvryzdm",
            "Cortex": "https://www.relay.fm/cortex/feed",
            "Exponent": "https://exponent.fm/feed/",
            "The Vergecast": "https://feeds.megaphone.fm/vergecast",
            "Decoder with Nilay Patel": "https://feeds.megaphone.fm/recodedecode",
            "The Big Picture": "https://feeds.megaphone.fm/the-big-picture",
            "The Rewatchables": "https://feeds.megaphone.fm/the-rewatchables"
        }

    def extract_transcript_from_episode_advanced(self, episode):
        """Advanced transcript extraction with multiple strategies"""

        try:
            response = self.session.get(episode['url'], timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Strategy 1: Look for transcript sections
            transcript_selectors = [
                '.transcript', '#transcript', '[class*="transcript"]',
                '.episode-transcript', '.full-text', '.show-notes',
                '[id*="transcript"]', '.entry-content', '.post-content',
                'article', 'main', '.content-area'
            ]

            for selector in transcript_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(separator=' ', strip=True)

                    # Quality checks for transcript content
                    if (len(text) > 2000 and
                        self.is_likely_transcript(text)):
                        return text

            # Strategy 2: Look for transcript download links
            transcript_links = soup.find_all('a', href=True)
            for link in transcript_links:
                link_text = link.get_text().lower()
                href = link.get('href', '')

                if ('transcript' in link_text or 'full text' in link_text or
                    'transcript' in href.lower()):

                    transcript_url = urljoin(episode['url'], href)
                    transcript = self.download_transcript_from_link(transcript_url)
                    if transcript:
                        return transcript

            # Strategy 3: Look for embedded transcript in JSON-LD or structured data
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Look for transcript in structured data
                        transcript_text = data.get('transcript', '')
                        if transcript_text and len(transcript_text) > 1000:
                            return transcript_text
                except:
                    continue

            # Strategy 4: Parse specific podcast platform patterns
            podcast_name = episode['podcast_name'].lower()

            if 'lex fridman' in podcast_name:
                return self.extract_lex_fridman_transcript(soup)
            elif 'econtalk' in podcast_name:
                return self.extract_econtalk_transcript(soup)
            elif 'this american life' in podcast_name:
                return self.extract_tal_transcript(soup)
            elif '99% invisible' in podcast_name:
                return self.extract_99pi_transcript(soup)

            return None

        except Exception as e:
            print(f"    ❌ Advanced extraction error: {e}")
            return None

    def is_likely_transcript(self, text):
        """Check if text looks like a podcast transcript"""

        # Look for transcript indicators
        transcript_indicators = [
            'transcript', 'speaker', 'host:', 'guest:', 'interviewer:',
            'moderator:', 'narrator:', 'announcer:'
        ]

        # Look for conversational patterns
        conversation_patterns = [
            ':', ' said ', ' says ', ' asked ', ' replied ',
            'yeah', 'um', 'uh', 'you know', 'i think'
        ]

        text_lower = text.lower()

        # Check for transcript indicators
        has_indicators = any(indicator in text_lower for indicator in transcript_indicators)

        # Check for conversational patterns
        has_conversation = sum(1 for pattern in conversation_patterns if pattern in text_lower) >= 3

        # Check for speaker formatting (e.g., "John: Hello there")
        has_speaker_format = len([line for line in text.split('\n') if ':' in line and len(line) < 200]) > 5

        return has_indicators or has_conversation or has_speaker_format

    def extract_lex_fridman_transcript(self, soup):
        """Extract Lex Fridman podcast transcript"""

        # Look for transcript section
        transcript_div = soup.find('div', class_='transcript')
        if transcript_div:
            return transcript_div.get_text(separator=' ', strip=True)

        # Look for show notes with transcript
        content = soup.find('div', class_='entry-content')
        if content:
            text = content.get_text(separator=' ', strip=True)
            if len(text) > 5000 and 'transcript' in text.lower():
                return text

        return None

    def extract_econtalk_transcript(self, soup):
        """Extract EconTalk transcript"""

        # EconTalk has transcripts in specific sections
        transcript_section = soup.find('div', {'id': 'transcript'})
        if transcript_section:
            return transcript_section.get_text(separator=' ', strip=True)

        # Look for transcript links
        transcript_links = soup.find_all('a', href=True)
        for link in transcript_links:
            if 'transcript' in link.get_text().lower():
                transcript_url = urljoin('https://www.econtalk.org/', link['href'])
                return self.download_transcript_from_link(transcript_url)

        return None

    def extract_tal_transcript(self, soup):
        """Extract This American Life transcript"""

        # TAL has act-based transcripts
        acts = soup.find_all('div', class_='act')
        if acts:
            transcript_parts = []
            for act in acts:
                text = act.get_text(separator=' ', strip=True)
                if len(text) > 100:
                    transcript_parts.append(text)

            if transcript_parts:
                return '\n\n'.join(transcript_parts)

        return None

    def extract_99pi_transcript(self, soup):
        """Extract 99% Invisible transcript"""

        # Look for transcript toggle/section
        transcript_section = soup.find('div', class_='transcript')
        if transcript_section:
            return transcript_section.get_text(separator=' ', strip=True)

        # Look for episode content
        episode_content = soup.find('div', class_='episode-content')
        if episode_content:
            text = episode_content.get_text(separator=' ', strip=True)
            if len(text) > 2000 and self.is_likely_transcript(text):
                return text

        return None

    def download_transcript_from_link(self, url):
        """Download transcript from a direct link"""

        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Check if it's HTML or plain text
                if 'text/html' in response.headers.get('content-type', ''):
                    soup = BeautifulSoup(response.content, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                else:
                    text = response.text

                if len(text) > 1000 and self.is_likely_transcript(text):
                    return text
        except:
            pass

        return None

    def store_episode_with_transcript(self, episode, transcript):
        """Store episode and transcript in database"""

        try:
            conn = sqlite3.connect('data/atlas.db')
            cursor = conn.cursor()

            # Check if already exists
            existing = cursor.execute(
                "SELECT id FROM content WHERE url = ?",
                (episode['url'],)
            ).fetchone()

            if existing:
                conn.close()
                return False

            # Insert new transcript
            cursor.execute("""
                INSERT INTO content (title, url, content, content_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"[{episode['podcast_name']}] {episode['title']}",
                episode['url'],
                transcript,
                'podcast_transcript',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            print(f"    ✅ Added: {episode['title'][:50]}... ({len(transcript):,} chars)")
            return True

        except Exception as e:
            print(f"    ❌ Database error: {e}")
            return False

    def process_priority_podcasts(self, episodes_per_podcast=100):
        """Process priority podcasts for maximum transcript yield"""

        print("FOCUSED MASS TRANSCRIPT EXTRACTION")
        print("=" * 80)
        print(f"Priority podcasts: {len(self.priority_feeds)}")
        print(f"Target episodes per podcast: {episodes_per_podcast}")
        print("=" * 80)

        total_transcripts = 0

        for i, (podcast_name, rss_url) in enumerate(self.priority_feeds.items(), 1):

            print(f"\n[{i}/{len(self.priority_feeds)}] {podcast_name}")
            print(f"RSS: {rss_url}")

            try:
                # Parse RSS feed
                feed = feedparser.parse(rss_url)

                if not feed.entries:
                    print(f"  ❌ No entries in RSS feed")
                    continue

                print(f"  Found {len(feed.entries)} episodes in RSS")

                podcast_transcripts = 0
                episodes_processed = 0

                # Process episodes
                for entry in feed.entries[:episodes_per_podcast]:

                    episode_url = entry.get('link', '')
                    if not episode_url:
                        continue

                    title = entry.get('title', 'Untitled Episode')

                    episode = {
                        'podcast_name': podcast_name,
                        'title': title,
                        'url': episode_url,
                        'pub_date': entry.get('published', ''),
                        'description': entry.get('description', '')
                    }

                    episodes_processed += 1
                    print(f"  [{episodes_processed}/{min(len(feed.entries), episodes_per_podcast)}] {title[:50]}...")

                    # Extract transcript
                    transcript = self.extract_transcript_from_episode_advanced(episode)

                    if transcript:
                        success = self.store_episode_with_transcript(episode, transcript)
                        if success:
                            podcast_transcripts += 1
                            total_transcripts += 1
                    else:
                        print(f"    ❌ No transcript found")

                    # Rate limiting
                    time.sleep(random.uniform(0.8, 2.0))

                    # Stop if we have enough for this podcast
                    if podcast_transcripts >= 20:  # Max per podcast
                        break

                print(f"  📊 {podcast_name}: {podcast_transcripts} transcripts extracted")

            except Exception as e:
                print(f"  ❌ Error processing {podcast_name}: {e}")

            # Pause between podcasts
            time.sleep(random.uniform(2, 4))

        # Final summary
        print(f"\n{'='*80}")
        print("FOCUSED EXTRACTION COMPLETE")
        print(f"{'='*80}")
        print(f"Total new transcripts: {total_transcripts}")

        # Check database totals
        conn = sqlite3.connect('data/atlas.db')
        cursor = conn.cursor()

        total_in_db = cursor.execute(
            "SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'"
        ).fetchone()[0]

        print(f"Total transcripts in database: {total_in_db:,}")
        conn.close()

def main():
    extractor = FocusedMassExtractor()
    extractor.process_priority_podcasts(episodes_per_podcast=50)

if __name__ == "__main__":
    main()