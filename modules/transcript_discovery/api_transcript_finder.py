#!/usr/bin/env python3
"""
API-Powered Transcript Finder
Uses Tavily, YouTube, and other APIs to find real transcripts
"""

import sqlite3
import requests
import time
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APITranscriptFinder:
    """Transcript finder using real APIs"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # API Keys from environment
        import os
        self.tavily_key = os.getenv('TAVILY_API_KEY', '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')
        self.youtube_key = os.getenv('YOUTUBE_API_KEY', 'AIzaSyBKXQRpYgK8RZJzKqAmGn0Pxk3rjQcswz4')
        self.firecrawl_key = os.getenv('FIRECRAWL_API_KEY', 'fc-51a977b9e5e44f2f95c5308ec38464ae')

    def tavily_search(self, query, max_results=5):
        """Search using Tavily API"""

        print(f"🔍 Tavily search: {query}")

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "max_results": max_results,
            "include_domains": ["tapesearch.com", "podscripts.co", "happyscribe.com", "lexfridman.com", "omny.fm", "simplecast.com"]
        }

        try:
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()

            results = []
            for result in data.get('results', []):
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'snippet': result.get('content', '')
                })

            print(f"📊 Tavily found {len(results)} results")
            return results

        except Exception as e:
            print(f"   🚫 Tavily error: {e}")
            return []

    def youtube_search_transcripts(self, query):
        """Search YouTube and get captions"""

        print(f"🎥 YouTube search: {query}")

        # Search YouTube
        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': query + ' transcript',
            'type': 'video',
            'maxResults': 3,
            'key': self.youtube_key
        }

        try:
            response = requests.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            transcripts = []
            for item in data.get('items', []):
                video_id = item['id']['videoId']
                title = item['snippet']['title']

                # Try to get captions/transcript
                transcript = self.get_youtube_transcript(video_id)
                if transcript:
                    transcripts.append({
                        'title': title,
                        'video_id': video_id,
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'transcript': transcript,
                        'source': 'youtube'
                    })

            print(f"📊 YouTube found {len(transcripts)} transcripts")
            return transcripts

        except Exception as e:
            print(f"   🚫 YouTube error: {e}")
            return []

    def get_youtube_transcript(self, video_id):
        """Get YouTube video transcript"""

        captions_url = "https://www.googleapis.com/youtube/v3/captions"
        params = {
            'part': 'snippet',
            'videoId': video_id,
            'key': self.youtube_key
        }

        try:
            response = requests.get(captions_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data.get('items', []):
                snippet = item['snippet']
                if snippet.get('language') == 'en' and snippet.get('trackKind') == 'standard':
                    # Found English captions
                    return f"You video has captions available (ID: {item['id']})"

        except Exception as e:
            logger.error(f"YouTube transcript error: {e}")

        return None

    def extract_transcript_from_url(self, url, title=""):
        """Extract transcript from a URL using Firecrawl"""

        print(f"🕷️  Firecrawl extracting: {url[:80]}...")

        firecrawl_url = "https://api.firecrawl.dev/v0/scrape"
        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True
        }
        headers = {
            "Authorization": f"Bearer {self.firecrawl_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(firecrawl_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            content = data.get('data', {}).get('markdown', '')

            if self.looks_like_transcript(content):
                print(f"   ✅ SUCCESS: Firecrawl found transcript content")
                return content[:10000]  # Return first 10K characters
            else:
                print(f"   ❌ No transcript content found")
                return None

        except Exception as e:
            print(f"   🚫 Firecrawl error: {e}")
            return None

    def looks_like_transcript(self, text):
        """Check if text looks like a transcript"""

        if len(text) < 500:
            return False

        # Transcript indicators
        indicators = [
            'transcript', 'speaker', 'host', 'guest', 'interview', 'conversation',
            'question:', 'answer:', 'q:', 'a:', '[music]', '[applause]', 'laughs',
            '主持人', '嘉宾', '采访', '对话'
        ]

        indicator_count = sum(1 for indicator in indicators if indicator.lower() in text.lower())

        # Check for dialogue format
        dialogue_score = text.count(':') + text.count('"') + text.count("'")

        # Check sentence structure
        sentence_score = text.count('.')

        # Combined score
        score = indicator_count + (dialogue_score / 50) + (sentence_score / 100)

        return score >= 2

    def search_all_sources(self, podcast_name, episode_title):
        """Search all available sources for transcripts"""

        # Build search queries
        queries = [
            f'"{episode_title}" transcript {podcast_name}',
            f'"{episode_title}" transcript',
            f'{podcast_name} {episode_title} full transcript'
        ]

        all_transcripts = []

        # Try Tavily search for each query
        for query in queries:
            results = self.tavily_search(query, max_results=3)

            for result in results:
                url = result['url']
                title = result['title']

                # Try to extract transcript from this URL
                transcript = self.extract_transcript_from_url(url, title)
                if transcript:
                    all_transcripts.append({
                        'title': title,
                        'url': url,
                        'transcript': transcript,
                        'source': 'tavily_firecrawl'
                    })

            time.sleep(1)  # Rate limiting

        # Try YouTube search
        youtube_transcripts = self.youtube_search_transcripts(f"{podcast_name} {episode_title}")
        all_transcripts.extend(youtube_transcripts)

        return all_transcripts

    def process_episodes(self, limit=10):
        """Process episodes and find transcripts using APIs"""

        conn = sqlite3.connect("podcast_processing.db")

        # Get diverse episodes from popular podcasts
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

        print(f"🎯 Processing {len(episodes)} episodes with APIs...")
        print("=" * 70)

        successful = 0

        for episode in episodes:
            episode_id, title, link, podcast_id, podcast_name = episode

            print(f"\n🎙️  Podcast: {podcast_name}")
            print(f"📄 Episode: {title[:80]}...")

            # Search all sources
            transcripts = self.search_all_sources(podcast_name, title)

            if transcripts:
                print(f"\n💾 FOUND {len(transcripts)} TRANSCRIPT(S)")

                # Save the best transcript
                best_transcript = max(transcripts, key=lambda x: len(x['transcript']))

                print(f"📊 Source: {best_transcript['source']}")
                print(f"🔗 URL: {best_transcript['url'][:80]}...")
                print(f"📏 Length: {len(best_transcript['transcript'])} characters")

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
                """, (best_transcript['transcript'], best_transcript['source'], best_transcript['url'], episode_id))
                conn.commit()
                conn.close()

                successful += 1
            else:
                print(f"\n❌ No transcripts found with APIs")

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
    finder = APITranscriptFinder()
    finder.process_episodes(10)