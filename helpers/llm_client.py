#!/usr/bin/env python3
"""
Unified LLM Client - OpenRouter integration with multi-provider support
Production-grade client with structured outputs, JSON repair, and error handling
"""

import os
import json
import re
import requests
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from helpers.utils import log_info, log_error


@dataclass
class LLMResponse:
    """Structured LLM response with metadata."""
    content: str
    model: str
    tokens_used: int
    cost_usd: float
    response_time: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class LLMClient:
    """
    Unified LLM client with OpenRouter integration.

    Features:
    - Multi-provider support (OpenRouter primary)
    - Structured JSON outputs with auto-repair
    - Cost tracking and optimization
    - Error handling with retries
    - Response caching
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize LLM client with configuration."""
        self.config = config or {}

        # OpenRouter configuration
        self.api_key = self.config.get('openrouter_api_key') or os.getenv('OPENROUTER_API_KEY', '')
        self.base_url = self.config.get('openrouter_base_url') or os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')

        # Request configuration
        self.timeout = self.config.get('llm_timeout', 90)
        self.max_retries = self.config.get('llm_max_retries', 2)

        # Headers for OpenRouter
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': self.config.get('app_url', 'https://github.com/atlas-local'),
            'X-Title': 'Atlas Unified AI System'
        }

        # Set up logging
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'llm_client.log')

        # Model pricing cache (updated from /models endpoint)
        self.model_pricing = {}
        self._update_model_pricing()

        log_info(self.log_path, f"LLM Client initialized (Provider: OpenRouter, Models: {len(self.model_pricing)})")

    def _update_model_pricing(self):
        """Update model pricing from OpenRouter API."""
        try:
            response = requests.get(f'{self.base_url}/models', headers=self.headers, timeout=10)
            if response.status_code == 200:
                models_data = response.json()

                for model in models_data.get('data', []):
                    model_id = model.get('id', '')
                    pricing = model.get('pricing', {})

                    self.model_pricing[model_id] = {
                        'input_per_1m': float(pricing.get('prompt', 0)),
                        'output_per_1m': float(pricing.get('completion', 0)),
                        'context_length': model.get('context_length', 0),
                        'updated_at': datetime.now().isoformat()
                    }

                log_info(self.log_path, f"Updated pricing for {len(self.model_pricing)} models")

        except Exception as e:
            log_error(self.log_path, f"Failed to update model pricing: {str(e)}")
            # Use fallback pricing
            self._set_fallback_pricing()

    def _set_fallback_pricing(self):
        """Set fallback pricing for key models."""
        self.model_pricing = {
            'meta-llama/llama-3.1-8b-instruct': {
                'input_per_1m': 0.015,
                'output_per_1m': 0.02,
                'context_length': 131072
            },
            'google/gemini-2.5-flash-lite': {
                'input_per_1m': 0.10,
                'output_per_1m': 0.40,
                'context_length': 1000000
            },
            'qwen/qwen-2.5-7b-instruct': {
                'input_per_1m': 0.04,
                'output_per_1m': 0.10,
                'context_length': 65536
            }
        }

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a request."""
        if model not in self.model_pricing:
            return 0.001  # Fallback estimate

        pricing = self.model_pricing[model]
        input_cost = (input_tokens / 1_000_000) * pricing['input_per_1m']
        output_cost = (output_tokens / 1_000_000) * pricing['output_per_1m']

        return round(input_cost + output_cost, 6)

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)."""
        return len(text) // 4

    def _build_json_schema_format(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Build OpenRouter structured output format."""
        return {
            'type': 'json_schema',
            'json_schema': {
                'name': 'response_schema',
                'schema': schema,
                'strict': True
            }
        }

    def chat_completion(self,
                       model: str,
                       messages: List[Dict[str, str]],
                       max_tokens: int = 2048,
                       temperature: float = 0.3,
                       response_schema: Optional[Dict[str, Any]] = None,
                       **kwargs) -> LLMResponse:
        """
        Make a chat completion request with full error handling.

        Args:
            model: Model identifier (e.g., 'meta-llama/llama-3.1-8b-instruct')
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0.0-1.0)
            response_schema: JSON schema for structured outputs
            **kwargs: Additional parameters

        Returns:
            LLMResponse with content, metadata, and cost information
        """
        if not self.api_key:
            return LLMResponse(
                content='',
                model=model,
                tokens_used=0,
                cost_usd=0.0,
                response_time=0.0,
                success=False,
                error='No API key configured'
            )

        start_time = time.time()

        # Estimate input tokens and cost
        input_text = ' '.join([msg.get('content', '') for msg in messages])
        input_tokens = self.estimate_tokens(input_text)
        estimated_cost = self.estimate_cost(model, input_tokens, max_tokens)

        # Build request payload
        payload = {
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            **kwargs
        }

        # Add structured output if schema provided
        if response_schema:
            payload['response_format'] = self._build_json_schema_format(response_schema)

        # Make request with retries
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    f'{self.base_url}/chat/completions',
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )

                response_time = time.time() - start_time

                if response.status_code == 200:
                    data = response.json()

                    # Extract response content
                    if 'choices' in data and data['choices']:
                        content = data['choices'][0]['message']['content']

                        # Calculate actual cost
                        usage = data.get('usage', {})
                        total_tokens = usage.get('total_tokens', input_tokens + max_tokens // 4)
                        actual_output_tokens = usage.get('completion_tokens', max_tokens // 4)
                        actual_cost = self.estimate_cost(model, input_tokens, actual_output_tokens)

                        return LLMResponse(
                            content=content,
                            model=model,
                            tokens_used=total_tokens,
                            cost_usd=actual_cost,
                            response_time=response_time,
                            success=True,
                            metadata={
                                'usage': usage,
                                'response_data': data,
                                'attempt': attempt + 1
                            }
                        )
                    else:
                        last_error = 'No choices in response'

                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get('retry-after', 5))
                    if attempt < self.max_retries:
                        log_info(f"Rate limited, waiting {retry_after}s before retry")
                        time.sleep(retry_after)
                        continue
                    last_error = f'Rate limited: {response.status_code}'

                elif response.status_code in [400, 401, 403]:
                    # Client errors - don't retry
                    last_error = f'Client error: {response.status_code} - {response.text}'
                    break

                else:
                    # Server errors - retry
                    last_error = f'Server error: {response.status_code} - {response.text}'
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue

            except requests.exceptions.Timeout:
                last_error = 'Request timeout'
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue

            except requests.exceptions.RequestException as e:
                last_error = f'Request failed: {str(e)}'
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue

            except Exception as e:
                last_error = f'Unexpected error: {str(e)}'
                break

        # All attempts failed
        response_time = time.time() - start_time
        log_error(f"LLM request failed after {self.max_retries + 1} attempts: {last_error}")

        return LLMResponse(
            content='',
            model=model,
            tokens_used=0,
            cost_usd=0.0,
            response_time=response_time,
            success=False,
            error=last_error
        )

    def is_valid_json(self, text: str, schema: Optional[Dict[str, Any]] = None) -> bool:
        """Check if text is valid JSON, optionally against schema."""
        try:
            data = json.loads(text)

            # Basic schema validation (simplified)
            if schema and 'properties' in schema:
                required_fields = schema.get('required', [])
                for field in required_fields:
                    if field not in data:
                        return False

            return True

        except (json.JSONDecodeError, TypeError):
            return False

    def repair_json(self, text: str) -> str:
        """Attempt to repair malformed JSON."""
        if not text:
            return text

        # Remove common issues
        text = text.strip()

        # Remove code fences
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)

        # Find JSON boundaries
        start = text.find('{')
        end = text.rfind('}')

        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]

            # Try to parse the candidate
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                # Try common fixes
                fixes = [
                    lambda s: s.replace('\\n', '\\\\n'),  # Escape newlines
                    lambda s: s.replace('\n', ' '),       # Remove actual newlines
                    lambda s: s.replace('\t', ' '),       # Remove tabs
                    lambda s: re.sub(r',\s*}', '}', s),   # Remove trailing commas
                    lambda s: re.sub(r',\s*]', ']', s),   # Remove trailing commas in arrays
                ]

                for fix in fixes:
                    try:
                        fixed = fix(candidate)
                        json.loads(fixed)
                        return fixed
                    except json.JSONDecodeError:
                        continue

        # If all else fails, return original
        return text

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get model information including pricing and limits."""
        return self.model_pricing.get(model, {
            'input_per_1m': 0.001,
            'output_per_1m': 0.001,
            'context_length': 4096,
            'status': 'unknown'
        })

    def list_available_models(self) -> List[str]:
        """List all available models."""
        return list(self.model_pricing.keys())


# Global client instance
_llm_client = None

def get_llm_client(config: Dict[str, Any] = None) -> LLMClient:
    """Get global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(config)
    return _llm_client


if __name__ == "__main__":
    # Test the client
    client = LLMClient()

    print("🤖 LLM Client Test")
    print("=" * 50)

    # Test model pricing
    models = client.list_available_models()
    print(f"Available models: {len(models)}")

    if models:
        test_model = models[0]
        info = client.get_model_info(test_model)
        print(f"Test model: {test_model}")
        print(f"Pricing: ${info['input_per_1m']:.3f}/${info['output_per_1m']:.3f} per 1M tokens")

    # Test JSON repair
    broken_json = '```json\n{"test": "value",}\n```'
    repaired = client.repair_json(broken_json)
    print(f"JSON repair test: {client.is_valid_json(repaired)}")