#!/usr/bin/env python3
"""
Content Enhancer for Atlas

This module automatically enhances content with discovered metadata,
links articles to related GitHub repositories, and creates cross-reference systems.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

class ContentEnhancer:
    """Enhances Atlas content with discovered metadata and cross-references"""

    def __init__(self):
        """Initialize the content enhancer"""
        self.enhanced_content = []
        self.cross_references = {}
        self.search_index = {}

    def enhance_content_with_metadata(self, content_items: List[Dict[str, Any]],
                                   metadata_sources: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Automatically enhance content with discovered metadata

        Args:
            content_items (List[Dict[str, Any]]): List of content items to enhance
            metadata_sources (Dict[str, List[Dict[str, Any]]]): Metadata from various sources

        Returns:
            List[Dict[str, Any]]: Enhanced content items
        """
        enhanced_items = []

        print(f"Enhancing {len(content_items)} content items with metadata...")

        for item in content_items:
            try:
                # Create enhanced item
                enhanced_item = self._enhance_single_item(item, metadata_sources)
                enhanced_items.append(enhanced_item)

            except Exception as e:
                logging.error(f"Failed to enhance content item {item.get('id', 'unknown')}: {e}")
                # Keep original item if enhancement fails
                enhanced_items.append(item)

        self.enhanced_content = enhanced_items
        print(f"Enhanced {len(enhanced_items)} content items")
        return enhanced_items

    def _enhance_single_item(self, item: Dict[str, Any],
                           metadata_sources: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Enhance a single content item with metadata

        Args:
            item (Dict[str, Any]): Content item to enhance
            metadata_sources (Dict[str, List[Dict[str, Any]]]): Metadata from various sources

        Returns:
            Dict[str, Any]: Enhanced content item
        """
        # Create a copy of the item to avoid modifying the original
        enhanced_item = item.copy()

        # Add metadata from different sources
        github_repos = metadata_sources.get('github_repos', [])
        api_references = metadata_sources.get('api_references', [])
        tutorials = metadata_sources.get('tutorials', [])
        dependencies = metadata_sources.get('dependencies', [])

        # Enhance with GitHub repository information
        if github_repos:
            enhanced_item['github_repositories'] = self._match_github_repos(item, github_repos)

        # Enhance with API references
        if api_references:
            enhanced_item['api_references'] = self._match_api_references(item, api_references)

        # Enhance with tutorials
        if tutorials:
            enhanced_item['related_tutorials'] = self._match_tutorials(item, tutorials)

        # Enhance with dependencies
        if dependencies:
            enhanced_item['dependencies'] = self._match_dependencies(item, dependencies)

        # Add enhancement metadata
        enhanced_item['atlas_enhancement'] = {
            'enhanced_at': datetime.now().isoformat(),
            'enhancement_version': '1.0',
            'sources_used': list(metadata_sources.keys())
        }

        return enhanced_item

    def _match_github_repos(self, item: Dict[str, Any],
                          github_repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match GitHub repositories to content item

        Args:
            item (Dict[str, Any]): Content item
            github_repos (List[Dict[str, Any]]): GitHub repository metadata

        Returns:
            List[Dict[str, Any]]: Matched repositories
        """
        matched_repos = []
        content_text = f"{item.get('title', '')} {item.get('content', '')}".lower()

        for repo in github_repos:
            repo_name = repo.get('full_name', '').lower()
            repo_desc = repo.get('description', '').lower()
            repo_topics = ' '.join(repo.get('topics', [])).lower()

            # Simple matching based on text overlap
            if (repo_name in content_text or
                any(word in repo_desc for word in content_text.split()) or
                any(topic in content_text for topic in repo.get('topics', []))):

                matched_repos.append({
                    'name': repo.get('full_name'),
                    'url': repo.get('url'),
                    'description': repo.get('description'),
                    'stars': repo.get('stars', 0),
                    'language': repo.get('language'),
                    'topics': repo.get('topics', []),
                    'confidence': self._calculate_confidence(item, repo)
                })

        return matched_repos

    def _match_api_references(self, item: Dict[str, Any],
                            api_references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match API references to content item

        Args:
            item (Dict[str, Any]): Content item
            api_references (List[Dict[str, Any]]): API reference metadata

        Returns:
            List[Dict[str, Any]]: Matched API references
        """
        matched_refs = []
        content_text = f"{item.get('title', '')} {item.get('content', '')}".lower()

        for ref in api_references:
            ref_content = ref.get('content', '').lower()
            ref_context = ref.get('context', '').lower()

            # Simple matching based on text overlap
            if (any(word in ref_content for word in content_text.split()) or
                any(word in ref_context for word in content_text.split())):

                matched_refs.append({
                    'type': ref.get('type'),
                    'content': ref.get('content'),
                    'url': ref.get('url'),
                    'language': ref.get('language', 'unknown'),
                    'context': ref.get('context'),
                    'confidence': self._calculate_confidence(item, ref)
                })

        return matched_refs

    def _match_tutorials(self, item: Dict[str, Any],
                       tutorials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match tutorials to content item

        Args:
            item (Dict[str, Any]): Content item
            tutorials (List[Dict[str, Any]]): Tutorial metadata

        Returns:
            List[Dict[str, Any]]: Matched tutorials
        """
        matched_tutorials = []
        content_text = f"{item.get('title', '')} {item.get('content', '')}".lower()

        for tutorial in tutorials:
            tutorial_title = tutorial.get('title', '').lower()
            tutorial_content = tutorial.get('content', '').lower()

            # Simple matching based on text overlap
            if (any(word in tutorial_title for word in content_text.split()) or
                any(word in tutorial_content for word in content_text.split())):

                matched_tutorials.append({
                    'title': tutorial.get('title'),
                    'url': tutorial.get('url'),
                    'word_count': tutorial.get('word_count', 0),
                    'code_snippets': len(tutorial.get('code_snippets', [])),
                    'confidence': self._calculate_confidence(item, tutorial)
                })

        return matched_tutorials

    def _match_dependencies(self, item: Dict[str, Any],
                          dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match dependencies to content item

        Args:
            item (Dict[str, Any]): Content item
            dependencies (List[Dict[str, Any]]): Dependency metadata

        Returns:
            List[Dict[str, Any]]: Matched dependencies
        """
        matched_deps = []
        content_text = f"{item.get('title', '')} {item.get('content', '')}".lower()

        for dep in dependencies:
            dep_name = dep.get('name', '').lower()

            # Simple matching based on text overlap
            if dep_name in content_text:
                matched_deps.append({
                    'name': dep.get('name'),
                    'version': dep.get('version', 'latest'),
                    'package_manager': dep.get('package_manager'),
                    'confidence': self._calculate_confidence(item, dep)
                })

        return matched_deps

    def _calculate_confidence(self, item: Dict[str, Any],
                            metadata: Dict[str, Any]) -> float:
        """
        Calculate confidence score for metadata match

        Args:
            item (Dict[str, Any]): Content item
            metadata (Dict[str, Any]): Metadata item

        Returns:
            float: Confidence score (0.0 - 1.0)
        """
        # Simple confidence calculation based on text overlap
        content_text = f"{item.get('title', '')} {item.get('content', '')}".lower()
        metadata_text = f"{metadata.get('title', '')} {metadata.get('content', '')} {metadata.get('description', '')}".lower()

        # Count matching words
        content_words = set(content_text.split())
        metadata_words = set(metadata_text.split())

        if not content_words or not metadata_words:
            return 0.1  # Minimum confidence

        # Calculate Jaccard similarity
        intersection = len(content_words.intersection(metadata_words))
        union = len(content_words.union(metadata_words))

        if union == 0:
            return 0.1

        jaccard_similarity = intersection / union

        # Scale to 0.0 - 1.0 range with some minimum confidence
        confidence = min(0.9, max(0.1, jaccard_similarity * 2))
        return confidence

    def link_articles_to_github(self, articles: List[Dict[str, Any]],
                              github_repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Link articles to related GitHub repositories

        Args:
            articles (List[Dict[str, Any]]): List of articles
            github_repos (List[Dict[str, Any]]): List of GitHub repositories

        Returns:
            List[Dict[str, Any]]: Articles with GitHub links
        """
        linked_articles = []

        for article in articles:
            # Find related GitHub repositories
            related_repos = self._find_related_repos(article, github_repos)

            # Add GitHub links to article
            linked_article = article.copy()
            if related_repos:
                linked_article['github_links'] = related_repos

            linked_articles.append(linked_article)

        return linked_articles

    def _find_related_repos(self, article: Dict[str, Any],
                          github_repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find related GitHub repositories for an article

        Args:
            article (Dict[str, Any]): Article metadata
            github_repos (List[Dict[str, Any]]): GitHub repository metadata

        Returns:
            List[Dict[str, Any]]: Related repositories
        """
        related_repos = []
        article_text = f"{article.get('title', '')} {article.get('content', '')}".lower()

        for repo in github_repos:
            repo_name = repo.get('full_name', '').lower()
            repo_desc = repo.get('description', '').lower()
            repo_topics = ' '.join(repo.get('topics', [])).lower()

            # Check for matches
            matches = []
            if repo_name in article_text:
                matches.append('name')
            if any(topic in article_text for topic in repo.get('topics', [])):
                matches.append('topic')
            if any(word in repo_desc for word in article_text.split()):
                matches.append('description')

            if matches:
                related_repos.append({
                    'name': repo.get('full_name'),
                    'url': repo.get('url'),
                    'description': repo.get('description'),
                    'stars': repo.get('stars', 0),
                    'match_types': matches,
                    'confidence': len(matches) / 3.0  # Simple confidence based on match types
                })

        # Sort by confidence
        related_repos.sort(key=lambda x: x['confidence'], reverse=True)
        return related_repos[:5]  # Limit to top 5 matches

    def add_code_examples_to_podcasts(self, podcast_episodes: List[Dict[str, Any]],
                                    code_examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add code examples to podcast transcript contexts

        Args:
            podcast_episodes (List[Dict[str, Any]]): List of podcast episodes
            code_examples (List[Dict[str, Any]]): List of code examples

        Returns:
            List[Dict[str, Any]]: Podcast episodes with code examples
        """
        enhanced_episodes = []

        for episode in podcast_episodes:
            # Find relevant code examples
            relevant_examples = self._find_relevant_examples(episode, code_examples)

            # Add code examples to episode
            enhanced_episode = episode.copy()
            if relevant_examples:
                enhanced_episode['code_examples'] = relevant_examples

            enhanced_episodes.append(enhanced_episode)

        return enhanced_episodes

    def _find_relevant_examples(self, episode: Dict[str, Any],
                              code_examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find relevant code examples for a podcast episode

        Args:
            episode (Dict[str, Any]): Podcast episode metadata
            code_examples (List[Dict[str, Any]]): Code example metadata

        Returns:
            List[Dict[str, Any]]: Relevant code examples
        """
        relevant_examples = []
        transcript = episode.get('transcript', '').lower()

        for example in code_examples:
            example_content = example.get('content', '').lower()
            example_language = example.get('language', '').lower()

            # Check for relevance
            if (any(word in example_content for word in transcript.split()) or
                example_language in transcript):

                relevant_examples.append({
                    'content': example.get('content'),
                    'language': example.get('language'),
                    'source': example.get('source', 'unknown'),
                    'confidence': self._calculate_confidence(episode, example)
                })

        # Sort by confidence
        relevant_examples.sort(key=lambda x: x['confidence'], reverse=True)
        return relevant_examples[:3]  # Limit to top 3 examples

    def create_cross_reference_system(self, content_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create cross-reference systems for technical concepts

        Args:
            content_items (List[Dict[str, Any]]): List of content items

        Returns:
            Dict[str, Any]: Cross-reference system
        """
        cross_ref_system = {
            'concepts': {},
            'relationships': {},
            'index': {}
        }

        # Build concept index
        for item in content_items:
            concepts = self._extract_concepts(item)
            item_id = item.get('id', str(hash(str(item))))

            for concept in concepts:
                # Add to concepts dictionary
                if concept not in cross_ref_system['concepts']:
                    cross_ref_system['concepts'][concept] = {
                        'items': [],
                        'related_concepts': set()
                    }

                cross_ref_system['concepts'][concept]['items'].append(item_id)

                # Add to index
                if concept not in cross_ref_system['index']:
                    cross_ref_system['index'][concept] = []
                cross_ref_system['index'][concept].append(item_id)

        # Build relationships between concepts
        cross_ref_system['relationships'] = self._build_concept_relationships(
            cross_ref_system['concepts']
        )

        # Convert sets to lists for JSON serialization
        for concept in cross_ref_system['concepts']:
            if 'related_concepts' in cross_ref_system['concepts'][concept]:
                cross_ref_system['concepts'][concept]['related_concepts'] = list(
                    cross_ref_system['concepts'][concept]['related_concepts']
                )

        self.cross_references = cross_ref_system
        return cross_ref_system

    def _extract_concepts(self, item: Dict[str, Any]) -> List[str]:
        """
        Extract technical concepts from a content item

        Args:
            item (Dict[str, Any]): Content item

        Returns:
            List[str]: Extracted concepts
        """
        # Simple concept extraction (in a real implementation, this would use NLP)
        content = f"{item.get('title', '')} {item.get('content', '')} {item.get('description', '')}"
        words = content.lower().split()

        # Filter for technical terms (simplified)
        technical_terms = [
            'python', 'javascript', 'java', 'go', 'rust', 'c++', 'c#',
            'react', 'vue', 'angular', 'django', 'flask', 'express',
            'docker', 'kubernetes', 'aws', 'gcp', 'azure',
            'postgresql', 'mongodb', 'redis', 'mysql',
            'tensorflow', 'pytorch', 'scikit-learn', 'machine learning',
            'api', 'database', 'framework', 'library', 'package',
            'algorithm', 'data structure', 'authentication', 'security'
        ]

        concepts = []
        for word in words:
            # Clean word
            clean_word = ''.join(c for c in word if c.isalnum())
            if clean_word in technical_terms and clean_word not in concepts:
                concepts.append(clean_word)

        return concepts

    def _build_concept_relationships(self, concepts: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Build relationships between concepts

        Args:
            concepts (Dict[str, Any]): Concept dictionary

        Returns:
            Dict[str, List[str]]: Concept relationships
        """
        relationships = {}

        # Simple relationship building based on co-occurrence
        concept_items = {}
        for concept, data in concepts.items():
            concept_items[concept] = set(data['items'])

        for concept1 in concept_items:
            relationships[concept1] = []
            for concept2 in concept_items:
                if concept1 != concept2:
                    # Calculate overlap
                    overlap = len(concept_items[concept1].intersection(concept_items[concept2]))
                    total = len(concept_items[concept1].union(concept_items[concept2]))

                    if total > 0 and overlap / total > 0.3:  # 30% overlap threshold
                        relationships[concept1].append(concept2)
                        # Add to related concepts in both directions
                        if 'related_concepts' in concepts[concept1]:
                            concepts[concept1]['related_concepts'].add(concept2)
                        if 'related_concepts' in concepts[concept2]:
                            concepts[concept2]['related_concepts'].add(concept1)

        return relationships

    def build_searchable_index(self, content_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build searchable index of code patterns and examples

        Args:
            content_items (List[Dict[str, Any]]): List of content items

        Returns:
            Dict[str, Any]: Searchable index
        """
        search_index = {
            'code_patterns': {},
            'examples': {},
            'keywords': {},
            'updated_at': datetime.now().isoformat()
        }

        for item in content_items:
            item_id = item.get('id', str(hash(str(item))))

            # Index code patterns
            code_patterns = self._extract_code_patterns(item)
            for pattern in code_patterns:
                if pattern not in search_index['code_patterns']:
                    search_index['code_patterns'][pattern] = []
                search_index['code_patterns'][pattern].append(item_id)

            # Index examples
            examples = self._extract_examples(item)
            for example in examples:
                if example not in search_index['examples']:
                    search_index['examples'][example] = []
                search_index['examples'][example].append(item_id)

            # Index keywords
            keywords = self._extract_keywords(item)
            for keyword in keywords:
                if keyword not in search_index['keywords']:
                    search_index['keywords'][keyword] = []
                search_index['keywords'][keyword].append(item_id)

        self.search_index = search_index
        return search_index

    def _extract_code_patterns(self, item: Dict[str, Any]) -> List[str]:
        """
        Extract code patterns from a content item

        Args:
            item (Dict[str, Any]): Content item

        Returns:
            List[str]: Extracted code patterns
        """
        # Look for common code patterns
        content = f"{item.get('content', '')} {item.get('code_examples', '')}"

        patterns = []

        # Function definitions
        func_patterns = [
            r'\bdef\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(',  # Python
            r'\bfunction\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(',  # JavaScript
            r'\b[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*function\s*\(',  # JS anonymous
            r'\bpublic\s+[a-zA-Z_][a-zA-Z0-9_]*\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(',  # Java/C#
        ]

        for pattern in func_patterns:
            import re
            matches = re.findall(pattern, content)
            patterns.extend(matches)

        return list(set(patterns))  # Remove duplicates

    def _extract_examples(self, item: Dict[str, Any]) -> List[str]:
        """
        Extract examples from a content item

        Args:
            item (Dict[str, Any]): Content item

        Returns:
            List[str]: Extracted examples
        """
        examples = []

        # Look for example markers
        content = item.get('content', '')
        example_indicators = ['example', 'sample', 'demo', 'illustration']

        for indicator in example_indicators:
            if indicator in content.lower():
                # Extract surrounding context
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if indicator in line.lower():
                        # Get a few lines of context
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = '\n'.join(lines[start:end])
                        examples.append(context[:200])  # Limit length

        return examples

    def _extract_keywords(self, item: Dict[str, Any]) -> List[str]:
        """
        Extract keywords from a content item

        Args:
            item (Dict[str, Any]): Content item

        Returns:
            List[str]: Extracted keywords
        """
        # Simple keyword extraction
        content = f"{item.get('title', '')} {item.get('content', '')}"
        words = content.lower().split()

        # Filter for important words (simplified)
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]

        return list(set(keywords))[:20]  # Limit to top 20 unique keywords

    def generate_enhanced_summaries(self, content_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate enhanced content summaries

        Args:
            content_items (List[Dict[str, Any]]): List of content items

        Returns:
            List[Dict[str, Any]]: Content items with enhanced summaries
        """
        enhanced_items = []

        for item in content_items:
            # Generate enhanced summary
            enhanced_summary = self._generate_enhanced_summary(item)

            # Add to item
            enhanced_item = item.copy()
            enhanced_item['enhanced_summary'] = enhanced_summary

            enhanced_items.append(enhanced_item)

        return enhanced_items

    def _generate_enhanced_summary(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an enhanced summary for a content item

        Args:
            item (Dict[str, Any]): Content item

        Returns:
            Dict[str, Any]: Enhanced summary
        """
        summary = {
            'title': item.get('title', 'Untitled'),
            'type': item.get('type', 'unknown'),
            'word_count': len(item.get('content', '').split()),
            'key_points': self._extract_key_points(item),
            'technical_concepts': self._extract_concepts(item),
            'github_repos': len(item.get('github_repositories', [])),
            'api_references': len(item.get('api_references', [])),
            'related_tutorials': len(item.get('related_tutorials', [])),
            'dependencies': len(item.get('dependencies', [])),
            'enhanced_at': datetime.now().isoformat()
        }

        return summary

    def _extract_key_points(self, item: Dict[str, Any]) -> List[str]:
        """
        Extract key points from a content item

        Args:
            item (Dict[str, Any]): Content item

        Returns:
            List[str]: Key points
        """
        content = item.get('content', '')
        lines = content.split('\n')

        # Look for bullet points, numbered lists, and heading-like content
        key_points = []

        for line in lines:
            line = line.strip()
            if (line.startswith(('-', '*', '•', '1.', '2.', '3.')) or
                (len(line) > 10 and line.endswith(('.', '!', '?')) and
                 any(word.isupper() for word in line.split()[:3]))):
                key_points.append(line[:100])  # Limit length
                if len(key_points) >= 5:  # Limit to 5 key points
                    break

        return key_points

def main():
    """Example usage of ContentEnhancer"""
    # Example usage
    enhancer = ContentEnhancer()

    # Sample content items
    sample_articles = [
        {
            'id': 'article_1',
            'title': 'Introduction to Python Programming',
            'content': 'Python is a versatile programming language. It is used for web development, data science, and automation.',
            'type': 'article'
        },
        {
            'id': 'article_2',
            'title': 'Getting Started with React',
            'content': 'React is a JavaScript library for building user interfaces. It uses components and virtual DOM.',
            'type': 'article'
        }
    ]

    # Sample metadata sources
    sample_metadata = {
        'github_repos': [
            {
                'full_name': 'python/cpython',
                'url': 'https://github.com/python/cpython',
                'description': 'The Python programming language',
                'stars': 45000,
                'language': 'python',
                'topics': ['python', 'interpreter', 'programming-language']
            },
            {
                'full_name': 'facebook/react',
                'url': 'https://github.com/facebook/react',
                'description': 'A declarative, efficient, and flexible JavaScript library for building user interfaces.',
                'stars': 180000,
                'language': 'javascript',
                'topics': ['javascript', 'react', 'frontend', 'ui']
            }
        ],
        'api_references': [
            {
                'type': 'api_reference',
                'content': 'def print(message): ...',
                'url': 'https://docs.python.org/3/library/functions.html#print',
                'language': 'python',
                'context': 'Python built-in functions'
            }
        ],
        'tutorials': [
            {
                'title': 'Python Tutorial for Beginners',
                'url': 'https://example.com/python-tutorial',
                'content': 'Learn Python from scratch with this comprehensive tutorial.',
                'word_count': 2500,
                'code_snippets': 15
            }
        ],
        'dependencies': [
            {
                'name': 'requests',
                'version': '2.25.1',
                'package_manager': 'pip'
            }
        ]
    }

    # Enhance content with metadata
    enhanced_articles = enhancer.enhance_content_with_metadata(sample_articles, sample_metadata)
    print(f"Enhanced {len(enhanced_articles)} articles with metadata")

    # Link articles to GitHub repositories
    linked_articles = enhancer.link_articles_to_github(sample_articles, sample_metadata['github_repos'])
    print(f"Linked {len(linked_articles)} articles to GitHub repositories")

    # Create cross-reference system
    cross_ref_system = enhancer.create_cross_reference_system(enhanced_articles)
    print(f"Created cross-reference system with {len(cross_ref_system['concepts'])} concepts")

    # Build searchable index
    search_index = enhancer.build_searchable_index(enhanced_articles)
    print(f"Built searchable index with {len(search_index['keywords'])} keywords")

    # Generate enhanced summaries
    summarized_articles = enhancer.generate_enhanced_summaries(enhanced_articles)
    print(f"Generated enhanced summaries for {len(summarized_articles)} articles")

    print("Content enhancement demo completed successfully!")

if __name__ == "__main__":
    main()