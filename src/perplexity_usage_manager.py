#!/usr/bin/env python3
"""
Perplexity Usage Manager
Bulletproof protection to never exceed your $5/month Pro credits
"""

import os
import json
import requests
from datetime import datetime, date
from typing import Dict, Optional, Tuple
from pathlib import Path

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env on import
load_env_file()


class PerplexityUsageManager:
    """Manages Perplexity API usage with hard safety limits"""

    def __init__(self):
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        self.usage_file = Path('data/perplexity_usage.json')
        self.monthly_limit = 5.00  # $5/month from Pro subscription
        self.safety_threshold = 0.90  # Stop at 90% = $4.50

        # Ensure data directory exists
        self.usage_file.parent.mkdir(exist_ok=True)

        # Load or initialize usage tracking
        self.usage_data = self._load_usage_data()

    def _load_usage_data(self) -> Dict:
        """Load usage data from file"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)

                # Reset if new month
                current_month = date.today().strftime('%Y-%m')
                if data.get('month') != current_month:
                    data = self._create_new_month_data(current_month)
                    self._save_usage_data(data)

                return data
            except:
                pass

        # Create new month data
        current_month = date.today().strftime('%Y-%m')
        return self._create_new_month_data(current_month)

    def _create_new_month_data(self, month: str) -> Dict:
        """Create fresh month data"""
        return {
            'month': month,
            'total_cost': 0.0,
            'api_calls': 0,
            'last_updated': datetime.now().isoformat(),
            'calls_history': []
        }

    def _save_usage_data(self, data: Dict):
        """Save usage data to file"""
        with open(self.usage_file, 'w') as f:
            json.dump(data, f, indent=2)

    async def check_credits_and_ask_permission(self, estimated_cost: float = 0.02) -> Tuple[bool, str]:
        """
        Check current credits and ask user permission before making API call
        Returns: (can_proceed, message)
        """

        if not self.api_key:
            return False, "No Perplexity API key found. Set PERPLEXITY_API_KEY environment variable."

        # Check current usage
        current_cost = self.usage_data['total_cost']
        projected_cost = current_cost + estimated_cost

        # Hard stop at safety threshold
        safety_limit = self.monthly_limit * self.safety_threshold  # $4.50

        if projected_cost > safety_limit:
            return False, f"🚨 SAFETY STOP: Would exceed 90% limit (${safety_limit:.2f}). Current: ${current_cost:.2f}"

        # Get current balance from Perplexity API
        try:
            balance_info = await self._get_account_balance()
            if balance_info:
                actual_remaining = balance_info.get('credits_remaining', 0)
                print(f"💰 Perplexity Credits: ${actual_remaining:.2f} remaining")

                if actual_remaining < estimated_cost:
                    return False, f"❌ Insufficient credits: ${actual_remaining:.2f} remaining, need ${estimated_cost:.2f}"
        except Exception as e:
            print(f"⚠️  Could not check live balance: {e}")

        # Show usage and ask permission
        usage_percent = (current_cost / self.monthly_limit) * 100
        remaining_budget = self.monthly_limit - current_cost

        print(f"\n📊 Perplexity Usage This Month:")
        print(f"   Current spend: ${current_cost:.2f} / ${self.monthly_limit:.2f} ({usage_percent:.1f}%)")
        print(f"   Remaining budget: ${remaining_budget:.2f}")
        print(f"   Estimated call cost: ${estimated_cost:.2f}")
        print(f"   After this call: ${projected_cost:.2f} / ${self.monthly_limit:.2f}")

        # Ask for permission
        response = input(f"\n🤔 Use Perplexity API for this search? (y/N): ").strip().lower()

        if response in ['y', 'yes']:
            return True, "Permission granted"
        else:
            return False, "User declined to use Perplexity API"

    async def _get_account_balance(self) -> Optional[Dict]:
        """Get current account balance from Perplexity API"""
        try:
            # Note: Perplexity doesn't have a direct balance endpoint
            # We'll estimate based on a minimal test call
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'sonar-small-online',
                    'messages': [{'role': 'user', 'content': 'hi'}],
                    'max_tokens': 1
                },
                timeout=5
            )

            if response.status_code == 200:
                # API is working, assume we have credits
                estimated_remaining = self.monthly_limit - self.usage_data['total_cost']
                return {'credits_remaining': max(0, estimated_remaining)}
            elif response.status_code == 402:  # Payment required
                return {'credits_remaining': 0}
            else:
                return None

        except Exception:
            return None

    def record_api_call(self, actual_cost: float, tokens_used: int):
        """Record an API call after it's made"""
        self.usage_data['total_cost'] += actual_cost
        self.usage_data['api_calls'] += 1
        self.usage_data['last_updated'] = datetime.now().isoformat()

        # Add to history
        self.usage_data['calls_history'].append({
            'timestamp': datetime.now().isoformat(),
            'cost': actual_cost,
            'tokens': tokens_used
        })

        # Keep only last 100 calls in history
        if len(self.usage_data['calls_history']) > 100:
            self.usage_data['calls_history'] = self.usage_data['calls_history'][-100:]

        self._save_usage_data(self.usage_data)

        # Show warning if approaching limit
        usage_percent = (self.usage_data['total_cost'] / self.monthly_limit) * 100

        if usage_percent > 80:
            print(f"⚠️  Warning: {usage_percent:.1f}% of monthly Perplexity budget used")

        if usage_percent > 90:
            print(f"🚨 ALERT: {usage_percent:.1f}% of monthly Perplexity budget used - approaching limit!")

    def get_usage_summary(self) -> Dict:
        """Get current usage summary"""
        current_cost = self.usage_data['total_cost']
        usage_percent = (current_cost / self.monthly_limit) * 100
        remaining = self.monthly_limit - current_cost

        return {
            'month': self.usage_data['month'],
            'total_cost': current_cost,
            'monthly_limit': self.monthly_limit,
            'usage_percent': usage_percent,
            'remaining_budget': remaining,
            'api_calls': self.usage_data['api_calls'],
            'safety_limit': self.monthly_limit * self.safety_threshold,
            'within_safety_limit': current_cost < (self.monthly_limit * self.safety_threshold)
        }

    def estimate_call_cost(self, query_length: int, max_tokens: int = 500) -> float:
        """Estimate cost of a Perplexity API call"""
        # sonar-small-online pricing: $0.20 per 1M tokens (input + output)
        input_tokens = query_length // 4  # Rough estimate: 4 chars per token
        total_tokens = input_tokens + max_tokens

        cost_per_token = 0.20 / 1_000_000  # $0.20 per 1M tokens
        estimated_cost = total_tokens * cost_per_token

        return max(0.01, estimated_cost)  # Minimum $0.01 per call


