#!/usr/bin/env python3
"""
Clarification Workflow System

Implements structured workflow: input cleaning → clarifying questions →
detailed planning → execution confirmation → automated documentation
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import logging
from enum import Enum
import re


class WorkflowStage(Enum):
    """Workflow stages"""
    INPUT_CLEANING = "input_cleaning"
    CLARIFICATION = "clarification"
    PLANNING = "planning"
    CONFIRMATION = "confirmation"
    EXECUTION = "execution"
    DOCUMENTATION = "documentation"
    COMPLETED = "completed"


class QuestionType(Enum):
    """Types of clarification questions"""
    CHOICE = "choice"           # Multiple choice
    CONFIRMATION = "confirmation"  # Yes/No confirmation
    CLARIFICATION = "clarification"  # Open-ended clarification
    SPECIFICATION = "specification"  # Technical specification


@dataclass
class CleanedInput:
    """Cleaned and structured input"""
    original_text: str
    cleaned_text: str
    extracted_intent: str
    key_entities: List[str]
    confidence: float
    ambiguities: List[str]
    context_hints: Dict[str, Any]


@dataclass
class ClarificationQuestion:
    """A clarification question"""
    id: str
    question_type: QuestionType
    text: str
    options: Optional[List[str]] = None
    default_answer: Optional[str] = None
    importance: float = 1.0
    context: Dict[str, Any] = None


@dataclass
class ClarificationResponse:
    """Response to clarification questions"""
    question_id: str
    answer: str
    confidence: float
    additional_context: Optional[str] = None


@dataclass
class DetailedPlan:
    """Detailed execution plan"""
    plan_id: str
    summary: str
    steps: List[Dict[str, Any]]
    estimated_duration: int  # minutes
    required_tools: List[str]
    prerequisites: List[str]
    success_criteria: List[str]
    risks: List[str]
    fallback_options: List[str]


@dataclass
class WorkflowSession:
    """Complete workflow session"""
    session_id: str
    stage: WorkflowStage
    created_at: datetime
    updated_at: datetime
    original_input: str
    cleaned_input: Optional[CleanedInput] = None
    questions: List[ClarificationQuestion] = None
    responses: List[ClarificationResponse] = None
    plan: Optional[DetailedPlan] = None
    execution_approved: bool = False
    execution_results: Optional[Dict[str, Any]] = None
    documentation_generated: bool = False
    completed: bool = False


class InputProcessor:
    """Processes and cleans user input"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.intent_patterns = self._load_intent_patterns()

    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """Load intent recognition patterns"""
        return {
            "analysis": [
                r"analyz[e|ing]", r"understand", r"explain", r"investigate",
                r"research", r"study", r"examine", r"review"
            ],
            "implementation": [
                r"implement", r"build", r"create", r"develop", r"code",
                r"make", r"construct", r"add", r"integrate"
            ],
            "optimization": [
                r"optimize", r"improve", r"enhance", r"speed up", r"fix",
                r"refactor", r"tune", r"upgrade"
            ],
            "documentation": [
                r"document", r"write docs", r"readme", r"comment",
                r"explain", r"describe"
            ],
            "testing": [
                r"test", r"verify", r"validate", r"check", r"ensure"
            ]
        }

    async def clean_input(self, raw_input: str) -> CleanedInput:
        """Clean and structure raw user input"""

        # Basic text cleaning
        cleaned_text = self._clean_text(raw_input)

        # Extract intent
        intent = self._extract_intent(cleaned_text)

        # Extract key entities
        entities = self._extract_entities(cleaned_text)

        # Identify ambiguities
        ambiguities = self._identify_ambiguities(cleaned_text)

        # Calculate confidence
        confidence = self._calculate_confidence(cleaned_text, intent, ambiguities)

        # Extract context hints
        context_hints = self._extract_context_hints(cleaned_text)

        return CleanedInput(
            original_text=raw_input,
            cleaned_text=cleaned_text,
            extracted_intent=intent,
            key_entities=entities,
            confidence=confidence,
            ambiguities=ambiguities,
            context_hints=context_hints
        )

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Fix common typos and expansions
        expansions = {
            r"\bw/\b": "with",
            r"\b&\b": "and",
            r"\bthru\b": "through",
            r"\bu\b": "you",
            r"\br\b": "are"
        }

        for pattern, replacement in expansions.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _extract_intent(self, text: str) -> str:
        """Extract primary intent from text"""
        text_lower = text.lower()

        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            intent_scores[intent] = score

        if not intent_scores or max(intent_scores.values()) == 0:
            return "general"

        return max(intent_scores, key=intent_scores.get)

    def _extract_entities(self, text: str) -> List[str]:
        """Extract key entities from text"""
        entities = []

        # File/path patterns
        file_patterns = [
            r'\b[\w/.-]+\.(py|js|ts|md|json|yaml|yml|txt|sh)\b',
            r'\b[\w/.-]+/[\w/.-]+\b'
        ]

        for pattern in file_patterns:
            entities.extend(re.findall(pattern, text))

        # Technology patterns
        tech_patterns = [
            r'\b(Python|JavaScript|TypeScript|React|Node|Git|Docker|API|REST|GraphQL)\b'
        ]

        for pattern in tech_patterns:
            entities.extend(re.findall(pattern, text, re.IGNORECASE))

        return list(set(entities))

    def _identify_ambiguities(self, text: str) -> List[str]:
        """Identify ambiguous parts of the input"""
        ambiguities = []

        # Vague terms
        vague_terms = [
            r'\bstuff\b', r'\bthings\b', r'\bit\b', r'\bthat\b',
            r'\bsomething\b', r'\banything\b', r'\beverything\b'
        ]

        for term in vague_terms:
            if re.search(term, text, re.IGNORECASE):
                ambiguities.append(f"Vague reference: {term}")

        # Missing context
        if len(text.split()) < 5:
            ambiguities.append("Very brief input - may need more context")

        # Multiple possible interpretations
        conjunctions = len(re.findall(r'\b(and|or|but|also)\b', text, re.IGNORECASE))
        if conjunctions > 2:
            ambiguities.append("Multiple tasks or requirements mentioned")

        return ambiguities

    def _calculate_confidence(self, text: str, intent: str, ambiguities: List[str]) -> float:
        """Calculate confidence in understanding the input"""
        base_confidence = 0.5

        # Length bonus
        word_count = len(text.split())
        if word_count > 10:
            base_confidence += 0.2
        elif word_count > 5:
            base_confidence += 0.1

        # Intent clarity bonus
        if intent != "general":
            base_confidence += 0.2

        # Ambiguity penalty
        ambiguity_penalty = len(ambiguities) * 0.1
        base_confidence -= ambiguity_penalty

        return max(0.1, min(1.0, base_confidence))

    def _extract_context_hints(self, text: str) -> Dict[str, Any]:
        """Extract context hints from input"""
        hints = {}

        # Urgency indicators
        urgency_patterns = [
            r'\b(urgent|asap|quickly|fast|immediately)\b',
            r'\b(rush|hurry|deadline)\b'
        ]

        for pattern in urgency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                hints['urgency'] = 'high'
                break
        else:
            hints['urgency'] = 'normal'

        # Complexity indicators
        complexity_patterns = [
            r'\b(complex|complicated|advanced|sophisticated)\b',
            r'\b(simple|basic|easy|straightforward)\b'
        ]

        for pattern in complexity_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                hints['complexity'] = 'high' if 'complex' in pattern else 'low'
                break
        else:
            hints['complexity'] = 'medium'

        return hints


