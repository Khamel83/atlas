#!/usr/bin/env python3
"""
Backlog URL Extraction and Submission

Extracts URLs from backlog content and submits them through the unified ingestion system.
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Set
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.unified_ingestion import UnifiedIngestionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_urls_from_json_file(file_path: Path) -> List[str]:
    """Extract URLs from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        urls = []

        def extract_from_text(text):
            if isinstance(text, str):
                # Extract URLs using regex
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls.extend(re.findall(url_pattern, text))

        def extract_recursive(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    extract_recursive(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item)
            else:
                extract_from_text(obj)

        extract_recursive(data)
        return urls

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return []

def extract_urls_from_markdown_file(file_path: Path) -> List[str]:
    """Extract URLs from a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract URLs using regex
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, content)

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return []

def extract_urls_from_html_file(file_path: Path) -> List[str]:
    """Extract URLs from an HTML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract URLs using regex
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, content)

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return []

def clean_url(url: str) -> str:
    """Clean and normalize URL."""
    # Remove trailing punctuation and whitespace
    url = url.strip('.,;:!?()[]{}"\'')

    # Remove common tracking parameters
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']
    if '?' in url:
        base_url = url.split('?')[0]
        params = url.split('?')[1].split('&')
        clean_params = [p for p in params if not any(p.startswith(param + '=') for param in tracking_params)]
        if clean_params:
            url = base_url + '?' + '&'.join(clean_params)
        else:
            url = base_url

    return url

def is_valid_url(url: str) -> bool:
    """Check if URL is valid and worth processing."""
    # Skip common non-content URLs
    skip_patterns = [
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
        'youtube.com', 'tiktok.com', 'reddit.com',
        'mailto:', 'tel:', 'javascript:',
        '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.tar.gz'
    ]

    url_lower = url.lower()
    return not any(pattern in url_lower for pattern in skip_patterns)

def main():
    """Extract URLs from backlog and submit to ingestion system."""
    logger.info("Starting backlog URL extraction...")

    # Initialize ingestion manager
    ingestion = UnifiedIngestionManager()

    # Track all URLs to avoid duplicates
    all_urls: Set[str] = set()

    # Process JSON files
    json_dir = Path("inputs/New Docs/json")
    if json_dir.exists():
        logger.info(f"Processing JSON files in {json_dir}...")
        json_files = list(json_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files")

        for i, json_file in enumerate(json_files):
            if i % 100 == 0:
                logger.info(f"Processing JSON file {i+1}/{len(json_files)}")

            urls = extract_urls_from_json_file(json_file)
            for url in urls:
                cleaned_url = clean_url(url)
                if is_valid_url(cleaned_url):
                    all_urls.add(cleaned_url)

    # Process markdown files in articles
    articles_dir = Path("processed_backlog/articles")
    if articles_dir.exists():
        logger.info(f"Processing markdown files in {articles_dir}...")
        md_files = list(articles_dir.glob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files")

        for i, md_file in enumerate(md_files):
            if i % 100 == 0:
                logger.info(f"Processing markdown file {i+1}/{len(md_files)}")

            urls = extract_urls_from_markdown_file(md_file)
            for url in urls:
                cleaned_url = clean_url(url)
                if is_valid_url(cleaned_url):
                    all_urls.add(cleaned_url)

    # Process HTML files
    html_dir = Path("processed_backlog/html")
    if html_dir.exists():
        logger.info(f"Processing HTML files in {html_dir}...")
        html_files = list(html_dir.glob("*.html"))
        logger.info(f"Found {len(html_files)} HTML files")

        for i, html_file in enumerate(html_files):
            if i % 100 == 0:
                logger.info(f"Processing HTML file {i+1}/{len(html_files)}")

            urls = extract_urls_from_html_file(html_file)
            for url in urls:
                cleaned_url = clean_url(url)
                if is_valid_url(cleaned_url):
                    all_urls.add(cleaned_url)

    logger.info(f"Found {len(all_urls)} unique URLs")

    # Submit URLs to ingestion system
    logger.info("Submitting URLs to ingestion system...")

    submitted_count = 0
    for i, url in enumerate(all_urls):
        if i % 100 == 0:
            logger.info(f"Submitted {i}/{len(all_urls)} URLs")

        try:
            ingestion.submit_single_url(
                url=url,
                priority=60,  # High priority for backlog
                source="backlog_cleanup"
            )
            submitted_count += 1
        except Exception as e:
            logger.error(f"Failed to submit URL {url}: {e}")

    logger.info(f"Successfully submitted {submitted_count} URLs from backlog")
    logger.info("Backlog URL extraction completed!")

if __name__ == "__main__":
    main()