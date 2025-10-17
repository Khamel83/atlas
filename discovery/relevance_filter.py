#!/usr/bin/env python3
"""
Relevance Filter for Atlas

This module filters content based on user interests and relevance scoring
using semantic similarity and personal relevance metrics.
"""

import re
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import math


class RelevanceFilter:
    """Content relevance filtering system"""

    def __init__(self):
        """Initialize the relevance filter"""
        # Semantic similarity thresholds
        self.similarity_thresholds = {
            'highly_relevant': 0.8,
            'relevant': 0.6,
            'somewhat_relevant': 0.4,
            'low_relevance': 0.2
        }

        # Temporal relevance decay parameters
        self.temporal_decay = {
            'evergreen_halflife': 365,  # days
            'timely_halflife': 30,      # days
            'breaking_halflife': 1      # days
        }

    def build_user_interest_profile(self, user_content_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build user interest profile from content history

        Args:
            user_content_history (List[Dict[str, Any]]): User's content consumption history

        Returns:
            Dict[str, Any]: User interest profile
        """
        print("Building user interest profile...")

        # Extract topics, tags, and content types
        topic_counts = defaultdict(int)
        tag_counts = defaultdict(int)
        content_type_counts = defaultdict(int)
        source_domains = defaultdict(int)

        for item in user_content_history:
            # Count topics (from title and content)
            title = item.get('title', '').lower()
            content = item.get('content', '').lower()
            text = title + ' ' + content

            # Extract words as topics (simple approach)
            words = re.findall(r'\b\w{4,}\b', text)  # Words with 4+ characters
            for word in words:
                topic_counts[word] += 1

            # Count tags
            tags = item.get('tags', [])
            for tag in tags:
                tag_counts[tag.lower()] += 1

            # Count content types
            content_type = item.get('content_type', 'unknown')
            content_type_counts[content_type] += 1

            # Count source domains
            source_url = item.get('source_url', '')
            if source_url:
                domain = self._extract_domain(source_url)
                if domain:
                    source_domains[domain] += 1

        # Calculate normalized scores
        total_topics = sum(topic_counts.values())
        total_tags = sum(tag_counts.values())

        topic_scores = {topic: count/total_topics for topic, count in topic_counts.items()}
        tag_scores = {tag: count/total_tags for tag, count in tag_counts.items()}

        # Get top interests
        top_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[:50]
        top_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)[:30]

        profile = {
            'topics': topic_scores,
            'tags': tag_scores,
            'content_types': dict(content_type_counts),
            'source_domains': dict(source_domains),
            'top_topics': top_topics,
            'top_tags': top_tags,
            'profile_created': __import__('time').time()
        }

        print(f"User profile built with {len(top_topics)} topics and {len(top_tags)} tags")
        return profile

    def calculate_semantic_similarity(self, content_text: str, user_profile: Dict[str, Any]) -> float:
        """
        Calculate semantic similarity between content and user interests

        Args:
            content_text (str): Content text to analyze
            user_profile (Dict[str, Any]): User interest profile

        Returns:
            float: Semantic similarity score (0.0 to 1.0)
        """
        content_text = content_text.lower()

        # Get user's top topics and tags
        user_topics = set(topic for topic, _ in user_profile.get('top_topics', []))
        user_tags = set(tag for tag, _ in user_profile.get('top_tags', []))

        if not user_topics and not user_tags:
            return 0.0

        # Extract content topics and tags
        content_words = set(re.findall(r'\b\w{4,}\b', content_text))
        content_topics = content_words.intersection(user_topics)
        content_tags = content_words.intersection(user_tags)

        # Calculate similarity scores
        topic_similarity = len(content_topics) / len(user_topics) if user_topics else 0.0
        tag_similarity = len(content_tags) / len(user_tags) if user_tags else 0.0

        # Weighted combination
        similarity_score = (topic_similarity * 0.7) + (tag_similarity * 0.3)

        return min(similarity_score, 1.0)

    def calculate_temporal_relevance(self, content_timestamp: str,
                                   content_type: str = 'evergreen') -> float:
        """
        Calculate temporal relevance score based on content age

        Args:
            content_timestamp (str): Content creation timestamp
            content_type (str): Type of content (evergreen, timely, breaking)

        Returns:
            float: Temporal relevance score (0.0 to 1.0)
        """
        from datetime import datetime

        # Parse timestamp
        try:
            content_time = datetime.fromisoformat(content_timestamp.replace('Z', '+00:00'))
        except:
            # If parsing fails, assume it's recent
            return 1.0

        # Calculate age in days
        current_time = datetime.now()
        age_days = (current_time - content_time).days

        if age_days < 0:
            age_days = 0

        # Get appropriate half-life
        halflife = self.temporal_decay.get(f'{content_type}_halflife', 365)

        # Calculate decay using exponential decay formula
        # R(t) = R₀ * 2^(-t/T) where T is half-life
        temporal_score = math.pow(2, -age_days / halflife)

        return temporal_score

    def calculate_personal_relevance(self, content_item: Dict[str, Any],
                                   user_profile: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate personal relevance score for content item

        Args:
            content_item (Dict[str, Any]): Content item to score
            user_profile (Dict[str, Any]): User interest profile

        Returns:
            Dict[str, float]: Relevance scores by component
        """
        # Calculate semantic similarity
        content_text = content_item.get('title', '') + ' ' + content_item.get('content', '')
        semantic_score = self.calculate_semantic_similarity(content_text, user_profile)

        # Calculate temporal relevance
        timestamp = content_item.get('timestamp', '')
        content_type = content_item.get('content_type', 'evergreen')
        temporal_score = self.calculate_temporal_relevance(timestamp, content_type)

        # Calculate source relevance (based on user's preferred domains)
        source_url = content_item.get('source_url', '')
        source_score = 0.0
        if source_url:
            domain = self._extract_domain(source_url)
            user_domains = user_profile.get('source_domains', {})
            if user_domains:
                max_domain_count = max(user_domains.values())
                domain_count = user_domains.get(domain, 0)
                source_score = domain_count / max_domain_count if max_domain_count > 0 else 0.0

        # Calculate tag relevance
        content_tags = set(tag.lower() for tag in content_item.get('tags', []))
        user_tags = set(tag for tag, _ in user_profile.get('top_tags', []))
        tag_score = 0.0
        if user_tags:
            common_tags = content_tags.intersection(user_tags)
            tag_score = len(common_tags) / len(user_tags)

        # Calculate overall personal relevance
        personal_score = (
            semantic_score * 0.4 +    # 40% weight
            temporal_score * 0.3 +    # 30% weight
            source_score * 0.2 +      # 20% weight
            tag_score * 0.1           # 10% weight
        )

        return {
            'semantic_similarity': semantic_score,
            'temporal_relevance': temporal_score,
            'source_relevance': source_score,
            'tag_relevance': tag_score,
            'personal_relevance': min(personal_score, 1.0)
        }

    def filter_content_by_relevance(self, content_items: List[Dict[str, Any]],
                                  user_profile: Dict[str, Any],
                                  min_relevance_score: float = 0.3) -> List[Dict[str, Any]]:
        """
        Filter content items by relevance score

        Args:
            content_items (List[Dict[str, Any]]): Content items to filter
            user_profile (Dict[str, Any]): User interest profile
            min_relevance_score (float): Minimum relevance score to include

        Returns:
            List[Dict[str, Any]]: Filtered content items with relevance scores
        """
        print(f"Filtering {len(content_items)} content items by relevance...")

        relevant_content = []

        for item in content_items:
            # Calculate relevance scores
            relevance_scores = self.calculate_personal_relevance(item, user_profile)

            # Check if meets minimum threshold
            if relevance_scores['personal_relevance'] >= min_relevance_score:
                # Add scores to item
                item_with_scores = item.copy()
                item_with_scores.update(relevance_scores)
                relevant_content.append(item_with_scores)

        # Sort by personal relevance (highest first)
        relevant_content.sort(key=lambda x: x['personal_relevance'], reverse=True)

        print(f"Filtered to {len(relevant_content)} relevant content items")
        return relevant_content

    def adapt_filtering_based_on_feedback(self, user_feedback: List[Dict[str, Any]],
                                        current_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt filtering based on user feedback

        Args:
            user_feedback (List[Dict[str, Any]]): User feedback on content
            current_profile (Dict[str, Any]): Current user profile

        Returns:
            Dict[str, Any]: Updated user profile
        """
        # Copy current profile
        updated_profile = current_profile.copy()

        # Process feedback to adjust interests
        for feedback in user_feedback:
            content_item = feedback.get('content', {})
            rating = feedback.get('rating', 0)  # 1-5 scale
            engagement_time = feedback.get('engagement_time', 0)

            if rating >= 4 or engagement_time > 300:  # 5 minutes
                # Positive feedback - boost related interests
                self._boost_interests_from_content(content_item, updated_profile, rating)
            elif rating <= 2 and engagement_time < 60:  # 1 minute
                # Negative feedback - reduce related interests
                self._reduce_interests_from_content(content_item, updated_profile)

        return updated_profile

    def _boost_interests_from_content(self, content_item: Dict[str, Any],
                                    profile: Dict[str, Any], rating: int):
        """
        Boost interests based on positive content feedback

        Args:
            content_item (Dict[str, Any]): Content item with positive feedback
            profile (Dict[str, Any]): User profile to update
            rating (int): Rating (1-5 scale)
        """
        boost_factor = rating / 5.0  # Scale boost by rating

        # Boost tags
        for tag in content_item.get('tags', []):
            tag_lower = tag.lower()
            if tag_lower in profile['tags']:
                profile['tags'][tag_lower] *= (1.0 + 0.1 * boost_factor)

        # Boost topics from title and content
        text = content_item.get('title', '') + ' ' + content_item.get('content', '')
        words = re.findall(r'\b\w{4,}\b', text.lower())
        for word in words:
            if word in profile['topics']:
                profile['topics'][word] *= (1.0 + 0.05 * boost_factor)

    def _reduce_interests_from_content(self, content_item: Dict[str, Any],
                                     profile: Dict[str, Any]):
        """
        Reduce interests based on negative content feedback

        Args:
            content_item (Dict[str, Any]): Content item with negative feedback
            profile (Dict[str, Any]): User profile to update
        """
        reduction_factor = 0.9  # Reduce by 10%

        # Reduce tags
        for tag in content_item.get('tags', []):
            tag_lower = tag.lower()
            if tag_lower in profile['tags']:
                profile['tags'][tag_lower] *= reduction_factor

        # Reduce topics from title and content
        text = content_item.get('title', '') + ' ' + content_item.get('content', '')
        words = re.findall(r'\b\w{4,}\b', text.lower())
        for word in words:
            if word in profile['topics']:
                profile['topics'][word] *= reduction_factor

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL

        Args:
            url (str): URL to extract domain from

        Returns:
            str: Extracted domain
        """
        import re
        domain_match = re.search(r'https?://([^/]+)', url)
        return domain_match.group(1) if domain_match else ''


def main():
    """Example usage of RelevanceFilter"""
    # Create relevance filter
    filter_system = RelevanceFilter()

    # Sample user content history
    user_history = [
        {
            'title': 'Python Programming Basics',
            'content': 'Learn the fundamentals of Python programming language including variables, loops, and functions.',
            'tags': ['python', 'programming', 'beginner'],
            'content_type': 'article',
            'source_url': 'https://realpython.com/python-basics',
            'timestamp': '2023-05-01T10:00:00Z'
        },
        {
            'title': 'Advanced JavaScript Concepts',
            'content': 'Deep dive into advanced JavaScript topics including closures, prototypes, and async programming.',
            'tags': ['javascript', 'web-development', 'advanced'],
            'content_type': 'article',
            'source_url': 'https://javascript.info',
            'timestamp': '2023-05-15T14:00:00Z'
        },
        {
            'title': 'Machine Learning Fundamentals',
            'content': 'Introduction to machine learning algorithms and their applications in data science.',
            'tags': ['machine-learning', 'data-science', 'ai'],
            'content_type': 'article',
            'source_url': 'https://towardsdatascience.com/ml-fundamentals',
            'timestamp': '2023-05-20T09:00:00Z'
        }
    ]

    # Build user profile
    print("Building user interest profile...")
    user_profile = filter_system.build_user_interest_profile(user_history)

    # Display top interests
    print(f"\nTop User Topics:")
    for topic, score in user_profile['top_topics'][:10]:
        print(f"  - {topic}: {score:.3f}")

    print(f"\nTop User Tags:")
    for tag, score in user_profile['top_tags'][:10]:
        print(f"  - {tag}: {score:.3f}")

    # Sample content to filter
    content_to_filter = [
        {
            'title': 'Python Web Development with Django',
            'content': 'Build web applications using Django framework, a high-level Python web framework.',
            'tags': ['python', 'django', 'web-development'],
            'content_type': 'article',
            'source_url': 'https://djangoproject.com',
            'timestamp': '2023-06-01T12:00:00Z'
        },
        {
            'title': 'Introduction to Cooking',
            'content': 'Basic cooking techniques for beginners including boiling, frying, and baking.',
            'tags': ['cooking', 'food', 'beginner'],
            'content_type': 'article',
            'source_url': 'https://cooking.com',
            'timestamp': '2023-06-01T10:00:00Z'
        },
        {
            'title': 'Advanced Machine Learning Algorithms',
            'content': 'Deep dive into neural networks, deep learning, and advanced ML algorithms.',
            'tags': ['machine-learning', 'ai', 'deep-learning'],
            'content_type': 'article',
            'source_url': 'https://arxiv.org',
            'timestamp': '2023-06-01T14:00:00Z'
        }
    ]

    # Filter content by relevance
    print("\n\nFiltering content by relevance...")
    relevant_content = filter_system.filter_content_by_relevance(
        content_to_filter, user_profile, min_relevance_score=0.2
    )

    # Display filtered content
    print(f"\nRelevant Content ({len(relevant_content)} items):")
    for item in relevant_content:
        print(f"  - {item['title']}")
        print(f"    Personal Relevance: {item['personal_relevance']:.3f}")
        print(f"    Semantic Similarity: {item['semantic_similarity']:.3f}")
        print(f"    Temporal Relevance: {item['temporal_relevance']:.3f}")
        print()

    # Test temporal relevance
    print("Testing temporal relevance...")
    temporal_scores = []
    for i in range(0, 365, 30):  # Test every 30 days for a year
        timestamp = f'2023-01-01T12:00:00Z'  # Placeholder - would need to adjust for real dates
        score = filter_system.calculate_temporal_relevance(timestamp, 'evergreen')
        temporal_scores.append((i, score))

    print(f"\nTemporal Relevance Decay (Evergreen content):")
    for days, score in temporal_scores[:5]:  # Show first 5
        print(f"  After {days} days: {score:.3f}")


if __name__ == "__main__":
    main()