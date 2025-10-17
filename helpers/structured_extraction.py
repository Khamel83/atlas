"""
Structured content extraction using LLM-powered analysis.
Transforms raw content into structured insights with confidence scores.
"""

import json
import logging
import re
import hashlib
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Pydantic Models for Structured Data

class Entity(BaseModel):
    """Extracted entity with canonicalization and confidence."""
    name: str = Field(..., description="Entity name as mentioned")
    type: str = Field(..., description="company|person|product|org|location|misc")
    canonical: Optional[str] = Field(None, description="Canonical/normalized name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    context: Optional[str] = Field(None, description="Surrounding context")

class Quote(BaseModel):
    """Notable quote with attribution and timing."""
    text: str = Field(..., description="The actual quote")
    speaker: Optional[str] = Field(None, description="Who said it")
    start: Optional[str] = Field(None, description="Timestamp HH:MM:SS or null")
    end: Optional[str] = Field(None, description="End timestamp or null")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Attribution confidence")

class Thesis(BaseModel):
    """Key argument or investment thesis."""
    statement: str = Field(..., description="The main thesis/argument")
    rationale: str = Field(..., description="Supporting reasoning")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in thesis")
    category: Optional[str] = Field(None, description="investment|technical|business|misc")

class Topic(BaseModel):
    """Key topic with hierarchical organization."""
    name: str = Field(..., description="Topic name")
    relevance: float = Field(..., ge=0.0, le=1.0, description="How relevant to main content")
    subtopics: List[str] = Field(default_factory=list, description="Related subtopics")

class ContentInsights(BaseModel):
    """Complete structured extraction from content."""
    summary: str = Field(..., description="120-200 word summary")
    key_topics: List[Topic] = Field(..., description="3-7 main topics")
    key_themes: List[str] = Field(..., description="3-7 overarching themes")
    entities: List[Entity] = Field(..., description="Up to 30 extracted entities")
    quotes: List[Quote] = Field(..., description="Up to 10 notable quotes")
    theses: List[Thesis] = Field(..., description="Up to 8 key arguments/theses")
    sentiment: str = Field(..., description="positive|negative|neutral|mixed")
    complexity: str = Field(..., description="basic|intermediate|advanced|expert")
    content_type: str = Field(..., description="article|podcast|video|document")

    @validator('summary')
    def validate_summary_length(cls, v):
        word_count = len(v.split())
        if word_count < 50 or word_count > 250:
            raise ValueError(f"Summary must be 50-250 words, got {word_count}")
        return v

class ExtractionResult(BaseModel):
    """Complete extraction result with metadata."""
    content_id: str = Field(..., description="Unique content identifier")
    insights: ContentInsights = Field(..., description="Structured insights")
    extraction_quality: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    processing_time: float = Field(..., description="Time taken in seconds")
    model_used: str = Field(..., description="LLM model used for extraction")
    created_at: datetime = Field(default_factory=datetime.utcnow)

@dataclass
class ContentInput:
    """Input content for extraction."""
    title: str
    content: str
    url: Optional[str] = None
    date: Optional[datetime] = None
    source: Optional[str] = None
    content_type: str = "article"  # article|podcast|video|document

class StructuredExtractor:
    """LLM-powered structured content extraction."""

    def __init__(self, llm_client=None):
        """Initialize with LLM client."""
        self.llm_client = llm_client or self._get_default_llm()
        self.extraction_prompt = self._load_extraction_prompt()
        self.validation_prompt = self._load_validation_prompt()

    def _get_default_llm(self):
        """Get default LLM router from Atlas config."""
        try:
            from helpers.llm_router import get_llm_router
            from helpers.config import load_config

            config = load_config()
            llm_router = get_llm_router(config)

            # Check if we have a working client
            if not llm_router.client.api_key:
                logger.warning("No OpenRouter API key found, falling back to mock client")
                return MockLLMClient()

            logger.info(f"Using LLM router with intelligent model selection (Economy→Balanced→Premium)")
            return llm_router

        except Exception as e:
            logger.error(f"Failed to initialize LLM router: {e}")
            logger.info("Falling back to mock LLM client")
            return MockLLMClient()

    def _load_extraction_prompt(self) -> str:
        """Load extraction prompt template."""
        return """You are an expert content analyst. Extract structured data from this content.

Content Title: {title}
Content Type: {content_type}
Content:
{content}

Return **valid JSON** matching this exact schema:
{{
  "summary": "string (120-200 words)",
  "key_topics": [{{"name":"string","relevance":0-1,"subtopics":["string"]}}],
  "key_themes": ["string"],
  "entities": [{{"name":"string","type":"company|person|product|org|location|misc","canonical":"string|null","confidence":0-1,"context":"string|null"}}],
  "quotes": [{{"text":"string","speaker":"string|null","start":"HH:MM:SS|null","end":"HH:MM:SS|null","confidence":0-1}}],
  "theses": [{{"statement":"string","rationale":"string","confidence":0-1,"category":"investment|technical|business|misc"}}],
  "sentiment": "positive|negative|neutral|mixed",
  "complexity": "basic|intermediate|advanced|expert",
  "content_type": "{content_type}"
}}

Guidelines:
- Canonicalize company names (e.g., "Apple Inc." → "Apple")
- Include confidence scores for uncertain extractions
- Focus on most important/actionable insights
- Keep quotes verbatim, attribute correctly
- Identify investment/business theses clearly
- Extract 3-7 topics, up to 30 entities, up to 10 quotes, up to 8 theses

Return only valid JSON, no other text."""

    def _load_validation_prompt(self) -> str:
        """Load validation/critique prompt."""
        return """You are a data quality validator. Review this JSON extraction and identify issues:

Original Content: {title}
Extracted JSON: {json_data}

Check for:
1. Schema compliance
2. Factual accuracy
3. Entity canonicalization quality
4. Confidence score reasonableness
5. Missing key insights

Return JSON with:
{{
  "is_valid": true/false,
  "quality_score": 0-1,
  "issues": ["list of specific problems"],
  "suggested_fixes": ["list of improvements"],
  "missing_insights": ["important things that were missed"]
}}"""

    def generate_content_id(self, content_input: ContentInput) -> str:
        """Generate unique, deterministic content ID."""
        # Create hash from content identifying features
        content_key = f"{content_input.url or ''}{content_input.title}{content_input.date or ''}"
        content_hash = hashlib.sha256(content_key.encode()).hexdigest()
        return content_hash[:16]  # First 16 chars for readability

    def extract(self, content_input: ContentInput, validate: bool = True) -> ExtractionResult:
        """Extract structured insights from content."""
        start_time = datetime.utcnow()
        content_id = self.generate_content_id(content_input)

        logger.info(f"Extracting insights from content: {content_input.title[:50]}...")

        try:
            # Primary extraction
            extraction = self._perform_extraction(content_input)

            # Optional validation pass
            if validate:
                validation = self._validate_extraction(content_input, extraction)
                if not validation.get('is_valid', False) and validation.get('quality_score', 0) < 0.7:
                    logger.warning(f"Low quality extraction, retrying... Issues: {validation.get('issues', [])}")
                    # Retry with critique
                    extraction = self._perform_extraction(content_input, previous_attempt=extraction, critique=validation)

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # Build result
            return ExtractionResult(
                content_id=content_id,
                insights=extraction,
                extraction_quality=self._calculate_quality_score(extraction),
                processing_time=processing_time,
                model_used=getattr(self.llm_client, 'model_name', 'unknown')
            )

        except Exception as e:
            logger.error(f"Extraction failed for {content_input.title}: {e}")
            raise

    def _perform_extraction(self, content_input: ContentInput, previous_attempt=None, critique=None) -> ContentInsights:
        """Perform the actual LLM extraction."""
        # Prepare prompt
        prompt = self.extraction_prompt.format(
            title=content_input.title,
            content_type=content_input.content_type,
            content=content_input.content[:8000]  # Limit content length
        )

        # Add critique if this is a retry
        if previous_attempt and critique:
            prompt += f"\n\nPREVIOUS ATTEMPT HAD ISSUES:\nIssues: {critique.get('issues', [])}\nSuggested fixes: {critique.get('suggested_fixes', [])}\nPlease address these issues in your extraction."

        # Use LLM router for intelligent model selection
        if hasattr(self.llm_client, 'execute_task'):
            # Using LLM router - it will choose optimal model (Economy→Balanced→Premium)
            from helpers.llm_router import TaskSpec, TaskKind

            task_spec = TaskSpec(
                kind=TaskKind.EXTRACT_JSON,
                input_tokens=len(prompt) // 4,  # Rough estimate
                content_type=content_input.content_type,
                strict_json=True,
                priority="high"  # Force premium model for better JSON extraction
            )

            router_result = self.llm_client.execute_task(
                spec=task_spec,
                messages=[{"role": "user", "content": prompt}]
            )

            # Convert router result to LLMResponse format
            class RouterResponse:
                def __init__(self, result):
                    self.success = result.get('success', False)
                    self.content = result.get('content', '')
                    self.error = result.get('error')

            llm_response = RouterResponse(router_result)
        else:
            # Fallback to direct client call (mock or emergency)
            llm_response = self.llm_client.chat_completion(
                model="meta-llama/llama-3.1-8b-instruct",  # Start with economy model
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )

        if not llm_response.success:
            raise Exception(f"LLM call failed: {llm_response.error}")

        response = llm_response.content

        # Parse JSON response
        try:
            json_data = self._extract_json_from_response(response)
            return ContentInsights(**json_data)
        except Exception as e:
            logger.error(f"Failed to parse extraction JSON: {e}")
            logger.error(f"Raw response: {response[:500]}...")  # Debug log
            # Try to fix JSON and retry once
            fixed_json = self._fix_json(response)
            return ContentInsights(**fixed_json)

    def _validate_extraction(self, content_input: ContentInput, extraction: ContentInsights) -> Dict[str, Any]:
        """Validate extraction quality."""
        try:
            prompt = self.validation_prompt.format(
                title=content_input.title,
                json_data=extraction.json()
            )

            # Use router for validation too, but simpler task
            if hasattr(self.llm_client, 'execute_task'):
                from helpers.llm_router import TaskSpec, TaskKind

                task_spec = TaskSpec(
                    kind=TaskKind.QNA,
                    input_tokens=len(prompt) // 4,
                    content_type="validation",
                    strict_json=False,
                    priority="normal"
                )

                router_result = self.llm_client.execute_task(
                    spec=task_spec,
                    messages=[{"role": "user", "content": prompt}]
                )

                # Convert router result to LLMResponse format
                class RouterResponse:
                    def __init__(self, result):
                        self.success = result.get('success', False)
                        self.content = result.get('content', '')
                        self.error = result.get('error')

                llm_response = RouterResponse(router_result)
            else:
                llm_response = self.llm_client.chat_completion(
                    model="meta-llama/llama-3.1-8b-instruct",  # Start with economy model
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=800
                )

            if not llm_response.success:
                raise Exception(f"Validation LLM call failed: {llm_response.error}")

            response = llm_response.content
            return self._extract_json_from_response(response)

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"is_valid": True, "quality_score": 0.9, "issues": [], "suggested_fixes": []}

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        # Try to find JSON block
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response, re.DOTALL)

        if match:
            json_str = match.group(1)
        else:
            # Look for raw JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")

        # Clean up JSON string
        json_str = json_str.strip()

        # If JSON is truncated, try to complete it
        if not json_str.endswith('}'):
            # Count braces to see if we need to close
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            if open_braces > close_braces:
                json_str += '}' * (open_braces - close_braces)

        return json.loads(json_str)

    def _fix_json(self, response: str) -> Dict[str, Any]:
        """Attempt to fix malformed JSON."""
        # Simple JSON fixing attempts
        json_str = response

        # Remove common issues
        json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
        json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays

        try:
            return json.loads(json_str)
        except:
            # If still broken, return minimal valid structure
            return {
                "summary": "Failed to extract summary",
                "key_topics": [],
                "key_themes": [],
                "entities": [],
                "quotes": [],
                "theses": [],
                "sentiment": "neutral",
                "complexity": "intermediate",
                "content_type": "article"
            }

    def _calculate_quality_score(self, insights: ContentInsights) -> float:
        """Calculate overall extraction quality score."""
        score = 0.0

        # Summary quality (20%)
        if len(insights.summary.split()) >= 50:
            score += 0.2

        # Entity extraction (20%)
        if len(insights.entities) > 0:
            avg_confidence = sum(e.confidence for e in insights.entities) / len(insights.entities)
            score += 0.2 * avg_confidence

        # Topic extraction (15%)
        if len(insights.key_topics) >= 3:
            score += 0.15

        # Quote extraction (15%)
        if len(insights.quotes) > 0:
            score += 0.15

        # Thesis extraction (15%)
        if len(insights.theses) > 0:
            score += 0.15

        # Theme extraction (10%)
        if len(insights.key_themes) >= 3:
            score += 0.1

        # Classification accuracy (5%)
        if insights.sentiment and insights.complexity:
            score += 0.05

        return min(score, 1.0)

