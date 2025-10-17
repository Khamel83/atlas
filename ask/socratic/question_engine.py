#!/usr/bin/env python3
"""
Socratic Question Engine

Generates thought-provoking questions based on content analysis to enhance
understanding and promote deeper thinking.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import re

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from helpers.metadata_manager import MetadataManager
    from helpers.config import load_config
except ImportError:
    MetadataManager = None
    load_config = lambda: {}


@dataclass
class SocraticQuestion:
    """Represents a Socratic question generated from content analysis."""
    question: str
    question_type: str  # assumption, evidence, perspective, implication, meta
    complexity_level: str  # basic, intermediate, advanced
    content_source: str
    related_concepts: List[str]
    confidence: float
    generated_at: str

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now().isoformat()


@dataclass
class QuestionContext:
    """Context for question generation."""
    focus_topics: List[str] = None
    question_types: List[str] = None
    complexity_levels: List[str] = None
    max_questions: int = 10
    include_meta_questions: bool = True
    recent_content_only: bool = False

    def __post_init__(self):
        if self.focus_topics is None:
            self.focus_topics = []
        if self.question_types is None:
            self.question_types = ["assumption", "evidence", "perspective", "implication", "meta"]
        if self.complexity_levels is None:
            self.complexity_levels = ["basic", "intermediate", "advanced"]


@dataclass
class ConceptAnalysis:
    """Analysis of concepts extracted from content."""
    concepts: Dict[str, int]  # concept -> frequency
    relationships: List[Tuple[str, str, str]]  # (concept1, concept2, relationship_type)
    emerging_themes: List[str]
    contradictions: List[Tuple[str, str]]  # conflicting concepts
    gaps: List[str]  # areas needing exploration


class QuestionEngine:
    """
    Socratic question engine for Atlas.

    Analyzes content to generate thought-provoking questions that:
    - Challenge assumptions
    - Explore implications
    - Examine evidence
    - Consider alternative perspectives
    - Promote meta-cognitive thinking
    """

    def __init__(self, metadata_manager=None, config: Dict[str, Any] = None):
        """Initialize QuestionEngine."""
        self.config = config or {}
        if not config and load_config:
            self.config = load_config()

        # Support both direct injection and automatic initialization
        if metadata_manager:
            self.metadata_manager = metadata_manager
        else:
            self.metadata_manager = None
            if MetadataManager:
                try:
                    self.metadata_manager = MetadataManager(self.config)
                except Exception:
                    pass

        # Question templates by type
        self.question_templates = {
            "assumption": [
                "What assumptions underlie the claim that {concept}?",
                "How might someone challenge the assumption that {concept}?",
                "What if the opposite of {concept} were true?",
                "What evidence would need to exist to invalidate {concept}?",
                "Why do we assume {concept} is important/valid/true?"
            ],
            "evidence": [
                "What evidence supports the connection between {concept1} and {concept2}?",
                "How reliable is the evidence for {concept}?",
                "What counter-evidence exists for {concept}?",
                "What would stronger evidence for {concept} look like?",
                "How might we test the validity of {concept}?"
            ],
            "perspective": [
                "How might {stakeholder} view {concept} differently?",
                "What are the limitations of viewing {concept} through {lens}?",
                "How does cultural context influence understanding of {concept}?",
                "What perspectives on {concept} are missing from this analysis?",
                "How might future generations view our current understanding of {concept}?"
            ],
            "implication": [
                "If {concept} is true, what does that imply for {domain}?",
                "What are the long-term consequences of {concept}?",
                "How might {concept} change our approach to {related_area}?",
                "What unintended consequences might arise from {concept}?",
                "How does {concept} connect to broader patterns in {field}?"
            ],
            "meta": [
                "How has your understanding of {concept} evolved through this content?",
                "What questions about {concept} remain unanswered?",
                "How might you verify your current understanding of {concept}?",
                "What would you need to learn to better understand {concept}?",
                "How does {concept} challenge your existing worldview?"
            ]
        }

        # Complexity indicators
        self.complexity_indicators = {
            "basic": ["what", "how", "when", "where", "who"],
            "intermediate": ["why", "compare", "analyze", "relationship"],
            "advanced": ["synthesize", "evaluate", "implications", "assumptions", "paradigm"]
        }

    def generate_questions(self, content=None, metadata=None, context: QuestionContext = None) -> List[SocraticQuestion]:
        """
        Generate Socratic questions based on content analysis.

        Args:
            content: Text content for analysis (legacy parameter)
            metadata: Content metadata (legacy parameter)
            context: Question generation context

        Returns:
            List of generated Socratic questions
        """
        if context is None:
            context = QuestionContext()

        # Handle legacy interface
        if content and not self.metadata_manager:
            return self._generate_from_text(content, context)

        if not self.metadata_manager:
            return self._mock_generate_questions(context)

        try:
            # Get content for analysis
            content_items = self._get_content_for_analysis(context)

            # Analyze concepts
            concept_analysis = self._analyze_concepts(content_items)

            # Generate questions by type
            questions = []

            for question_type in context.question_types:
                type_questions = self._generate_questions_by_type(
                    question_type, concept_analysis, context
                )
                questions.extend(type_questions)

            # Filter and rank questions
            questions = self._filter_and_rank_questions(questions, context)

            return questions[:context.max_questions]

        except Exception as e:
            print(f"Error generating questions: {e}")
            return self._mock_generate_questions(context)

    def generate_follow_up_questions(self,
                                   base_question: SocraticQuestion,
                                   max_questions: int = 5) -> List[SocraticQuestion]:
        """Generate follow-up questions based on a base question."""
        follow_ups = []

        # Extract key concepts from base question
        concepts = self._extract_concepts_from_question(base_question.question)

        # Generate deeper questions
        for concept in concepts[:3]:  # Focus on top 3 concepts
            if base_question.question_type == "assumption":
                follow_ups.append(SocraticQuestion(
                    question=f"What would happen if we questioned the fundamental nature of {concept}?",
                    question_type="meta",
                    complexity_level="advanced",
                    content_source=base_question.content_source,
                    related_concepts=[concept],
                    confidence=0.7,
                    generated_at=datetime.now().isoformat()
                ))

            elif base_question.question_type == "evidence":
                follow_ups.append(SocraticQuestion(
                    question=f"How might personal bias influence our interpretation of evidence about {concept}?",
                    question_type="perspective",
                    complexity_level="intermediate",
                    content_source=base_question.content_source,
                    related_concepts=[concept],
                    confidence=0.8,
                    generated_at=datetime.now().isoformat()
                ))

        return follow_ups[:max_questions]

    def analyze_question_patterns(self, questions: List[SocraticQuestion]) -> Dict[str, Any]:
        """Analyze patterns in generated questions."""
        if not questions:
            return {"total": 0, "by_type": {}, "by_complexity": {}, "concepts": []}

        type_counts = Counter(q.question_type for q in questions)
        complexity_counts = Counter(q.complexity_level for q in questions)

        # Extract all concepts
        all_concepts = []
        for q in questions:
            all_concepts.extend(q.related_concepts)
        concept_counts = Counter(all_concepts)

        return {
            "total": len(questions),
            "by_type": dict(type_counts),
            "by_complexity": dict(complexity_counts),
            "top_concepts": dict(concept_counts.most_common(10)),
            "average_confidence": sum(q.confidence for q in questions) / len(questions)
        }

    def generate_reflection_questions(self,
                                    content_metadata=None,
                                    reflection_type="learning") -> List[SocraticQuestion]:
        """Generate questions focused on reflection and metacognition."""
        reflection_templates = {
            "learning": [
                "What was the most surprising insight you gained from this content?",
                "How has this content changed or challenged your previous understanding?",
                "What connections can you make between this content and your own experiences?",
                "What questions do you still have after engaging with this content?",
                "How might you apply what you've learned to a current project or challenge?"
            ],
            "critical_thinking": [
                "What evidence would you need to change your mind about the main argument?",
                "What perspectives or voices might be missing from this discussion?",
                "How might someone with a different worldview interpret this content?",
                "What are the potential unintended consequences of the ideas presented?",
                "How does your emotional response to this content affect your evaluation of it?"
            ],
            "creativity": [
                "How might you combine ideas from this content with concepts from another field?",
                "What new possibilities emerge when you approach the content from a different angle?",
                "How could you reimagine the core concepts in an entirely different context?",
                "What would happen if you inverted a key assumption from this content?",
                "How might this content inspire a creative project or solution?"
            ]
        }

        templates = reflection_templates.get(reflection_type, reflection_templates["learning"])

        questions = []
        for i, template in enumerate(templates):
            questions.append(SocraticQuestion(
                question=template,
                question_type="meta",
                complexity_level="intermediate" if reflection_type == "learning" else "advanced",
                content_source="reflection" if not content_metadata else getattr(content_metadata, 'uid', 'unknown'),
                related_concepts=["reflection", "metacognition", reflection_type],
                confidence=0.8,
                generated_at=datetime.now().isoformat()
            ))

        return questions

    def evaluate_question_quality(self, questions: List[SocraticQuestion]) -> Dict[str, Any]:
        """Evaluate the quality and diversity of generated questions."""
        if not questions:
            return {"total": 0, "quality_score": 0, "diversity_score": 0, "feedback": "No questions to evaluate"}

        # Quality metrics
        avg_confidence = sum(q.confidence for q in questions) / len(questions)

        # Check for question variety (starts with different words)
        question_starts = [q.question.split()[0].lower() for q in questions if q.question.split()]
        unique_starts = len(set(question_starts))
        variety_score = min(1.0, unique_starts / len(questions))

        # Complexity distribution
        complexity_counts = Counter(q.complexity_level for q in questions)
        complexity_balance = len(complexity_counts) / 3  # 3 complexity levels

        # Type distribution
        type_counts = Counter(q.question_type for q in questions)
        type_balance = len(type_counts) / 5  # 5 question types

        # Overall quality score (0-1)
        quality_score = (avg_confidence + variety_score + complexity_balance + type_balance) / 4

        # Diversity feedback
        if len(questions) < 3:
            feedback = "Too few questions to assess diversity"
        elif unique_starts < 3:
            feedback = "Questions could be more varied in structure"
        elif len(complexity_counts) < 2:
            feedback = "Consider generating questions with more complexity levels"
        elif len(type_counts) < 3:
            feedback = "Include more question types for better coverage"
        else:
            feedback = "Good variety of questions across structures, types, and complexity levels"

        return {
            "total": len(questions),
            "quality_score": quality_score,
            "avg_confidence": avg_confidence,
            "diversity_score": (variety_score + complexity_balance + type_balance) / 3,
            "question_variety": unique_starts,
            "complexity_distribution": dict(complexity_counts),
            "type_distribution": dict(type_counts),
            "feedback": feedback
        }

    def get_questions_for_content(self, content_id: str) -> List[SocraticQuestion]:
        """Get questions specifically related to a piece of content."""
        if not self.metadata_manager:
            return []

        try:
            # Find the specific content
            content_item = None
            all_content = self.metadata_manager.list_all_content()

            for item in all_content:
                if getattr(item, 'uid', None) == content_id:
                    content_item = item
                    break

            if not content_item:
                return []

            # Analyze this specific content
            concept_analysis = self._analyze_concepts([content_item])

            # Generate targeted questions
            context = QuestionContext(max_questions=15)
            questions = []

            for question_type in context.question_types:
                type_questions = self._generate_questions_by_type(
                    question_type, concept_analysis, context
                )
                questions.extend(type_questions)

            return self._filter_and_rank_questions(questions, context)

        except Exception as e:
            print(f"Error getting questions for content: {e}")
            return []

    # Legacy methods for backward compatibility
    def generate_progressive_questions(self, metadata, difficulty_level=1):
        """Generate questions with progressive difficulty levels (legacy method)."""
        # Map difficulty levels to complexity
        complexity_map = {
            1: ["basic"],
            2: ["basic", "intermediate"],
            3: ["intermediate"],
            4: ["intermediate", "advanced"],
            5: ["advanced"]
        }

        context = QuestionContext(
            complexity_levels=complexity_map.get(difficulty_level, ["basic"]),
            max_questions=5
        )

        # If single content item, analyze specifically
        if hasattr(metadata, 'uid'):
            return self.get_questions_for_content(metadata.uid)

        return self.generate_questions(context=context)

    def get_question_analytics(self):
        """Get analytics about question generation and user engagement (legacy method)."""
        if not self.metadata_manager:
            return {"error": "No metadata manager available"}

        try:
            all_content = self.metadata_manager.list_all_content()

            questionable_content = 0
            total_tags = 0

            for item in all_content:
                if hasattr(item, 'content_path') and item.content_path:
                    questionable_content += 1
                elif hasattr(item, 'title') and item.title:
                    questionable_content += 1

                if hasattr(item, 'tags'):
                    total_tags += len(item.tags)

            return {
                "total_content_items": len(all_content),
                "questionable_content": questionable_content,
                "average_tags_per_item": total_tags / max(len(all_content), 1),
                "question_generation_coverage": questionable_content / max(len(all_content), 1),
            }
        except Exception as e:
            return {"error": f"Analytics generation failed: {e}"}

    def _get_content_for_analysis(self, context: QuestionContext) -> List[Dict[str, Any]]:
        """Get content items for analysis."""
        if hasattr(self.metadata_manager, 'list_all_content'):
            all_content = self.metadata_manager.list_all_content()
        else:
            all_content = self.metadata_manager.get_all_metadata()

        # Filter by recency if requested
        if context.recent_content_only:
            cutoff_date = datetime.now() - timedelta(days=30)
            filtered_content = []

            for item in all_content:
                try:
                    if hasattr(item, 'created_at'):
                        created_at = item.created_at
                    else:
                        created_at = item.get('created_at', item.get('date', ''))

                    if created_at:
                        content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if content_date >= cutoff_date:
                            filtered_content.append(item)
                except Exception:
                    pass

            return filtered_content

        return all_content

    def _analyze_concepts(self, content_items: List[Dict[str, Any]]) -> ConceptAnalysis:
        """Analyze concepts from content items."""
        concepts = Counter()
        relationships = []
        themes = set()

        for item in content_items:
            # Extract concepts from title
            if hasattr(item, 'title'):
                title = item.title
            else:
                title = item.get('title', '')

            if title:
                title_concepts = self._extract_concepts_from_text(title)
                for concept in title_concepts:
                    concepts[concept] += 2  # Weight titles higher

            # Extract concepts from tags
            if hasattr(item, 'tags'):
                tags = item.tags
            else:
                tags = item.get('tags', [])

            for tag in tags:
                if tag:
                    concepts[tag.lower()] += 1
                    themes.add(tag.lower())

            # Extract concepts from content if available
            if hasattr(item, 'content'):
                content = item.content
            else:
                content = item.get('content', '')

            if content and len(content) > 100:  # Only analyze substantial content
                content_concepts = self._extract_concepts_from_text(content[:1000])  # First 1000 chars
                for concept in content_concepts:
                    concepts[concept] += 1

        # Find relationships between top concepts
        top_concepts = [concept for concept, _ in concepts.most_common(20)]
        for i, concept1 in enumerate(top_concepts):
            for concept2 in top_concepts[i+1:]:
                if self._are_concepts_related(concept1, concept2):
                    relationships.append((concept1, concept2, "related"))

        # Identify emerging themes
        emerging_themes = [theme for theme in themes if concepts[theme] >= 3]

        return ConceptAnalysis(
            concepts=dict(concepts),
            relationships=relationships,
            emerging_themes=list(emerging_themes),
            contradictions=[],  # Would need more sophisticated analysis
            gaps=self._identify_knowledge_gaps(top_concepts)
        )

    def _extract_concepts_from_text(self, text: str) -> List[str]:
        """Extract key concepts from text."""
        if not text:
            return []

        # Simple concept extraction - could be enhanced with NLP
        text = text.lower()

        # Remove common stop words and extract meaningful phrases
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

        # Split into words and filter
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        concepts = [word for word in words if word not in stop_words and len(word) > 3]

        # Return unique concepts
        return list(set(concepts))

    def _extract_concepts_from_question(self, question: str) -> List[str]:
        """Extract concepts from a question."""
        return self._extract_concepts_from_text(question)

    def _are_concepts_related(self, concept1: str, concept2: str) -> bool:
        """Determine if two concepts are related."""
        # Simple relatedness check - could be enhanced with semantic analysis

        # Check for shared roots
        if concept1[:4] == concept2[:4] and len(concept1) > 4:
            return True

        # Check for domain relationships (would need knowledge base)
        tech_terms = {'technology', 'software', 'programming', 'data', 'ai', 'machine', 'learning'}
        business_terms = {'business', 'strategy', 'market', 'company', 'revenue', 'growth'}

        if (concept1 in tech_terms and concept2 in tech_terms) or \
           (concept1 in business_terms and concept2 in business_terms):
            return True

        return False

    def _identify_knowledge_gaps(self, concepts: List[str]) -> List[str]:
        """Identify potential knowledge gaps."""
        gaps = []

        # Look for concepts that might have missing context
        if 'technology' in concepts and 'ethics' not in concepts:
            gaps.append('ethical implications of technology')

        if 'ai' in concepts and 'bias' not in concepts:
            gaps.append('bias in AI systems')

        if 'data' in concepts and 'privacy' not in concepts:
            gaps.append('data privacy considerations')

        return gaps

    def _generate_questions_by_type(self,
                                  question_type: str,
                                  analysis: ConceptAnalysis,
                                  context: QuestionContext) -> List[SocraticQuestion]:
        """Generate questions of a specific type."""
        questions = []
        templates = self.question_templates.get(question_type, [])

        if not templates:
            return questions

        # Get top concepts for question generation
        top_concepts = list(analysis.concepts.keys())[:10]

        for template in templates:
            for concept in top_concepts:
                if context.focus_topics and not any(topic.lower() in concept.lower() for topic in context.focus_topics):
                    continue

                try:
                    # Generate question from template
                    if '{concept}' in template:
                        question_text = template.format(concept=concept)
                    elif '{concept1}' in template and '{concept2}' in template:
                        if len(top_concepts) > 1:
                            concept2 = top_concepts[1] if top_concepts[1] != concept else top_concepts[0]
                            question_text = template.format(concept1=concept, concept2=concept2)
                        else:
                            continue
                    else:
                        question_text = template.format(
                            concept=concept,
                            stakeholder="stakeholders",
                            lens="current framework",
                            domain="this field",
                            related_area="related areas",
                            field="the field"
                        )

                    # Determine complexity level
                    complexity = self._determine_complexity(question_text, template)

                    if complexity not in context.complexity_levels:
                        continue

                    # Calculate confidence based on concept frequency
                    confidence = min(0.9, analysis.concepts.get(concept, 1) / 10)

                    questions.append(SocraticQuestion(
                        question=question_text,
                        question_type=question_type,
                        complexity_level=complexity,
                        content_source="content_analysis",
                        related_concepts=[concept],
                        confidence=confidence,
                        generated_at=datetime.now().isoformat()
                    ))

                except Exception as e:
                    continue

        return questions

    def _determine_complexity(self, question: str, template: str) -> str:
        """Determine the complexity level of a question."""
        question_lower = question.lower()

        # Check for advanced indicators
        advanced_terms = ['assumptions', 'implications', 'paradigm', 'framework', 'worldview']
        if any(term in question_lower for term in advanced_terms):
            return "advanced"

        # Check for intermediate indicators
        intermediate_terms = ['relationship', 'analyze', 'compare', 'evidence', 'perspective']
        if any(term in question_lower for term in intermediate_terms):
            return "intermediate"

        # Default to basic
        return "basic"

    def _filter_and_rank_questions(self,
                                 questions: List[SocraticQuestion],
                                 context: QuestionContext) -> List[SocraticQuestion]:
        """Filter and rank questions by quality and relevance."""
        if not questions:
            return []

        # Remove duplicates
        unique_questions = []
        seen_questions = set()

        for question in questions:
            question_key = question.question.lower().strip()
            if question_key not in seen_questions:
                seen_questions.add(question_key)
                unique_questions.append(question)

        # Sort by confidence and complexity diversity
        def rank_question(q):
            complexity_bonus = {
                "advanced": 0.3,
                "intermediate": 0.2,
                "basic": 0.1
            }
            return q.confidence + complexity_bonus.get(q.complexity_level, 0)

        unique_questions.sort(key=rank_question, reverse=True)

        return unique_questions

    def _generate_from_text(self, content: str, context: QuestionContext) -> List[SocraticQuestion]:
        """Generate questions from raw text (legacy method)."""
        # Simple text-based question generation
        questions = []

        # Extract concepts from text
        concepts = self._extract_concepts_from_text(content)[:5]  # Top 5 concepts

        for concept in concepts:
            questions.append(SocraticQuestion(
                question=f"What assumptions underlie {concept}?",
                question_type="assumption",
                complexity_level="intermediate",
                content_source="text_analysis",
                related_concepts=[concept],
                confidence=0.6,
                generated_at=datetime.now().isoformat()
            ))

        return questions[:context.max_questions]

    def _mock_generate_questions(self, context: QuestionContext) -> List[SocraticQuestion]:
        """Mock question generation when metadata manager unavailable."""
        mock_questions = [
            SocraticQuestion(
                question="What assumptions underlie our current approach to artificial intelligence?",
                question_type="assumption",
                complexity_level="advanced",
                content_source="mock_analysis",
                related_concepts=["artificial intelligence", "assumptions"],
                confidence=0.85,
                generated_at=datetime.now().isoformat()
            ),
            SocraticQuestion(
                question="How might different cultures view the role of technology in society?",
                question_type="perspective",
                complexity_level="intermediate",
                content_source="mock_analysis",
                related_concepts=["technology", "society", "culture"],
                confidence=0.78,
                generated_at=datetime.now().isoformat()
            ),
            SocraticQuestion(
                question="What evidence supports the effectiveness of remote work?",
                question_type="evidence",
                complexity_level="basic",
                content_source="mock_analysis",
                related_concepts=["remote work", "effectiveness"],
                confidence=0.72,
                generated_at=datetime.now().isoformat()
            ),
            SocraticQuestion(
                question="If automation continues to advance, what are the implications for human employment?",
                question_type="implication",
                complexity_level="advanced",
                content_source="mock_analysis",
                related_concepts=["automation", "employment"],
                confidence=0.82,
                generated_at=datetime.now().isoformat()
            ),
            SocraticQuestion(
                question="How has your understanding of sustainability evolved through recent content?",
                question_type="meta",
                complexity_level="intermediate",
                content_source="mock_analysis",
                related_concepts=["sustainability", "learning"],
                confidence=0.75,
                generated_at=datetime.now().isoformat()
            )
        ]

        # Filter by context preferences
        filtered = []
        for question in mock_questions:
            if question.question_type in context.question_types and \
               question.complexity_level in context.complexity_levels:
                filtered.append(question)

        return filtered[:context.max_questions]


if __name__ == "__main__":
    # Example usage
    engine = QuestionEngine()

    # Generate questions
    context = QuestionContext(
        question_types=["assumption", "perspective", "implication"],
        complexity_levels=["intermediate", "advanced"],
        max_questions=8
    )

    questions = engine.generate_questions(context=context)

    print("Generated Socratic Questions:")
    print("=" * 50)

    for i, question in enumerate(questions, 1):
        print(f"\n{i}. {question.question}")
        print(f"   Type: {question.question_type}")
        print(f"   Complexity: {question.complexity_level}")
        print(f"   Concepts: {', '.join(question.related_concepts)}")
        print(f"   Confidence: {question.confidence:.2f}")

    # Analyze patterns
    print(f"\n\nQuestion Analysis:")
    print("=" * 50)
    analysis = engine.analyze_question_patterns(questions)
    print(f"Total questions: {analysis['total']}")
    print(f"By type: {analysis['by_type']}")
    print(f"By complexity: {analysis['by_complexity']}")
    print(f"Average confidence: {analysis['average_confidence']:.2f}")