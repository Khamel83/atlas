#!/usr/bin/env python3
"""
LLM Router - Intelligent model selection with cost optimization
Implements 3-tier routing strategy: Llama → Qwen → Gemini with smart fallback logic
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from helpers.utils import log_info, log_error
from helpers.llm_client import get_llm_client, LLMResponse


class TaskKind(Enum):
    """Types of LLM tasks with different requirements."""
    SUMMARIZE = "summarize"
    EXTRACT_JSON = "extract_json"
    TAG = "tag"
    QNA = "qna"
    CLASSIFY = "classify"
    REWRITE = "rewrite"
    CODE_ANALYSIS = "code_analysis"


@dataclass
class TaskSpec:
    """Specification for an LLM task with routing requirements."""
    kind: TaskKind
    input_tokens: int
    content_type: str = "text"
    requires_long_ctx: bool = False
    code_heavy: bool = False
    strict_json: bool = True
    retry_count: int = 0
    previous_fail_reason: Optional[str] = None
    priority: str = "normal"  # normal, high, low

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            **asdict(self),
            'kind': self.kind.value
        }


class ModelTier(Enum):
    """Model tiers by cost and capability."""
    ECONOMY = "economy"      # Cheapest (Llama)
    BALANCED = "balanced"    # Code-optimized (Qwen)
    PREMIUM = "premium"      # Highest quality (Gemini)


@dataclass
class ModelInfo:
    """Model information and capabilities."""
    slug: str
    tier: ModelTier
    context_length: int
    cost_per_1m_in: float
    cost_per_1m_out: float
    strengths: List[str]
    weaknesses: List[str]

    def estimated_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for this model."""
        input_cost = (input_tokens / 1_000_000) * self.cost_per_1m_in
        output_cost = (output_tokens / 1_000_000) * self.cost_per_1m_out
        return round(input_cost + output_cost, 6)


