#!/usr/bin/env python3
"""
Clarification Workflow System

Analyzes user input, extracts intent, identifies entities, and determines if clarification is needed.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re

class IntentType(Enum):
    """Types of user intents"""
    OPTIMIZATION = "optimization"
    IMPLEMENTATION = "implementation"
    ANALYSIS = "analysis"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    GENERAL = "general"

@dataclass
class CleanedInput:
    """Processed and analyzed user input"""
    original_text: str
    cleaned_text: str
    extracted_intent: IntentType
    confidence: float
    key_entities: List[str]
    identified_problems: List[str]
    suggested_actions: List[str]

class ClarificationSession:
    """Manages a clarification workflow session"""

    def __init__(self, original_input: str):
        self.original_input = original_input
        self.cleaned_input = None
        self.clarification_questions = []
        self.is_complete = False

    async def process_input(self) -> CleanedInput:
        """Process and analyze the user input"""
        # Clean the input
        cleaned_text = self._clean_text(self.original_input)

        # Extract intent
        intent, confidence = self._extract_intent(cleaned_text)

        # Identify entities
        entities = self._extract_entities(cleaned_text)

        # Identify problems
        problems = self._identify_problems(cleaned_text)

        # Suggest actions
        actions = self._suggest_actions(intent, entities, problems)

        self.cleaned_input = CleanedInput(
            original_text=self.original_input,
            cleaned_text=cleaned_text,
            extracted_intent=intent,
            confidence=confidence,
            key_entities=entities,
            identified_problems=problems,
            suggested_actions=actions
        )

        return self.cleaned_input

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove common conversational filler
        filler_phrases = [
            r"hey can you\s+",
            r"could you please\s+",
            r"i was wondering if you could\s+",
            r"i need to\s+",
            r"i want to\s+",
            r"help me\s+",
            r"can you\s+"
        ]

        for phrase in filler_phrases:
            text = re.sub(phrase, '', text, flags=re.IGNORECASE)

        return text.strip()

    def _extract_intent(self, text: str) -> tuple[IntentType, float]:
        """Extract the primary intent and confidence score"""
        text_lower = text.lower()

        # Keyword patterns for different intents
        intent_patterns = {
            IntentType.OPTIMIZATION: [
                r'optimize?', r'performance', r'speed', r'faster', r'slower',
                r'efficient', r'improve', r'better', r'reduce', r'increase'
            ],
            IntentType.IMPLEMENTATION: [
                r'implement', r'create', r'build', r'develop', r'write',
                r'code', r'script', r'function', r'class', r'add'
            ],
            IntentType.ANALYSIS: [
                r'analyz', r'examine', r'review', r'check', r'what', r'why',
                r'how does', r'compare', r'difference', r'issue'
            ],
            IntentType.DOCUMENTATION: [
                r'document', r'readme', r'guide', r'manual', r'explain',
                r'describe', r'what is', r'how to'
            ],
            IntentType.DEBUGGING: [
                r'bug', r'error', r'fix', r'debug', r'broken', r'not working',
                r'issue', r'problem', r'wrong', r'fail'
            ]
        }

        # Score each intent
        intent_scores = {}
        for intent, patterns in intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            intent_scores[intent] = score

        # Find the best intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            max_score = intent_scores[best_intent]

            # Calculate confidence based on score and text length
            confidence = min(max_score / max(len(text.split()), 1), 1.0)

            # If no strong signals, default to general
            if max_score == 0:
                return IntentType.GENERAL, 0.5

            return best_intent, confidence

        return IntentType.GENERAL, 0.5

    def _extract_entities(self, text: str) -> List[str]:
        """Extract key entities from text"""
        entities = []

        # Look for technical terms (camelCase, snake_case, etc.)
        technical_terms = re.findall(r'\b[A-Za-z][A-Za-z0-9_]*[A-Za-z0-9]\b', text)
        entities.extend([term for term in technical_terms if len(term) > 2])

        # Look for file paths
        file_paths = re.findall(r'\b(?:\./|/)?[A-Za-z0-9_\-./]+\.[A-Za-z]{2,}\b', text)
        entities.extend(file_paths)

        # Look for numbers that might be versions, sizes, etc.
        numbers = re.findall(r'\b\d+(?:\.\d+)?\s*(?:KB|MB|GB|v\d+\.?\d*)?\b', text)
        entities.extend(numbers)

        # Remove duplicates and return
        return list(set(entities))

    def _identify_problems(self, text: str) -> List[str]:
        """Identify potential problems mentioned"""
        problems = []

        # Common problem indicators
        problem_indicators = [
            r'(?:not|no|n\'t)\s+working',
            r'error|bug|issue|problem',
            r'(?:too|very)\s+(?:slow|fast|big|small)',
            r'broken|failed|crashed',
            r'doesn\'t|won\'t|can\'t'
        ]

        for pattern in problem_indicators:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                problems.extend(matches)

        return list(set(problems))

    def _suggest_actions(self, intent: IntentType, entities: List[str], problems: List[str]) -> List[str]:
        """Suggest actions based on analysis"""
        actions = []

        if intent == IntentType.OPTIMIZATION:
            actions.append("Analyze current performance")
            actions.append("Identify bottlenecks")
            actions.append("Suggest optimizations")

        elif intent == IntentType.IMPLEMENTATION:
            actions.append("Plan implementation approach")
            actions.append("Identify required components")
            actions.append("Create development steps")

        elif intent == IntentType.ANALYSIS:
            actions.append("Gather relevant data")
            actions.append("Perform analysis")
            actions.append("Provide insights and recommendations")

        elif intent == IntentType.DEBUGGING:
            actions.append("Identify error source")
            actions.append("Debug the issue")
            actions.append("Test the fix")

        return actions

class ClarificationWorkflow:
    """Main clarification workflow system"""

    def __init__(self):
        self.logger = logging.getLogger("clarification_workflow")

    async def start_workflow(self, user_input: str) -> ClarificationSession:
        """Start a new clarification workflow session"""
        session = ClarificationSession(user_input)
        await session.process_input()
        return session

    async def get_clarification_questions(self, session: ClarificationSession) -> List[str]:
        """Generate clarification questions if needed"""
        questions = []

        if session.cleaned_input.confidence < 0.7:
            questions.append("Could you provide more details about what you want to accomplish?")

        if not session.cleaned_input.key_entities:
            questions.append("What specific files, components, or systems are involved?")

        if session.cleaned_input.extracted_intent == IntentType.GENERAL:
            questions.append("Are you looking to implement something new, analyze existing code, or fix an issue?")

        return questions

def get_clarification_workflow() -> ClarificationWorkflow:
    """Factory function to create clarification workflow instance"""
    return ClarificationWorkflow()