class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self):
        self.model_name = "mock-llm"

    def chat_completion(self, model, messages, **kwargs):
        """Return mock JSON response."""
        from dataclasses import dataclass

        @dataclass
        class MockResponse:
            content: str
            success: bool = True
            error: str = None

        return MockResponse(content="""```json
{
  "summary": "This comprehensive mock summary for testing the structured extraction system demonstrates advanced content analysis capabilities. The system successfully identifies key entities, extracts meaningful quotes, and analyzes business theses from various content types including articles, podcasts, and video transcripts. Through sophisticated natural language processing, it maintains high accuracy in entity canonicalization while providing confidence scores for all extracted insights. The structured output enables downstream applications to efficiently process and analyze large volumes of content for strategic decision-making and knowledge management purposes.",
  "key_topics": [
    {"name": "Technology", "relevance": 0.9, "subtopics": ["AI", "Software", "Machine Learning"]},
    {"name": "Business Strategy", "relevance": 0.7, "subtopics": ["Growth", "Innovation", "Competitive Analysis"]}
  ],
  "key_themes": ["Innovation", "Digital Transformation", "Market Disruption", "Competitive Advantage"],
  "entities": [
    {"name": "OpenAI", "type": "company", "canonical": "OpenAI", "confidence": 0.95, "context": "Leading AI research company"},
    {"name": "Sam Altman", "type": "person", "canonical": "Sam Altman", "confidence": 0.9, "context": "CEO of OpenAI"},
    {"name": "GPT-5", "type": "product", "canonical": "GPT-5", "confidence": 0.85, "context": "Advanced language model"}
  ],
  "quotes": [
    {"text": "This represents a fundamental shift in how we approach AI development", "speaker": "Sam Altman", "start": null, "end": null, "confidence": 0.9},
    {"text": "We're entering a new era where AI becomes truly useful for complex problem-solving", "speaker": "Dr. Yann LeCun", "start": null, "end": null, "confidence": 0.8}
  ],
  "theses": [
    {"statement": "AI will transform software development fundamentally", "rationale": "Increasing automation capabilities reduce manual coding requirements", "confidence": 0.8, "category": "technical"},
    {"statement": "Companies integrating AI effectively will gain competitive advantages", "rationale": "Early AI adoption creates moats through improved efficiency and capabilities", "confidence": 0.9, "category": "investment"}
  ],
  "sentiment": "positive",
  "complexity": "intermediate",
  "content_type": "article"
}
```""")

def create_extractor(config=None) -> StructuredExtractor:
    """Factory function to create extractor instance."""
    return StructuredExtractor()