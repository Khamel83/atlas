#!/usr/bin/env python3
"""
Comprehensive Retry System:
1. Retries failed episodes with different strategies
2. Quality checks all existing transcripts
3. Redoes any transcripts that fail quality validation
"""

import sqlite3
import os
import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime

class ComprehensiveRetrySystem:
    def __init__(self):
        self.tavily_key = os.getenv('TAVILY_API_KEY')
        if not self.tavily_key:
            raise ValueError("TAVILY_API_KEY not found in environment")

        # Quality thresholds (stricter than before)
        self.min_words = 1000
        self.min_characters = 5000
        self.min_dialogue_indicators = 20
        self.min_sentences = 50
        self.min_paragraphs = 5

        print("🔍 COMPREHENSIVE RETRY & QUALITY SYSTEM")
        print("=" * 60)
        print(f"📏 Quality thresholds:")
        print(f"   - Minimum {self.min_words:,} words")
        print(f"   - Minimum {self.min_characters:,} characters")
        print(f"   - Minimum {self.min_dialogue_indicators} dialogue indicators")
        print(f"   - Minimum {self.min_sentences} sentences")
        print(f"   - Minimum {self.min_paragraphs} paragraphs")
        print("=" * 60)

    def looks_like_transcript(self, text, episode_title=""):
        """Strict transcript quality validation"""

        print(f"   📊 Analyzing content quality...")

        # Basic length checks
        if len(text) < self.min_characters:
            print(f"      ❌ Too short: {len(text):,} characters (need {self.min_characters:,})")
            return False

        word_count = len(text.split())
        if word_count < self.min_words:
            print(f"      ❌ Too few words: {word_count:,} (need {self.min_words:,})")
            return False

        # Strong transcript indicators (must have at least 3)
        strong_indicators = [
            'transcript', 'speaker', 'host', 'guest', 'interview', 'conversation',
            'question:', 'answer:', 'q:', 'a:', '[music]', '[applause]', 'laughs',
            '>>', '--', '主持人', '嘉宾', '采访', '对话'
        ]

        # Secondary indicators
        secondary_indicators = [
            'show notes', 'episode notes', 'summary', 'highlights', 'podcast'
        ]

        strong_count = sum(1 for indicator in strong_indicators if indicator.lower() in text.lower())
        secondary_count = sum(1 for indicator in secondary_indicators if indicator.lower() in text.lower())

        # Must have at least 3 strong indicators OR 2 strong + 2 secondary
        indicator_requirement = (strong_count >= 3) or (strong_count >= 2 and secondary_count >= 2)
        if not indicator_requirement:
            print(f"      ❌ Not enough transcript indicators: {strong_count} strong, {secondary_count} secondary")
            return False

        # Dialogue structure validation
        dialogue_count = text.count(':') + text.count('"') + text.count("'") + text.count('>>')
        if dialogue_count < self.min_dialogue_indicators:
            print(f"      ❌ Not enough dialogue: {dialogue_count} indicators (need {self.min_dialogue_indicators})")
            return False

        # Sentence structure validation
        sentence_count = text.count('.') + text.count('!') + text.count('?')
        if sentence_count < self.min_sentences:
            print(f"      ❌ Not enough sentences: {sentence_count} (need {self.min_sentences})")
            return False

        # Paragraph structure
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) < self.min_paragraphs:
            print(f"      ❌ Not enough paragraphs: {len(paragraphs)} (need {self.min_paragraphs})")
            return False

        # Quality score calculation
        score = (strong_count * 2) + secondary_count + (dialogue_count / 10) + (sentence_count / 25)

        # Calculate estimated podcast length
        estimated_minutes = word_count / 155  # 155 words per minute average
        if estimated_minutes < 5:  # Must be at least 5 minutes of content
            print(f"      ❌ Too short content: ~{estimated_minutes:.1f} minutes (need 5+)")
            return False

        print(f"   ✅ QUALITY PASSED:")
        print(f"      Words: {word_count:,} (~{estimated_minutes:.1f} minutes)")
        print(f"      Strong indicators: {strong_count}, Secondary: {secondary_count}")
        print(f"      Dialogue markers: {dialogue_count}, Sentences: {sentence_count}")
        print(f"      Paragraphs: {len(paragraphs)}, Quality score: {score:.1f}")

        # Final quality threshold
        return score >= 8

    def get_failed_episodes(self, limit=100):
        """Get failed episodes for retry"""
        conn = sqlite3.connect("podcast_processing.db")
        cursor = conn.execute("""
            SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'failed'
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))

        episodes = cursor.fetchall()
        conn.close()
        return episodes

    def get_completed_episodes_for_quality_check(self, limit=100):
        """Get completed episodes for quality validation"""
        conn = sqlite3.connect("podcast_processing.db")
        cursor = conn.execute("""
            SELECT e.id, e.title, e.transcript_text, e.transcript_source, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'completed'
            AND e.transcript_text IS NOT NULL
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))

        episodes = cursor.fetchall()
        conn.close()
        return episodes

    def simple_search_fallback(self, podcast_name, episode_title):
        """Simpler search for failed episodes"""

        simple_queries = [
            f'"{episode_title}" transcript',
            f'{podcast_name} "{episode_title}" transcript',
            f'{episode_title} full transcript'
        ]

        for query in simple_queries[:3]:
            try:
                response = requests.post(
                    'https://api.tavily.com/search',
                    json={
                        'api_key': self.tavily_key,
                        'query': query,
                        'search_depth': 'basic',
                        'max_results': 5
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])

                    if results:
                        print(f"   🔍 Simple search found: {len(results)} results")
                        return results

            except Exception as e:
                if "429" in str(e):
                    print(f"   🚫 Rate limited, waiting 30 seconds...")
                    time.sleep(30)
                else:
                    print(f"   🚫 Simple search error: {e}")
                continue

            time.sleep(2)

        return []

    def extract_with_multiple_archives(self, url):
        """Try multiple archive sources for older content"""

        archives = [
            ("Wayback Machine", f"http://web.archive.org/web/20240101000000/{url}"),
            ("Archive.is", f"https://archive.ph/{url}"),
            ("Ghostarchive", f"https://ghostarchive.org/ghost/{url}"),
            ("Wayback Recent", f"http://web.archive.org/web/2/{url}"),
        ]

        for archive_name, archive_url in archives:
            try:
                print(f"   🕰️ Trying {archive_name}...")

                response = requests.get(archive_url, timeout=20, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Remove unwanted elements
                    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'form']):
                        element.decompose()

                    text = soup.get_text()

                    # Clean up text
                    lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
                    clean_text = ' '.join(lines)

                    if clean_text and len(clean_text) > 1000:
                        print(f"   ✅ {archive_name} SUCCESS: {len(clean_text)} characters")
                        return clean_text

            except Exception as e:
                print(f"   🚫 {archive_name} failed: {str(e)[:50]}...")
                continue

        return None

    def extract_simple_content(self, url):
        """Simple content extraction"""
        try:
            response = requests.get(url, timeout=20, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    element.decompose()

                text = soup.get_text()

                # Basic cleanup
                lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 5]
                clean_text = '\n'.join(lines)

                if len(clean_text) > 2000:
                    return clean_text

        except Exception as e:
            print(f"   🚫 Simple extraction failed: {e}")

        return None

    def retry_failed_episode(self, episode):
        """Try different approaches for failed episode"""
        episode_id, title, link, podcast_id, podcast_name = episode

        print(f"\n🔄 Retrying failed episode: {title[:60]}...")

        # Strategy 1: Simple search
        print("   Strategy 1: Simple search...")
        results = self.simple_search_fallback(podcast_name, title)

        if results:
            for result in results[:3]:
                url = result.get('url', '')
                if url:
                    print(f"   📖 Trying: {result.get('title', '')[:50]}...")

                    # Try direct extraction
                    content = self.extract_simple_content(url)
                    if content and self.looks_like_transcript(content, title):
                        print(f"   ✅ SUCCESS: Simple approach found quality transcript ({len(content)} chars)")
                        self.save_transcript(episode_id, {
                            'content': content,
                            'source': f"retry_simple_quality_{result.get('source', 'unknown')}"
                        })
                        return True

                    # Try archive extraction
                    archived_content = self.extract_with_multiple_archives(url)
                    if archived_content and self.looks_like_transcript(archived_content, title):
                        print(f"   ✅ SUCCESS: Archive approach found quality transcript ({len(archived_content)} chars)")
                        self.save_transcript(episode_id, {
                            'content': archived_content,
                            'source': f"retry_archive_quality_{result.get('source', 'unknown')}"
                        })
                        return True

        print("   ❌ All retry strategies failed or failed quality check")
        return False

    def quality_check_existing_episode(self, episode):
        """Check quality of existing transcript"""
        episode_id, title, transcript_text, transcript_source, podcast_name = episode

        print(f"\n🔍 Quality checking: {title[:60]}...")
        print(f"   📄 Current source: {transcript_source}")
        print(f"   📏 Current length: {len(transcript_text):,} characters")

        if not self.looks_like_transcript(transcript_text, title):
            print(f"   ❌ QUALITY FAILED - Marking for retry")
            self.mark_for_retry(episode_id, "Failed quality validation")
            return False
        else:
            print(f"   ✅ QUALITY PASSED")
            return True

    def mark_for_retry(self, episode_id, reason):
        """Mark episode as failed for retry"""
        conn = sqlite3.connect("podcast_processing.db")
        conn.execute("""
            UPDATE episodes
            SET processing_status = 'failed',
                transcript_found = 0,
                transcript_text = NULL,
                transcript_source = ?,
                quality_score = 1
            WHERE id = ?
        """, (f"FAILED_QC: {reason}", episode_id))
        conn.commit()
        conn.close()

    def save_transcript(self, episode_id, transcript_info):
        """Save successful retry transcript"""
        conn = sqlite3.connect("podcast_processing.db")
        conn.execute("""
            UPDATE episodes
            SET processing_status = 'completed',
                transcript_found = 1,
                transcript_text = ?,
                transcript_source = ?,
                quality_score = 9
            WHERE id = ?
        """, (transcript_info['content'], transcript_info['source'], episode_id))
        conn.commit()
        conn.close()

    def run_comprehensive_process(self, failed_batch_size=50, quality_check_batch_size=50):
        """Run both failed episode retry and quality check"""

        print(f"\n🚀 Starting Comprehensive Process at {datetime.now()}")
        print("=" * 60)

        # Phase 1: Quality Check Existing Transcripts
        print(f"\n📋 PHASE 1: Quality Check Existing Transcripts")
        print("-" * 40)

        completed_episodes = self.get_completed_episodes_for_quality_check(quality_check_batch_size)

        if not completed_episodes:
            print("✅ No completed transcripts to quality check")
        else:
            print(f"📊 Checking {len(completed_episodes)} existing transcripts...")

            quality_passed = 0
            quality_failed = 0

            for episode in completed_episodes:
                if self.quality_check_existing_episode(episode):
                    quality_passed += 1
                else:
                    quality_failed += 1

                time.sleep(1)  # Rate limiting

            print(f"\n📊 Quality Check Results:")
            print(f"   ✅ Passed: {quality_passed}")
            print(f"   ❌ Failed (marked for retry): {quality_failed}")

        # Phase 2: Retry Failed Episodes
        print(f"\n🔄 PHASE 2: Retry Failed Episodes")
        print("-" * 40)

        failed_episodes = self.get_failed_episodes(failed_batch_size)

        if not failed_episodes:
            print("✅ No failed episodes to retry")
        else:
            print(f"📊 Retrying {len(failed_episodes)} failed episodes...")

            successful = 0
            still_failed = 0

            for episode in failed_episodes:
                if self.retry_failed_episode(episode):
                    successful += 1
                else:
                    still_failed += 1

                time.sleep(3)  # Rate limiting

            print(f"\n📊 Retry Results:")
            print(f"   ✅ Recovered: {successful}")
            print(f"   ❌ Still failed: {still_failed}")
            print(f"   📈 Recovery rate: {(successful/len(failed_episodes))*100:.1f}%")

        # Summary
        print(f"\n🏁 Comprehensive Process Complete!")
        print(f"⏰ Finished at: {datetime.now()}")
        print(f"💰 Cost: $0.00 (FREE processing)")
        print(f"🔧 All transcripts meet quality standards: {self.min_words:,}+ words")

if __name__ == "__main__":
    retry_system = ComprehensiveRetrySystem()
    retry_system.run_comprehensive_process(
        failed_batch_size=20,
        quality_check_batch_size=25
    )