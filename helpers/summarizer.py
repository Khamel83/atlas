#!/usr/bin/env python3
"""
Content Summarizer - Intelligent content summarization and key extraction
Provides multiple summarization strategies for different content types.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from collections import Counter

from helpers.utils import log_info, log_error
from helpers.ai_cost_manager import get_cost_manager, with_ai_cost_management
from helpers.unified_ai import get_unified_ai


class ContentSummarizer:
    """
    Intelligent content summarizer with multiple strategies.

    Provides various summarization approaches:
    - Extractive summarization (key sentence extraction)
    - Abstractive summarization (when AI available)
    - Key point extraction
    - Topic summarization
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize ContentSummarizer with configuration."""
        self.config = config or {}
        self.max_summary_length = self.config.get('max_summary_length', 500)
        self.min_content_length = self.config.get('min_content_length', 200)

        # Initialize cost manager
        self.cost_manager = get_cost_manager(config)

        # AI fallback strategies for summarization
        self.ai_fallback_strategies = [
            'cache_lookup',
            'simple_extraction',
            'keyword_based',
            'template_based'
        ]

    def summarize(self,
                  content: str,
                  summary_type: str = "auto",
                  target_length: int = None,
                  metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Summarize content using specified strategy.

        Args:
            content: Text content to summarize
            summary_type: Type of summary ("extractive", "key_points", "auto")
            target_length: Target summary length in characters
            metadata: Content metadata for context

        Returns:
            Dict containing summary and analysis
        """
        try:
            if not content or len(content) < self.min_content_length:
                return {
                    "summary": content,
                    "summary_type": "unchanged",
                    "reason": "Content too short to summarize",
                    "original_length": len(content or ""),
                    "summary_length": len(content or "")
                }

            target_length = target_length or self.max_summary_length
            metadata = metadata or {}

            # Choose summarization strategy
            if summary_type == "auto":
                summary_type = self._choose_strategy(content, metadata)

            # Apply summarization
            if summary_type == "extractive":
                summary_result = self._extractive_summarize(content, target_length)
            elif summary_type == "key_points":
                summary_result = self._key_points_summarize(content, target_length)
            elif summary_type == "topic":
                summary_result = self._topic_summarize(content, target_length)
            else:
                summary_result = self._extractive_summarize(content, target_length)

            # Add metadata
            summary_result.update({
                "original_length": len(content),
                "compression_ratio": len(summary_result["summary"]) / len(content),
                "timestamp": datetime.now().isoformat(),
                "summarizer_version": "1.0"
            })

            log_info(f"Content summarized: {len(content)} -> {len(summary_result['summary'])} chars")
            return summary_result

        except Exception as e:
            log_error(f"Error summarizing content: {str(e)}")
            return {
                "summary": content[:target_length] if content else "",
                "summary_type": "truncated",
                "error": str(e),
                "original_length": len(content or ""),
                "summary_length": len(content[:target_length] if content else "")
            }

    def _choose_strategy(self, content: str, metadata: Dict[str, Any]) -> str:
        """Choose the best summarization strategy for content."""
        # Analyze content characteristics
        word_count = len(content.split())
        has_structure = bool(re.search(r'^#+\s|\n\s*[-*]\s|\n\n', content, re.MULTILINE))

        # Choose strategy based on content
        if word_count > 2000 and has_structure:
            return "extractive"
        elif word_count > 1000:
            return "key_points"
        else:
            return "topic"

    def _extractive_summarize(self, content: str, target_length: int) -> Dict[str, Any]:
        """Create extractive summary by selecting key sentences."""
        sentences = self._split_sentences(content)

        if len(sentences) <= 3:
            return {
                "summary": content,
                "summary_type": "extractive",
                "sentences_used": len(sentences),
                "summary_length": len(content)
            }

        # Score sentences
        scored_sentences = self._score_sentences(sentences, content)

        # Select top sentences
        selected_sentences = self._select_sentences(scored_sentences, target_length)

        # Maintain original order
        original_order = []
        for sentence, score in selected_sentences:
            original_index = sentences.index(sentence)
            original_order.append((original_index, sentence))

        original_order.sort(key=lambda x: x[0])
        summary = " ".join([sentence for _, sentence in original_order])

        return {
            "summary": summary,
            "summary_type": "extractive",
            "sentences_used": len(selected_sentences),
            "sentences_available": len(sentences),
            "summary_length": len(summary)
        }

    def _key_points_summarize(self, content: str, target_length: int) -> Dict[str, Any]:
        """Create summary by extracting key points."""
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        key_points = []
        for para in paragraphs:
            # Get first sentence of each substantial paragraph
            sentences = self._split_sentences(para)
            if sentences and len(sentences[0]) > 50:
                key_points.append(sentences[0])

        # If we have too many points, score and select best
        if len(" ".join(key_points)) > target_length:
            scored_points = self._score_sentences(key_points, content)
            selected_points = self._select_sentences(scored_points, target_length)
            key_points = [sentence for sentence, score in selected_points]

        summary = " ".join(key_points)

        return {
            "summary": summary,
            "summary_type": "key_points",
            "points_extracted": len(key_points),
            "paragraphs_processed": len(paragraphs),
            "summary_length": len(summary)
        }

    def _topic_summarize(self, content: str, target_length: int) -> Dict[str, Any]:
        """Create topic-based summary."""
        # Extract key topics and create summary around them
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        word_freq = Counter(words)

        # Get top keywords
        top_keywords = [word for word, freq in word_freq.most_common(10)]

        # Find sentences containing top keywords
        sentences = self._split_sentences(content)
        keyword_sentences = []

        for sentence in sentences:
            sentence_lower = sentence.lower()
            keyword_count = sum(1 for keyword in top_keywords if keyword in sentence_lower)
            if keyword_count >= 2:  # Sentence contains multiple keywords
                keyword_sentences.append((sentence, keyword_count))

        # Sort by keyword density and select
        keyword_sentences.sort(key=lambda x: x[1], reverse=True)

        selected = []
        current_length = 0
        for sentence, count in keyword_sentences:
            if current_length + len(sentence) <= target_length:
                selected.append(sentence)
                current_length += len(sentence)
            else:
                break

        summary = " ".join(selected)

        return {
            "summary": summary,
            "summary_type": "topic",
            "top_keywords": top_keywords[:5],
            "sentences_with_keywords": len(keyword_sentences),
            "summary_length": len(summary)
        }

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        return sentences

    def _score_sentences(self, sentences: List[str], full_content: str) -> List[tuple]:
        """Score sentences for importance."""
        scored = []

        # Get word frequencies from full content
        words = re.findall(r'\b[a-zA-Z]{3,}\b', full_content.lower())
        word_freq = Counter(words)

        for sentence in sentences:
            score = 0
            sentence_words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())

            # Position score (earlier sentences slightly preferred)
            position_score = 1.0 - (sentences.index(sentence) / len(sentences)) * 0.2

            # Word frequency score
            freq_score = sum(word_freq.get(word, 0) for word in sentence_words)

            # Length score (prefer medium-length sentences)
            length = len(sentence)
            if 50 <= length <= 200:
                length_score = 1.0
            elif length < 50:
                length_score = length / 50
            else:
                length_score = 200 / length

            # Numbers/facts score (sentences with numbers often important)
            numbers_score = 1.2 if re.search(r'\d', sentence) else 1.0

            score = position_score + (freq_score / 100) + length_score + numbers_score
            scored.append((sentence, score))

        return sorted(scored, key=lambda x: x[1], reverse=True)

    def _select_sentences(self, scored_sentences: List[tuple], target_length: int) -> List[tuple]:
        """Select sentences up to target length."""
        selected = []
        current_length = 0

        for sentence, score in scored_sentences:
            if current_length + len(sentence) <= target_length:
                selected.append((sentence, score))
                current_length += len(sentence)
            elif current_length == 0:  # First sentence is too long, include it anyway
                selected.append((sentence, score))
                break

        return selected

    def extract_key_phrases(self, content: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases from content."""
        if not content:
            return []

        try:
            # Simple n-gram extraction
            words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())

            # Extract 2-3 word phrases
            phrases = []
            for i in range(len(words) - 1):
                # 2-word phrases
                phrase2 = " ".join(words[i:i+2])
                phrases.append(phrase2)

                # 3-word phrases
                if i < len(words) - 2:
                    phrase3 = " ".join(words[i:i+3])
                    phrases.append(phrase3)

            # Count phrase frequencies
            phrase_freq = Counter(phrases)

            # Filter common phrases and get top ones
            filtered_phrases = []
            stop_phrases = {'of the', 'in the', 'to the', 'for the', 'and the', 'on the'}

            for phrase, freq in phrase_freq.most_common(max_phrases * 2):
                if freq > 1 and phrase not in stop_phrases and len(phrase) > 5:
                    filtered_phrases.append(phrase)
                    if len(filtered_phrases) >= max_phrases:
                        break

            return filtered_phrases

        except Exception as e:
            log_error(f"Error extracting key phrases: {str(e)}")
            return []

    def create_outline(self, content: str) -> Dict[str, Any]:
        """Create content outline."""
        if not content:
            return {"outline": [], "sections": 0}

        try:
            # Look for existing structure
            headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
            if headings:
                return {
                    "outline": headings,
                    "sections": len(headings),
                    "structure_type": "headings"
                }

            # Create outline from paragraphs
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            outline = []

            for para in paragraphs[:10]:  # First 10 paragraphs
                # Get first sentence as section summary
                sentences = self._split_sentences(para)
                if sentences:
                    # Shorten if too long
                    first_sentence = sentences[0]
                    if len(first_sentence) > 100:
                        first_sentence = first_sentence[:97] + "..."
                    outline.append(first_sentence)

            return {
                "outline": outline,
                "sections": len(outline),
                "structure_type": "paragraphs"
            }

        except Exception as e:
            log_error(f"Error creating outline: {str(e)}")
            return {"outline": [], "sections": 0, "error": str(e)}


def summarize_content(content: str, max_length: int = 500) -> str:
    """Convenience function for quick summarization."""
    summarizer = ContentSummarizer()
    result = summarizer.summarize(content, target_length=max_length)
    return result.get("summary", content[:max_length])


def extract_key_points(content: str, max_points: int = 5) -> List[str]:
    """Convenience function for key point extraction."""
    summarizer = ContentSummarizer()
    result = summarizer.summarize(content, summary_type="key_points")

    # Split summary into points
    summary = result.get("summary", "")
    points = [s.strip() for s in summary.split('. ') if s.strip()]
    return points[:max_points]


class Summarizer(ContentSummarizer):
    """
    Enhanced Summarizer with AI cost management and production-grade features.
    Provides backwards compatibility while adding advanced cost control.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Enhanced Summarizer with cost management."""
        super().__init__(config)

        # AI model configuration
        self.ai_enabled = self.config.get('ai_features_enabled', True)
        self.openrouter_api_key = self.config.get('openrouter_api_key', '')
        self.ai_model = self.config.get('ai_model', 'openai/gpt-3.5-turbo')

        log_info(f"Enhanced Summarizer initialized (AI: {'enabled' if self.ai_enabled else 'disabled'})")

    @with_ai_cost_management('summarize', ['simple_extraction', 'keyword_based', 'template_based'])
    def ai_summarize(self, content: str, target_length: int = 300, **kwargs) -> Dict[str, Any]:
        """
        AI-powered summarization with comprehensive cost management.

        Features:
        - Automatic budget checking and enforcement
        - Graceful degradation to non-AI methods
        - Response caching to reduce costs
        - Usage tracking and reporting
        """
        try:
            if not self.ai_enabled or not self.openrouter_api_key:
                log_info("AI summarization disabled, using fallback")
                return self._fallback_summarize(content, target_length)

            # Prepare AI request
            prompt = self._build_summarization_prompt(content, target_length)

            # Make AI request with cost tracking
            response = self._make_ai_request(prompt, content)

            if response.get('success'):
                summary = response.get('summary', '')

                return {
                    'success': True,
                    'summary': summary,
                    'method': 'ai_summarization',
                    'model': self.ai_model,
                    'cost': response.get('cost', 0.0),
                    'tokens_used': response.get('tokens_used', 0),
                    'response_time': response.get('response_time', 0.0),
                    'summary_length': len(summary),
                    'compression_ratio': len(summary) / len(content) if content else 0
                }
            else:
                # AI request failed, but decorator handles fallback
                return response

        except Exception as e:
            log_error(f"Error in AI summarization: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fallback_used': True
            }

    def _build_summarization_prompt(self, content: str, target_length: int) -> str:
        """Build optimized prompt for AI summarization."""
        # Optimize prompt length to reduce tokens
        if len(content) > 8000:  # Truncate very long content
            content = content[:8000] + "..."

        prompt = f"""Summarize the following content in approximately {target_length} characters.
Focus on the main points and key insights. Be concise but comprehensive.

Content:
{content}

Summary:"""

        return prompt

    def _make_ai_request(self, prompt: str, content: str) -> Dict[str, Any]:
        """Make cost-managed AI request."""
        import requests
        import time

        if not self.openrouter_api_key:
            return {'success': False, 'error': 'No API key configured'}

        start_time = time.time()

        try:
            headers = {
                'Authorization': f'Bearer {self.openrouter_api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://atlas-local',
                'X-Title': 'Atlas Content Summarizer'
            }

            data = {
                'model': self.ai_model,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': min(500, len(content) // 10),  # Reasonable token limit
                'temperature': 0.3  # Lower temperature for consistent summaries
            }

            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=self.config.get('ai_timeout', 30)
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()

                # Extract summary
                if 'choices' in result and result['choices']:
                    summary = result['choices'][0]['message']['content'].strip()

                    # Calculate costs (approximate)
                    usage = result.get('usage', {})
                    total_tokens = usage.get('total_tokens', 0)
                    estimated_cost = (total_tokens / 1000) * 0.001  # Rough estimate

                    return {
                        'success': True,
                        'summary': summary,
                        'tokens_used': total_tokens,
                        'cost': estimated_cost,
                        'response_time': response_time,
                        'metadata': {
                            'model': self.ai_model,
                            'usage': usage
                        }
                    }
                else:
                    return {'success': False, 'error': 'No content in AI response'}

            elif response.status_code == 429:
                # Rate limited
                return {
                    'success': False,
                    'error': 'Rate limited',
                    'retry_after': response.headers.get('retry-after', 60)
                }

            else:
                return {
                    'success': False,
                    'error': f'AI API error: {response.status_code}',
                    'response_time': response_time
                }

        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'AI request timeout'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'AI request failed: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Unexpected AI error: {str(e)}'}

    def _fallback_summarize(self, content: str, target_length: int) -> Dict[str, Any]:
        """Fallback summarization without AI."""
        try:
            # Use the parent class extractive summarization
            result = self.extractive_summarize(content, target_length)

            return {
                'success': True,
                'summary': result.get('summary', ''),
                'method': 'extractive_fallback',
                'summary_length': len(result.get('summary', '')),
                'fallback_used': True,
                'ai_skipped': True
            }

        except Exception as e:
            # Final fallback - simple truncation
            simple_summary = content[:target_length] + '...' if len(content) > target_length else content

            return {
                'success': True,
                'summary': simple_summary,
                'method': 'simple_truncation',
                'summary_length': len(simple_summary),
                'fallback_used': True,
                'ai_skipped': True
            }

    def get_cost_report(self) -> Dict[str, Any]:
        """Get AI cost usage report."""
        return self.cost_manager.get_cost_report()

    def summarize(self, content: str, summary_type: str = "auto", target_length: int = None, **kwargs) -> Dict[str, Any]:
        """
        Enhanced summarize method with AI cost management.

        Automatically chooses between AI and non-AI methods based on:
        - Budget availability
        - Content complexity
        - User preferences
        """
        target_length = target_length or self.max_summary_length

        try:
            # Check if AI summarization is appropriate
            if (summary_type in ['ai', 'auto'] and
                self.ai_enabled and
                len(content) > self.min_content_length):

                # Try AI summarization with cost management
                ai_result = self.ai_summarize(content, target_length, **kwargs)

                if ai_result.get('success'):
                    return ai_result

                log_info("AI summarization failed or blocked, using fallback")

            # Use parent class methods for non-AI summarization
            if summary_type == "extractive" or summary_type == "auto":
                return self.extractive_summarize(content, target_length)
            elif summary_type == "key_points":
                return self.key_points_summarize(content, target_length)
            elif summary_type == "topic":
                return self.topic_summarize(content, target_length)
            else:
                # Default to extractive
                return self.extractive_summarize(content, target_length)

        except Exception as e:
            log_error(f"Error in enhanced summarization: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'summary': content[:target_length] + '...' if len(content) > target_length else content
            }


class UnifiedSummarizer:
    """
    Next-generation summarizer using the Unified AI System.

    Features:
    - Intelligent 3-tier model routing (Llama → Qwen → Gemini)
    - Automatic cost management and budget enforcement
    - Graceful degradation with multiple fallback strategies
    - Comprehensive analytics and monitoring
    - Backwards compatibility with existing interfaces
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize unified summarizer."""
        self.config = config or {}
        self.ai_system = get_unified_ai(config)

        # Compatibility settings
        self.max_summary_length = self.config.get('max_summary_length', 500)
        self.min_content_length = self.config.get('min_content_length', 200)

        log_info("Unified Summarizer initialized with intelligent AI routing")

    def summarize(self,
                  content: str,
                  summary_type: str = "auto",
                  target_length: int = None,
                  metadata: Dict[str, Any] = None,
                  priority: str = "normal",
                  **kwargs) -> Dict[str, Any]:
        """
        Advanced summarization with unified AI system.

        Args:
            content: Text content to summarize
            summary_type: "auto", "ai", "extractive", "key_points", "topic"
            target_length: Target summary length
            metadata: Content metadata for context
            priority: Task priority (low, normal, high)
            **kwargs: Additional parameters

        Returns:
            Dict with comprehensive summarization results
        """
        target_length = target_length or self.max_summary_length
        metadata = metadata or {}

        try:
            # Check content length requirements
            if len(content) < self.min_content_length:
                log_info("Content too short for AI summarization, using simple truncation")
                return {
                    'success': True,
                    'summary': content,
                    'method': 'no_summarization_needed',
                    'summary_length': len(content),
                    'content_length': len(content)
                }

            # Try unified AI system for "auto" or "ai" types
            if summary_type in ["auto", "ai"]:
                log_info(f"Using unified AI system for {summary_type} summarization")

                ai_result = self.ai_system.summarize(
                    content=content,
                    target_length=target_length,
                    priority=priority,
                    **kwargs
                )

                if ai_result.success:
                    return {
                        'success': True,
                        'summary': ai_result.content,
                        'method': 'unified_ai',
                        'model_used': ai_result.model_used,
                        'cost_usd': ai_result.cost_usd,
                        'tokens_used': ai_result.tokens_used,
                        'response_time': ai_result.response_time,
                        'summary_length': len(ai_result.content),
                        'content_length': len(content),
                        'compression_ratio': len(ai_result.content) / len(content),
                        'routing_decision': ai_result.routing_decision,
                        'fallback_used': ai_result.fallback_used,
                        'budget_status': ai_result.budget_status,
                        'ai_metadata': ai_result.metadata,
                        'warnings': ai_result.warnings
                    }
                else:
                    log_info(f"AI summarization failed: {ai_result.error}, trying fallback")
                    # Continue to fallback methods below

            # Fallback to traditional methods
            log_info(f"Using traditional {summary_type} summarization")

            # Use parent class methods via ContentSummarizer
            from helpers.summarizer import ContentSummarizer
            traditional_summarizer = ContentSummarizer(self.config)

            if summary_type == "extractive" or summary_type == "auto":
                result = traditional_summarizer.extractive_summarize(content, target_length)
            elif summary_type == "key_points":
                result = traditional_summarizer.key_points_summarize(content, target_length)
            elif summary_type == "topic":
                result = traditional_summarizer.topic_summarize(content, target_length)
            else:
                # Default fallback
                result = traditional_summarizer.extractive_summarize(content, target_length)

            # Enhance result with unified system metadata
            result.update({
                'method': f'traditional_{summary_type}',
                'content_length': len(content),
                'compression_ratio': len(result.get('summary', '')) / len(content),
                'ai_attempted': summary_type in ["auto", "ai"],
                'fallback_used': True
            })

            return result

        except Exception as e:
            log_error(f"Unified summarization failed: {str(e)}")

            # Emergency fallback
            emergency_summary = content[:target_length] + '...' if len(content) > target_length else content

            return {
                'success': True,
                'summary': emergency_summary,
                'method': 'emergency_fallback',
                'summary_length': len(emergency_summary),
                'content_length': len(content),
                'error': str(e),
                'fallback_used': True
            }

    def batch_summarize(self,
                       content_list: List[Dict[str, Any]],
                       target_length: int = None,
                       priority: str = "normal",
                       **kwargs) -> List[Dict[str, Any]]:
        """
        Batch summarization with cost optimization.

        Args:
            content_list: List of dicts with 'content' and optional metadata
            target_length: Target summary length
            priority: Batch priority
            **kwargs: Additional parameters

        Returns:
            List of summarization results
        """
        target_length = target_length or self.max_summary_length
        results = []

        log_info(f"Starting batch summarization of {len(content_list)} items")

        # Get current budget status
        system_status = self.ai_system.get_system_status()
        budget_available = system_status.get('cost_management', {}).get('budget_status', {}).get('daily_remaining', 0)

        # Prioritize items if budget is limited
        if budget_available < 1.0:  # Less than $1 remaining
            log_info(f"Limited budget (${budget_available:.2f}), prioritizing shorter content")
            content_list = sorted(content_list, key=lambda x: len(x.get('content', '')))

        for i, item in enumerate(content_list):
            try:
                content = item.get('content', '')
                item_metadata = item.get('metadata', {})

                log_info(f"Processing item {i+1}/{len(content_list)}")

                result = self.summarize(
                    content=content,
                    target_length=target_length,
                    metadata=item_metadata,
                    priority=priority,
                    **kwargs
                )

                # Add batch metadata
                result.update({
                    'batch_index': i,
                    'batch_total': len(content_list),
                    'item_id': item.get('id', f'item_{i}')
                })

                results.append(result)

                # Check if we should continue based on budget
                if result.get('budget_status', {}).get('daily_remaining', 1.0) < 0.1:
                    log_info("Daily budget nearly exhausted, stopping batch processing")

                    # Add remaining items with fallback processing
                    for j in range(i + 1, len(content_list)):
                        remaining_item = content_list[j]
                        remaining_content = remaining_item.get('content', '')

                        fallback_result = {
                            'success': True,
                            'summary': remaining_content[:target_length] + '...' if len(remaining_content) > target_length else remaining_content,
                            'method': 'budget_limited_fallback',
                            'batch_index': j,
                            'batch_total': len(content_list),
                            'item_id': remaining_item.get('id', f'item_{j}'),
                            'budget_limited': True
                        }
                        results.append(fallback_result)

                    break

            except Exception as e:
                log_error(f"Error processing batch item {i}: {str(e)}")

                error_result = {
                    'success': False,
                    'error': str(e),
                    'batch_index': i,
                    'batch_total': len(content_list),
                    'item_id': item.get('id', f'item_{i}')
                }
                results.append(error_result)

        log_info(f"Batch summarization complete: {len(results)} results")

        return results

    def get_summarization_report(self) -> Dict[str, Any]:
        """Get comprehensive summarization system report."""
        try:
            system_status = self.ai_system.get_system_status()

            return {
                'timestamp': datetime.now().isoformat(),
                'system_type': 'unified_summarizer',
                'ai_system_status': system_status,
                'capabilities': {
                    'ai_summarization': True,
                    'traditional_fallbacks': True,
                    'batch_processing': True,
                    'cost_management': True,
                    'intelligent_routing': True
                },
                'configuration': {
                    'max_summary_length': self.max_summary_length,
                    'min_content_length': self.min_content_length
                }
            }

        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Enhanced convenience functions with unified AI
def unified_summarize_content(content: str, max_length: int = 500, priority: str = "normal") -> str:
    """Convenience function using unified AI system."""
    unified_summarizer = UnifiedSummarizer()
    result = unified_summarizer.summarize(content, target_length=max_length, priority=priority)
    return result.get("summary", content[:max_length])


def smart_extract_key_points(content: str, max_points: int = 5, use_ai: bool = True) -> List[str]:
    """Smart key point extraction with AI enhancement."""
    if use_ai:
        # Try AI-powered extraction
        unified_ai = get_unified_ai()

        schema = {
            "type": "object",
            "properties": {
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": max_points
                }
            },
            "required": ["key_points"]
        }

        try:
            result = unified_ai.extract_json(
                content=content,
                schema=schema,
                extraction_prompt=f"Extract the {max_points} most important key points from this content"
            )

            if result.success:
                extracted_data = json.loads(result.content)
                return extracted_data.get("key_points", [])

        except Exception as e:
            log_error(f"AI key point extraction failed: {str(e)}")

    # Fallback to traditional method
    return extract_key_points(content, max_points)