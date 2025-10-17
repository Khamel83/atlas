#!/usr/bin/env python3
"""
ATP Enhanced Transcript Generator

Combines scraped transcripts from catatp.fm with existing ATP metadata:
- Chapter marks from RSS feeds
- Show notes
- Links and sponsors
- Duration and timestamps

This creates comprehensive, searchable transcripts with all ATP's meticulous metadata.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

from helpers.atp_transcript_scraper import ATPTranscriptScraper

logger = logging.getLogger(__name__)

class ATPEnhancedTranscript:
    """Combine ATP transcripts with existing metadata"""

    def __init__(self, atlas_root: Path):
        self.atlas_root = atlas_root
        self.podcasts_dir = atlas_root / "output" / "podcasts"
        self.scraper = ATPTranscriptScraper()

    def load_episode_metadata(self, episode_id: str) -> Optional[Dict]:
        """Load existing ATP episode metadata"""
        metadata_file = self.podcasts_dir / f"{episode_id}_rss_entry.json"

        try:
            with open(metadata_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load metadata for {episode_id}: {e}")
            return None

    def extract_chapter_marks(self, metadata: Dict) -> List[Dict]:
        """Extract chapter marks from ATP metadata if available"""
        chapters = []

        # ATP often has chapter data in different formats
        raw_data = metadata.get("raw_data", {})

        # Look for chapter information in common places
        chapter_sources = [
            raw_data.get("chapters", []),
            raw_data.get("summary_detail", {}).get("chapters", []),
            raw_data.get("content", [])
        ]

        for source in chapter_sources:
            if isinstance(source, list):
                for item in source:
                    if isinstance(item, dict):
                        # Standard chapter format
                        if "title" in item:
                            chapters.append({
                                "title": item.get("title", ""),
                                "timestamp": item.get("start", item.get("time", "00:00:00")),
                                "url": item.get("url", "")
                            })

        # Parse from description if structured
        description = raw_data.get("summary", "")
        if description and not chapters:
            chapters = self._parse_chapters_from_description(description)

        return chapters

    def _parse_chapters_from_description(self, description: str) -> List[Dict]:
        """Parse chapter marks from episode description"""
        chapters = []

        # Common ATP chapter patterns
        patterns = [
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–]\s*([^\n\r]+)',  # 12:34 - Chapter title
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*([^\n\r]+)',        # 12:34 Chapter title
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description, re.MULTILINE)
            for timestamp, title in matches:
                chapters.append({
                    "title": title.strip(),
                    "timestamp": timestamp,
                    "url": ""
                })

            if matches:  # Stop after first successful pattern
                break

        return chapters

    def extract_sponsors_and_links(self, metadata: Dict) -> Dict:
        """Extract sponsor information and links"""
        raw_data = metadata.get("raw_data", {})

        # ATP is meticulous about sponsor info
        sponsors = []
        links = []

        description = raw_data.get("summary", "")

        # Look for sponsor sections
        sponsor_section = re.search(r'Sponsored by:?\s*(.+?)(?:\n\n|\n-|\nLinks)', description, re.IGNORECASE | re.DOTALL)
        if sponsor_section:
            sponsor_text = sponsor_section.group(1)

            # Extract individual sponsors
            sponsor_matches = re.findall(r'([^:\n]+):\s*([^\n]+)', sponsor_text)
            for name, description in sponsor_matches:
                sponsors.append({
                    "name": name.strip(),
                    "description": description.strip()
                })

        # Extract links section
        links_section = re.search(r'Links?:?\s*(.+?)(?:\n\n|\Z)', description, re.IGNORECASE | re.DOTALL)
        if links_section:
            links_text = links_section.group(1)

            # Extract URLs and titles
            link_matches = re.findall(r'([^\n]+?)(?:\s*-\s*|\s*:\s*)?(https?://[^\s\n]+)', links_text)
            for title, url in link_matches:
                links.append({
                    "title": title.strip() if title else url,
                    "url": url
                })

        return {
            "sponsors": sponsors,
            "links": links
        }

    def enhance_episode_transcript(self, episode_id: str, episode_num: int) -> Optional[str]:
        """Create enhanced transcript combining scraped content with metadata"""

        # Load existing metadata
        metadata = self.load_episode_metadata(episode_id)
        if not metadata:
            return None

        # Get scraped transcript (if available)
        transcript_data = None
        episodes = self.scraper.get_episode_list()

        for ep in episodes:
            if ep["number"] == episode_num:
                logger.info(f"Fetching transcript for Episode {episode_num}")
                transcript_data = self.scraper.scrape_episode_transcript(ep["url"])
                break

        if not transcript_data:
            logger.warning(f"No transcript found for Episode {episode_num}")
            return None

        # Extract enhanced metadata
        chapters = self.extract_chapter_marks(metadata)
        sponsors_links = self.extract_sponsors_and_links(metadata)

        # Build enhanced transcript
        raw_data = metadata.get("raw_data", {})

        enhanced_content = f"""---
