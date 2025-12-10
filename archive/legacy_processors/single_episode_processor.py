#!/usr/bin/env python3
"""
Process a single episode for the Atlas Manager
Enhanced with multi-source transcript discovery
"""

import sys
import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/home/ubuntu/dev/atlas/.env')

sys.path.append('/home/ubuntu/dev/atlas')
from free_transcript_finder import FreeTranscriptFinder
from helpers.universal_transcript_discoverer import UniversalTranscriptDiscoverer
from youtube_caption_scraper import YouTubeCaptionScraper
from archive_org_scraper import ArchiveOrgScraper
from community_scraper import CommunityScraper
from transcript_judge import TranscriptJudge

def _verify_transcript_accuracy(content: str, podcast_name: str, episode_title: str) -> bool:
    """Verify that the transcript is actually for our specific episode"""
    import re
    content_lower = content.lower()
    podcast_lower = podcast_name.lower()
    episode_lower = episode_title.lower()

    # Check for podcast name presence
    podcast_found = False
    # Try different variations of the podcast name
    podcast_variations = [
        podcast_lower,
        podcast_lower.replace(' podcast', ''),
        podcast_lower.replace(' the ', ' '),
        podcast_lower.replace(' with ', ' '),
    ]

    for variation in podcast_variations:
        if variation in content_lower:
            podcast_found = True
            break

    if not podcast_found:
        return False

    # Check for episode-specific content
    # Extract key terms from episode title
    episode_terms = re.findall(r'\b\w{4,}\b', episode_lower)
    if not episode_terms:  # If no meaningful terms, just check length
        return len(content) > 10000

    # Count how many episode terms appear in the transcript
    terms_found = sum(1 for term in episode_terms if term in content_lower)
    term_coverage = terms_found / len(episode_terms) if episode_terms else 0

    # Require at least 30% coverage of episode terms OR very long content
    return term_coverage >= 0.3 or len(content) > 25000

def _get_source_tier(source: str) -> int:
    """Get hierarchy tier for sources - lower tier = higher quality"""
    # Tier 1: Professional transcript services (immediate stop)
    tier_1 = ['fireflies.ai', 'otter.ai', 'rev.com', 'sonix.ai', 'trint.com']
    # Tier 2: Community platforms with good transcripts
    tier_2 = ['github.com', 'medium.com', 'substack.com', 'notion.so']
    # Tier 3: Other sources
    tier_3 = ['archive.org', 'youtube.com', 'reddit.com']

    if source in tier_1:
        return 1
    elif source in tier_2:
        return 2
    elif source in tier_3:
        return 3
    else:
        return 4

