#!/usr/bin/env python3
"""
Continuous transcript extraction engine for all queued episodes
"""

import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
import json
import threading
from urllib.parse import urljoin, urlparse
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/transcript_extraction.log'),
        logging.StreamHandler()
    ]
)

class TranscriptExtractionEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()

        # Load transcript extraction patterns
        self.transcript_patterns = self.load_transcript_patterns()

        # Track progress
        self.extraction_stats = {
            'total_processed': 0,
            'transcripts_found': 0,
            'failed_extractions': 0,
            'current_podcast': '',
            'start_time': datetime.now()
        }

    def load_transcript_patterns(self):
        """Load transcript extraction patterns from config"""
        patterns = {
            'Lex Fridman Podcast': {
                'domains': ['lexfridman.com'],
                'selectors': ['.transcript', '.episode-transcript', '.transcript-text', '.full-transcript'],
                'min_length': 1000,
                'success_rate': 0.95
            },
            'EconTalk': {
                'domains': ['econtalk.org'],
                'selectors': ['.transcript', '.episode-transcript', '.transcript-text'],
                'min_length': 800,
                'success_rate': 0.90
            },
            'Acquired': {
                'domains': ['acquired.fm'],
                'selectors': ['.transcript', '.episode-transcript'],
                'min_length': 1500,
                'success_rate': 0.85
            },
            'Conversations with Tyler': {
                'domains': ['conversationswithtyler.com'],
                'selectors': ['.transcript', '.episode-transcript'],
                'min_length': 800,
                'success_rate': 0.80
            },
            'Planet Money': {
                'domains': ['npr.org'],
                'selectors': ['.transcript', '.storytext', '.story-text'],
                'min_length': 500,
                'success_rate': 0.75
            },
            'Radiolab': {
                'domains': ['radiolab.org'],
                'selectors': ['.transcript', '.episode-transcript'],
                'min_length': 600,
                'success_rate': 0.70
            },
            '99% Invisible': {
                'domains': ['99percentinvisible.org'],
                'selectors': ['.transcript', '.episode-transcript'],
                'min_length': 800,
                'success_rate': 0.75
            },
            'This American Life': {
                'domains': ['thisamericanlife.org'],
                'selectors': ['.transcript', '.storytext', '.story-text'],
                'min_length': 1000,
                'success_rate': 0.85
            },
            'The Ezra Klein Show': {
                'domains': ['nytimes.com'],
                'selectors': ['.transcript', '.episode-transcript'],
                'min_length': 1000,
                'success_rate': 0.80
            },
            'Hard Fork': {
                'domains': ['nytimes.com'],
                'selectors': ['.transcript', '.episode-transcript'],
                'min_length': 800,
                'success_rate': 0.75
            },
            'Stratechery': {
                'domains': ['stratechery.com'],
                'selectors': ['.transcript', '.episode-transcript'],
                'min_length': 1000,
                'success_rate': 0.85
            },
            'Sharp Tech with Ben Thompson': {
                'domains': ['stratechery.com'],
                'selectors': ['.transcript', '.episode-transcript'],
                'min_length': 800,
                'success_rate': 0.80
            },
            'Universal': {
                'selectors': [
                    '.transcript', '#transcript', '[class*="transcript"]',
                    '.episode-transcript', '.full-text', '.show-notes',
                    '[id*="transcript"]', '.entry-content', '.post-content',
                    'article', 'main', '.content-area', '.storytext',
                    '.story-text', '.article-content'
                ],
                'min_length': 500,
                'max_length': 50000
            }
        }
        return patterns

    def get_unprocessed_episodes(self, batch_size=100):
        """Get episodes that haven't been processed yet"""
        self.cursor.execute('''
            SELECT id, title, url FROM content
            WHERE content_type = 'podcast_episode'
            AND url NOT IN (SELECT source_url FROM podcast_transcripts WHERE source_url IS NOT NULL)
            ORDER BY created_at
            LIMIT ?
        ''', (batch_size,))

        return self.cursor.fetchall()

    def identify_podcast_from_title(self, title):
        """Identify podcast name from episode title"""
        title_lower = title.lower()

        podcast_keywords = {
            'Lex Fridman Podcast': ['lex fridman'],
            'EconTalk': ['econtalk'],
            'Acquired': ['acquired'],
            'ACQ2 by Acquired': ['acq2'],
            'Conversations with Tyler': ['conversations with tyler'],
            'Planet Money': ['planet money'],
            'Radiolab': ['radiolab'],
            '99% Invisible': ['99% invisible'],
            'This American Life': ['this american life'],
            'The Ezra Klein Show': ['ezra klein'],
            'Hard Fork': ['hard fork'],
            'Stratechery': ['stratechery'],
            'Sharp Tech with Ben Thompson': ['sharp tech'],
            'The Recipe with Kenji and Deb': ['recipe with kenji'],
            'The Knowledge Project with Shane Parrish': ['knowledge project'],
            'The Rewatchables': ['rewatchables'],
            'Decoder with Nilay Patel': ['decoder'],
            'The Vergecast': ['vergecast'],
            'The Big Picture': ['big picture'],
            'Practical AI': ['practical ai'],
            'Cortex': ['cortex'],
            'Exponent': ['exponent'],
            'Accidental Tech Podcast': ['accidental tech'],
            'Political Gabfest': ['political gabfest'],
            'The NPR Politics Podcast': ['npr politics'],
            'Today, Explained': ['today explained'],
            'The Cognitive Revolution': ['cognitive revolution']
        }

        for podcast, keywords in podcast_keywords.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return podcast

        return 'Unknown'

    def extract_transcript_from_url(self, url, podcast_name):
        """Extract transcript from episode URL"""
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Get podcast-specific patterns
            pattern = self.transcript_patterns.get(podcast_name, self.transcript_patterns['Universal'])

            # Try each selector
            for selector in pattern['selectors']:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(separator=' ', strip=True)

                    # Clean the text
                    text = re.sub(r'\s+', ' ', text).strip()

                    # Quality checks
                    if (len(text) >= pattern['min_length'] and
                        len(text) <= pattern.get('max_length', 100000) and
                        self.is_likely_transcript(text)):

                        return text

            # Look for transcript download links
            transcript_links = soup.find_all('a', href=True)
            for link in transcript_links:
                link_text = link.get_text().lower()
                href = link.get('href', '')

                if ('transcript' in link_text or 'full text' in link_text or
                    'read' in link_text or 'transcript' in href.lower()):

                    transcript_url = urljoin(url, href)
                    transcript = self.download_transcript_from_link(transcript_url)
                    if transcript:
                        return transcript

            return None

        except Exception as e:
            logging.error(f"Error extracting transcript from {url}: {e}")
            return None

    def download_transcript_from_link(self, transcript_url):
        """Download transcript from direct link"""
        try:
            response = self.session.get(transcript_url, timeout=15)
            if response.status_code == 200:
                text = response.text
                if len(text) > 500 and self.is_likely_transcript(text):
                    return text
        except Exception as e:
            logging.error(f"Error downloading transcript from {transcript_url}: {e}")
        return None

    def is_likely_transcript(self, text):
        """Check if text is likely a transcript vs show notes"""
        # Check for transcript indicators
        transcript_indicators = [
            'speaker:', 'host:', 'guest:', 'interviewer:', 'interviewee:',
            'transcript', 'full transcript', 'complete transcript',
            'episode transcript', 'show transcript'
        ]

        text_lower = text.lower()
        indicator_count = sum(1 for indicator in transcript_indicators if indicator in text_lower)

        # Check for excessive HTML/markdown (likely show notes)
        html_tags = re.findall(r'<[^>]+>', text)
        markdown_links = re.findall(r'\[([^\]]+)\]\([^)]+\)', text)

        # Heuristic scoring
        score = indicator_count * 2
        score -= len(html_tags) * 0.5
        score -= len(markdown_links) * 0.3

        # Check word patterns (transcripts have more conversational patterns)
        words = text.split()
        question_words = words.count('?') + words.count('what') + words.count('how') + words.count('why')
        conversational_words = words.count('well') + words.count('like') + words.count('you know')

        score += question_words * 0.1
        score += conversational_words * 0.05

        return score > 1.0

    def save_transcript(self, episode_id, url, transcript_text, podcast_name):
        """Save transcript to database"""
        try:
            # Get episode title
            self.cursor.execute('SELECT title FROM content WHERE id = ?', (episode_id,))
            result = self.cursor.fetchone()
            episode_title = result[0] if result else 'Unknown Episode'

            # Save to podcast_transcripts table
            self.cursor.execute('''
                INSERT INTO podcast_transcripts (
                    podcast_name, episode_title, transcript, source, source_url,
                    metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                podcast_name,
                episode_title,
                transcript_text,
                'web_extraction',
                url,
                json.dumps({'quality_score': self.calculate_quality_score(transcript_text)}),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            # Update content table to mark as processed
            self.cursor.execute('''
                UPDATE content SET content_type = 'podcast_transcript'
                WHERE id = ?
            ''', (episode_id,))

            self.conn.commit()
            return True

        except Exception as e:
            logging.error(f"Error saving transcript: {e}")
            return False

    def calculate_quality_score(self, transcript):
        """Calculate quality score for transcript"""
        score = 0
        words = transcript.split()

        # Length score
        if len(words) > 1000:
            score += 0.3
        elif len(words) > 500:
            score += 0.2

        # Conversational indicators
        question_count = transcript.count('?')
        speaker_pattern = len(re.findall(r'[A-Z][a-z]+:', transcript))

        if question_count > 10:
            score += 0.2
        if speaker_pattern > 5:
            score += 0.2

        # Content density (ratio of actual content vs markup)
        content_ratio = len(re.sub(r'[^\w\s]', '', transcript)) / len(transcript)
        score += content_ratio * 0.3

        return min(score, 1.0)

    def process_episodes_batch(self, batch_size=50):
        """Process a batch of episodes"""
        episodes = self.get_unprocessed_episodes(batch_size)

        if not episodes:
            logging.info("No unprocessed episodes found")
            return 0

        transcripts_found = 0

        for i, (episode_id, title, url) in enumerate(episodes, 1):
            try:
                podcast_name = self.identify_podcast_from_title(title)
                self.extraction_stats['current_podcast'] = podcast_name

                logging.info(f"🎯 [{i}/{len(episodes)}] Processing: {title[:60]}...")
                logging.info(f"   📺 Podcast: {podcast_name}")
                logging.info(f"   🔗 URL: {url}")

                # Extract transcript
                transcript = self.extract_transcript_from_url(url, podcast_name)

                if transcript:
                    # Save transcript
                    if self.save_transcript(episode_id, url, transcript, podcast_name):
                        transcripts_found += 1
                        self.extraction_stats['transcripts_found'] += 1
                        logging.info(f"   ✅ SUCCESS: Transcript saved ({len(transcript)} chars)")
                        logging.info(f"   📊 Total transcripts: {self.extraction_stats['transcripts_found']}")
                else:
                    self.extraction_stats['failed_extractions'] += 1
                    logging.info(f"   ❌ No transcript found")

                self.extraction_stats['total_processed'] += 1

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                logging.error(f"Error processing episode {episode_id}: {e}")
                self.extraction_stats['failed_extractions'] += 1

        return transcripts_found

    def run_continuous_extraction(self, max_batches=None):
        """Run continuous transcript extraction"""
        logging.info("🚀 STARTING CONTINUOUS TRANSCRIPT EXTRACTION")
        logging.info("=" * 80)
        logging.info(f"📊 Processing episodes in batches of 50")
        logging.info(f"⏱️  Rate limiting: 1 second between requests")
        logging.info("=" * 80)

        batch_count = 0
        total_transcripts = 0

        while True:
            if max_batches and batch_count >= max_batches:
                logging.info("🎯 Reached maximum batch limit")
                break

            logging.info(f"\n🔄 Processing batch {batch_count + 1}...")
            transcripts_found = self.process_episodes_batch(50)

            if transcripts_found == 0:
                logging.info("📭 No transcripts found in this batch")
                break

            total_transcripts += transcripts_found
            batch_count += 1

            # Progress report
            self.print_progress_report()

            # Check if we should continue
            remaining_episodes = self.get_unprocessed_episodes(1)
            if not remaining_episodes:
                logging.info("🎉 All episodes processed!")
                break

        logging.info("\n" + "=" * 80)
        logging.info("🎉 TRANSCRIPT EXTRACTION COMPLETE!")
        logging.info("=" * 80)
        logging.info(f"📊 Total batches processed: {batch_count}")
        logging.info(f"📊 Total transcripts found: {total_transcripts}")
        logging.info(f"📊 Total episodes processed: {self.extraction_stats['total_processed']}")
        logging.info(f"📊 Failed extractions: {self.extraction_stats['failed_extractions']}")
        logging.info("=" * 80)

        self.conn.close()
        return total_transcripts

    def print_progress_report(self):
        """Print current progress"""
        elapsed = datetime.now() - self.extraction_stats['start_time']
        hours = elapsed.total_seconds() / 3600

        success_rate = (self.extraction_stats['transcripts_found'] /
                       max(1, self.extraction_stats['total_processed'])) * 100

        episodes_per_hour = self.extraction_stats['total_processed'] / max(1, hours)

        logging.info(f"\n📊 PROGRESS REPORT:")
        logging.info(f"   🎯 Episodes processed: {self.extraction_stats['total_processed']}")
        logging.info(f"   ✅ Transcripts found: {self.extraction_stats['transcripts_found']}")
        logging.info(f"   ❌ Failed extractions: {self.extraction_stats['failed_extractions']}")
        logging.info(f"   📈 Success rate: {success_rate:.1f}%")
        logging.info(f"   ⚡ Processing speed: {episodes_per_hour:.1f} episodes/hour")
        logging.info(f"   ⏱️  Time elapsed: {hours:.1f} hours")

    def get_estimated_completion_time(self):
        """Get estimated completion time"""
        remaining_episodes = len(self.get_unprocessed_episodes(1000))
        if remaining_episodes == 0:
            return "Already complete!"

        current_speed = self.extraction_stats['total_processed'] / max(1, (datetime.now() - self.extraction_stats['start_time']).total_seconds() / 3600)

        if current_speed > 0:
            hours_needed = remaining_episodes / current_speed
            return f"Estimated {hours_needed:.1f} hours remaining"
        else:
            return "Cannot estimate (processing just started)"

def main():
    engine = TranscriptExtractionEngine()

    # Check current status
    unprocessed = len(engine.get_unprocessed_episodes(1))
    logging.info(f"📋 Found {unprocessed} episodes to process")

    if unprocessed == 0:
        logging.info("🎉 No episodes need processing!")
        return

    # Run extraction
    total_transcripts = engine.run_continuous_extraction(max_batches=None)

    print(f"\n✅ Extraction complete! Found {total_transcripts} transcripts")

if __name__ == "__main__":
    main()