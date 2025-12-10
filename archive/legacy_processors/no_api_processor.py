#!/usr/bin/env python3
"""
No-API Processor - Works without Tavily using direct crawling strategies
"""

import sqlite3
import requests
import time
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import random

class NoAPIProcessor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Known transcript sites that don't require search
        self.transcript_sites = [
            "podscripts.co",
            "transcript.fm",
            "listennotes.com",
            "podcastaddict.com",
            "player.fm",
            "stitcher.com",
            "podbean.com"
        ]

        print("🚀 NO-API PROCESSOR - Zero Dependencies")
        print("=" * 50)
        print("✅ No Tavily required")
        print("✅ Direct crawling only")
        print("✅ Archive sources")
        print("✅ RSS feed extraction")
        print("=" * 50)

    def get_episodes_to_process(self, limit=100):
        """Get episodes that need processing"""
        conn = sqlite3.connect("podcast_processing.db")
        cursor = conn.execute("""
            SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name, p.rss_feed
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'failed'
            AND (e.transcript_text IS NULL OR LENGTH(e.transcript_text) < 5000)
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))

        episodes = cursor.fetchall()
        conn.close()
        return episodes

    def construct_transcript_urls(self, podcast_name, episode_title):
        """Construct likely transcript URLs without searching"""

        urls = []

        # Known transcript sites with specific patterns
        podcast_lower = podcast_name.lower()

        # Lex Fridman specific patterns
        if 'lex fridman' in podcast_lower:
            # Extract guest name from title
            guest_name = episode_title.split(':')[0].strip() if ':' in episode_title else episode_title.split('–')[0].strip()
            # Remove episode number and clean
            guest_name = re.sub(r'^#\d+\s*[-–]\s*', '', guest_name).strip()
            guest_slug = guest_name.lower().replace(' ', '-').replace('?', '').replace('!', '').replace(',', '').replace('.', '').replace('–', '-').replace('--', '-')
            urls.extend([
                f"https://lexfridman.com/{guest_slug}-transcript/",
                f"https://lexfridman.com/{guest_slug}/",
                f"https://lexfridman.com/podcast/{guest_slug}/"
            ])

        # Huberman Lab specific patterns
        elif 'huberman' in podcast_lower:
            urls.extend([
                f"https://hubermanlab.com/{episode_title.lower().replace(' ', '-')}/",
                f"https://hubermanlab.com/episode-{episode_title}/"
            ])

        # Jordan Peterson specific patterns
        elif 'jordan peterson' in podcast_lower:
            guest_name = episode_title.split(':')[0].strip() if ':' in episode_title else episode_title
            guest_slug = guest_name.lower().replace(' ', '-').replace(',', '').replace('.', '')
            urls.extend([
                f"https://jordanpeterson.com/podcast/{guest_slug}/",
                f"https://jordanpeterson.com/{guest_slug}-transcript/"
            ])

        # Joe Rogan specific patterns
        elif 'joe rogan' in podcast_lower:
            guest_name = episode_title.split(':')[0].strip() if ':' in episode_title else episode_title.split('#')[0].strip()
            guest_slug = guest_name.lower().replace(' ', '-').replace(',', '').replace('.', '')
            urls.extend([
                f"https://www.joeroganexp.com/podcast/{guest_slug}",
                f"https://open.spotify.com/episode/{guest_slug}"
            ])

        # Generic patterns for other podcasts
        clean_title = re.sub(r'[^\w\s]', '', episode_title).strip()
        clean_podcast = re.sub(r'[^\w\s]', '', podcast_name).strip()

        # Podscripts patterns
        base_title = clean_title.replace(' ', '-').lower()[:50]
        urls.extend([
            f"https://podscripts.co/podcasts/{clean_podcast.lower().replace(' ', '-')}/{base_title}",
            f"https://podscripts.co/search?q={episode_title}",
        ])

        # Generic patterns
        encoded_title = requests.utils.quote(episode_title)
        urls.extend([
            f"https://www.google.com/search?q={encoded_title}+transcript",
            f"https://duckduckgo.com/?q={encoded_title}+transcript",
        ])

        # Direct site searches
        for site in self.transcript_sites:
            urls.append(f"https://www.google.com/search?q=site:{site}+{encoded_title}")

        return urls[:20]  # Limit to 20 URLs

    def try_rss_extraction(self, rss_feed_url):
        """Extract transcripts from RSS feeds"""
        try:
            response = self.session.get(rss_feed_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')[:20]  # Recent 20 episodes

            transcripts_found = []

            for item in items:
                title = item.find('title')
                description = item.find('description')
                link = item.find('link')

                if title and description:
                    desc_text = description.get_text()

                    # Check if description contains substantial content
                    if len(desc_text) > 5000 and 'transcript' in desc_text.lower():
                        transcripts_found.append({
                            'title': title.get_text(),
                            'content': desc_text,
                            'source': 'rss_extraction',
                            'url': link.get_text() if link else ''
                        })

            return transcripts_found

        except Exception as e:
            print(f"   🚫 RSS extraction failed: {e}")
            return []

    def extract_from_page(self, url):
        """Extract content from a specific URL with better selectors"""
        try:
            print(f"   🕷️ Crawling: {url[:60]}...")

            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try specific content selectors in order
            content_selectors = [
                'div.post-content',
                'article',
                'main',
                'div.content',
                'div.entry-content',
                'div.single-content',
                'section.content',
                '.transcript-content',
                'div[class*="content"]',
                'div[id*="content"]'
            ]

            content = None
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    print(f"   🎯 Found content with: {selector}")
                    break

            # Fallback: use body but remove obvious non-content
            if not content:
                content = soup.find('body')
                if content:
                    # Remove common non-content elements
                    for element in content(['nav', 'header', 'footer', 'aside', 'script', 'style', 'iframe', 'form']):
                        element.decompose()

            if not content:
                print("   🚫 No content found")
                return None

            text = content.get_text()

            # Clean up text
            lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
            clean_text = '\n'.join(lines)

            if len(clean_text) > 2000:
                print(f"   ✅ Extracted: {len(clean_text):,} characters ({len(clean_text.split()):,} words)")
                return clean_text
            else:
                print(f"   ❌ Too short: {len(clean_text)} characters")

        except Exception as e:
            print(f"   🚫 Extraction failed: {e}")

        return None

    def try_wayback_extraction(self, url):
        """Try Wayback Machine for archived content"""
        try:
            wayback_url = f"http://web.archive.org/web/20240101000000/{url}"
            print(f"   🕰️ Trying Wayback: {wayback_url[:60]}...")

            response = self.session.get(wayback_url, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    element.decompose()

                text = soup.get_text()
                lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
                clean_text = '\n'.join(lines)

                if len(clean_text) > 2000:
                    print(f"   ✅ Wayback success: {len(clean_text)} characters")
                    return clean_text

        except Exception as e:
            print(f"   🚫 Wayback failed: {e}")

        return None

    def basic_quality_check(self, text):
        """Basic quality check without strict validation"""
        if len(text) < 2000:  # Lower threshold for no-API processing
            return False

        word_count = len(text.split())
        if word_count < 500:  # Lower word count threshold
            return False

        # Basic transcript indicators
        indicators = ['transcript', 'speaker', 'host', 'guest', 'interview', ':', '"']
        indicator_count = sum(1 for indicator in indicators if indicator in text.lower())

        return indicator_count >= 3

    def process_episode_without_api(self, episode):
        """Process episode using direct crawling only"""
        episode_id, title, link, podcast_id, podcast_name, rss_feed = episode

        print(f"\n🎙️  {podcast_name}")
        print(f"📄 {title[:60]}...")

        # Strategy 1: Try RSS feed extraction
        if rss_feed:
            print("   📡 Strategy 1: RSS extraction...")
            rss_transcripts = self.try_rss_extraction(rss_feed)

            for rss_transcript in rss_transcripts:
                if self.basic_quality_check(rss_transcript['content']):
                    print(f"   ✅ RSS SUCCESS: {len(rss_transcript['content'])} chars")
                    self.save_transcript(episode_id, {
                        'content': rss_transcript['content'],
                        'source': f"no_api_rss_{rss_transcript['source']}"
                    })
                    return True

        # Strategy 2: Construct likely URLs
        print("   🔧 Strategy 2: Direct URL construction...")
        constructed_urls = self.construct_transcript_urls(podcast_name, title)

        for url in constructed_urls[:8]:  # Try first 8 URLs
            content = self.extract_from_page(url)
            if content and self.basic_quality_check(content):
                print(f"   ✅ DIRECT SUCCESS: {len(content)} chars")
                self.save_transcript(episode_id, {
                    'content': content,
                    'source': f"no_api_direct_{urlparse(url).netloc}"
                })
                return True

            # Try Wayback for this URL
            archived_content = self.try_wayback_extraction(url)
            if archived_content and self.basic_quality_check(archived_content):
                print(f"   ✅ WAYBACK SUCCESS: {len(archived_content)} chars")
                self.save_transcript(episode_id, {
                    'content': archived_content,
                    'source': f"no_api_wayback_{urlparse(url).netloc}"
                })
                return True

            time.sleep(2)  # Rate limiting

        print("   ❌ No success with any strategy")
        return False

    def save_transcript(self, episode_id, transcript_info):
        """Save transcript to database"""
        conn = sqlite3.connect("podcast_processing.db")
        conn.execute("""
            UPDATE episodes
            SET processing_status = 'completed',
                transcript_found = 1,
                transcript_text = ?,
                transcript_source = ?,
                quality_score = 6
            WHERE id = ?
        """, (transcript_info['content'], transcript_info['source'], episode_id))
        conn.commit()
        conn.close()

    def run_no_api_processing(self, batch_size=50):
        """Run processing without any API dependencies"""
        print(f"\n🚀 Starting No-API Processing")
        print(f"📦 Batch size: {batch_size}")
        print(f"🔧 Methods: Direct crawling + RSS + Archives")
        print()

        episodes = self.get_episodes_to_process(batch_size)

        if not episodes:
            print("✅ No episodes need processing!")
            return

        print(f"📋 Processing {len(episodes)} episodes without APIs...")

        successful = 0
        failed = 0

        for episode in episodes:
            try:
                if self.process_episode_without_api(episode):
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"🚫 ERROR: {e}")
                failed += 1

            print("-" * 50)
            time.sleep(3)  # Respectful crawling

        print(f"\n🏁 No-API Batch Complete!")
        print(f"📊 Results: {successful} successful, {failed} failed")
        print(f"📈 Success rate: {(successful/(successful+failed))*100:.1f}%" if (successful+failed) > 0 else "No episodes processed")

if __name__ == "__main__":
    processor = NoAPIProcessor()
    processor.run_no_api_processing(50)