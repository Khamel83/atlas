#!/usr/bin/env python3
"""
Article Ingestor - Comprehensive Metadata Capture

CORE PRINCIPLE: NEVER LOSE ANY DATA - PRESERVE EVERYTHING!

This ingestor captures ALL available metadata from web articles including:
- HTML meta tags (title, description, keywords, author, etc.)
- Open Graph metadata (og:title, og:description, og:image, etc.)
- Twitter Card metadata (twitter:title, twitter:description, etc.)
- Schema.org structured data (JSON-LD, microdata)
- Dublin Core metadata
- Article-specific metadata (publication date, author, tags)
- Technical metadata (headers, response codes, encoding)
- Raw HTML and processed content
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify
from readability import Document

from helpers.article_manager import ArticleManager
from helpers.base_ingestor import BaseIngestor
from helpers.dedupe import link_uid
from helpers.metadata_manager import ContentType
from helpers.utils import generate_markdown_summary, log_error, log_info


class ArticleIngestor(BaseIngestor):
    """Comprehensive article ingestor that preserves ALL metadata"""

    def get_content_type(self):
        return ContentType.ARTICLE

    def get_module_name(self):
        return "article_ingestor"

    def __init__(self, config):
        super().__init__(config, ContentType.ARTICLE, "article_ingestor")
        self.article_manager = ArticleManager(config)

    def process_urls(self, urls: List[str]) -> Dict[str, Any]:
        """Process multiple URLs and capture comprehensive metadata"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_urls": len(urls),
            "processed": [],
            "failed": [],
            "skipped": []
        }

        for url in urls:
            try:
                result = self.process_content(url, {"source": url})
                if result:
                    results["processed"].append(url)
                else:
                    results["failed"].append(url)
            except Exception as e:
                log_error(self.log_path, f"Failed to process {url}: {e}")
                results["failed"].append(url)

        return results

    def process_content(self, url: str, metadata: Dict[str, Any]) -> bool:
        """Process a single article URL with comprehensive metadata capture"""
        log_info(self.log_path, f"Processing article: {url}")

        # Generate UID for deduplication
        file_id = link_uid(url)

        # Get paths for all file types we'll create
        paths = self.path_manager.get_path_set(self.content_type, file_id)
        html_path = paths.get_path("html")
        markdown_path = paths.get_path("markdown")

        try:
            # Fetch article using unified ArticleManager
            article_result = self.article_manager.process_article(url, log_path=self.log_path)

            if not article_result.success:
                log_error(self.log_path, f"Failed to fetch article: {article_result.error}")
                return False

            # Convert ArticleResult to legacy format for compatibility
            class FetchResult:
                def __init__(self, success, content, title, error, metadata):
                    self.success = success
                    self.content = content
                    self.title = title
                    self.error = error
                    self.metadata = metadata

            fetch_result = FetchResult(
                success=article_result.success,
                content=article_result.content,
                title=article_result.title,
                error=article_result.error,
                metadata=article_result.metadata or {}
            )

            # COMPREHENSIVE METADATA EXTRACTION - Never lose any data!
            comprehensive_metadata = self._extract_all_article_metadata(
                url, fetch_result.content, fetch_result.title, fetch_result.metadata
            )

            # Create metadata object with ALL captured information
            meta = self.create_metadata(
                source=url,
                title=fetch_result.title,
                type_specific=comprehensive_metadata["type_specific"]
            )
            meta.uid = file_id

            # Save raw HTML content for complete preservation
            self.save_raw_data(fetch_result.content, meta, "raw_html")

            # Save structured HTML
            if html_path:
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(fetch_result.content)
                meta.html_path = html_path

            # Process with readability for clean content
            doc = Document(fetch_result.content)
            clean_content = doc.summary()

            # Convert to markdown
            markdown_content = markdownify(clean_content)

            # Generate comprehensive markdown summary
            markdown_summary = generate_markdown_summary(
                title=fetch_result.title or "Untitled Article",
                source=url,
                date=meta.date,
                tags=comprehensive_metadata.get("extracted_tags", []),
                notes=[],
                content=markdown_content
            )

            # Save markdown
            if markdown_path:
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_summary)
                meta.content_path = markdown_path

            # Run evaluations if configured
            if markdown_content:
                self.run_evaluations(markdown_content, meta)

            meta.set_success(markdown_path)

        except Exception as e:
            log_error(self.log_path, f"Failed to process article {url}: {e}")
            meta = self.create_metadata(source=url, title="Failed Article")
            meta.uid = file_id
            meta.set_error(str(e))

        # Save comprehensive metadata
        self.save_metadata(meta)
        return meta.status.value == "success"

    def _extract_all_article_metadata(self, url: str, html_content: str, title: str, fetch_metadata: Dict) -> Dict[str, Any]:
        """
        Extract ALL available metadata from article HTML.
        CORE PRINCIPLE: Never lose any data - capture everything!
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # HTML Meta Tags - capture ALL of them
        meta_tags = {}
        for tag in soup.find_all('meta'):
            name = tag.get('name') or tag.get('property') or tag.get('http-equiv') or tag.get('charset')
            content = tag.get('content')
            if name and content:
                meta_tags[name] = content
            # Also capture by attributes for complete preservation
            tag_attrs = dict(tag.attrs)
            if tag_attrs:
                meta_tags[f"_tag_{len(meta_tags)}"] = tag_attrs

        # Open Graph metadata
        og_metadata = {}
        for tag in soup.find_all('meta', property=re.compile(r'^og:')):
            property_name = tag.get('property')
            content = tag.get('content')
            if property_name and content:
                og_metadata[property_name] = content

        # Twitter Card metadata
        twitter_metadata = {}
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            name = tag.get('name')
            content = tag.get('content')
            if name and content:
                twitter_metadata[name] = content

        # Schema.org JSON-LD structured data
        json_ld_data = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                json_ld_data.append(data)
            except (json.JSONDecodeError, AttributeError):
                # Preserve even malformed JSON-LD as text
                json_ld_data.append({"raw_text": script.string, "parse_error": True})

        # Dublin Core metadata
        dublin_core = {}
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'^DC\.|^dc\.')}):
            name = tag.get('name')
            content = tag.get('content')
            if name and content:
                dublin_core[name] = content

        # Article-specific semantic extraction
        article_data = {
            "canonical_url": self._extract_canonical_url(soup, url),
            "extracted_title": self._extract_title(soup),
            "extracted_description": self._extract_description(soup),
            "extracted_author": self._extract_author(soup),
            "extracted_publication_date": self._extract_publication_date(soup),
            "extracted_tags": self._extract_tags(soup),
            "extracted_images": self._extract_images(soup, url),
            "extracted_links": self._extract_links(soup, url),
            "language": self._extract_language(soup),
            "word_count": self._estimate_word_count(soup),
            "reading_time": self._estimate_reading_time(soup)
        }

        # Technical metadata
        technical_metadata = {
            "fetch_method": fetch_metadata.get("method", "unknown"),
            "response_metadata": fetch_metadata,
            "url_parsed": dict(urlparse(url)._asdict()),
            "content_length": len(html_content),
            "has_javascript": bool(soup.find_all('script')),
            "has_css": bool(soup.find_all(['style', 'link'])),
            "form_count": len(soup.find_all('form')),
            "iframe_count": len(soup.find_all('iframe'))
        }

        # Microdata extraction
        microdata = self._extract_microdata(soup)

        # HTML head metadata
        head_metadata = {}
        if soup.head:
            head_metadata = {
                "title_tag": soup.head.title.string if soup.head.title else None,
                "base_url": soup.head.base.get('href') if soup.head.base else None,
                "all_head_tags": [str(tag) for tag in soup.head.find_all()][:50]  # Limit for storage
            }

        return {
            "type_specific": {
                "article": article_data,
                "meta_tags": meta_tags,
                "open_graph": og_metadata,
                "twitter_cards": twitter_metadata,
                "dublin_core": dublin_core,
                "json_ld": json_ld_data,
                "microdata": microdata,
                "technical": technical_metadata,
                "head_metadata": head_metadata,
                "extraction_timestamp": datetime.now().isoformat(),
                "original_url": url,
                "final_title": title
            },
            "extracted_tags": article_data["extracted_tags"]
        }

    def _extract_canonical_url(self, soup: BeautifulSoup, fallback_url: str) -> str:
        """Extract canonical URL"""
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            return urljoin(fallback_url, canonical['href'])
        return fallback_url

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article title from multiple sources"""
        # Try multiple sources in order of preference
        sources = [
            soup.find('meta', property='og:title'),
            soup.find('meta', attrs={'name': 'twitter:title'}),
            soup.find('h1'),
            soup.find('title'),
            soup.find('meta', attrs={'name': 'title'})
        ]

        for source in sources:
            if source:
                content = source.get('content') or source.string or source.text
                if content and content.strip():
                    return content.strip()
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article description/summary"""
        sources = [
            soup.find('meta', property='og:description'),
            soup.find('meta', attrs={'name': 'description'}),
            soup.find('meta', attrs={'name': 'twitter:description'}),
            soup.find('meta', attrs={'name': 'summary'})
        ]

        for source in sources:
            if source and source.get('content'):
                return source['content'].strip()
        return None

    def _extract_author(self, soup: BeautifulSoup) -> List[str]:
        """Extract author information"""
        authors = []

        # Try multiple sources
        sources = [
            soup.find_all('meta', attrs={'name': 'author'}),
            soup.find_all('meta', property='article:author'),
            soup.find_all('[rel="author"]'),
            soup.find_all('.author'),
            soup.find_all('.byline'),
            soup.find_all('[itemprop="author"]')
        ]

        for source_list in sources:
            for tag in source_list:
                content = tag.get('content') or tag.text or tag.string
                if content and content.strip():
                    authors.append(content.strip())

        return list(set(authors))  # Remove duplicates

    def _extract_publication_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date"""
        sources = [
            soup.find('meta', property='article:published_time'),
            soup.find('meta', attrs={'name': 'date'}),
            soup.find('meta', attrs={'name': 'publish_date'}),
            soup.find('[datetime]'),
            soup.find('time'),
            soup.find('[itemprop="datePublished"]')
        ]

        for source in sources:
            if source:
                date = source.get('content') or source.get('datetime') or source.text
                if date and date.strip():
                    return date.strip()
        return None

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract tags/keywords"""
        tags = []

        # Keywords meta tag
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag and keywords_tag.get('content'):
            tags.extend([tag.strip() for tag in keywords_tag['content'].split(',')])

        # Article tags
        tag_elements = soup.find_all(['meta'], property=re.compile(r'article:tag'))
        for element in tag_elements:
            if element.get('content'):
                tags.append(element['content'].strip())

        # Common tag selectors
        tag_selectors = ['.tag', '.tags', '.category', '.categories', '[rel="tag"]']
        for selector in tag_selectors:
            elements = soup.select(selector)
            for element in elements:
                if element.text.strip():
                    tags.append(element.text.strip())

        return list(set(tags))  # Remove duplicates

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract image metadata"""
        images = []

        # Open Graph images
        og_images = soup.find_all('meta', property=re.compile(r'^og:image'))
        for img in og_images:
            if img.get('content'):
                images.append({
                    "url": urljoin(base_url, img['content']),
                    "type": "og_image",
                    "property": img.get('property', '')
                })

        # Twitter images
        twitter_images = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:image')})
        for img in twitter_images:
            if img.get('content'):
                images.append({
                    "url": urljoin(base_url, img['content']),
                    "type": "twitter_image",
                    "name": img.get('name', '')
                })

        # Regular images
        img_tags = soup.find_all('img', src=True)[:10]  # Limit to first 10
        for img in img_tags:
            images.append({
                "url": urljoin(base_url, img['src']),
                "type": "content_image",
                "alt": img.get('alt', ''),
                "title": img.get('title', '')
            })

        return images

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract outbound links"""
        links = []

        # Limit to first 20 external links
        link_tags = soup.find_all('a', href=True)[:20]
        for link in link_tags:
            href = link['href']
            if href.startswith('http') or href.startswith('//'):
                links.append({
                    "url": urljoin(base_url, href),
                    "text": link.text.strip()[:100],  # Limit text length
                    "title": link.get('title', '')
                })

        return links

    def _extract_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract document language"""
        # Check html lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag['lang']

        # Check meta tag
        lang_meta = soup.find('meta', attrs={'http-equiv': 'content-language'})
        if lang_meta and lang_meta.get('content'):
            return lang_meta['content']

        return None

    def _estimate_word_count(self, soup: BeautifulSoup) -> int:
        """Estimate word count of main content"""
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        text = soup.get_text()
        words = text.split()
        return len(words)

    def _estimate_reading_time(self, soup: BeautifulSoup) -> int:
        """Estimate reading time in minutes (200 words per minute)"""
        word_count = self._estimate_word_count(soup)
        return max(1, word_count // 200)

    def _extract_microdata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract microdata structured markup"""
        microdata = {}

        # Find elements with itemscope
        items = soup.find_all(attrs={'itemscope': True})
        for i, item in enumerate(items[:10]):  # Limit to first 10
            item_data = {
                "itemtype": item.get('itemtype', ''),
                "properties": {}
            }

            # Find properties within this item
            props = item.find_all(attrs={'itemprop': True})
            for prop in props:
                prop_name = prop.get('itemprop')
                prop_value = prop.get('content') or prop.text.strip()
                if prop_name and prop_value:
                    item_data["properties"][prop_name] = prop_value

            microdata[f"item_{i}"] = item_data

        return microdata


def ingest_articles(config: dict, input_file: str = "inputs/articles.txt") -> Dict[str, Any]:
    """Main function to ingest articles from a file"""
    ingestor = ArticleIngestor(config)

    if not os.path.exists(input_file):
        log_error(ingestor.log_path, f"Input file not found: {input_file}")
        return {"success": False, "error": f"File not found: {input_file}"}

    # Read URLs from file
    urls = []
    with open(input_file, 'r') as f:
        for line in f:
            url = line.strip()
            if url and not url.startswith('#'):
                urls.append(url)

    log_info(ingestor.log_path, f"Processing {len(urls)} URLs from {input_file}")

    # Process all URLs
    results = ingestor.process_urls(urls)

    log_info(ingestor.log_path, f"Article ingestion complete. Processed: {len(results['processed'])}, Failed: {len(results['failed'])}")

    return results