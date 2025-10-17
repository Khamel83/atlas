#!/usr/bin/env python3
"""
Topic Discovery for Atlas

This module implements topic-based source discovery, finding new content sources
based on user's existing content and reading patterns.
"""

import re
from typing import List, Dict, Any, Set
from collections import defaultdict
import json


class TopicDiscovery:
    \"\"\"Topic-based source discovery system\"\"\"

    def __init__(self):
        \"\"\"Initialize the topic discovery system\"\"\"
        # Common technology domains and their associated sources
        self.domain_sources = {
            'python': [
                'https://realpython.com',
                'https://python.org',
                'https://pypi.org',
                'https://docs.python.org',
                'https://github.com/python',
                'https://stackoverflow.com/questions/tagged/python'
            ],
            'javascript': [
                'https://javascript.info',
                'https://developer.mozilla.org/en-US/docs/Web/JavaScript',
                'https://nodejs.org',
                'https://npmjs.com',
                'https://github.com/topics/javascript',
                'https://stackoverflow.com/questions/tagged/javascript'
            ],
            'machine-learning': [
                'https://arxiv.org',
                'https://paperswithcode.com',
                'https://distill.pub',
                'https://openai.com/research',
                'https://deepmind.com/research',
                'https://ai.googleblog.com'
            ],
            'data-science': [
                'https://kaggle.com',
                'https://towardsdatascience.com',
                'https://analyticsvidhya.com',
                'https://datacamp.com',
                'https://kdnuggets.com',
                'https://oreilly.com/topics/data-science'
            ],
            'web-development': [
                'https://css-tricks.com',
                'https://smashingmagazine.com',
                'https://web.dev',
                'https://developer.mozilla.org',
                'https://github.com/topics/web',
                'https://dev.to'
            ],
            'devops': [
                'https://devops.com',
                'https://github.com/topics/devops',
                'https://docker.com',
                'https://kubernetes.io',
                'https://cloud.google.com/blog/products/devops-sre',
                'https://aws.amazon.com/blogs/devops'
            ],
            'cybersecurity': [
                'https://krebsonsecurity.com',
                'https://schneier.com',
                'https://owasp.org',
                'https://nvd.nist.gov',
                'https://github.com/topics/security',
                'https://security.googleblog.com'
            ],
            'mobile-development': [
                'https://developer.android.com',
                'https://developer.apple.com/documentation',
                'https://reactnative.dev',
                'https://flutter.dev',
                'https://github.com/topics/mobile',
                'https://stackoverflow.com/questions/tagged/mobile'
            ]
        }

        # RSS/Atom feed patterns
        self.feed_patterns = [
            r'https?://[^/]+/feed',
            r'https?://[^/]+/rss',
            r'https?://[^/]+/atom.xml',
            r'https?://[^/]+/feed.xml',
            r'https?://[^/]+/rss.xml'
        ]

    def build_user_profile(self, existing_content_metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
        \"\"\"
        Build user interest profile from existing content metadata

        Args:
            existing_content_metadata (List[Dict[str, Any]]): User's existing content metadata

        Returns:
            Dict[str, Any]: User interest profile
        \"\"\"
        print(\"Building user interest profile...\")

        # Extract topics from tags and content types
        topic_counts = defaultdict(int)
        source_domains = set()
        content_types = defaultdict(int)

        for metadata in existing_content_metadata:
            # Count tags as topics
            if 'tags' in metadata:
                for tag in metadata['tags']:
                    topic_counts[tag.lower()] += 1

            # Extract domain from source URLs
            if 'source_url' in metadata:
                domain = self._extract_domain(metadata['source_url'])
                source_domains.add(domain)

                # Map domains to topics
                domain_topic = self._domain_to_topic(domain)
                if domain_topic:
                    topic_counts[domain_topic] += 1

            # Count content types
            if 'content_type' in metadata:
                content_types[metadata['content_type']] += 1

        # Normalize topic scores
        total_topics = sum(topic_counts.values())
        topic_scores = {topic: count/total_topics for topic, count in topic_counts.items()}

        profile = {
            'topics': topic_scores,
            'source_domains': list(source_domains),
            'content_types': dict(content_types),
            'top_topics': sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        }

        print(f\"User profile built with {len(topic_scores)} topics\")
        return profile

    def discover_sources_by_topic(self, user_profile: Dict[str, Any], max_sources: int = 20) -> List[Dict[str, Any]]:
        \"\"\"
        Discover new sources based on user's topic profile

        Args:
            user_profile (Dict[str, Any]): User's interest profile
            max_sources (int): Maximum number of sources to return

        Returns:
            List[Dict[str, Any]]: Discovered sources
        \"\"\"
        print(\"Discovering sources by topic...\")

        sources = []
        topic_sources = defaultdict(list)

        # Get user's top topics
        top_topics = [topic for topic, _ in user_profile['top_topics']]

        # Find sources for each topic
        for topic in top_topics:
            # Direct topic matches
            if topic in self.domain_sources:
                for source_url in self.domain_sources[topic]:
                    topic_sources[topic].append({
                        'url': source_url,
                        'type': 'direct',
                        'confidence': 0.9,
                        'topic': topic
                    })

            # Partial matches
            for domain_topic, domain_sources in self.domain_sources.items():
                if topic in domain_topic or domain_topic in topic:
                    for source_url in domain_sources:
                        topic_sources[topic].append({
                            'url': source_url,
                            'type': 'related',
                            'confidence': 0.7,
                            'topic': domain_topic
                        })

        # Collect and deduplicate sources
        seen_urls = set()
        for topic, topic_source_list in topic_sources.items():
            for source in topic_source_list:
                if source['url'] not in seen_urls:
                    seen_urls.add(source['url'])
                    sources.append(source)

        # Sort by confidence and limit
        sources.sort(key=lambda x: x['confidence'], reverse=True)
        sources = sources[:max_sources]

        print(f\"Discovered {len(sources)} sources by topic\")
        return sources

    def discover_rss_feeds(self, websites: List[str]) -> List[Dict[str, Any]]:
        \"\"\"
        Discover RSS/Atom feeds from websites

        Args:
            websites (List[str]): List of website URLs

        Returns:
            List[Dict[str, Any]]: Discovered RSS/Atom feeds
        \"\"\"
        print(\"Discovering RSS/Atom feeds...\")

        feeds = []

        for website in websites:
            # Generate potential feed URLs
            domain = self._extract_domain(website)
            if not domain:
                continue

            # Try common feed URL patterns
            for pattern in self.feed_patterns:
                feed_url = pattern.replace('[^/]+', domain)
                feeds.append({
                    'url': feed_url,
                    'source_website': website,
                    'type': 'rss_feed',
                    'confidence': 0.8
                })

        print(f\"Discovered {len(feeds)} potential RSS/Atom feeds\")
        return feeds

    def discover_social_sources(self, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        \"\"\"
        Discover social media sources based on user interests

        Args:
            user_profile (Dict[str, Any]): User's interest profile

        Returns:
            List[Dict[str, Any]]: Discovered social sources
        \"\"\"
        print(\"Discovering social media sources...\")

        social_sources = []
        top_topics = [topic for topic, _ in user_profile['top_topics']][:5]  # Top 5 topics

        # Twitter/X sources
        for topic in top_topics:
            social_sources.append({
                'url': f'https://twitter.com/search?q={topic.replace(\" \", \"%20\")}',
                'platform': 'twitter',
                'type': 'social_search',
                'topic': topic,
                'confidence': 0.7
            })

            # Topic-specific Twitter accounts
            if topic in ['python', 'javascript', 'machine-learning']:
                social_sources.append({
                    'url': f'https://twitter.com/i/lists/{topic}-developers',
                    'platform': 'twitter',
                    'type': 'social_list',
                    'topic': topic,
                    'confidence': 0.8
                })

        # Reddit sources
        for topic in top_topics:
            # Direct subreddit
            subreddit = topic.replace(' ', '').replace('-', '')
            social_sources.append({
                'url': f'https://reddit.com/r/{subreddit}',
                'platform': 'reddit',
                'type': 'subreddit',
                'topic': topic,
                'confidence': 0.8
            })

            # Related subreddits
            related_subreddits = {
                'python': ['Python', 'learnpython', 'PythonProjects'],
                'javascript': ['javascript', 'webdev', 'ReactJS'],
                'machine-learning': ['MachineLearning', 'datascience', 'artificial'],
                'web-development': ['webdev', 'frontend', 'css'],
                'devops': ['devops', 'sysadmin', 'docker'],
                'cybersecurity': ['cybersecurity', 'netsec', 'privacy'],
                'data-science': ['datascience', 'statistics', 'analytics']
            }

            if topic in related_subreddits:
                for subreddit in related_subreddits[topic]:
                    social_sources.append({
                        'url': f'https://reddit.com/r/{subreddit}',
                        'platform': 'reddit',
                        'type': 'related_subreddit',
                        'topic': topic,
                        'confidence': 0.7
                    })

        print(f\"Discovered {len(social_sources)} social media sources\")
        return social_sources

    def generate_source_recommendations(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"
        Generate comprehensive source recommendations

        Args:
            user_profile (Dict[str, Any]): User's interest profile

        Returns:
            Dict[str, Any]: Source recommendations by category
        \"\"\"
        print(\"Generating source recommendations...\")

        # Get topic-based sources
        topic_sources = self.discover_sources_by_topic(user_profile)

        # Get social sources
        social_sources = self.discover_social_sources(user_profile)

        # Get RSS feeds for top websites
        top_websites = user_profile.get('source_domains', [])[:10]
        rss_feeds = self.discover_rss_feeds(top_websites)

        recommendations = {
            'topic_sources': topic_sources,
            'social_sources': social_sources,
            'rss_feeds': rss_feeds,
            'total_count': len(topic_sources) + len(social_sources) + len(rss_feeds)
        }

        print(f\"Generated {recommendations['total_count']} source recommendations\")
        return recommendations

    def _extract_domain(self, url: str) -> str:
        \"\"\"
        Extract domain from URL

        Args:
            url (str): URL to extract domain from

        Returns:
            str: Extracted domain
        \"\"\"
        import re
        domain_match = re.search(r'https?://([^/]+)', url)
        return domain_match.group(1) if domain_match else ''

    def _domain_to_topic(self, domain: str) -> str:
        \"\"\"
        Map domain to topic

        Args:
            domain (str): Domain name

        Returns:
            str: Mapped topic
        \"\"\"
        domain_mappings = {
            'github.com': 'open-source',
            'stackoverflow.com': 'programming',
            'medium.com': 'technical-writing',
            'towardsdatascience.com': 'data-science',
            'arxiv.org': 'research',
            'kaggle.com': 'data-science',
            'python.org': 'python',
            'javascript.info': 'javascript',
            'reactjs.org': 'javascript',
            'nodejs.org': 'javascript',
            'docker.com': 'devops',
            'kubernetes.io': 'devops',
            'owasp.org': 'cybersecurity',
            'krebsonsecurity.com': 'cybersecurity'
        }

        return domain_mappings.get(domain, '')


def main():
    \"\"\"Example usage of TopicDiscovery\"\"\"
    # Create topic discovery system
    topic_discovery = TopicDiscovery()

    # Sample user content metadata
    sample_metadata = [
        {
            'title': 'Introduction to Python Programming',
            'tags': ['python', 'programming', 'beginner'],
            'source_url': 'https://realpython.com/python-introduction',
            'content_type': 'article'
        },
        {
            'title': 'Advanced JavaScript Concepts',
            'tags': ['javascript', 'web-development', 'advanced'],
            'source_url': 'https://javascript.info',
            'content_type': 'article'
        },
        {
            'title': 'Machine Learning Basics',
            'tags': ['machine-learning', 'ai', 'data-science'],
            'source_url': 'https://towardsdatascience.com/ml-basics',
            'content_type': 'article'
        },
        {
            'title': 'Docker for DevOps',
            'tags': ['devops', 'docker', 'containers'],
            'source_url': 'https://docker.com',
            'content_type': 'article'
        }
    ]

    # Build user profile
    print(\"Building user profile...\")
    user_profile = topic_discovery.build_user_profile(sample_metadata)

    # Display user profile
    print(f\"\\nUser Profile:\")
    print(f\"  Top Topics: {user_profile['top_topics']}\")
    print(f\"  Content Types: {user_profile['content_types']}\")
    print(f\"  Source Domains: {user_profile['source_domains']}\")

    # Generate source recommendations
    print(\"\\nGenerating source recommendations...\")
    recommendations = topic_discovery.generate_source_recommendations(user_profile)

    # Display recommendations
    print(f\"\\nSource Recommendations:\")
    print(f\"  Topic Sources: {len(recommendations['topic_sources'])}\")
    print(f\"  Social Sources: {len(recommendations['social_sources'])}\")
    print(f\"  RSS Feeds: {len(recommendations['rss_feeds'])}\")
    print(f\"  Total: {recommendations['total_count']}\")

    # Show sample topic sources
    if recommendations['topic_sources']:
        print(\"\\nSample Topic Sources:\")
        for source in recommendations['topic_sources'][:5]:
            print(f\"  - {source['url']} (confidence: {source['confidence']}, topic: {source['topic']})\")

    # Show sample social sources
    if recommendations['social_sources']:
        print(\"\\nSample Social Sources:\")
        for source in recommendations['social_sources'][:5]:
            print(f\"  - {source['url']} (platform: {source['platform']}, topic: {source['topic']})\")

    # Show sample RSS feeds
    if recommendations['rss_feeds']:
        print(\"\\nSample RSS Feeds:\")
        for feed in recommendations['rss_feeds'][:5]:
            print(f\"  - {feed['url']} (source: {feed['source_website']})\")


if __name__ == \"__main__\":
    main()