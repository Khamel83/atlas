#!/usr/bin/env python3
"""
Technical Resource Crawler for Atlas

This module detects documentation links, extracts API references,
and crawls technical resources to enhance Atlas content.
"""

import re
import logging
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
from datetime import datetime

class TechResourceCrawler:
    """Crawls technical resources and extracts documentation"""

    def __init__(self, user_agent: str = "Atlas/1.0"):
        """
        Initialize the technical resource crawler

        Args:
            user_agent (str): User agent string for HTTP requests
        """
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.crawled_urls = set()
        self.extracted_resources = []

    def detect_documentation_links(self, content: str) -> List[str]:
        """
        Detect documentation links (docs.python.org, reactjs.org, etc.)

        Args:
            content (str): Text content to search for documentation links

        Returns:
            List[str]: List of detected documentation URLs
        """
        # Common documentation domains
        doc_domains = [
            r'docs\.python\.org',
            r'reactjs\.org',
            r'developer\.mozilla\.org',
            r'docs\.nodejs\.org',
            r'kubernetes\.io/docs',
            r'docs\.docker\.com',
            r'angular\.io/docs',
            r'vuejs\.org/v2/guide',
            r'expressjs\.com',
            r'flask\.pocoo\.org/docs',
            r'django\.documentation',
            r'docs\.mongodb\.com',
            r'redis\.io/documentation',
            r'postgresql\.org/docs',
            r'docs\.aws\.amazon\.com',
            r'cloud\.google\.com/docs',
            r'docs\.microsoft\.com',
            r'developer\.android\.com',
            r'developer\.apple\.com/documentation',
            r'getbootstrap\.com/docs'
        ]

        # Build regex pattern for documentation URLs
        doc_pattern = r'https?://(?:' + '|'.join(doc_domains) + r')[^\s"\'<>]+'

        # Find all documentation URLs
        urls = re.findall(doc_pattern, content, re.IGNORECASE)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    def extract_api_references(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract API references and code examples

        Args:
            urls (List[str]): List of documentation URLs

        Returns:
            List[Dict[str, Any]]: List of API references with examples
        """
        api_references = []

        for url in urls[:10]:  # Limit to avoid overwhelming
            try:
                if url in self.crawled_urls:
                    continue

                self.crawled_urls.add(url)

                # Fetch page content
                response = self.session.get(url, timeout=10)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract API references
                references = self._parse_api_references(soup, url)
                api_references.extend(references)

            except Exception as e:
                logging.warning(f"Failed to extract API references from {url}: {e}")

        return api_references

    def _parse_api_references(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Parse API references from HTML content

        Args:
            soup (BeautifulSoup): Parsed HTML content
            base_url (str): Base URL for resolving relative links

        Returns:
            List[Dict[str, Any]]: List of API references
        """
        references = []

        # Look for common API reference patterns
        # 1. Code blocks with function signatures
        code_blocks = soup.find_all(['code', 'pre', 'samp'])
        for block in code_blocks:
            text = block.get_text().strip()
            if self._looks_like_api_reference(text):
                references.append({
                    'type': 'api_reference',
                    'content': text,
                    'url': base_url,
                    'context': self._get_context(block),
                    'language': self._detect_language(text)
                })

        # 2. API method documentation (headings with method names)
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
        for heading in headings:
            text = heading.get_text().strip()
            if self._looks_like_api_method(text):
                # Find associated content
                content = self._get_associated_content(heading)
                if content:
                    references.append({
                        'type': 'api_method',
                        'name': text,
                        'url': base_url,
                        'content': content,
                        'context': self._get_context(heading)
                    })

        return references

    def _looks_like_api_reference(self, text: str) -> bool:
        """
        Check if text looks like an API reference

        Args:
            text (str): Text to check

        Returns:
            bool: True if looks like API reference
        """
        # Simple heuristics for API references
        api_patterns = [
            r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)',  # Function signatures
            r'^function\s+[a-zA-Z_][a-zA-Z0-9_]*',  # JavaScript functions
            r'^def\s+[a-zA-Z_][a-zA-Z0-9_]*',  # Python functions
            r'^class\s+[a-zA-Z_][a-zA-Z0-9_]*',  # Class definitions
            r'^public\s+[a-zA-Z_][a-zA-Z0-9_]*',  # Java/C# methods
            r'^[A-Z][a-zA-Z0-9]*\.[a-zA-Z_][a-zA-Z0-9_]*'  # Static method calls
        ]

        return any(re.match(pattern, text.strip()) for pattern in api_patterns)

    def _looks_like_api_method(self, text: str) -> bool:
        """
        Check if text looks like an API method name

        Args:
            text (str): Text to check

        Returns:
            bool: True if looks like API method
        """
        # Common API method patterns
        method_patterns = [
            r'^[a-zA-Z_][a-zA-Z0-9_]*\(\)',  # Method calls
            r'^\.[a-zA-Z_][a-zA-Z0-9_]*',  # Method accessors
            r'^[A-Z][a-zA-Z0-9]*\.[a-zA-Z_][a-zA-Z0-9_]*',  # Static methods
            r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*[:\-]',  # Method signatures with description
        ]

        return any(re.match(pattern, text.strip()) for pattern in method_patterns)

    def _get_context(self, element) -> str:
        """
        Get context around an HTML element

        Args:
            element: BeautifulSoup element

        Returns:
            str: Context text
        """
        # Get parent elements for context
        context_elements = []
        parent = element.parent
        for _ in range(3):  # Go up 3 levels
            if parent:
                context_elements.append(parent.get_text().strip())
                parent = parent.parent
            else:
                break

        # Join context elements
        return ' '.join(reversed(context_elements))[:500]  # Limit length

    def _get_associated_content(self, element) -> str:
        """
        Get content associated with an element (e.g., method documentation)

        Args:
            element: BeautifulSoup element

        Returns:
            str: Associated content
        """
        content = []

        # Get next siblings until next heading
        sibling = element.find_next_sibling()
        while sibling and sibling.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if sibling.name in ['p', 'div', 'li', 'td']:
                text = sibling.get_text().strip()
                if text:
                    content.append(text)
            sibling = sibling.find_next_sibling()

        return ' '.join(content)[:1000]  # Limit length

    def _detect_language(self, code: str) -> str:
        """
        Detect programming language from code snippet

        Args:
            code (str): Code snippet

        Returns:
            str: Detected language
        """
        # Simple language detection based on keywords
        if re.search(r'\b(def|import|from|class)\s', code):
            return 'python'
        elif re.search(r'\b(function|var|let|const|=>)\s', code):
            return 'javascript'
        elif re.search(r'\b(public|private|class|interface)\s', code):
            return 'java'
        elif re.search(r'\b(func|package|import)\s', code):
            return 'go'
        elif re.search(r'\b(fn|let|mut)\s', code):
            return 'rust'
        else:
            return 'unknown'

    def identify_package_dependencies(self, content: str) -> List[Dict[str, Any]]:
        """
        Identify package/library dependencies

        Args:
            content (str): Text content to search for dependencies

        Returns:
            List[Dict[str, Any]]: List of identified dependencies
        """
        dependencies = []

        # Common dependency patterns
        patterns = {
            'npm': r'["\']([a-zA-Z0-9\-_]+)["\']\s*:\s*["\']([^"\']+)["\']',  # package.json
            'pip': r'([a-zA-Z0-9\-_]+)(?:\s*==\s*([0-9.]+))?',  # requirements.txt
            'cargo': r'name\s*=\s*["\']([a-zA-Z0-9\-_]+)["\']',  # Cargo.toml
            'gradle': r"implementation\s+['\"]([a-zA-Z0-9\-_.:]+)['\"]",  # build.gradle
            'maven': r'<artifactId>([a-zA-Z0-9\-_.]+)</artifactId>',  # pom.xml
        }

        for package_manager, pattern in patterns.items():
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    name, version = match[0], match[1] if len(match) > 1 else 'latest'
                else:
                    name, version = match, 'latest'

                dependencies.append({
                    'name': name,
                    'version': version,
                    'package_manager': package_manager,
                    'source': 'content_analysis'
                })

        return dependencies

    def crawl_linked_tutorials(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Crawl linked technical blogs and tutorials

        Args:
            urls (List[str]): List of URLs to crawl

        Returns:
            List[Dict[str, Any]]: List of crawled tutorials
        """
        tutorials = []

        for url in urls[:5]:  # Limit to avoid overwhelming
            try:
                if url in self.crawled_urls:
                    continue

                self.crawled_urls.add(url)

                # Fetch page content
                response = self.session.get(url, timeout=10)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract tutorial information
                tutorial = self._parse_tutorial(soup, url)
                if tutorial:
                    tutorials.append(tutorial)

            except Exception as e:
                logging.warning(f"Failed to crawl tutorial from {url}: {e}")

        return tutorials

    def _parse_tutorial(self, soup: BeautifulSoup, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse tutorial information from HTML content

        Args:
            soup (BeautifulSoup): Parsed HTML content
            url (str): Source URL

        Returns:
            Dict[str, Any]: Tutorial information or None
        """
        try:
            # Extract title
            title_element = soup.find('title') or soup.find('h1')
            title = title_element.get_text().strip() if title_element else 'Unknown Tutorial'

            # Extract content
            content_elements = soup.find_all(['p', 'div', 'article'])
            content = ' '.join([elem.get_text().strip() for elem in content_elements if elem.get_text().strip()])

            # Extract code snippets
            code_snippets = []
            code_blocks = soup.find_all(['code', 'pre'])
            for block in code_blocks:
                code_text = block.get_text().strip()
                if code_text and len(code_text) > 20:  # Only include substantial code blocks
                    code_snippets.append({
                        'content': code_text,
                        'language': self._detect_language(code_text)
                    })

            return {
                'title': title,
                'url': url,
                'content': content[:2000],  # Limit content length
                'code_snippets': code_snippets,
                'word_count': len(content.split()),
                'crawled_at': datetime.now().isoformat()
            }

        except Exception as e:
            logging.warning(f"Failed to parse tutorial from {url}: {e}")
            return None

    def extract_code_snippets(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract code snippets and technical diagrams

        Args:
            content (str): Text content to search for code snippets

        Returns:
            List[Dict[str, Any]]: List of extracted code snippets
        """
        snippets = []

        # Look for code blocks in markdown-style content
        # Pattern for fenced code blocks: ```language\n...\n```
        fenced_pattern = r'```([a-zA-Z]*)\n(.*?)\n```'
        matches = re.findall(fenced_pattern, content, re.DOTALL)

        for language, code in matches:
            snippets.append({
                'content': code.strip(),
                'language': language or self._detect_language(code),
                'source': 'fenced_code_block'
            })

        # Look for inline code (single backticks)
        inline_pattern = r'`([^`\n]+)`'
        inline_matches = re.findall(inline_pattern, content)

        for code in inline_matches:
            if self._looks_like_api_reference(code):
                snippets.append({
                    'content': code,
                    'language': self._detect_language(code),
                    'source': 'inline_code'
                })

        return snippets

    def build_technology_stack_maps(self, resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build technology stack relationship maps

        Args:
            resources (List[Dict[str, Any]]): List of extracted resources

        Returns:
            Dict[str, Any]: Technology stack mapping
        """
        tech_map = {
            'languages': {},
            'frameworks': {},
            'libraries': {},
            'tools': {},
            'relationships': []
        }

        # Process extracted resources
        for resource in resources:
            # Count languages
            if 'language' in resource:
                lang = resource['language']
                if lang != 'unknown':
                    tech_map['languages'][lang] = tech_map['languages'].get(lang, 0) + 1

            # Extract technology names from content
            content = resource.get('content', '')
            title = resource.get('title', '')
            text = content + ' ' + title

            # Simple technology detection (in a real implementation, this would use NLP)
            technologies = [
                'python', 'javascript', 'java', 'go', 'rust', 'c++', 'c#',
                'react', 'vue', 'angular', 'django', 'flask', 'express',
                'docker', 'kubernetes', 'aws', 'gcp', 'azure',
                'postgresql', 'mongodb', 'redis', 'mysql',
                'tensorflow', 'pytorch', 'scikit-learn'
            ]

            for tech in technologies:
                if tech in text.lower():
                    # Categorize technology
                    if tech in ['python', 'javascript', 'java', 'go', 'rust', 'c++', 'c#']:
                        category = 'languages'
                    elif tech in ['react', 'vue', 'angular', 'django', 'flask', 'express']:
                        category = 'frameworks'
                    elif tech in ['docker', 'kubernetes', 'aws', 'gcp', 'azure']:
                        category = 'tools'
                    else:
                        category = 'libraries'

                    tech_map[category][tech] = tech_map[category].get(tech, 0) + 1

                    # Add relationship
                    tech_map['relationships'].append({
                        'technology': tech,
                        'category': category,
                        'resource_url': resource.get('url', ''),
                        'frequency': tech_map[category][tech]
                    })

        return tech_map

def main():
    """Example usage of TechResourceCrawler"""
    # Example usage
    crawler = TechResourceCrawler()

    # Sample content with documentation links
    sample_content = """
    For Python development, check out the official docs at https://docs.python.org/3/
    For React development, see https://reactjs.org/docs/getting-started.html
    Node.js documentation is available at https://nodejs.org/api/
    You can also read about Docker at https://docs.docker.com/get-started/
    And don't forget the Kubernetes documentation: https://kubernetes.io/docs/home/

    Here's a Python code example:
    ```python
    def hello_world():
        print("Hello, World!")
        return True
    ```

    And a JavaScript example:
    ```javascript
    function helloWorld() {
        console.log("Hello, World!");
        return true;
    }
    ```

    Dependencies in requirements.txt:
    requests==2.25.1
    beautifulsoup4==4.9.3
    flask==2.0.1

    Dependencies in package.json:
    "express": "^4.17.1",
    "lodash": "^4.17.21"
    """

    # Detect documentation links
    doc_urls = crawler.detect_documentation_links(sample_content)
    print(f"Detected {len(doc_urls)} documentation links:")
    for url in doc_urls:
        print(f"  - {url}")

    # Extract API references
    api_refs = crawler.extract_api_references(doc_urls)
    print(f"\nExtracted {len(api_refs)} API references:")
    for ref in api_refs[:3]:  # Show first 3
        print(f"  - {ref.get('type', 'unknown')}: {ref.get('content', '')[:50]}...")

    # Identify package dependencies
    dependencies = crawler.identify_package_dependencies(sample_content)
    print(f"\nIdentified {len(dependencies)} dependencies:")
    for dep in dependencies:
        print(f"  - {dep['name']} ({dep['package_manager']})")

    # Extract code snippets
    snippets = crawler.extract_code_snippets(sample_content)
    print(f"\nExtracted {len(snippets)} code snippets:")
    for snippet in snippets:
        print(f"  - {snippet['language']}: {snippet['content'][:30]}...")

    # Build technology stack maps
    all_resources = api_refs + [{'content': sample_content, 'title': 'Sample Content'}]
    tech_map = crawler.build_technology_stack_maps(all_resources)
    print(f"\nTechnology stack map created with {len(tech_map['relationships'])} relationships")

    print("Technical resource crawling demo completed successfully!")

if __name__ == "__main__":
    main()