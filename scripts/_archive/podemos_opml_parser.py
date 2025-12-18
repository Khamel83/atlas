#!/usr/bin/env python3
"""
PODEMOS OPML Parser
Parse Overcast OPML exports to extract podcast RSS feeds for ad removal processing.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_overcast_opml(opml_file: str) -> List[Dict[str, str]]:
    """
    Parse Overcast OPML export to extract podcast RSS feed URLs.

    Args:
        opml_file: Path to OPML file exported from Overcast

    Returns:
        List of dictionaries containing podcast metadata:
        [
            {
                'title': 'Podcast Name',
                'rss_url': 'https://example.com/feed.xml',
                'website': 'https://example.com',
                'description': 'Podcast description'
            }
        ]
    """
    try:
        logger.info(f"Parsing OPML file: {opml_file}")

        # Check if file exists
        if not Path(opml_file).exists():
            logger.error(f"OPML file not found: {opml_file}")
            return []

        # Parse XML
        tree = ET.parse(opml_file)
        root = tree.getroot()

        podcasts = []

        # Find all outline elements (podcast entries)
        for outline in root.iter('outline'):
            # Skip category/folder outlines that contain other outlines
            if list(outline):
                continue

            # Extract podcast metadata
            podcast = {}

            # Get title from text or title attribute
            title = outline.get('text') or outline.get('title')
            if not title:
                continue

            podcast['title'] = title

            # Get RSS URL (the most important field)
            rss_url = outline.get('xmlUrl') or outline.get('url')
            if not rss_url:
                logger.warning(f"No RSS URL found for podcast: {title}")
                continue

            podcast['rss_url'] = rss_url

            # Get additional metadata
            podcast['website'] = outline.get('htmlUrl') or ''
            podcast['description'] = outline.get('description') or outline.get('desc') or ''
            podcast['type'] = outline.get('type') or 'rss'

            podcasts.append(podcast)
            logger.debug(f"Found podcast: {title}")

        logger.info(f"Successfully parsed {len(podcasts)} podcasts from OPML")
        return podcasts

    except ET.ParseError as e:
        logger.error(f"Failed to parse OPML file - XML error: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to parse OPML file: {e}")
        return []

def validate_rss_feeds(podcasts: List[Dict[str, str]], timeout: int = 10) -> List[Dict[str, str]]:
    """
    Validate that RSS feeds are accessible and contain episodes.

    Args:
        podcasts: List of podcast dictionaries from parse_overcast_opml
        timeout: Timeout in seconds for HTTP requests

    Returns:
        List of validated podcasts with working RSS feeds
    """
    try:
        import requests
        import feedparser

        valid_podcasts = []

        for podcast in podcasts:
            try:
                logger.info(f"Validating RSS feed for: {podcast['title']}")

                # Test RSS feed access
                response = requests.get(podcast['rss_url'], timeout=timeout)
                if response.status_code != 200:
                    logger.warning(f"RSS feed not accessible ({response.status_code}): {podcast['title']}")
                    continue

                # Parse feed to check if it contains episodes
                feed = feedparser.parse(response.content)
                if not feed.entries:
                    logger.warning(f"RSS feed contains no episodes: {podcast['title']}")
                    continue

                # Add additional metadata from RSS feed
                podcast['feed_title'] = feed.feed.get('title', podcast['title'])
                podcast['feed_description'] = feed.feed.get('description', podcast['description'])
                podcast['episode_count'] = len(feed.entries)

                valid_podcasts.append(podcast)
                logger.info(f"✅ Valid RSS feed: {podcast['title']} ({len(feed.entries)} episodes)")

            except Exception as e:
                logger.warning(f"Failed to validate RSS feed for {podcast['title']}: {e}")
                continue

        logger.info(f"Validated {len(valid_podcasts)} out of {len(podcasts)} podcasts")
        return valid_podcasts

    except ImportError:
        logger.warning("requests or feedparser not available - skipping RSS validation")
        return podcasts

def create_test_opml(output_file: str = "test.opml") -> str:
    """
    Create a test OPML file for testing purposes.

    Args:
        output_file: Path where to create the test OPML file

    Returns:
        Path to created test file
    """
    test_opml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
    <head>
        <title>Overcast Podcast Subscriptions</title>
        <dateCreated>Sun, 08 Sep 2025 15:00:00 GMT</dateCreated>
    </head>
    <body>
        <outline text="Podcasts">
            <outline
                text="The Daily"
                type="rss"
                xmlUrl="https://feeds.nytimes.com/nyt/rss/podcasts/the-daily"
                htmlUrl="https://www.nytimes.com/column/the-daily"
                description="This is what the news should sound like."
            />
            <outline
                text="Lex Fridman Podcast"
                type="rss"
                xmlUrl="https://lexfridman.com/feed/podcast/"
                htmlUrl="https://lexfridman.com/podcast/"
                description="Conversations about science, technology, history, philosophy and the nature of intelligence, consciousness, love, and power."
            />
            <outline
                text="This American Life"
                type="rss"
                xmlUrl="https://feeds.thisamericanlife.org/talpodcast"
                htmlUrl="https://www.thisamericanlife.org/"
                description="This American Life is a weekly public radio show, heard by 2.2 million people on more than 500 stations."
            />
        </outline>
    </body>
</opml>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(test_opml_content)

    logger.info(f"Created test OPML file: {output_file}")
    return output_file

def main():
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="PODEMOS OPML Parser")
    parser.add_argument('--opml', help='OPML file to parse')
    parser.add_argument('--create-test', action='store_true', help='Create test OPML file')
    parser.add_argument('--validate', action='store_true', help='Validate RSS feeds')
    args = parser.parse_args()

    if args.create_test:
        create_test_opml()
        return

    if args.opml:
        podcasts = parse_overcast_opml(args.opml)
        print(f"Found {len(podcasts)} podcast feeds:")

        for podcast in podcasts[:5]:  # Show first 5
            print(f"  - {podcast['title']}: {podcast['rss_url']}")

        if len(podcasts) > 5:
            print(f"  ... and {len(podcasts) - 5} more")

        if args.validate:
            valid_podcasts = validate_rss_feeds(podcasts)
            print(f"\nValidated {len(valid_podcasts)} working RSS feeds")
    else:
        print("Usage: python podemos_opml_parser.py --opml <file> [--validate]")
        print("       python podemos_opml_parser.py --create-test")

if __name__ == "__main__":
    main()