class ClarificationEngine:
    """Generates targeted clarification questions"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.question_templates = self._load_question_templates()
        self.meta_clarification_enabled = True

    def _load_question_templates(self) -> Dict[str, List[str]]:
        """Load question templates for different scenarios"""
        return {
            "intent_unclear": [
                "What is your primary goal with this request?",
                "Are you looking to analyze, implement, or optimize something?",
                "What would success look like for this task?"
            ],
            "scope_unclear": [
                "Should this be a quick fix or a comprehensive solution?",
                "Are there any constraints I should be aware of?",
                "What's the scope of changes you're comfortable with?"
            ],
            "context_missing": [
                "What type of project/codebase are you working with?",
                "Are there any existing patterns or conventions to follow?",
                "What's the current state of the system?"
            ],
            "technology_choice": [
                "Do you have a preferred technology stack?",
                "Are there any tools or frameworks already in use?",
                "Should I stick to existing dependencies?"
            ]
        }

    async def generate_questions(self, cleaned_input: CleanedInput) -> List[ClarificationQuestion]:
        """Generate clarification questions based on cleaned input"""
        questions = []

        # If confidence is high, minimal questions
        if cleaned_input.confidence > 0.8:
            return self._generate_confirmation_questions(cleaned_input)

        # Generate questions based on ambiguities
        if cleaned_input.confidence < 0.6:
            questions.extend(self._generate_intent_questions(cleaned_input))

        questions.extend(self._generate_context_questions(cleaned_input))
        questions.extend(self._generate_scope_questions(cleaned_input))

        # Limit to most important questions
        questions.sort(key=lambda q: q.importance, reverse=True)
        return questions[:3]

    async def generate_meta_clarification_prompt(self, questions: List[ClarificationQuestion], context: Dict[str, Any]) -> str:
        """Generate prompt for external AI to help user craft detailed responses back to Claude"""

        prompt = f"""I'm working with Claude Code and need help crafting a detailed, structured response to these clarification questions.

