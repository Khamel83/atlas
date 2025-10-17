#!/usr/bin/env python3
"""
Pipeline Integration for Atlas

This module integrates discovered content with the existing ingestion pipeline,
handling preprocessing, validation, and metadata tracking.
"""

import re
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
import os


class PipelineIntegration:
    \"\"\"Content pipeline integration system\"\"\"

    def __init__(self, output_directory: str = \"output/discovered\"):
        \"\"\"Initialize the pipeline integration\"\"\"
        self.output_directory = output_directory
        self.metadata_tracker = {}

        # Ensure output directory exists
        os.makedirs(output_directory, exist_ok=True)

    def integrate_discovered_content(self, discovered_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        \"\"\"
        Integrate discovered content with existing ingestion pipeline

        Args:
            discovered_items (List[Dict[str, Any]]): Discovered content items

        Returns:
            List[Dict[str, Any]]: Integrated content items with pipeline metadata
        \"\"\"
        print(f\"Integrating {len(discovered_items)} discovered items with pipeline...\")

        integrated_items = []

        for item in discovered_items:
            try:
                # Preprocess the discovered item
                preprocessed_item = self._preprocess_discovered_item(item)

                # Validate the item
                if self._validate_discovered_item(preprocessed_item):
                    # Add pipeline metadata
                    integrated_item = self._add_pipeline_metadata(preprocessed_item)

                    # Save to output directory
                    self._save_discovered_content(integrated_item)

                    # Track metadata
                    self._track_metadata(integrated_item)

                    integrated_items.append(integrated_item)
                else:
                    print(f\"Skipping invalid item: {item.get('title', 'Unknown')}\")

            except Exception as e:
                print(f\"Error integrating item: {e}\")
                continue

        print(f\"Successfully integrated {len(integrated_items)} items\")
        return integrated_items

    def _preprocess_discovered_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"
        Preprocess discovered item for pipeline integration

        Args:
            item (Dict[str, Any]): Discovered item

        Returns:
            Dict[str, Any]: Preprocessed item
        \"\"\"
        # Create a copy to avoid modifying original
        processed_item = item.copy()

        # Ensure required fields
        if 'title' not in processed_item:
            processed_item['title'] = 'Untitled Discovered Content'

        if 'content' not in processed_item:
            processed_item['content'] = ''

        if 'source_url' not in processed_item:
            processed_item['source_url'] = ''

        # Normalize content
        processed_item['content'] = self._normalize_content(processed_item['content'])

        # Extract metadata from content if not provided
        if 'tags' not in processed_item or not processed_item['tags']:
            processed_item['tags'] = self._extract_tags(processed_item['content'], processed_item['title'])

        if 'summary' not in processed_item or not processed_item['summary']:
            processed_item['summary'] = self._extract_summary(processed_item['content'])

        # Generate unique identifier
        processed_item['discovery_id'] = self._generate_discovery_id(processed_item)

        # Add discovery timestamp
        processed_item['discovered_at'] = datetime.now().isoformat()

        return processed_item

    def _validate_discovered_item(self, item: Dict[str, Any]) -> bool:
        \"\"\"
        Validate discovered item before pipeline integration

        Args:
            item (Dict[str, Any]): Item to validate

        Returns:
            bool: True if valid, False otherwise
        \"\"\"
        # Check minimum content requirements
        if not item.get('title') or not item['title'].strip():
            return False

        # Check content length
        content = item.get('content', '')
        if len(content.strip()) < 100:  # Minimum 100 characters
            return False

        # Check for duplicate content
        discovery_id = item.get('discovery_id', '')
        if discovery_id in self.metadata_tracker:
            print(f\"Duplicate content detected: {item['title']}\")
            return False

        # Check source validity (if provided)
        source_url = item.get('source_url', '')
        if source_url and not self._is_valid_url(source_url):
            print(f\"Invalid source URL: {source_url}\")
            return False

        return True

    def _add_pipeline_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"
        Add pipeline metadata to discovered item

        Args:
            item (Dict[str, Any]): Item to add metadata to

        Returns:
            Dict[str, Any]: Item with pipeline metadata
        \"\"\"
        # Add pipeline-specific metadata
        pipeline_metadata = {
            'pipeline_entry_type': 'discovered_content',
            'pipeline_status': 'pending_ingestion',
            'pipeline_added_at': datetime.now().isoformat(),
            'pipeline_source': 'autonomous_discovery',
            'pipeline_priority': self._calculate_pipeline_priority(item),
            'pipeline_validation_passed': True,
            'pipeline_preprocessing_complete': True
        }

        # Merge with existing item
        integrated_item = item.copy()
        integrated_item.update(pipeline_metadata)

        return integrated_item

    def _save_discovered_content(self, item: Dict[str, Any]):
        \"\"\"
        Save discovered content to output directory

        Args:
            item (Dict[str, Any]): Item to save
        \"\"\"
        # Create filename from title
        title = item.get('title', 'untitled')
        safe_title = re.sub(r'[^\\w\\-_\\. ]', '_', title)[:50]  # Limit length and sanitize
        filename = f\"{safe_title}_{item['discovery_id'][:8]}.json\"
        filepath = os.path.join(self.output_directory, filename)

        # Save item as JSON
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(item, f, indent=2, ensure_ascii=False)
            print(f\"Saved discovered content: {filename}\")
        except Exception as e:
            print(f\"Error saving content {filename}: {e}\")

    def _track_metadata(self, item: Dict[str, Any]):
        \"\"\"
        Track metadata for discovered item

        Args:
            item (Dict[str, Any]): Item to track
        \"\"\"
        discovery_id = item['discovery_id']
        self.metadata_tracker[discovery_id] = {
            'title': item['title'],
            'source_url': item.get('source_url', ''),
            'discovered_at': item['discovered_at'],
            'pipeline_status': item['pipeline_status'],
            'tags': item.get('tags', []),
            'word_count': len(item.get('content', '').split())
        }

    def _normalize_content(self, content: str) -> str:
        \"\"\"
        Normalize content for processing

        Args:
            content (str): Content to normalize

        Returns:
            str: Normalized content
        \"\"\"
        # Remove extra whitespace
        content = re.sub(r'\\s+', ' ', content)

        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)

        # Fix common encoding issues
        content = content.replace('\\u2019', \"'\")  # Right single quotation mark
        content = content.replace('\\u2018', \"'\")  # Left single quotation mark
        content = content.replace('\\u201d', '\"')  # Right double quotation mark
        content = content.replace('\\u201c', '\"')  # Left double quotation mark
        content = content.replace('\\u2013', '-')  # En dash
        content = content.replace('\\u2014', '-')  # Em dash

        return content.strip()

    def _extract_tags(self, content: str, title: str) -> List[str]:
        \"\"\"
        Extract tags from content and title

        Args:
            content (str): Content to extract tags from
            title (str): Title to extract tags from

        Returns:
            List[str]: Extracted tags
        \"\"\"
        # Combine title and content for tag extraction
        text = (title + ' ' + content).lower()

        # Common technical tags
        common_tags = [
            'python', 'javascript', 'java', 'go', 'rust', 'c++', 'c#',
            'react', 'vue', 'angular', 'django', 'flask', 'express',
            'docker', 'kubernetes', 'aws', 'gcp', 'azure',
            'postgresql', 'mongodb', 'redis', 'mysql',
            'tensorflow', 'pytorch', 'scikit-learn', 'machine-learning',
            'api', 'database', 'framework', 'library',
            'algorithm', 'data-structure', 'authentication', 'security',
            'web-development', 'mobile-development', 'devops',
            'data-science', 'artificial-intelligence',
            'cybersecurity', 'testing', 'microservices'
        ]

        # Find matching tags
        found_tags = []
        for tag in common_tags:
            if tag in text:
                found_tags.append(tag)

        # Extract additional tags from words
        words = re.findall(r'\\b\\w{4,15}\\b', text)
        word_tags = [word for word in words if len(word) > 3 and word not in found_tags]

        # Combine and limit
        all_tags = found_tags + word_tags[:10]
        return list(set(all_tags))[:20]  # Remove duplicates and limit to 20

    def _extract_summary(self, content: str) -> str:
        \"\"\"
        Extract summary from content

        Args:
            content (str): Content to extract summary from

        Returns:
            str: Extracted summary
        \"\"\"
        # Simple extraction: first few sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Take first 2-3 sentences as summary
        summary_sentences = sentences[:3]
        summary = '. '.join(summary_sentences)

        # Limit length
        if len(summary) > 500:
            summary = summary[:497] + '...'

        return summary

    def _generate_discovery_id(self, item: Dict[str, Any]) -> str:
        \"\"\"
        Generate unique discovery ID for item

        Args:
            item (Dict[str, Any]): Item to generate ID for

        Returns:
            str: Unique discovery ID
        \"\"\"
        # Create hash from title, content, and source
        content_to_hash = (
            item.get('title', '') +
            item.get('content', '')[:1000] +  # Limit content length for hashing
            item.get('source_url', '')
        )

        discovery_id = hashlib.sha256(content_to_hash.encode('utf-8')).hexdigest()
        return discovery_id

    def _calculate_pipeline_priority(self, item: Dict[str, Any]) -> int:
        \"\"\"
        Calculate pipeline priority for discovered item

        Args:
            item (Dict[str, Any]): Item to calculate priority for

        Returns:
            int: Priority (1=highest, 10=lowest)
        \"\"\"
        priority = 5  # Default priority

        # Adjust based on source quality
        source_url = item.get('source_url', '')
        if 'github.com' in source_url:
            priority = 2  # High priority for GitHub
        elif 'stackoverflow.com' in source_url:
            priority = 3  # High priority for Stack Overflow
        elif 'arxiv.org' in source_url:
            priority = 2  # High priority for academic papers
        elif 'medium.com' in source_url:
            priority = 4  # Medium priority for Medium

        # Adjust based on content quality indicators
        content = item.get('content', '')
        if len(content.split()) > 1000:  # Long content
            priority = min(priority, 4)

        # Adjust based on tags (technical content gets higher priority)
        tags = item.get('tags', [])
        technical_tags = ['python', 'javascript', 'machine-learning', 'data-science', 'devops']
        if any(tag in tags for tag in technical_tags):
            priority = min(priority, 3)

        return priority

    def _is_valid_url(self, url: str) -> bool:
        \"\"\"
        Check if URL is valid

        Args:
            url (str): URL to validate

        Returns:
            bool: True if valid, False otherwise
        \"\"\"
        if not url:
            return False

        # Simple URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\\.)+[A-Z]{2,6}\\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})'  # ...or ip
            r'(?::\\d+)?'  # optional port
            r'(?:/?|[/?]\\S+)$', re.IGNORECASE)

        return url_pattern.match(url) is not None

    def get_integration_stats(self) -> Dict[str, Any]:
        \"\"\"
        Get pipeline integration statistics

        Returns:
            Dict[str, Any]: Integration statistics
        \"\"\"
        total_items = len(self.metadata_tracker)

        # Calculate tag distribution
        tag_counts = {}
        for item in self.metadata_tracker.values():
            for tag in item.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Get most common tags
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        top_tags = sorted_tags[:10]

        # Calculate source distribution
        source_counts = {}
        for item in self.metadata_tracker.values():
            source = item.get('source_url', '')
            if source:
                domain = re.search(r'https?://([^/]+)', source)
                if domain:
                    domain = domain.group(1)
                    source_counts[domain] = source_counts.get(domain, 0) + 1

        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
        top_sources = sorted_sources[:10]

        return {
            'total_integrated_items': total_items,
            'top_tags': top_tags,
            'top_sources': top_sources,
            'average_word_count': sum(item['word_count'] for item in self.metadata_tracker.values()) / max(total_items, 1),
            'tracking_since': datetime.now().isoformat()
        }

    def get_pending_items(self) -> List[Dict[str, Any]]:
        \"\"\"
        Get items pending pipeline processing

        Returns:
            List[Dict[str, Any]]: Pending items
        \"\"\"
        pending_items = []
        for discovery_id, metadata in self.metadata_tracker.items():
            if metadata.get('pipeline_status') == 'pending_ingestion':
                pending_items.append({
                    'discovery_id': discovery_id,
                    'title': metadata['title'],
                    'source_url': metadata['source_url'],
                    'discovered_at': metadata['discovered_at'],
                    'tags': metadata['tags'],
                    'word_count': metadata['word_count']
                })

        return pending_items


def main():
    \"\"\"Example usage of PipelineIntegration\"\"\"
    # Create pipeline integration
    pipeline = PipelineIntegration()

    # Sample discovered items
    sample_items = [
        {
            'title': 'Introduction to Python Decorators',
            'content': 'Python decorators are a powerful feature that allows you to modify the behavior of functions or classes. They provide a clean and readable way to add functionality to existing code without permanently modifying it.',
            'source_url': 'https://realpython.com/primer-on-python-decorators/',
            'tags': ['python', 'decorators', 'programming'],
            'summary': 'Python decorators provide a way to modify function behavior.'
        },
        {
            'title': 'Machine Learning Model Evaluation',
            'content': 'Evaluating machine learning models is crucial for understanding their performance and reliability. Common metrics include accuracy, precision, recall, and F1-score. Cross-validation helps ensure robust evaluation.',
            'source_url': 'https://towardsdatascience.com/model-evaluation-techniques-6d2b3b4c7c2c',
            'tags': ['machine-learning', 'evaluation', 'data-science'],
            'summary': 'Model evaluation techniques for machine learning.'
        },
        {
            'title': 'Docker Best Practices',
            'content': 'When working with Docker, following best practices can significantly improve your container security, performance, and maintainability. Key practices include using multi-stage builds, minimizing layer count, and running containers as non-root users.',
            'source_url': 'https://docs.docker.com/develop/develop-images/dockerfile_best-practices/',
            'tags': ['docker', 'devops', 'containers'],
            'summary': 'Best practices for Docker container development.'
        }
    ]

    # Integrate discovered content
    print(\"Integrating discovered content with pipeline...\")
    integrated_items = pipeline.integrate_discovered_content(sample_items)

    # Display results
    print(f\"\\nIntegrated {len(integrated_items)} items:\")
    for item in integrated_items:
        print(f\"  - {item['title']}\")
        print(f\"    Discovery ID: {item['discovery_id'][:16]}...\")
        print(f\"    Priority: {item['pipeline_priority']}\")
        print(f\"    Tags: {', '.join(item.get('tags', [])[:5])}\")
        print()

    # Get integration stats
    stats = pipeline.get_integration_stats()
    print(f\"\\nIntegration Statistics:\")
    print(f\"  Total Items: {stats['total_integrated_items']}\")
    print(f\"  Average Word Count: {stats['average_word_count']:.1f}\")

    print(f\"\\nTop Tags:\")
    for tag, count in stats['top_tags']:
        print(f\"  - {tag}: {count}\")

    print(f\"\\nTop Sources:\")
    for source, count in stats['top_sources']:
        print(f\"  - {source}: {count}\")

    # Check pending items
    pending = pipeline.get_pending_items()
    print(f\"\\nPending Items: {len(pending)}\")


if __name__ == \"__main__\":
    main()