class LLMRouter:
    """
    Intelligent LLM routing with cost optimization and fallback strategies.

    Routing Strategy:
    1. Default to cheapest model that meets requirements (Llama)
    2. Use code-optimized model for code-heavy tasks (Qwen)
    3. Fallback to premium model for complex/failed tasks (Gemini)
    4. Always respect context length limits
    5. Escalate on JSON validation failures
    """

    # Model definitions with exact pricing and capabilities
    MODELS = {
        'meta-llama/llama-3.1-8b-instruct': ModelInfo(
            slug='meta-llama/llama-3.1-8b-instruct',
            tier=ModelTier.ECONOMY,
            context_length=131_072,
            cost_per_1m_in=0.015,
            cost_per_1m_out=0.02,
            strengths=['fast', 'cheap', 'general_purpose', 'long_context'],
            weaknesses=['json_formatting', 'complex_reasoning']
        ),
        'qwen/qwen-2.5-7b-instruct': ModelInfo(
            slug='qwen/qwen-2.5-7b-instruct',
            tier=ModelTier.BALANCED,
            context_length=65_536,
            cost_per_1m_in=0.04,
            cost_per_1m_out=0.10,
            strengths=['code', 'structured_output', 'technical_content'],
            weaknesses=['very_long_context', 'creative_writing']
        ),
        'google/gemini-2.5-flash-lite': ModelInfo(
            slug='google/gemini-2.5-flash-lite',
            tier=ModelTier.PREMIUM,
            context_length=1_000_000,
            cost_per_1m_in=0.10,
            cost_per_1m_out=0.40,
            strengths=['json_quality', 'complex_reasoning', 'very_long_context', 'reliability'],
            weaknesses=['cost', 'speed']
        )
    }

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize router with configuration."""
        self.config = config or {}
        self.client = get_llm_client(config)

        # Router settings
        self.prefer_economy = self.config.get('prefer_economy_models', True)
        self.max_fallback_attempts = self.config.get('max_fallback_attempts', 2)

        # Fallback triggers
        self.json_failure_triggers = {
            'invalid_json', 'schema_mismatch', 'parse_error',
            'malformed_response', 'incomplete_json'
        }

        self.quality_failure_triggers = {
            'lost_steps', 'hallucination', 'incomplete_response',
            'poor_quality', 'context_limit_exceeded'
        }

        # Set up logging
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'llm_router.log')

        log_info(self.log_path, f"LLM Router initialized with {len(self.MODELS)} models")

    def choose_model(self, spec: TaskSpec) -> str:
        """
        Choose optimal model based on task specification.

        Decision tree:
        1. Check context length requirements
        2. For code-heavy tasks, prefer Qwen
        3. For very long context (>120k tokens), use Gemini
        4. Default to Llama for cost efficiency
        5. Escalate on previous failures
        """

        # Check for escalation due to previous failures
        if self.should_escalate(spec):
            return self._get_fallback_model(spec)

        # Context length check - must fit in model
        available_models = [
            model for model in self.MODELS.values()
            if model.context_length >= spec.input_tokens
        ]

        if not available_models:
            log_error(self.log_path, f"No model can handle {spec.input_tokens} tokens")
            return self.MODELS['google/gemini-2.5-flash-lite'].slug  # Largest context

        # Very long context requirement
        if spec.requires_long_ctx or spec.input_tokens > 120_000:
            return self.MODELS['google/gemini-2.5-flash-lite'].slug

        # Code-heavy tasks - Qwen is optimized for technical content
        if spec.code_heavy or spec.kind == TaskKind.CODE_ANALYSIS:
            qwen_model = self.MODELS['qwen/qwen-2.5-7b-instruct']
            if qwen_model.context_length >= spec.input_tokens:
                return qwen_model.slug

        # Strict JSON requirements with previous failures
        if spec.strict_json and spec.retry_count > 0:
            if spec.previous_fail_reason in self.json_failure_triggers:
                return self.MODELS['google/gemini-2.5-flash-lite'].slug

        # High priority tasks
        if spec.priority == "high":
            return self.MODELS['google/gemini-2.5-flash-lite'].slug

        # Default to most economical model
        llama_model = self.MODELS['meta-llama/llama-3.1-8b-instruct']
        if llama_model.context_length >= spec.input_tokens:
            return llama_model.slug

        # Fallback to next tier
        qwen_model = self.MODELS['qwen/qwen-2.5-7b-instruct']
        if qwen_model.context_length >= spec.input_tokens:
            return qwen_model.slug

        # Final fallback
        return self.MODELS['google/gemini-2.5-flash-lite'].slug

    def should_escalate(self, spec: TaskSpec) -> bool:
        """Determine if we should escalate to a higher-tier model."""
        if spec.retry_count == 0:
            return False

        # Escalate on JSON failures
        if (spec.strict_json and
            spec.previous_fail_reason in self.json_failure_triggers):
            return True

        # Escalate on quality failures
        if spec.previous_fail_reason in self.quality_failure_triggers:
            return True

        # Escalate after multiple failures
        if spec.retry_count >= 2:
            return True

        return False

    def _get_fallback_model(self, spec: TaskSpec) -> str:
        """Get next tier model for fallback."""
        # For JSON failures, always go to Gemini
        if spec.previous_fail_reason in self.json_failure_triggers:
            return self.MODELS['google/gemini-2.5-flash-lite'].slug

        # For other failures, step up one tier
        current_model = self._get_current_model_tier(spec)

        if current_model == ModelTier.ECONOMY:
            # Llama → Qwen (if context allows) or Gemini
            qwen_model = self.MODELS['qwen/qwen-2.5-7b-instruct']
            if qwen_model.context_length >= spec.input_tokens:
                return qwen_model.slug
            else:
                return self.MODELS['google/gemini-2.5-flash-lite'].slug

        elif current_model == ModelTier.BALANCED:
            # Qwen → Gemini
            return self.MODELS['google/gemini-2.5-flash-lite'].slug

        else:
            # Already at premium tier, can't escalate further
            return self.MODELS['google/gemini-2.5-flash-lite'].slug

    def _get_current_model_tier(self, spec: TaskSpec) -> ModelTier:
        """Determine current model tier based on task spec."""
        if spec.retry_count == 0:
            return ModelTier.ECONOMY
        elif spec.retry_count == 1:
            return ModelTier.BALANCED
        else:
            return ModelTier.PREMIUM

    def execute_task(self,
                    spec: TaskSpec,
                    messages: List[Dict[str, str]],
                    response_schema: Optional[Dict[str, Any]] = None,
                    force_model: Optional[str] = None,
                    dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute LLM task with intelligent routing and fallback.

        Args:
            spec: Task specification
            messages: Chat messages for the LLM
            response_schema: JSON schema for structured outputs
            force_model: Override model selection
            dry_run: Only return routing decision, don't call API

        Returns:
            Dict with response, model used, cost, and metadata
        """

        # Choose model
        model = force_model or self.choose_model(spec)
        model_info = self._get_model_info(model)

        # Estimate cost
        estimated_output_tokens = min(500, spec.input_tokens // 5)  # Conservative estimate
        estimated_cost = model_info.estimated_cost(spec.input_tokens, estimated_output_tokens)

        routing_decision = {
            'task_spec': spec.to_dict(),
            'selected_model': model,
            'model_tier': model_info.tier.value,
            'estimated_cost': estimated_cost,
            'reasoning': self._explain_choice(spec, model),
            'timestamp': datetime.now().isoformat()
        }

        if dry_run:
            return {
                'success': True,
                'dry_run': True,
                'routing_decision': routing_decision
            }

        log_info(self.log_path, f"Executing {spec.kind.value} task with {model} (${estimated_cost:.6f})")

        # Execute request
        try:
            response = self.client.chat_completion(
                model=model,
                messages=messages,
                response_schema=response_schema,
                max_tokens=min(4000, max(1500, spec.input_tokens // 2))  # Ensure minimum for JSON extraction
            )

            # Handle JSON validation for structured outputs
            if response.success and response_schema and spec.strict_json:
                if not self.client.is_valid_json(response.content, response_schema):
                    # Attempt repair
                    repaired = self.client.repair_json(response.content)
                    if self.client.is_valid_json(repaired, response_schema):
                        response.content = repaired
                        response.metadata = response.metadata or {}
                        response.metadata['json_repaired'] = True
                    else:
                        # JSON validation failed
                        if spec.retry_count < self.max_fallback_attempts:
                            log_info(self.log_path, f"JSON validation failed, attempting fallback")

                            # Create new spec for fallback
                            fallback_spec = TaskSpec(
                                kind=spec.kind,
                                input_tokens=spec.input_tokens,
                                content_type=spec.content_type,
                                requires_long_ctx=spec.requires_long_ctx,
                                code_heavy=spec.code_heavy,
                                strict_json=spec.strict_json,
                                retry_count=spec.retry_count + 1,
                                previous_fail_reason='invalid_json',
                                priority=spec.priority
                            )

                            # Recursive fallback
                            return self.execute_task(fallback_spec, messages, response_schema)

            # Success - return comprehensive result
            return {
                'success': response.success,
                'content': response.content,
                'model': response.model,
                'tokens_used': response.tokens_used,
                'cost_usd': response.cost_usd,
                'response_time': response.response_time,
                'routing_decision': routing_decision,
                'metadata': {
                    **(response.metadata or {}),
                    'task_spec': spec.to_dict(),
                    'retry_count': spec.retry_count
                },
                'error': response.error
            }

        except Exception as e:
            log_error(self.log_path, f"Task execution failed: {str(e)}")

            # Attempt fallback on execution failure
            if spec.retry_count < self.max_fallback_attempts:
                fallback_spec = TaskSpec(
                    kind=spec.kind,
                    input_tokens=spec.input_tokens,
                    content_type=spec.content_type,
                    requires_long_ctx=spec.requires_long_ctx,
                    code_heavy=spec.code_heavy,
                    strict_json=spec.strict_json,
                    retry_count=spec.retry_count + 1,
                    previous_fail_reason='execution_error',
                    priority=spec.priority
                )

                return self.execute_task(fallback_spec, messages, response_schema)

            return {
                'success': False,
                'error': str(e),
                'routing_decision': routing_decision,
                'final_attempt': True
            }

    def _get_model_info(self, model_slug: str) -> ModelInfo:
        """Get model information by slug."""
        return self.MODELS.get(model_slug, self.MODELS['meta-llama/llama-3.1-8b-instruct'])

    def _explain_choice(self, spec: TaskSpec, model: str) -> str:
        """Generate human-readable explanation for model choice."""
        reasons = []

        if model == 'meta-llama/llama-3.1-8b-instruct':
            reasons.append("Cost-optimized choice for general tasks")
        elif model == 'qwen/qwen-2.5-7b-instruct':
            reasons.append("Code-optimized model selected")
        elif model == 'google/gemini-2.5-flash-lite':
            reasons.append("Premium model for quality/context requirements")

        if spec.code_heavy:
            reasons.append("Code-heavy task detected")
        if spec.requires_long_ctx:
            reasons.append("Long context requirement")
        if spec.retry_count > 0:
            reasons.append(f"Fallback attempt #{spec.retry_count}")
        if spec.previous_fail_reason:
            reasons.append(f"Previous failure: {spec.previous_fail_reason}")

        return "; ".join(reasons)

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics and recommendations."""
        return {
            'available_models': len(self.MODELS),
            'model_tiers': [tier.value for tier in ModelTier],
            'routing_strategy': 'cost_optimized_with_fallback',
            'max_context_length': max(m.context_length for m in self.MODELS.values()),
            'cost_range': {
                'min_per_1m': min(m.cost_per_1m_in for m in self.MODELS.values()),
                'max_per_1m': max(m.cost_per_1m_out for m in self.MODELS.values())
            }
        }


# Global router instance
_llm_router = None

def get_llm_router(config: Dict[str, Any] = None) -> LLMRouter:
    """Get global LLM router instance."""
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter(config)
    return _llm_router


if __name__ == "__main__":
    # Test the router
    router = LLMRouter()

    print("🎯 LLM Router Test")
    print("=" * 50)

    # Test model selection
    test_specs = [
        TaskSpec(TaskKind.SUMMARIZE, 1000),
        TaskSpec(TaskKind.CODE_ANALYSIS, 5000, code_heavy=True),
        TaskSpec(TaskKind.EXTRACT_JSON, 150000, requires_long_ctx=True),
        TaskSpec(TaskKind.SUMMARIZE, 1000, retry_count=1, previous_fail_reason='invalid_json')
    ]

    for spec in test_specs:
        model = router.choose_model(spec)
        model_info = router._get_model_info(model)
        print(f"{spec.kind.value}: {model} ({model_info.tier.value})")
        print(f"  Reasoning: {router._explain_choice(spec, model)}")

    # Test routing stats
    stats = router.get_routing_stats()
    print(f"\nRouting Stats: {stats['available_models']} models, {stats['routing_strategy']}")