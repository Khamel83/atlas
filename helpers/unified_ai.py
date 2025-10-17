#!/usr/bin/env python3
"""
Unified AI System - Integration of LLM Router + Cost Manager
Production-grade AI system with intelligent routing, budget enforcement, and comprehensive monitoring
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from helpers.utils import log_info, log_error
from helpers.llm_router import get_llm_router, LLMRouter, TaskSpec, TaskKind
from helpers.ai_cost_manager import get_cost_manager, AICostManager


@dataclass
class UnifiedAIResponse:
    """Comprehensive AI response with routing and cost information."""
    success: bool
    content: str
    model_used: str
    cost_usd: float
    tokens_used: int
    response_time: float

    # Routing information
    routing_decision: Dict[str, Any]
    fallback_used: bool = False
    fallback_reason: Optional[str] = None

    # Cost management
    budget_status: Dict[str, Any] = None
    cost_saved: float = 0.0
    cache_hit: bool = False

    # Error handling
    error: Optional[str] = None
    warnings: List[str] = None

    # Metadata
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'success': self.success,
            'content': self.content,
            'model_used': self.model_used,
            'cost_usd': self.cost_usd,
            'tokens_used': self.tokens_used,
            'response_time': self.response_time,
            'routing_decision': self.routing_decision,
            'fallback_used': self.fallback_used,
            'fallback_reason': self.fallback_reason,
            'budget_status': self.budget_status,
            'cost_saved': self.cost_saved,
            'cache_hit': self.cache_hit,
            'error': self.error,
            'warnings': self.warnings or [],
            'metadata': self.metadata or {},
            'timestamp': datetime.now().isoformat()
        }


class UnifiedAISystem:
    """
    Unified AI System combining intelligent routing with cost management.

    Features:
    - Smart model selection (Llama → Qwen → Gemini)
    - Budget enforcement and cost tracking
    - Automatic fallback strategies
    - Response caching and optimization
    - Comprehensive monitoring and analytics
    - Graceful degradation
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize unified AI system."""
        self.config = config or {}

        # Initialize subsystems
        self.router = get_llm_router(config)
        self.cost_manager = get_cost_manager(config)

        # System settings
        self.enable_caching = self.config.get('ai_caching_enabled', True)
        self.enable_fallbacks = self.config.get('ai_fallbacks_enabled', True)
        self.max_cost_per_request = self.config.get('max_cost_per_request', 0.10)

        # Set up logging
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'unified_ai.log')

        log_info(self.log_path, "Unified AI System initialized with intelligent routing and cost management")

    def summarize(self,
                 content: str,
                 target_length: int = 300,
                 force_model: Optional[str] = None,
                 priority: str = "normal",
                 **kwargs) -> UnifiedAIResponse:
        """
        Intelligent content summarization with cost optimization.

        Args:
            content: Text content to summarize
            target_length: Target summary length in characters
            force_model: Override model selection
            priority: Task priority (low, normal, high)
            **kwargs: Additional parameters

        Returns:
            UnifiedAIResponse with summary and comprehensive metadata
        """
        return self._execute_ai_task(
            task_kind=TaskKind.SUMMARIZE,
            content=content,
            task_params={'target_length': target_length},
            force_model=force_model,
            priority=priority,
            **kwargs
        )

    def extract_json(self,
                    content: str,
                    schema: Dict[str, Any],
                    extraction_prompt: str = None,
                    force_model: Optional[str] = None,
                    **kwargs) -> UnifiedAIResponse:
        """
        Extract structured JSON data from content.

        Args:
            content: Source content
            schema: JSON schema for output validation
            extraction_prompt: Custom extraction instructions
            force_model: Override model selection
            **kwargs: Additional parameters

        Returns:
            UnifiedAIResponse with extracted JSON data
        """
        return self._execute_ai_task(
            task_kind=TaskKind.EXTRACT_JSON,
            content=content,
            task_params={
                'schema': schema,
                'extraction_prompt': extraction_prompt
            },
            response_schema=schema,
            force_model=force_model,
            strict_json=True,
            **kwargs
        )

    def classify_content(self,
                        content: str,
                        categories: List[str],
                        force_model: Optional[str] = None,
                        **kwargs) -> UnifiedAIResponse:
        """
        Classify content into predefined categories.

        Args:
            content: Content to classify
            categories: List of possible categories
            force_model: Override model selection
            **kwargs: Additional parameters

        Returns:
            UnifiedAIResponse with classification results
        """
        # Build classification schema
        schema = {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": categories
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "reasoning": {
                    "type": "string"
                }
            },
            "required": ["category", "confidence"]
        }

        return self._execute_ai_task(
            task_kind=TaskKind.CLASSIFY,
            content=content,
            task_params={'categories': categories},
            response_schema=schema,
            force_model=force_model,
            strict_json=True,
            **kwargs
        )

    def analyze_code(self,
                    code: str,
                    analysis_type: str = "general",
                    force_model: Optional[str] = None,
                    **kwargs) -> UnifiedAIResponse:
        """
        Analyze code with specialized code-optimized models.

        Args:
            code: Source code to analyze
            analysis_type: Type of analysis (general, security, performance)
            force_model: Override model selection
            **kwargs: Additional parameters

        Returns:
            UnifiedAIResponse with code analysis
        """
        return self._execute_ai_task(
            task_kind=TaskKind.CODE_ANALYSIS,
            content=code,
            task_params={'analysis_type': analysis_type},
            force_model=force_model,
            code_heavy=True,
            **kwargs
        )

    def _execute_ai_task(self,
                        task_kind: TaskKind,
                        content: str,
                        task_params: Dict[str, Any] = None,
                        response_schema: Optional[Dict[str, Any]] = None,
                        force_model: Optional[str] = None,
                        priority: str = "normal",
                        code_heavy: bool = False,
                        strict_json: bool = False,
                        **kwargs) -> UnifiedAIResponse:
        """
        Execute AI task with unified routing and cost management.

        This is the core method that coordinates:
        1. Cost budget checking
        2. Model routing decisions
        3. Request execution with fallbacks
        4. Response validation and repair
        5. Cost tracking and analytics
        """

        start_time = datetime.now()
        warnings = []

        try:
            # Step 1: Estimate tokens and cost
            input_tokens = len(content) // 4  # Rough estimation
            estimated_output_tokens = min(500, input_tokens // 5)

            # Step 2: Create task specification
            task_spec = TaskSpec(
                kind=task_kind,
                input_tokens=input_tokens,
                content_type=self._detect_content_type(content),
                requires_long_ctx=input_tokens > 120_000,
                code_heavy=code_heavy,
                strict_json=strict_json,
                priority=priority
            )

            # Step 3: Check budget constraints
            chosen_model = force_model or self.router.choose_model(task_spec)
            model_info = self.router._get_model_info(chosen_model)
            estimated_cost = model_info.estimated_cost(input_tokens, estimated_output_tokens)

            # Budget check with cost manager
            budget_check = self.cost_manager.check_budget_limits(estimated_cost)

            if not budget_check['allowed']:
                log_info(self.log_path, f"AI request blocked by budget: {budget_check['reason']}")

                # Try cost-optimized fallback strategies
                fallback_result = self._try_cost_fallbacks(
                    task_kind, content, task_params, budget_check
                )

                if fallback_result:
                    return fallback_result

                # Budget exceeded, return error
                return UnifiedAIResponse(
                    success=False,
                    content='',
                    model_used='none',
                    cost_usd=0.0,
                    tokens_used=0,
                    response_time=0.0,
                    routing_decision={'blocked_by_budget': True},
                    budget_status=budget_check,
                    error=budget_check['reason']
                )

            # Step 4: Build messages for LLM
            messages = self._build_messages(task_kind, content, task_params)

            # Step 5: Execute with router (handles fallbacks automatically)
            router_result = self.router.execute_task(
                spec=task_spec,
                messages=messages,
                response_schema=response_schema,
                force_model=force_model
            )

            # Step 6: Process results
            if router_result['success']:
                # Record successful usage in cost manager
                actual_cost = router_result.get('cost_usd', estimated_cost)

                # Update cost manager statistics
                try:
                    self.cost_manager._record_api_usage(
                        operation=task_kind.value,
                        cost=actual_cost,
                        response_time=router_result.get('response_time', 0),
                        success=True,
                        tokens_used=router_result.get('tokens_used', 0)
                    )
                except Exception as e:
                    warnings.append(f"Cost tracking failed: {str(e)}")

                # Build successful response
                return UnifiedAIResponse(
                    success=True,
                    content=router_result['content'],
                    model_used=router_result['model'],
                    cost_usd=actual_cost,
                    tokens_used=router_result.get('tokens_used', 0),
                    response_time=router_result.get('response_time', 0),
                    routing_decision=router_result.get('routing_decision', {}),
                    fallback_used=task_spec.retry_count > 0,
                    budget_status=budget_check,
                    warnings=warnings,
                    metadata=router_result.get('metadata', {})
                )

            else:
                # Router failed, try final fallbacks
                log_error(self.log_path, f"Router execution failed: {router_result.get('error')}")

                final_fallback = self._try_final_fallbacks(
                    task_kind, content, task_params, router_result
                )

                if final_fallback:
                    final_fallback.warnings = warnings
                    return final_fallback

                # Complete failure
                return UnifiedAIResponse(
                    success=False,
                    content='',
                    model_used=router_result.get('model', 'unknown'),
                    cost_usd=0.0,
                    tokens_used=0,
                    response_time=router_result.get('response_time', 0),
                    routing_decision=router_result.get('routing_decision', {}),
                    budget_status=budget_check,
                    error=router_result.get('error', 'Unknown router error'),
                    warnings=warnings
                )

        except Exception as e:
            log_error(self.log_path, f"Critical error in unified AI system: {str(e)}")

            # Emergency fallback
            emergency_result = self._emergency_fallback(task_kind, content, task_params)
            emergency_result.warnings = warnings + [f"Emergency fallback due to: {str(e)}"]
            return emergency_result

    def _build_messages(self,
                       task_kind: TaskKind,
                       content: str,
                       params: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """Build optimized messages for different task types."""
        params = params or {}

        if task_kind == TaskKind.SUMMARIZE:
            target_length = params.get('target_length', 300)
            prompt = f"""Summarize the following content in approximately {target_length} characters. Focus on the main points and key insights.