**My Original Request**: {context.get('original_input', 'User request for assistance')}

**Claude's Clarification Questions**:
"""

        for i, question in enumerate(questions, 1):
            prompt += f"\n{i}. {question.text}"
            if question.options:
                prompt += "\n   Options to choose from:"
                for j, option in enumerate(question.options, 1):
                    prompt += f"\n   • {option}"
            prompt += "\n"

        prompt += """
**Help me craft a comprehensive response that includes**:
1. Clear, specific answers to each question with reasoning
2. Additional context Claude might need to understand my requirements
3. Technical details, constraints, or preferences I should mention
4. Any edge cases or special considerations

**Format your response so I can copy-paste it directly back to Claude Code.**

The goal is to give Claude enough structured detail (400-600 words) instead of my typical brief responses, so Claude can provide much better assistance.

Please provide a well-structured response that will help Claude understand exactly what I need and how to implement it effectively.
"""

        return prompt

    def parse_meta_clarification_response(self, ai_response: str, questions: List[ClarificationQuestion]) -> List[ClarificationResponse]:
        """Parse AI response into structured clarification responses"""
        responses = []

        lines = ai_response.strip().split('\n')
        current_question_idx = 0
        additional_context = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for question patterns
            if line.startswith(f"Question {current_question_idx + 1}:"):
                if current_question_idx < len(questions):
                    # Extract answer and reasoning
                    content = line.split(':', 1)[1].strip()
                    if ' - ' in content:
                        answer, reasoning = content.split(' - ', 1)
                        answer = answer.strip()
                        additional_context = reasoning.strip()
                    else:
                        answer = content
                        additional_context = ""

                    responses.append(ClarificationResponse(
                        question_id=questions[current_question_idx].id,
                        answer=answer,
                        confidence=0.9,  # High confidence for AI-assisted responses
                        additional_context=additional_context
                    ))

                    current_question_idx += 1

            elif line.startswith("Additional context:"):
                additional_context = line.split(':', 1)[1].strip()
                # Add to last response if available
                if responses:
                    if responses[-1].additional_context:
                        responses[-1].additional_context += f" {additional_context}"
                    else:
                        responses[-1].additional_context = additional_context

        return responses

    def _generate_confirmation_questions(self, cleaned_input: CleanedInput) -> List[ClarificationQuestion]:
        """Generate simple confirmation questions for high-confidence inputs"""
        return [
            ClarificationQuestion(
                id="confirm_understanding",
                question_type=QuestionType.CONFIRMATION,
                text=f"I understand you want to {cleaned_input.extracted_intent} {cleaned_input.cleaned_text}. Is this correct?",
                importance=1.0,
                context={"type": "confirmation"}
            )
        ]

    def _generate_intent_questions(self, cleaned_input: CleanedInput) -> List[ClarificationQuestion]:
        """Generate intent clarification questions"""
        questions = []

        if "Vague reference" in str(cleaned_input.ambiguities):
            questions.append(ClarificationQuestion(
                id="clarify_intent",
                question_type=QuestionType.CHOICE,
                text="What's your primary goal?",
                options=[
                    "Analyze and understand existing code",
                    "Implement new functionality",
                    "Fix or optimize existing code",
                    "Create documentation",
                    "Test or validate something"
                ],
                importance=1.0,
                context={"type": "intent_clarification"}
            ))

        return questions

    def _generate_context_questions(self, cleaned_input: CleanedInput) -> List[ClarificationQuestion]:
        """Generate context-related questions"""
        questions = []

        if not cleaned_input.key_entities:
            questions.append(ClarificationQuestion(
                id="project_context",
                question_type=QuestionType.CLARIFICATION,
                text="What type of project or technology stack are you working with?",
                importance=0.8,
                context={"type": "context"}
            ))

        return questions

    def _generate_scope_questions(self, cleaned_input: CleanedInput) -> List[ClarificationQuestion]:
        """Generate scope-related questions"""
        questions = []

        if cleaned_input.context_hints.get('complexity') == 'medium':
            questions.append(ClarificationQuestion(
                id="scope_preference",
                question_type=QuestionType.CHOICE,
                text="What level of solution are you looking for?",
                options=[
                    "Quick and simple approach",
                    "Comprehensive and robust solution",
                    "Balanced approach with good practices"
                ],
                importance=0.7,
                context={"type": "scope"}
            ))

        return questions


class PlanningEngine:
    """Creates detailed execution plans"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def create_plan(self, cleaned_input: CleanedInput, responses: List[ClarificationResponse]) -> DetailedPlan:
        """Create detailed execution plan based on input and clarifications"""

        # Analyze responses to refine understanding
        refined_intent = self._refine_intent(cleaned_input, responses)
        scope = self._determine_scope(responses)
        context = self._build_context(cleaned_input, responses)

        # Generate plan steps
        steps = await self._generate_steps(refined_intent, scope, context)

        # Estimate duration and requirements
        duration = self._estimate_duration(steps)
        tools = self._identify_required_tools(steps)
        prerequisites = self._identify_prerequisites(steps, context)

        # Define success criteria and risks
        success_criteria = self._define_success_criteria(refined_intent, scope)
        risks = self._identify_risks(steps, context)
        fallbacks = self._generate_fallback_options(steps)

        return DetailedPlan(
            plan_id=f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            summary=self._generate_summary(refined_intent, scope),
            steps=steps,
            estimated_duration=duration,
            required_tools=tools,
            prerequisites=prerequisites,
            success_criteria=success_criteria,
            risks=risks,
            fallback_options=fallbacks
        )

    def _refine_intent(self, cleaned_input: CleanedInput, responses: List[ClarificationResponse]) -> str:
        """Refine intent based on clarification responses"""
        base_intent = cleaned_input.extracted_intent

        for response in responses:
            if response.question_id == "clarify_intent":
                intent_mapping = {
                    "Analyze and understand": "analysis",
                    "Implement new": "implementation",
                    "Fix or optimize": "optimization",
                    "Create documentation": "documentation",
                    "Test or validate": "testing"
                }

                for key, intent in intent_mapping.items():
                    if key in response.answer:
                        return intent

        return base_intent

    def _determine_scope(self, responses: List[ClarificationResponse]) -> str:
        """Determine scope from responses"""
        for response in responses:
            if response.question_id == "scope_preference":
                if "Quick and simple" in response.answer:
                    return "minimal"
                elif "Comprehensive" in response.answer:
                    return "comprehensive"
                else:
                    return "balanced"

        return "balanced"

    def _build_context(self, cleaned_input: CleanedInput, responses: List[ClarificationResponse]) -> Dict[str, Any]:
        """Build execution context from input and responses"""
        context = cleaned_input.context_hints.copy()

        for response in responses:
            if response.question_id == "project_context":
                context['project_type'] = response.answer
            elif response.additional_context:
                context['additional_info'] = response.additional_context

        return context

    async def _generate_steps(self, intent: str, scope: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate execution steps based on intent and scope"""

        step_templates = {
            "analysis": [
                {"name": "Explore codebase structure", "type": "investigation", "tools": ["file_explorer", "grep"]},
                {"name": "Analyze key components", "type": "analysis", "tools": ["code_reader"]},
                {"name": "Document findings", "type": "documentation", "tools": ["markdown_writer"]}
            ],
            "implementation": [
                {"name": "Plan implementation approach", "type": "planning", "tools": ["architecture_designer"]},
                {"name": "Implement core functionality", "type": "coding", "tools": ["code_editor", "compiler"]},
                {"name": "Add tests and validation", "type": "testing", "tools": ["test_runner"]},
                {"name": "Document changes", "type": "documentation", "tools": ["doc_generator"]}
            ],
            "optimization": [
                {"name": "Profile current performance", "type": "analysis", "tools": ["profiler"]},
                {"name": "Identify bottlenecks", "type": "investigation", "tools": ["analyzer"]},
                {"name": "Implement optimizations", "type": "coding", "tools": ["code_editor"]},
                {"name": "Validate improvements", "type": "testing", "tools": ["benchmarker"]}
            ]
        }

        base_steps = step_templates.get(intent, step_templates["analysis"])

        # Adjust based on scope
        if scope == "minimal":
            return base_steps[:2]  # Just core steps
        elif scope == "comprehensive":
            # Add extra validation and documentation steps
            extra_steps = [
                {"name": "Comprehensive testing", "type": "testing", "tools": ["test_suite"]},
                {"name": "Performance validation", "type": "validation", "tools": ["performance_tester"]},
                {"name": "Documentation review", "type": "review", "tools": ["doc_reviewer"]}
            ]
            return base_steps + extra_steps

        return base_steps

    def _estimate_duration(self, steps: List[Dict[str, Any]]) -> int:
        """Estimate duration in minutes"""
        duration_mapping = {
            "investigation": 15,
            "analysis": 20,
            "planning": 10,
            "coding": 30,
            "testing": 15,
            "documentation": 10,
            "validation": 10,
            "review": 5
        }

        total = sum(duration_mapping.get(step.get("type", "analysis"), 15) for step in steps)
        return total

    def _identify_required_tools(self, steps: List[Dict[str, Any]]) -> List[str]:
        """Identify required tools from steps"""
        tools = set()
        for step in steps:
            tools.update(step.get("tools", []))
        return list(tools)

    def _identify_prerequisites(self, steps: List[Dict[str, Any]], context: Dict[str, Any]) -> List[str]:
        """Identify prerequisites for execution"""
        prerequisites = ["Access to codebase", "Appropriate permissions"]

        if any("coding" in step.get("type", "") for step in steps):
            prerequisites.append("Development environment setup")

        if any("testing" in step.get("type", "") for step in steps):
            prerequisites.append("Test framework availability")

        return prerequisites

    def _define_success_criteria(self, intent: str, scope: str) -> List[str]:
        """Define success criteria"""
        criteria_mapping = {
            "analysis": [
                "Clear understanding of codebase structure",
                "Identified key components and relationships",
                "Documented findings in readable format"
            ],
            "implementation": [
                "Functionality works as specified",
                "Code follows existing patterns",
                "Tests pass successfully"
            ],
            "optimization": [
                "Measurable performance improvement",
                "No regression in functionality",
                "Optimizations are maintainable"
            ]
        }

        base_criteria = criteria_mapping.get(intent, criteria_mapping["analysis"])

        if scope == "comprehensive":
            base_criteria.append("Comprehensive documentation provided")
            base_criteria.append("Full test coverage achieved")

        return base_criteria

    def _identify_risks(self, steps: List[Dict[str, Any]], context: Dict[str, Any]) -> List[str]:
        """Identify potential risks"""
        risks = []

        if any("coding" in step.get("type", "") for step in steps):
            risks.append("Code changes may introduce bugs")
            risks.append("Breaking changes to existing functionality")

        if context.get("urgency") == "high":
            risks.append("Time pressure may compromise quality")

        if any("testing" in step.get("type", "") for step in steps):
            risks.append("Test environment may not match production")

        return risks

    def _generate_fallback_options(self, steps: List[Dict[str, Any]]) -> List[str]:
        """Generate fallback options"""
        fallbacks = [
            "Break down into smaller incremental changes",
            "Implement minimal viable solution first",
            "Use existing solutions/libraries where possible"
        ]

        if any("coding" in step.get("type", "") for step in steps):
            fallbacks.append("Implement feature flags for safe rollback")

        return fallbacks

    def _generate_summary(self, intent: str, scope: str) -> str:
        """Generate plan summary"""
        return f"{scope.title()} {intent} plan with systematic approach and validation"


class ClarificationWorkflow:
    """Main clarification workflow orchestrator"""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or Path.home() / ".oos" / "workflows")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.input_processor = InputProcessor()
        self.clarification_engine = ClarificationEngine()
        self.planning_engine = PlanningEngine()

        self.logger = logging.getLogger(__name__)

        # Active sessions
        self.active_sessions: Dict[str, WorkflowSession] = {}

    async def start_workflow(self, user_input: str) -> WorkflowSession:
        """Start new clarification workflow"""

        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create new session
        session = WorkflowSession(
            session_id=session_id,
            stage=WorkflowStage.INPUT_CLEANING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            original_input=user_input
        )

        # Store session
        self.active_sessions[session_id] = session
        await self._save_session(session)

        # Process input
        session.cleaned_input = await self.input_processor.clean_input(user_input)
        session.stage = WorkflowStage.CLARIFICATION
        session.updated_at = datetime.now()

        # Generate clarification questions
        session.questions = await self.clarification_engine.generate_questions(session.cleaned_input)

        await self._save_session(session)

        return session

    async def submit_responses(self, session_id: str, responses: List[ClarificationResponse]) -> WorkflowSession:
        """Submit responses to clarification questions"""

        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]

        if session.stage != WorkflowStage.CLARIFICATION:
            raise ValueError(f"Session not in clarification stage")

        # Store responses
        session.responses = responses
        session.stage = WorkflowStage.PLANNING
        session.updated_at = datetime.now()

        # Generate detailed plan
        session.plan = await self.planning_engine.create_plan(
            session.cleaned_input, session.responses
        )

        session.stage = WorkflowStage.CONFIRMATION
        await self._save_session(session)

        return session

    async def approve_execution(self, session_id: str, approved: bool) -> WorkflowSession:
        """Approve or reject plan execution"""

        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]

        if session.stage != WorkflowStage.CONFIRMATION:
            raise ValueError(f"Session not in confirmation stage")

        session.execution_approved = approved
        session.updated_at = datetime.now()

        if approved:
            session.stage = WorkflowStage.EXECUTION
        else:
            # Return to clarification for modifications
            session.stage = WorkflowStage.CLARIFICATION

        await self._save_session(session)

        return session

    async def execute_plan(self, session_id: str) -> WorkflowSession:
        """Execute the approved plan"""

        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]

        if session.stage != WorkflowStage.EXECUTION or not session.execution_approved:
            raise ValueError(f"Session not ready for execution")

        # This would integrate with actual execution systems
        # For now, we'll simulate execution
        execution_results = {
            "status": "completed",
            "steps_completed": len(session.plan.steps),
            "execution_time": session.plan.estimated_duration,
            "success": True,
            "outputs": []
        }

        session.execution_results = execution_results
        session.stage = WorkflowStage.DOCUMENTATION
        session.updated_at = datetime.now()

        await self._save_session(session)

        return session

    async def generate_documentation(self, session_id: str) -> WorkflowSession:
        """Generate documentation for completed workflow"""

        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]

        if session.stage != WorkflowStage.DOCUMENTATION:
            raise ValueError(f"Session not in documentation stage")

        # Generate documentation
        doc_content = self._generate_workflow_documentation(session)

        # Save documentation
        doc_path = self.storage_path / f"{session_id}_documentation.md"
        doc_path.write_text(doc_content)

        session.documentation_generated = True
        session.stage = WorkflowStage.COMPLETED
        session.completed = True
        session.updated_at = datetime.now()

        await self._save_session(session)

        return session

    def _generate_workflow_documentation(self, session: WorkflowSession) -> str:
        """Generate markdown documentation for workflow"""

        doc = f"""# Workflow Documentation: {session.session_id}

## Summary
- **Original Request**: {session.original_input}
- **Intent**: {session.cleaned_input.extracted_intent if session.cleaned_input else 'Unknown'}
- **Completed**: {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
- **Duration**: {session.plan.estimated_duration if session.plan else 'Unknown'} minutes

## Plan Executed
{session.plan.summary if session.plan else 'No plan available'}

### Steps Completed
"""

        if session.plan and session.plan.steps:
            for i, step in enumerate(session.plan.steps, 1):
                doc += f"{i}. **{step['name']}** ({step['type']})\n"

        doc += f"""
## Clarifications Made
"""

        if session.responses:
            for response in session.responses:
                question = next((q for q in session.questions if q.id == response.question_id), None)
                if question:
                    doc += f"- **{question.text}**: {response.answer}\n"

        doc += f"""
## Results
"""

        if session.execution_results:
            doc += f"- **Status**: {session.execution_results['status']}\n"
            doc += f"- **Success**: {session.execution_results['success']}\n"
            doc += f"- **Steps Completed**: {session.execution_results['steps_completed']}\n"

        doc += f"""
## Generated Files
- Workflow session: `{session.session_id}.json`
- Documentation: `{session.session_id}_documentation.md`
"""

        return doc

    async def _save_session(self, session: WorkflowSession):
        """Save session to storage"""
        session_file = self.storage_path / f"{session.session_id}.json"

        # Convert to serializable format
        session_data = asdict(session)
        session_data['created_at'] = session.created_at.isoformat()
        session_data['updated_at'] = session.updated_at.isoformat()
        session_data['stage'] = session.stage.value  # Convert enum to string

        # Convert questions and responses to dict if they exist
        if session_data.get('questions'):
            session_data['questions'] = [asdict(q) for q in session.questions]
            # Convert enum values in questions
            for q in session_data['questions']:
                if 'question_type' in q:
                    q['question_type'] = q['question_type'].value if hasattr(q['question_type'], 'value') else str(q['question_type'])

        if session_data.get('responses'):
            session_data['responses'] = [asdict(r) for r in session.responses]

        if session_data.get('plan'):
            session_data['plan'] = asdict(session.plan)

        session_file.write_text(json.dumps(session_data, indent=2))

    async def load_session(self, session_id: str) -> Optional[WorkflowSession]:
        """Load session from storage"""
        session_file = self.storage_path / f"{session_id}.json"

        if not session_file.exists():
            return None

        session_data = json.loads(session_file.read_text())

        # Convert back to objects
        session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
        session_data['updated_at'] = datetime.fromisoformat(session_data['updated_at'])

        session = WorkflowSession(**session_data)
        self.active_sessions[session_id] = session

        return session

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session status"""
        session = self.active_sessions.get(session_id)

        if not session:
            return None

        return {
            "session_id": session.session_id,
            "stage": session.stage.value,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "completed": session.completed,
            "questions_count": len(session.questions) if session.questions else 0,
            "responses_count": len(session.responses) if session.responses else 0,
            "plan_ready": session.plan is not None,
            "execution_approved": session.execution_approved
        }


# Global workflow instance
_workflow_instance = None


def get_clarification_workflow() -> ClarificationWorkflow:
    """Get or create global workflow instance"""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = ClarificationWorkflow()
    return _workflow_instance


# Convenience functions
async def start_clarification(user_input: str) -> WorkflowSession:
    """Start clarification workflow"""
    workflow = get_clarification_workflow()
    return await workflow.start_workflow(user_input)


async def submit_clarification_responses(session_id: str, responses: List[ClarificationResponse]) -> WorkflowSession:
    """Submit clarification responses"""
    workflow = get_clarification_workflow()
    return await workflow.submit_responses(session_id, responses)


async def approve_plan(session_id: str, approved: bool = True) -> WorkflowSession:
    """Approve execution plan"""
    workflow = get_clarification_workflow()
    return await workflow.approve_execution(session_id, approved)


async def execute_workflow(session_id: str) -> WorkflowSession:
    """Execute approved workflow"""
    workflow = get_clarification_workflow()
    return await workflow.execute_plan(session_id)


async def complete_workflow(session_id: str) -> WorkflowSession:
    """Complete workflow with documentation"""
    workflow = get_clarification_workflow()
    return await workflow.generate_documentation(session_id)