def process_episode(episode_id, episode_url, podcast_name):
    """Process a single episode with enhanced multi-source transcript discovery"""
    try:
        # Connect to database
        conn = sqlite3.connect('data/atlas.db')
        cursor = conn.cursor()

        # Load sources cache
        sources_cache = {}
        try:
            with open('config/podcast_sources_cache.json', 'r') as f:
                sources_cache = json.load(f)
        except:
            pass

        # Setup session and judge
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Initialize transcript judge
        judge = TranscriptJudge()

        print(f"🔍 Processing {podcast_name} - Episode {episode_id}")
        print(f"📍 URL: {episode_url}")

        transcript = None
        transcript_source = None
        best_evaluation = None

        # STRATEGY 1: Direct scraping with cached patterns
        print("📋 Strategy 1: Direct scraping...")
        response = session.get(episode_url, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try cached patterns first
            for podcast_key, podcast_data in sources_cache.items():
                if podcast_name.lower() in podcast_key.lower():
                    network_config = podcast_data.get('config', {})
                    if 'selectors' in network_config:
                        for selector in network_config['selectors']:
                            element = soup.select_one(selector)
                            if element:
                                text = element.get_text(separator=' ', strip=True)
                                min_length = network_config.get('min_length', 1000)
                                if len(text) > min_length:
                                    transcript = text
                                    transcript_source = "cached_pattern"
                                    break
                    if transcript:
                        break

            # Enhanced generic selectors if no cached patterns found
            if not transcript:
                transcript_selectors = ['.transcript', '#transcript', '.episode-transcript', '[class*="transcript"]']
                for selector in transcript_selectors:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(separator=' ', strip=True)
                        if len(text) > 1000:
                            transcript = text
                            transcript_source = "direct_scraping"
                            break

        # STRATEGY 2: Free search alternatives (was: expensive Google-powered search)
        if not transcript:
            print("🔍 Strategy 2: Free search alternatives...")
            try:
                free_finder = FreeTranscriptFinder()
                # Try to get episode title from URL or use generic
                episode_title = f"Episode {episode_id}"
                search_results = free_finder.exhaustive_search(podcast_name, max_results=10)
                if search_results and len(search_results) > 0:
                    # Sort by source tier and quality
                    sorted_results = sorted(search_results, key=lambda x: (
                        _get_source_tier(x.get('site', 'unknown')),
                        x.get('content_length', 0)
                    ))

                    for result in sorted_results[:5]:  # Only try top 5 results
                        source = result.get('site', 'unknown')
                        length = result.get('content_length', 0)
                        tier = _get_source_tier(source)

                        print(f"🎯 Trying {source} (Tier {tier}, {length} chars)...")

                        try:
                            transcript_response = session.get(result['url'], timeout=15)
                            if transcript_response.status_code == 200:
                                transcript_soup = BeautifulSoup(transcript_response.content, 'html.parser')
                                content = transcript_soup.get_text(separator=' ', strip=True)

                                # Use comprehensive transcript judge evaluation
                                episode_title = f"Episode {episode_id}"
                                evaluation = judge.evaluate_transcript(content, podcast_name, episode_title)

                                if evaluation['is_valid_transcript']:
                                    print(f"✅ Valid transcript from {source} (Tier {tier}) - Quality: {evaluation['quality_score']:.1%}")

                                    # Update best transcript if this is better
                                    if best_evaluation is None or evaluation['quality_score'] > best_evaluation['quality_score']:
                                        transcript = content
                                        transcript_source = f"free_search:{source}"
                                        best_evaluation = evaluation

                                    # STOP SEARCHING if we found a high-quality Tier 1 source
                                    if tier == 1 and evaluation['quality_score'] >= 0.8:
                                        print(f"🏆 STOPPING: Found high-quality Tier 1 transcript from {source}")
                                        break
                                else:
                                    print(f"❌ Transcript from {source} failed quality check: {evaluation['assessment']}")
                            else:
                                print(f"⚠️  Failed to fetch {source} (HTTP {transcript_response.status_code})")
                        except Exception as e:
                            print(f"⚠️  Failed to process {source}: {e}")
                            continue

                        # Stop after finding any valid transcript or 3 tries
                        if transcript or len([r for r in sorted_results[:5] if sorted_results.index(r) <= sorted_results.index(result)]) >= 3:
                            break
            except Exception as e:
                print(f"⚠️  Free search failed: {e}")

        # STRATEGY 3: YouTube caption search
        if not transcript:
            print("🎥 Strategy 3: YouTube caption search...")
            try:
                youtube_scraper = YouTubeCaptionScraper()
                # Extract episode title from URL or use generic title
                episode_title = f"Episode {episode_id}"
                youtube_result = youtube_scraper.find_episode_transcript(podcast_name, episode_title, episode_url)
                if youtube_result:
                    transcript = youtube_result['transcript']
                    transcript_source = f"youtube_captions:{youtube_result['channel']}"
                    print(f"✅ Found transcript via YouTube captions from {youtube_result['channel']}")
            except Exception as e:
                print(f"⚠️  YouTube search failed: {e}")

        # STRATEGY 4: Archive.org search
        if not transcript:
            print("📚 Strategy 4: Archive.org search...")
            try:
                archive_scraper = ArchiveOrgScraper()
                archive_result = archive_scraper.find_transcript(podcast_name, episode_title, episode_url)
                if archive_result:
                    transcript = archive_result['transcript']
                    transcript_source = f"archive_org:{archive_result['source']}"
                    print(f"✅ Found transcript via Archive.org")
            except Exception as e:
                print(f"⚠️  Archive.org search failed: {e}")

        # STRATEGY 5: Community sources search
        if not transcript:
            print("👥 Strategy 5: Community sources search...")
            try:
                community_scraper = CommunityScraper()
                community_result = community_scraper.find_community_transcript(podcast_name, episode_title)
                if community_result:
                    transcript = community_result['transcript']
                    transcript_source = f"community:{community_result['source']}"
                    print(f"✅ Found transcript via community sources")
            except Exception as e:
                print(f"⚠️  Community search failed: {e}")

        # STRATEGY 6: Universal transcript discovery
        if not transcript:
            print("🌐 Strategy 6: Universal discovery...")
            try:
                universal_discoverer = UniversalTranscriptDiscoverer(Path('/home/ubuntu/dev/atlas'))
                # Create a mock podcast dict for the discoverer
                podcast_dict = {
                    'name': podcast_name,
                    'rss_url': episode_url,  # Use episode URL as fallback
                    'website': episode_url
                }
                discovery_results = universal_discoverer.discover_podcast_transcripts(podcast_dict)
                if discovery_results and 'transcripts' in discovery_results:
                    for transcript_info in discovery_results['transcripts'][:2]:  # Try top 2 results
                        source_url = transcript_info.get('url')
                        if source_url:
                            try:
                                transcript_response = session.get(source_url, timeout=10)
                                if transcript_response.status_code == 200:
                                    transcript_soup = BeautifulSoup(transcript_response.content, 'html.parser')
                                    content = transcript_soup.get_text(separator=' ', strip=True)
                                    if len(content) > 1000:
                                        transcript = content
                                        transcript_source = "universal_discovery"
                                        print(f"✅ Found transcript via universal discovery")
                                        break
                            except Exception as e:
                                print(f"⚠️  Failed to fetch universal result: {e}")
                                continue
            except Exception as e:
                print(f"⚠️  Universal discovery failed: {e}")

        # STRATEGY 7: Fallback to content extraction
        if not transcript and response.status_code == 200:
            print("📝 Strategy 7: Content fallback...")
            content_selectors = ['.entry-content', '.post-content', '.article-content', '.content', 'article', '.episode-content', '.show-notes']
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 2000:
                        paragraphs = text.split('\n')
                        if len(paragraphs) > 5 or any(word in text.lower() for word in ['episode', 'podcast', 'transcript', 'show', 'interview']):
                            transcript = text
                            transcript_source = "content_fallback"
                            break

            # Final fallback: largest text block
            if not transcript:
                text_blocks = []
                for elem in soup.find_all(['div', 'section', 'article']):
                    text = elem.get_text(separator=' ', strip=True)
                    if len(text) > 3000:
                        text_blocks.append((len(text), text))

                if text_blocks:
                    text_blocks.sort(reverse=True)
                    transcript = text_blocks[0][1]
                    transcript_source = "largest_block"

        if transcript and best_evaluation:
            # Store transcript with comprehensive quality metadata
            metadata = json.dumps({
                "episode_id": episode_id,
                "podcast_name": podcast_name,
                "transcript_source": transcript_source,
                "episode_url": episode_url,
                "quality_score": best_evaluation['quality_score'],
                "confidence": best_evaluation['confidence'],
                "assessment": best_evaluation['assessment'],
                "component_scores": best_evaluation['scores'],
                "analysis": best_evaluation['analysis']
            })

            cursor.execute("""
                INSERT INTO content (title, url, content, content_type, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"[{podcast_name}] Episode {episode_id}",
                episode_url,
                transcript,
                'podcast_transcript',
                metadata,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()

            # Display quality report
            print(f"✅ TRANSCRIPT FOUND AND STORED")
            print(f"   📊 Quality Score: {best_evaluation['quality_score']:.1%}")
            print(f"   🎯 Confidence: {best_evaluation['confidence']}")
            print(f"   📝 Assessment: {best_evaluation['assessment']}")
            print(f"   🔍 Source: {transcript_source}")
            print(f"   📏 Length: {len(transcript):,} characters")
            return True
        else:
            print("❌ No valid transcript found after all strategies")
            return False

    except Exception as e:
        print(f"Error processing episode: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 single_episode_processor.py <episode_id> <episode_url> <podcast_name>")
        sys.exit(1)

    episode_id = sys.argv[1]
    episode_url = sys.argv[2]
    podcast_name = sys.argv[3]

    process_episode(episode_id, episode_url, podcast_name)