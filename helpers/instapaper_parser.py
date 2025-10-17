"""
Instapaper Export Parser - Extract individual articles from Instapaper exports

CORE PRINCIPLE: Instapaper exports are article LISTS, not articles themselves
- Parse HTML exports to find individual saved articles
- Extract article URLs, titles, and metadata
- Feed each article to ArticleManager for proper processing
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class InstapaperParser:
    """Parse Instapaper HTML exports to extract individual article URLs."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def parse_export(self, file_path: str) -> Dict[str, Any]:
        """
        Parse Instapaper HTML export to extract individual articles.

        Returns:
            Dict with articles list and parsing metadata
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Extract articles from different export formats
            articles = []

            # Method 1: Look for article links in HTML
            article_links = soup.find_all('a', href=True)
            for link in article_links:
                href = link.get('href', '')
                text = link.get_text().strip()

                # Filter for actual article URLs (not Instapaper interface)
                if self._is_article_url(href) and self._is_article_title(text):
                    articles.append({
                        'url': href,
                        'title': text,
                        'source': 'html_link'
                    })

            # Method 2: Parse text-based exports (like the .md files we're seeing)
            if not articles:
                articles.extend(self._parse_text_export(content))

            # Method 3: Parse CSV exports if this is a CSV
            if file_path.endswith('.csv'):
                articles.extend(self._parse_csv_export(content))

            # Deduplicate and clean
            articles = self._deduplicate_articles(articles)

            return {
                'articles': articles,
                'total_found': len(articles),
                'source_file': file_path,
                'parsing_method': self._determine_parsing_method(content),
                'metadata': {
                    'file_size': os.path.getsize(file_path),
                    'export_type': self._detect_export_type(content),
                }
            }

        except Exception as e:
            return {
                'articles': [],
                'total_found': 0,
                'error': str(e),
                'source_file': file_path
            }

    def _parse_text_export(self, content: str) -> List[Dict[str, Any]]:
        """Parse text-based Instapaper export (like converted .md files)."""
        articles = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Look for article title patterns
            if self._looks_like_article_title(line):
                # Look for source info in next few lines
                source_info = self._find_source_info(lines, i)

                # Try to construct article info
                article = {
                    'title': self._clean_title(line),
                    'url': None,  # Will try to find or reconstruct
                    'source': 'text_export',
                    'metadata': source_info
                }

                # Try to extract domain/source from nearby lines
                for j in range(max(0, i-2), min(len(lines), i+5)):
                    nearby_line = lines[j].strip()
                    if self._contains_domain(nearby_line):
                        article['source_domain'] = self._extract_domain(nearby_line)
                        break

                articles.append(article)

        return articles

    def _parse_csv_export(self, content: str) -> List[Dict[str, Any]]:
        """Parse CSV Instapaper export."""
        articles = []
        lines = content.split('\n')

        # Skip header if present
        start_line = 1 if lines and 'url' in lines[0].lower() else 0

        for line in lines[start_line:]:
            parts = line.split(',')
            if len(parts) >= 2:
                url = parts[0].strip().strip('"')
                title = parts[1].strip().strip('"')

                if self._is_article_url(url):
                    articles.append({
                        'url': url,
                        'title': title,
                        'source': 'csv_export'
                    })

        return articles

    def _is_article_url(self, url: str) -> bool:
        """Check if URL looks like a real article URL."""
        if not url or not url.startswith(('http://', 'https://')):
            return False

        # Skip Instapaper interface URLs
        if 'instapaper.com' in url:
            return False

        # Must have a domain
        parsed = urlparse(url)
        return bool(parsed.netloc and len(parsed.netloc) > 4)

    def _is_article_title(self, text: str) -> bool:
        """Check if text looks like an article title."""
        if not text or len(text) < 5:
            return False

        # Skip common interface elements
        interface_terms = [
            'instapaper', 'search', 'profile', 'settings', 'sign out',
            'help', 'blog', 'apps', 'premium', 'api', 'privacy', 'terms',
            'like liked', 'tags', 'feedly'
        ]

        return not any(term in text.lower() for term in interface_terms)

    def _looks_like_article_title(self, line: str) -> bool:
        """Check if line looks like an article title."""
        # Skip obvious interface elements
        if any(x in line.lower() for x in [
            'instapaper', 'search', 'like liked', 'tags', 'feedly',
            'khamel83@gmail.com', 'selected all', 'oldest first'
        ]):
            return False

        # Must be reasonable title length
        if len(line) < 10 or len(line) > 200:
            return False

        # Skip lines that are just numbers/dates
        if re.match(r'^[\d\s\-/:]+$', line):
            return False

        # Skip lines with too many special chars (likely interface)
        special_char_ratio = len(re.findall(r'[^\w\s]', line)) / len(line)
        if special_char_ratio > 0.3:
            return False

        return True

    def _find_source_info(self, lines: List[str], index: int) -> Dict[str, Any]:
        """Find source information near the article title."""
        info = {}

        # Check next few lines for source info
        for i in range(index + 1, min(len(lines), index + 5)):
            line = lines[i].strip()
            if not line:
                continue

            # Look for domain info
            if self._contains_domain(line):
                info['source_line'] = line
                info['domain'] = self._extract_domain(line)

            # Look for reading time
            time_match = re.search(r'(\d+)\s*min', line)
            if time_match:
                info['reading_time'] = int(time_match.group(1))

            # Look for author info
            if '·' in line and 'min' not in line:
                info['author_line'] = line

        return info

    def _contains_domain(self, line: str) -> bool:
        """Check if line contains a domain name."""
        return bool(re.search(r'\w+\.\w{2,}', line))

    def _extract_domain(self, line: str) -> Optional[str]:
        """Extract domain from line."""
        match = re.search(r'(\w+\.\w{2,})', line)
        return match.group(1) if match else None

    def _clean_title(self, title: str) -> str:
        """Clean up article title."""
        # Remove markdown formatting
        title = re.sub(r'^#+\s*', '', title)

        # Remove common prefixes
        title = re.sub(r'^(Document:\s*)?', '', title)

        return title.strip()

    def _deduplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate articles."""
        seen = set()
        unique_articles = []

        for article in articles:
            # Create key for deduplication
            key = (article.get('url') or article.get('title', '')).lower()
            if key and key not in seen:
                seen.add(key)
                unique_articles.append(article)

        return unique_articles

    def _determine_parsing_method(self, content: str) -> str:
        """Determine which parsing method was most effective."""
        if '<a href=' in content:
            return 'html_links'
        elif ',' in content and 'http' in content:
            return 'csv_format'
        else:
            return 'text_patterns'

    def _detect_export_type(self, content: str) -> str:
        """Detect the type of Instapaper export."""
        if content.startswith('<!DOCTYPE html'):
            return 'html_export'
        elif 'URL,Title' in content:
            return 'csv_export'
        else:
            return 'converted_export'


def parse_instapaper_file(file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convenience function to parse an Instapaper export file."""
    if config is None:
        from helpers.config import load_config
        config = load_config()

    parser = InstapaperParser(config)
    return parser.parse_export(file_path)