title: "{transcript_data.get('title', f'ATP {episode_num}')}"
type: enhanced_podcast_transcript
podcast: "Accidental Tech Podcast"
episode_number: {episode_num}
published: "{raw_data.get('published', 'Unknown')}"
duration: "{raw_data.get('itunes_duration', 'Unknown')}"
word_count: {transcript_data.get('word_count', 0)}
chapter_count: {len(chapters)}
sponsor_count: {len(sponsors_links.get('sponsors', []))}
link_count: {len(sponsors_links.get('links', []))}
scraped_from: catatp.fm
original_source: atp.fm
enhanced_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---

# {transcript_data.get('title', f'ATP Episode {episode_num}')}

**Published:** {raw_data.get('published', 'Unknown')}
**Duration:** {raw_data.get('itunes_duration', 'Unknown')}
**Original URL:** {raw_data.get('link', 'https://atp.fm')}

## Episode Description

{raw_data.get('summary', 'No description available').strip()}

"""

        # Add chapters if available
        if chapters:
            enhanced_content += "## Chapters\n\n"
            for chapter in chapters:
                enhanced_content += f"- **{chapter['timestamp']}** - {chapter['title']}\n"
                if chapter.get('url'):
                    enhanced_content += f"  - Link: {chapter['url']}\n"
            enhanced_content += "\n"

        # Add sponsors if available
        if sponsors_links.get('sponsors'):
            enhanced_content += "## Sponsors\n\n"
            for sponsor in sponsors_links['sponsors']:
                enhanced_content += f"### {sponsor['name']}\n\n{sponsor['description']}\n\n"

        # Add links if available
        if sponsors_links.get('links'):
            enhanced_content += "## Links\n\n"
            for link in sponsors_links['links']:
                enhanced_content += f"- [{link['title']}]({link['url']})\n"
            enhanced_content += "\n"

        # Add the transcript
        enhanced_content += "## Transcript\n\n"
        enhanced_content += transcript_data.get('transcript', 'No transcript available')

        return enhanced_content

    def process_recent_episodes(self, min_episode: int = 500, max_episodes: int = 10) -> Dict:
        """Process recent ATP episodes with enhanced transcripts"""
        results = {
            "processed": 0,
            "enhanced_transcripts": 0,
            "errors": []
        }

        # Get ATP episodes from Atlas
        episode_mapping = self.scraper.match_to_atlas_episodes(self.podcasts_dir)

        # Filter to recent episodes
        recent_episodes = {k: v for k, v in episode_mapping.items()
                          if k >= min_episode}

        # Process limited number for testing
        episodes_to_process = sorted(recent_episodes.keys(), reverse=True)[:max_episodes]

        for episode_num in episodes_to_process:
            episode_id = recent_episodes[episode_num]
            results["processed"] += 1

            logger.info(f"Processing ATP Episode {episode_num} (ID: {episode_id})")

            try:
                enhanced_content = self.enhance_episode_transcript(episode_id, episode_num)

                if enhanced_content:
                    # Save enhanced transcript
                    output_file = self.podcasts_dir / "markdown" / f"{episode_id}.md"
                    output_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(enhanced_content)

                    results["enhanced_transcripts"] += 1
                    logger.info(f"Saved enhanced transcript for Episode {episode_num}")

            except Exception as e:
                error_msg = f"Error processing Episode {episode_num}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        return results


def main():
    """Test enhanced transcript generation"""
    atlas_root = Path("/home/ubuntu/dev/atlas")

    enhancer = ATPEnhancedTranscript(atlas_root)

    print("🎯 Testing ATP Enhanced Transcript Generation...")

    # Process a few recent episodes
    results = enhancer.process_recent_episodes(min_episode=600, max_episodes=3)

    print(f"📊 Results:")
    print(f"   Episodes processed: {results['processed']}")
    print(f"   Enhanced transcripts created: {results['enhanced_transcripts']}")
    print(f"   Errors: {len(results['errors'])}")

    for error in results['errors']:
        print(f"   ❌ {error}")


if __name__ == "__main__":
    main()