Content:
{content}

Summary:"""

        elif task_kind == TaskKind.EXTRACT_JSON:
            extraction_prompt = params.get('extraction_prompt', 'Extract structured data')
            prompt = f"""{extraction_prompt} from the following content. Return only valid JSON.

Content:
{content}

JSON:"""

        elif task_kind == TaskKind.CLASSIFY:
            categories = params.get('categories', [])
            prompt = f"""Classify the following content into one of these categories: {', '.join(categories)}

Content:
{content}

Classification:"""

        elif task_kind == TaskKind.CODE_ANALYSIS:
            analysis_type = params.get('analysis_type', 'general')
            prompt = f"""Analyze the following code for {analysis_type} aspects. Provide detailed insights.

Code:
{content}

Analysis:"""

        else:
            prompt = f"""Process the following content for {task_kind.value}:

{content}

Response:"""

        return [{'role': 'user', 'content': prompt}]

    def _detect_content_type(self, content: str) -> str:
        """Detect content type for optimization."""
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in ['def ', 'class ', 'import ', 'function', '#!/']):
            return 'code'
        elif any(keyword in content_lower for keyword in ['<html', '<div', '<?xml']):
            return 'markup'
        elif content.count('\n') / len(content) > 0.1:
            return 'structured_text'
        else:
            return 'natural_text'

    def _try_cost_fallbacks(self,
                           task_kind: TaskKind,
                           content: str,
                           params: Dict[str, Any],
                           budget_check: Dict[str, Any]) -> Optional[UnifiedAIResponse]:
        """Try cost-optimized fallback strategies when budget is exceeded."""

        if not self.enable_fallbacks:
            return None

        # Strategy 1: Non-AI processing for summarization
        if task_kind == TaskKind.SUMMARIZE:
            try:
                # Use cost manager's extractive fallback
                from helpers.summarizer import ContentSummarizer
                summarizer = ContentSummarizer()

                target_length = params.get('target_length', 300)
                result = summarizer.extractive_summarize(content, target_length)

                return UnifiedAIResponse(
                    success=True,
                    content=result.get('summary', ''),
                    model_used='extractive_fallback',
                    cost_usd=0.0,
                    tokens_used=0,
                    response_time=0.5,
                    routing_decision={'fallback_strategy': 'extractive'},
                    fallback_used=True,
                    fallback_reason='budget_exceeded',
                    budget_status=budget_check,
                    cost_saved=0.01  # Estimated AI cost saved
                )
            except Exception as e:
                log_error(self.log_path, f"Extractive fallback failed: {str(e)}")

        # Strategy 2: Template-based responses
        template_response = self._generate_template_response(task_kind, content, params)
        if template_response:
            return template_response

        return None

    def _try_final_fallbacks(self,
                           task_kind: TaskKind,
                           content: str,
                           params: Dict[str, Any],
                           router_result: Dict[str, Any]) -> Optional[UnifiedAIResponse]:
        """Final fallback strategies when all AI methods fail."""

        # For summarization, always have a fallback
        if task_kind == TaskKind.SUMMARIZE:
            target_length = params.get('target_length', 300)
            simple_summary = content[:target_length] + '...' if len(content) > target_length else content

            return UnifiedAIResponse(
                success=True,
                content=simple_summary,
                model_used='simple_truncation',
                cost_usd=0.0,
                tokens_used=0,
                response_time=0.1,
                routing_decision={'final_fallback': True},
                fallback_used=True,
                fallback_reason='all_ai_methods_failed'
            )

        return None

    def _emergency_fallback(self,
                          task_kind: TaskKind,
                          content: str,
                          params: Dict[str, Any]) -> UnifiedAIResponse:
        """Emergency fallback for system failures."""

        emergency_content = f"Emergency fallback: Unable to process {task_kind.value} request due to system error."

        return UnifiedAIResponse(
            success=False,
            content=emergency_content,
            model_used='emergency_fallback',
            cost_usd=0.0,
            tokens_used=0,
            response_time=0.0,
            routing_decision={'emergency_fallback': True},
            fallback_used=True,
            fallback_reason='system_error',
            error='Emergency fallback activated'
        )

    def _generate_template_response(self,
                                  task_kind: TaskKind,
                                  content: str,
                                  params: Dict[str, Any]) -> Optional[UnifiedAIResponse]:
        """Generate template-based responses for basic tasks."""

        if task_kind == TaskKind.CLASSIFY:
            categories = params.get('categories', ['unknown'])

            # Simple keyword-based classification
            content_lower = content.lower()

            best_category = 'unknown'
            best_score = 0.0

            for category in categories:
                if category.lower() in content_lower:
                    best_category = category
                    best_score = 0.8
                    break

            if best_category == 'unknown' and categories:
                best_category = categories[0]  # Default to first category
                best_score = 0.1

            template_response = json.dumps({
                'category': best_category,
                'confidence': best_score,
                'reasoning': 'Template-based classification due to budget constraints'
            })

            return UnifiedAIResponse(
                success=True,
                content=template_response,
                model_used='template_classifier',
                cost_usd=0.0,
                tokens_used=0,
                response_time=0.2,
                routing_decision={'template_strategy': 'keyword_classification'},
                fallback_used=True,
                fallback_reason='budget_exceeded'
            )

        return None

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status and analytics."""
        try:
            router_stats = self.router.get_routing_stats()
            cost_report = self.cost_manager.get_cost_report()

            return {
                'timestamp': datetime.now().isoformat(),
                'system_status': 'operational',
                'routing': router_stats,
                'cost_management': cost_report,
                'capabilities': {
                    'summarization': True,
                    'json_extraction': True,
                    'classification': True,
                    'code_analysis': True,
                    'cost_management': True,
                    'intelligent_routing': True,
                    'fallback_strategies': self.enable_fallbacks
                },
                'configuration': {
                    'caching_enabled': self.enable_caching,
                    'fallbacks_enabled': self.enable_fallbacks,
                    'max_cost_per_request': self.max_cost_per_request
                }
            }

        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'system_status': 'degraded',
                'error': str(e)
            }


# Global unified AI instance
_unified_ai = None

def get_unified_ai(config: Dict[str, Any] = None) -> UnifiedAISystem:
    """Get global unified AI system instance."""
    global _unified_ai
    if _unified_ai is None:
        _unified_ai = UnifiedAISystem(config)
    return _unified_ai


if __name__ == "__main__":
    # Test the unified system
    ai = UnifiedAISystem()

    print("🤖 Unified AI System Test")
    print("=" * 50)

    # Test summarization
    test_content = "This is a test article about artificial intelligence and machine learning. " * 50

    result = ai.summarize(test_content, target_length=200)
    print(f"Summarization test:")
    print(f"  Success: {result.success}")
    print(f"  Model: {result.model_used}")
    print(f"  Cost: ${result.cost_usd:.6f}")
    print(f"  Fallback used: {result.fallback_used}")

    # Test system status
    status = ai.get_system_status()
    print(f"\nSystem Status: {status['system_status']}")
    print(f"Available capabilities: {len(status['capabilities'])}")