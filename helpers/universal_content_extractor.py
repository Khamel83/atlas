"""
Universal Content Extractor - Intelligent content extraction from any file type

CORE PRINCIPLE: Any file in, meaningful content out
- Auto-detects content type and structure
- Applies appropriate extraction strategy
- Filters noise, preserves signal
- Never fails, always extracts something useful
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup


class UniversalContentExtractor:
    """Intelligent content extractor that handles any file type gracefully."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def extract_content(self, file_path: str) -> Dict[str, Any]:
        """
        Extract meaningful content from any file type.

        Returns:
            Dict with: content, title, content_type, extraction_method, metadata
        """
        try:
            # Detect file characteristics
            file_info = self._analyze_file(file_path)

            # Choose extraction strategy
            if file_info['is_instapaper_export']:
                return self._extract_from_instapaper(file_path, file_info)
            elif file_info['is_email_html']:
                return self._extract_from_email_html(file_path, file_info)
            elif file_info['is_newsletter']:
                return self._extract_from_newsletter(file_path, file_info)
            elif file_info['is_article_html']:
                return self._extract_from_article_html(file_path, file_info)
            else:
                return self._extract_generic_text(file_path, file_info)

        except Exception as e:
            # Never fail - return something useful
            return {
                'content': f"Failed to extract content from {file_path}: {str(e)}",
                'title': Path(file_path).stem,
                'content_type': 'error',
                'extraction_method': 'fallback',
                'metadata': {'error': str(e), 'file_path': file_path}
            }

    def _analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze file to determine content type and extraction strategy."""
        info = {
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'extension': Path(file_path).suffix.lower(),
            'is_instapaper_export': False,
            'is_email_html': False,
            'is_newsletter': False,
            'is_article_html': False,
            'has_html': False
        }

        try:
            # Read first part of file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content_sample = f.read(5000)

            # Detect patterns
            info['has_html'] = '<html' in content_sample.lower()
            info['is_instapaper_export'] = any(x in content_sample.lower() for x in [
                'instapaper', 'selected all · cancel', 'oldest first', 'archive all'
            ])
            info['is_email_html'] = any(x in content_sample.lower() for x in [
                'unsubscribe', 'view in browser', 'email', '@gmail.com', '@'
            ])
            info['is_newsletter'] = any(x in content_sample.lower() for x in [
                'newsletter', 'stratechery', 'not boring', 'substackcdn'
            ])
            info['is_article_html'] = info['has_html'] and not any([
                info['is_instapaper_export'], info['is_email_html']
            ])

        except Exception as e:
            info['analysis_error'] = str(e)

        return info

    def _extract_from_instapaper(self, file_path: str, file_info: Dict) -> Dict[str, Any]:
        """Extract content from Instapaper HTML export - skip interface noise."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Parse HTML
            soup = BeautifulSoup(content, 'html.parser')

            # Remove Instapaper interface elements
            for element in soup.find_all(['nav', 'header', 'footer']):
                element.decompose()

            # Remove common interface text
            interface_patterns = [
                'instapaper', 'selected all', 'cancel', 'oldest first',
                'archive all', 'download...', 'profile', 'settings', 'sign out',
                'help blog more', 'apps how to save', 'premium api press',
                'publishers privacy & terms', 'twitter facebook',
                'upgrade to premium', 'full-text search', 'permanent archive',
                'unlimited notes', 'text-to-speech playlists'
            ]

            # Extract text and filter
            text = soup.get_text()
            lines = text.split('\n')
            clean_lines = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Skip interface noise
                if any(pattern in line.lower() for pattern in interface_patterns):
                    continue

                # Skip navigation elements
                if line.lower() in ['search', 'like liked', 'tags', 'feedly', 'stratechery']:
                    continue

                # Skip time indicators without content
                if re.match(r'^\d+\s+(min|days?|weeks?|months?)\s+ago$', line.lower()):
                    continue

                clean_lines.append(line)

            # Extract title from filename or first meaningful line
            title = Path(file_path).stem.replace('_', ' ')
            if ' · ' in title:
                title = title.split(' · ')[0]

            clean_content = '\n'.join(clean_lines)

            return {
                'content': clean_content,
                'title': title,
                'content_type': 'instapaper_filtered',
                'extraction_method': 'instapaper_noise_filter',
                'metadata': {
                    'original_length': len(content),
                    'filtered_length': len(clean_content),
                    'lines_removed': len(lines) - len(clean_lines),
                    'filter_effectiveness': f"{(1 - len(clean_content)/len(content))*100:.1f}% noise removed"
                }
            }

        except Exception as e:
            return self._extract_generic_text(file_path, file_info)

    def _extract_from_email_html(self, file_path: str, file_info: Dict) -> Dict[str, Any]:
        """Extract content from email HTML files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'html.parser')

            # Try to find main content area
            main_content = (
                soup.find('div', class_=re.compile(r'content|article|main')) or
                soup.find('td', class_=re.compile(r'content|article|main')) or
                soup.find('body')
            )

            if main_content:
                # Remove unsubscribe links and footers
                for element in main_content.find_all(text=re.compile(r'unsubscribe|view.*browser', re.I)):
                    if element.parent:
                        element.parent.decompose()

                text = main_content.get_text()
            else:
                text = soup.get_text()

            # Clean up text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            clean_content = '\n'.join(lines)

            # Extract title
            title_element = soup.find('title') or soup.find('h1')
            title = title_element.get_text().strip() if title_element else Path(file_path).stem

            return {
                'content': clean_content,
                'title': title,
                'content_type': 'email_html',
                'extraction_method': 'email_content_filter',
                'metadata': {'file_size': file_info['file_size']}
            }

        except Exception as e:
            return self._extract_generic_text(file_path, file_info)

    def _extract_from_newsletter(self, file_path: str, file_info: Dict) -> Dict[str, Any]:
        """Extract content from newsletter HTML."""
        return self._extract_from_email_html(file_path, file_info)

    def _extract_from_article_html(self, file_path: str, file_info: Dict) -> Dict[str, Any]:
        """Extract content from article HTML files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'html.parser')

            # Try common article content selectors
            article_selectors = [
                'article', '.article-content', '.content', '.post-content',
                '.entry-content', 'main', '.main-content'
            ]

            main_content = None
            for selector in article_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if not main_content:
                main_content = soup.find('body') or soup

            text = main_content.get_text()
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            clean_content = '\n'.join(lines)

            # Extract title
            title_element = soup.find('title') or soup.find('h1')
            title = title_element.get_text().strip() if title_element else Path(file_path).stem

            return {
                'content': clean_content,
                'title': title,
                'content_type': 'article_html',
                'extraction_method': 'html_content_extraction',
                'metadata': {'file_size': file_info['file_size']}
            }

        except Exception as e:
            return self._extract_generic_text(file_path, file_info)

    def _extract_generic_text(self, file_path: str, file_info: Dict) -> Dict[str, Any]:
        """Fallback: extract any readable text from file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Basic text cleanup
            if file_info.get('has_html'):
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text()

            lines = [line.strip() for line in content.split('\n') if line.strip()]
            clean_content = '\n'.join(lines)

            return {
                'content': clean_content,
                'title': Path(file_path).stem,
                'content_type': 'generic_text',
                'extraction_method': 'fallback_text_extraction',
                'metadata': {'file_size': file_info['file_size']}
            }

        except Exception as e:
            return {
                'content': f"Could not extract content: {str(e)}",
                'title': Path(file_path).stem,
                'content_type': 'error',
                'extraction_method': 'error_fallback',
                'metadata': {'error': str(e)}
            }


def extract_content_universal(file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convenience function for universal content extraction."""
    if config is None:
        from helpers.config import load_config
        config = load_config()

    extractor = UniversalContentExtractor(config)
    return extractor.extract_content(file_path)