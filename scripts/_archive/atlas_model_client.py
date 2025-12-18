#!/usr/bin/env python3
"""
Atlas Model Client - Production Ready Single Model System
Using Gemini 2.5 Flash Lite for all Atlas workloads

This is the ONLY LLM client Atlas needs. Simple, fast, reliable.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AtlasModelClient:
    """Production single model client for all Atlas workloads"""

    def __init__(self):
        # Configuration
        self.model_id = "google/gemini-2.5-flash-lite"
        self.api_key = os.getenv('OPENROUTER_API_KEY', '')
        self.base_url = "https://openrouter.ai/api/v1"

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        # Model specs
        self.cost_per_1k_tokens = 0.00005  # $0.05/1M tokens
        self.quality_score = 9.5

        # No token limits - let the model generate complete responses
        self.workload_tokens = {
            'tags': 10000,
            'summary': 10000,
            'socratic': 10000,
            'patterns': 10000,
            'recommendations': 10000
        }

        logger.info(f"Atlas Model Client initialized: {self.model_id}")

    def process_workload(self, workload: str, content: str, title: str = "") -> Tuple[str, Dict[str, Any]]:
        """Process Atlas workload with single optimal model"""

        prompt = self._get_workload_prompt(workload, content, title)
        max_tokens = self.workload_tokens.get(workload, 10000)  # No token limits

        try:
            response = self._call_openrouter(prompt, max_tokens)

            # Parse response
            if 'choices' in response and len(response['choices']) > 0:
                result = response['choices'][0]['message']['content'].strip()

                # Calculate metadata
                tokens_used = response.get('usage', {}).get('total_tokens', max_tokens)
                cost_estimate = (tokens_used / 1000) * self.cost_per_1k_tokens

                metadata = {
                    'model': self.model_id,
                    'workload': workload,
                    'tokens': tokens_used,
                    'cost': cost_estimate,
                    'quality_score': self.quality_score,
                    'status': 'success'
                }

                logger.info(f"✅ {workload}: {tokens_used} tokens, ${cost_estimate:.6f}")
                return result, metadata
            else:
                raise ValueError("Invalid response format from OpenRouter")

        except Exception as e:
            error_msg = f"Failed {workload}: {str(e)}"
            logger.error(error_msg)

            metadata = {
                'model': self.model_id,
                'workload': workload,
                'status': 'failed',
                'error': str(e)
            }

            return f"ERROR: {error_msg}", metadata

    def _call_openrouter(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Call OpenRouter API directly with proper error handling"""

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/anthropics/atlas',
            'X-Title': 'Atlas Personal Knowledge System'
        }

        data = {
            'model': self.model_id,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': 0.3
        }

        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )

            logger.debug(f"OpenRouter response status: {response.status_code}")

            if response.status_code == 401:
                raise Exception(f"OpenRouter authentication failed: {response.text}")
            elif response.status_code != 200:
                raise Exception(f"OpenRouter API error {response.status_code}: {response.text}")

            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error calling OpenRouter: {str(e)}")

    def _get_workload_prompt(self, workload: str, content: str, title: str) -> str:
        """Get optimized prompt for each workload"""

        prompts = {
            'tags': f"Generate 3-5 relevant tags for this article. Return only tags, comma-separated.\n\nTitle: {title}\nContent: {content[:800]}...",

            'summary': f"Write a concise 2-3 sentence summary capturing key points.\n\nTitle: {title}\nContent: {content}",

            'socratic': f"Generate 2 thoughtful Socratic questions to provoke deeper thinking.\n\nTitle: {title}\nContent: {content[:1500]}...",

            'patterns': f"Identify 1-2 key patterns or themes connecting to broader trends.\n\nTitle: {title}\nContent: {content[:1500]}...",

            'recommendations': f"Suggest 2 specific follow-up actions or resources to explore.\n\nTitle: {title}\nContent: {content[:1500]}..."
        }

        return prompts.get(workload, f"Process this content for {workload}:\n\n{content}")

    def get_stats(self) -> Dict[str, Any]:
        """Get model statistics and configuration"""
        return {
            'model_id': self.model_id,
            'cost_per_1k_tokens': self.cost_per_1k_tokens,
            'quality_score': self.quality_score,
            'workload_tokens': self.workload_tokens
        }

# Convenience functions
def create_client() -> AtlasModelClient:
    """Create Atlas model client"""
    return AtlasModelClient()

def process_content(workload: str, content: str, title: str = "") -> Tuple[str, Dict[str, Any]]:
    """Process content with Atlas model"""
    client = create_client()
    return client.process_workload(workload, content, title)

if __name__ == "__main__":
    # Test the client
    client = create_client()

    print("🎯 Atlas Model Client - Production Ready")
    print("=" * 50)
    print(f"Model: {client.model_id}")
    print(f"Cost: ${client.cost_per_1k_tokens * 1000:.2f}/1M tokens")
    print(f"Quality Score: {client.quality_score}/10")
    print()

    # Test with sample content
    test_content = "Artificial intelligence is transforming business operations through automation, predictive analytics, and enhanced decision-making capabilities."
    test_title = "AI Business Transformation"

    for workload in ['tags', 'summary']:
        print(f"Testing {workload}...")
        result, metadata = client.process_workload(workload, test_content, test_title)

        if metadata['status'] == 'success':
            print(f"  ✅ Success: {metadata['tokens']} tokens, ${metadata['cost']:.6f}")
            print(f"  Result: {result}")
        else:
            print(f"  ❌ Failed: {metadata.get('error', 'Unknown error')}")
        print()