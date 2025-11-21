#!/usr/bin/env python3
"""
PODEMOS RSS Feed Generator
Generate clean, private RSS feeds with ad-free episodes hosted on Oracle OCI.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import requests
import feedparser
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
import hashlib
import os
from pathlib import Path
from urllib.parse import urljoin, quote

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PodmosRSSGenerator:
    """RSS feed generator for clean podcast episodes."""

    def __init__(self, base_url: str = None, private_key: str = None):
        """
        Initialize RSS generator.

        Args:
            base_url: Base URL for hosted clean episodes (e.g., Oracle OCI)
            private_key: Private key for generating secure URLs
        """
        self.base_url = base_url or "https://clean-podcasts.oracle-oci-url.com"
        self.private_key = private_key or "podemos-private-key-2025"

    def generate_clean_feed(self, original_feed_url: str, clean_episodes: List[Dict],
                          output_file: str = None) -> Optional[str]:
        """
        Generate clean RSS feed based on original feed.

        Args:
            original_feed_url: URL of original podcast RSS feed
            clean_episodes: List of clean episode data
            output_file: Output RSS file path

        Returns:
            Path to generated RSS file or None if failed
        """
        try:
            logger.info(f"Generating clean RSS feed for: {original_feed_url}")

            # Parse original RSS feed
            original_feed = self._parse_original_feed(original_feed_url)
            if not original_feed:
                return None

            # Create clean RSS structure
            rss_root = self._create_rss_structure(original_feed)

            # Add clean episodes
            channel = rss_root.find('channel')
            for episode_data in clean_episodes:
                episode_item = self._create_episode_item(episode_data, original_feed)
                if episode_item is not None:
                    channel.append(episode_item)

            # Generate output filename if not provided
            if not output_file:
                feed_hash = hashlib.md5(original_feed_url.encode()).hexdigest()[:8]
                output_file = f"clean_feed_{feed_hash}.xml"

            # Write RSS file
            self._write_rss_file(rss_root, output_file)

            logger.info(f"✅ Generated clean RSS feed: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to generate clean feed: {e}")
            return None

    def _parse_original_feed(self, feed_url: str) -> Optional[Dict]:
        """Parse original RSS feed to extract metadata."""
        try:
            logger.info(f"Parsing original feed: {feed_url}")

            # Fetch and parse feed
            response = requests.get(feed_url, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.feed:
                logger.error("Invalid RSS feed format")
                return None

            # Extract feed metadata
            feed_data = {
                'title': feed.feed.get('title', 'Unknown Podcast'),
                'description': feed.feed.get('description', ''),
                'link': feed.feed.get('link', ''),
                'language': feed.feed.get('language', 'en'),
                'copyright': feed.feed.get('rights', ''),
                'managing_editor': feed.feed.get('managingEditor', ''),
                'webmaster': feed.feed.get('webMaster', ''),
                'category': feed.feed.get('tags', []),
                'image_url': '',
                'image_title': '',
                'image_link': ''
            }

            # Extract image information
            if hasattr(feed.feed, 'image'):
                feed_data['image_url'] = feed.feed.image.get('href', '')
                feed_data['image_title'] = feed.feed.image.get('title', '')
                feed_data['image_link'] = feed.feed.image.get('link', '')

            # iTunes-specific metadata
            feed_data['itunes_author'] = getattr(feed.feed, 'itunes_author', '')
            feed_data['itunes_owner_name'] = getattr(feed.feed, 'itunes_owner', {}).get('name', '')
            feed_data['itunes_owner_email'] = getattr(feed.feed, 'itunes_owner', {}).get('email', '')
            feed_data['itunes_category'] = getattr(feed.feed, 'itunes_category', '')
            feed_data['itunes_image'] = getattr(feed.feed, 'itunes_image', {}).get('href', '')
            feed_data['itunes_explicit'] = getattr(feed.feed, 'itunes_explicit', 'no')

            logger.info(f"Parsed feed: {feed_data['title']}")
            return feed_data

        except Exception as e:
            logger.error(f"Failed to parse original feed: {e}")
            return None

    def _create_rss_structure(self, feed_data: Dict) -> ET.Element:
        """Create base RSS structure with original feed metadata."""
        # Create RSS root
        rss = ET.Element('rss')
        rss.set('version', '2.0')
        rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
        rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')

        # Create channel
        channel = ET.SubElement(rss, 'channel')

        # Basic channel information
        ET.SubElement(channel, 'title').text = f"{feed_data['title']} (PODEMOS Clean)"
        ET.SubElement(channel, 'description').text = (
            f"{feed_data['description']}\n\n"
            "🧹 This is a clean version with advertisements removed by PODEMOS. "
            "All content belongs to the original creators."
        )
        ET.SubElement(channel, 'link').text = feed_data['link']
        ET.SubElement(channel, 'language').text = feed_data['language']
        ET.SubElement(channel, 'copyright').text = feed_data['copyright']
        ET.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        ET.SubElement(channel, 'generator').text = 'PODEMOS RSS Generator'

        # Atom self link for the clean feed
        clean_feed_url = self._generate_private_feed_url(feed_data['title'])
        atom_link = ET.SubElement(channel, 'atom:link')
        atom_link.set('href', clean_feed_url)
        atom_link.set('rel', 'self')
        atom_link.set('type', 'application/rss+xml')

        # iTunes metadata
        ET.SubElement(channel, 'itunes:author').text = feed_data.get('itunes_author', '')
        ET.SubElement(channel, 'itunes:explicit').text = feed_data.get('itunes_explicit', 'no')

        # iTunes owner
        if feed_data.get('itunes_owner_name') or feed_data.get('itunes_owner_email'):
            owner = ET.SubElement(channel, 'itunes:owner')
            if feed_data.get('itunes_owner_name'):
                ET.SubElement(owner, 'itunes:name').text = feed_data['itunes_owner_name']
            if feed_data.get('itunes_owner_email'):
                ET.SubElement(owner, 'itunes:email').text = feed_data['itunes_owner_email']

        # iTunes image
        if feed_data.get('itunes_image'):
            itunes_image = ET.SubElement(channel, 'itunes:image')
            itunes_image.set('href', feed_data['itunes_image'])

        # iTunes category
        if feed_data.get('itunes_category'):
            itunes_cat = ET.SubElement(channel, 'itunes:category')
            itunes_cat.set('text', feed_data['itunes_category'])

        # Regular image
        if feed_data.get('image_url'):
            image = ET.SubElement(channel, 'image')
            ET.SubElement(image, 'url').text = feed_data['image_url']
            ET.SubElement(image, 'title').text = feed_data.get('image_title', feed_data['title'])
            ET.SubElement(image, 'link').text = feed_data.get('image_link', feed_data['link'])

        return rss

    def _create_episode_item(self, episode_data: Dict, feed_data: Dict) -> Optional[ET.Element]:
        """Create RSS item element for clean episode."""
        try:
            item = ET.Element('item')

            # Basic episode information
            ET.SubElement(item, 'title').text = episode_data.get('title', 'Unknown Episode')

            # Enhanced description noting ad removal
            original_desc = episode_data.get('description', '')
            clean_desc = (
                f"{original_desc}\n\n"
                f"🧹 Advertisements removed by PODEMOS on {episode_data.get('processed_at', 'Unknown date')}.\n"
                f"Ad segments removed: {len(episode_data.get('ad_segments', []))}\n"
                f"Original episode: {episode_data.get('original_url', 'N/A')}"
            )
            ET.SubElement(item, 'description').text = clean_desc
            ET.SubElement(item, 'itunes:summary').text = clean_desc

            # Episode URL (link to original)
            ET.SubElement(item, 'link').text = episode_data.get('url', '')

            # GUID (unique identifier)
            guid = ET.SubElement(item, 'guid')
            guid.text = episode_data.get('guid', hashlib.md5(episode_data.get('title', '').encode()).hexdigest())
            guid.set('isPermaLink', 'false')

            # Publication date
            if episode_data.get('published_date'):
                pub_date = episode_data['published_date']
                if isinstance(pub_date, str):
                    # Try to parse ISO format
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    except:
                        pub_date = datetime.now()

                ET.SubElement(item, 'pubDate').text = pub_date.strftime('%a, %d %b %Y %H:%M:%S +0000')

            # Clean audio enclosure
            if episode_data.get('clean_audio_file'):
                clean_audio_url = self._generate_clean_audio_url(episode_data['clean_audio_file'])

                enclosure = ET.SubElement(item, 'enclosure')
                enclosure.set('url', clean_audio_url)
                enclosure.set('type', 'audio/mpeg')

                # Try to get file size
                if os.path.exists(episode_data['clean_audio_file']):
                    file_size = os.path.getsize(episode_data['clean_audio_file'])
                    enclosure.set('length', str(file_size))
                else:
                    enclosure.set('length', '1000000')  # Default size

            # Duration (if available)
            if episode_data.get('duration'):
                duration = episode_data['duration']
                if isinstance(duration, (int, float)):
                    # Convert seconds to HH:MM:SS
                    hours = int(duration // 3600)
                    minutes = int((duration % 3600) // 60)
                    seconds = int(duration % 60)
                    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = str(duration)

                ET.SubElement(item, 'itunes:duration').text = duration_str

            # iTunes episode metadata
            ET.SubElement(item, 'itunes:author').text = feed_data.get('itunes_author', '')
            ET.SubElement(item, 'itunes:explicit').text = 'no'  # Clean episodes are not explicit

            return item

        except Exception as e:
            logger.error(f"Failed to create episode item: {e}")
            return None

    def _generate_private_feed_url(self, podcast_title: str) -> str:
        """Generate private URL for RSS feed."""
        # Create hash-based private URL
        title_hash = hashlib.md5(f"{podcast_title}{self.private_key}".encode()).hexdigest()[:12]
        safe_title = "".join(c for c in podcast_title if c.isalnum() or c in (' ', '-')).replace(' ', '-').lower()[:30]

        return f"{self.base_url}/feeds/{safe_title}-{title_hash}.xml"

    def _generate_clean_audio_url(self, clean_file_path: str) -> str:
        """Generate URL for clean audio file."""
        filename = Path(clean_file_path).name
        file_hash = hashlib.md5(f"{filename}{self.private_key}".encode()).hexdigest()[:8]

        return f"{self.base_url}/audio/{file_hash}-{quote(filename)}"

    def _write_rss_file(self, rss_root: ET.Element, output_file: str):
        """Write RSS XML to file with proper formatting."""
        try:
            # Convert to string
            rough_string = ET.tostring(rss_root, encoding='unicode')

            # Pretty print
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ", encoding=None)

            # Remove empty lines
            pretty_lines = [line for line in pretty_xml.split('\n') if line.strip()]
            pretty_xml = '\n'.join(pretty_lines)

            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)

        except Exception as e:
            logger.error(f"Failed to write RSS file: {e}")
            raise

    def generate_episode_metadata(self, original_episode: Dict, clean_audio_file: str,
                                ad_segments: List[Tuple[float, float]]) -> Dict:
        """Generate metadata for clean episode."""
        return {
            'title': original_episode.get('title', 'Unknown Episode'),
            'description': original_episode.get('description', ''),
            'url': original_episode.get('url', ''),
            'original_url': original_episode.get('audio_url', ''),
            'guid': original_episode.get('guid', ''),
            'published_date': original_episode.get('published_date', datetime.now()),
            'duration': original_episode.get('duration'),
            'clean_audio_file': clean_audio_file,
            'ad_segments': ad_segments,
            'processed_at': datetime.now().isoformat()
        }

    def create_oci_deployment_script(self, output_file: str = "deploy_to_oci.sh") -> str:
        """Create Oracle OCI deployment script."""
        script_content = f'''#!/bin/bash
# PODEMOS Oracle OCI Deployment Script
# Deploy clean podcast feeds and audio files to Oracle OCI

set -e

echo "🚀 PODEMOS OCI Deployment Starting..."

# Configuration
OCI_BUCKET="clean-podcasts-bucket"
OCI_NAMESPACE="your-oci-namespace"
OCI_REGION="us-ashburn-1"

# Check if OCI CLI is installed
if ! command -v oci &> /dev/null; then
    echo "❌ OCI CLI not found. Please install: pip install oci-cli"
    exit 1
fi

echo "✅ OCI CLI found"

# Create bucket if it doesn't exist
echo "📦 Creating/checking bucket: $OCI_BUCKET"
oci os bucket create --compartment-id $OCI_COMPARTMENT_ID --name $OCI_BUCKET --public-access-type ObjectRead || echo "Bucket may already exist"

# Upload RSS feeds
echo "📡 Uploading RSS feeds..."
for rss_file in *.xml; do
    if [ -f "$rss_file" ]; then
        oci os object put --bucket-name $OCI_BUCKET --name "feeds/$rss_file" --file "$rss_file"
        echo "  Uploaded: $rss_file"
    fi
done

# Upload clean audio files
echo "🎵 Uploading clean audio files..."
for audio_file in *_clean_*.mp3; do
    if [ -f "$audio_file" ]; then
        # Generate hash for private URL
        file_hash=$(echo "$audio_file{self.private_key}" | md5sum | cut -d' ' -f1 | cut -c1-8)
        oci_name="audio/$file_hash-$audio_file"

        oci os object put --bucket-name $OCI_BUCKET --name "$oci_name" --file "$audio_file"
        echo "  Uploaded: $audio_file -> $oci_name"
    fi
done

# Set up public access for feeds (but not audio files)
echo "🔓 Setting up public access for RSS feeds..."
oci os object bulk-put --bucket-name $OCI_BUCKET --src-dir . --include "*.xml" --object-prefix "feeds/" --overwrite

# Generate public URLs
echo "✅ Deployment complete!"
echo ""
echo "RSS Feed URLs:"
for rss_file in *.xml; do
    if [ -f "$rss_file" ]; then
        url="https://objectstorage.$OCI_REGION.oraclecloud.com/n/$OCI_NAMESPACE/b/$OCI_BUCKET/o/feeds%2F$rss_file"
        echo "  📡 $rss_file: $url"
    fi
done

echo ""
echo "🔒 Audio files are uploaded with private URLs for security"
echo "⚠️  Remember to set OCI_COMPARTMENT_ID environment variable"
'''

        with open(output_file, 'w') as f:
            f.write(script_content)

        # Make script executable
        os.chmod(output_file, 0o755)

        logger.info(f"Created OCI deployment script: {output_file}")
        return output_file

def create_test_feed() -> str:
    """Create a test RSS feed for testing purposes."""
    test_episodes = [
        {
            'title': 'Test Episode 1: Clean Audio Demo',
            'description': 'This is a test episode to demonstrate clean audio generation.',
            'url': 'https://example.com/episode1',
            'original_url': 'https://example.com/original1.mp3',
            'guid': 'test-episode-1-guid',
            'published_date': datetime.now(),
            'duration': 1800,  # 30 minutes
            'clean_audio_file': 'test_episode_1_clean.mp3',
            'ad_segments': [(60, 90), (300, 330)],
            'processed_at': datetime.now().isoformat()
        }
    ]

    generator = PodmosRSSGenerator()

    # Create a mock original feed URL (won't actually fetch)
    original_feed_data = {
        'title': 'Test Podcast',
        'description': 'A test podcast for PODEMOS development',
        'link': 'https://example.com',
        'language': 'en',
        'copyright': '© 2025 Test Podcast',
        'itunes_author': 'Test Author',
        'itunes_image': 'https://example.com/image.jpg'
    }

    # Create RSS structure manually for testing
    rss_root = generator._create_rss_structure(original_feed_data)
    channel = rss_root.find('channel')

    for episode_data in test_episodes:
        episode_item = generator._create_episode_item(episode_data, original_feed_data)
        if episode_item is not None:
            channel.append(episode_item)

    # Write test feed
    test_file = "test_clean_feed.xml"
    generator._write_rss_file(rss_root, test_file)

    logger.info(f"Created test RSS feed: {test_file}")
    return test_file

def main():
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="PODEMOS RSS Generator")
    parser.add_argument('--original-feed', help='Original RSS feed URL')
    parser.add_argument('--episodes', help='Clean episodes JSON file')
    parser.add_argument('--output', help='Output RSS file')
    parser.add_argument('--test', action='store_true', help='Create test feed')
    parser.add_argument('--deploy-script', action='store_true', help='Create OCI deployment script')
    args = parser.parse_args()

    if args.test:
        create_test_feed()
        return

    if args.deploy_script:
        generator = PodmosRSSGenerator()
        generator.create_oci_deployment_script()
        return

    if args.original_feed and args.episodes:
        try:
            # Load clean episodes data
            with open(args.episodes, 'r') as f:
                episodes_data = json.load(f)

            # Generate RSS feed
            generator = PodmosRSSGenerator()
            output_file = generator.generate_clean_feed(
                args.original_feed,
                episodes_data,
                args.output
            )

            if output_file:
                print(f"✅ Generated clean RSS feed: {output_file}")
            else:
                print("❌ Failed to generate RSS feed")

        except Exception as e:
            print(f"Error: {e}")

    else:
        print("Usage:")
        print("  python podemos_rss_generator.py --original-feed <url> --episodes <json> [--output <file>]")
        print("  python podemos_rss_generator.py --test")
        print("  python podemos_rss_generator.py --deploy-script")

if __name__ == "__main__":
    main()