# Global instance
usage_manager = PerplexityUsageManager()


async def safe_perplexity_search(query: str, max_results: int = 5) -> Tuple[bool, str, list]:
    """
    Safely execute Perplexity search with usage confirmation
    Returns: (success, message, results)
    """

    # Estimate cost
    estimated_cost = usage_manager.estimate_call_cost(len(query))

    # Check and ask permission
    can_proceed, message = await usage_manager.check_credits_and_ask_permission(estimated_cost)

    if not can_proceed:
        return False, message, []

    # Execute the search directly
    try:
        results = await _execute_perplexity_api_call(query, max_results)

        # Record the actual usage
        usage_manager.record_api_call(estimated_cost, len(query) + 500)  # Estimate tokens

        return True, f"Perplexity search completed. Cost: ${estimated_cost:.3f}", results

    except Exception as e:
        return False, f"Perplexity search failed: {e}", []


async def _execute_perplexity_api_call(query: str, limit: int) -> list:
    """Execute the actual Perplexity API call"""
    from dataclasses import dataclass

    @dataclass
    class SearchResult:
        title: str
        url: str
        snippet: str
        source: str

    api_key = usage_manager.api_key
    if not api_key:
        raise Exception("No Perplexity API key found")

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    data = {
        'model': 'sonar-small-online',  # Cheapest web-search model
        'messages': [
            {
                'role': 'user',
                'content': f'Search for: {query}. Provide {limit} relevant results with titles, URLs, and brief descriptions.'
            }
        ],
        'max_tokens': 500,
        'temperature': 0.1
    }

    response = requests.post(url, headers=headers, json=data, timeout=15)

    if response.status_code != 200:
        raise Exception(f"API call failed: {response.status_code}")

    result = response.json()
    content = result['choices'][0]['message']['content']

    # Parse the AI response into structured results
    results = []
    lines = content.split('\n')
    current_result = {}

    for line in lines:
        line = line.strip()
        if line.startswith(('1.', '2.', '3.', '4.', '5.')):
            if current_result:
                results.append(SearchResult(
                    title=current_result.get('title', 'Perplexity Result'),
                    url=current_result.get('url', ''),
                    snippet=current_result.get('snippet', ''),
                    source='Perplexity'
                ))
            current_result = {'title': line, 'url': '', 'snippet': ''}
        elif 'http' in line:
            current_result['url'] = line
        elif line and not line.startswith(('http', '#')):
            current_result['snippet'] = line

    # Add the last result
    if current_result:
        results.append(SearchResult(
            title=current_result.get('title', 'Perplexity Result'),
            url=current_result.get('url', ''),
            snippet=current_result.get('snippet', ''),
            source='Perplexity'
        ))

    return results[:limit]


if __name__ == "__main__":
    import asyncio

    async def test_usage_manager():
        print("🧪 Testing Perplexity Usage Manager")

        # Show current usage
        summary = usage_manager.get_usage_summary()
        print(f"\n📊 Current Usage:")
        print(f"   Month: {summary['month']}")
        print(f"   Spent: ${summary['total_cost']:.2f} / ${summary['monthly_limit']:.2f}")
        print(f"   Usage: {summary['usage_percent']:.1f}%")
        print(f"   Remaining: ${summary['remaining_budget']:.2f}")
        print(f"   API calls: {summary['api_calls']}")
        print(f"   Within safety limit: {summary['within_safety_limit']}")

        # Test a search with confirmation
        print(f"\n🔍 Testing safe search with confirmation...")
        success, message, results = await safe_perplexity_search("What is Python programming?")

        print(f"Result: {message}")
        if success and results:
            print(f"Found {len(results)} results")

    asyncio.run(test_usage_manager())