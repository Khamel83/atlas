"""
Cost Management for OOS
Tracks spending and enforces $1/day limit per project with Telegram notifications
"""

import asyncio
import json
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass

from renderers import Colors


@dataclass
class CostTracker:
    """Track daily costs for a project"""
    project_id: str
    date: str
    total_cost: float = 0.0
    api_calls: int = 0
    last_updated: datetime = None


class CostManager:
    """Manages OpenRouter costs and enforces daily limits"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.daily_limit = config.get('daily_cost_limit', 1.0)  # $1 default
        self.openrouter_api_key = config.get('openrouter_api_key')
        self.telegram_bot_token = config.get('telegram_bot_token')
        self.telegram_chat_id = config.get('telegram_chat_id')

        # Cost tracking storage
        self.cost_file = Path.home() / '.oos' / 'costs.json'
        self.cost_file.parent.mkdir(exist_ok=True)

        self.daily_costs: Dict[str, CostTracker] = self._load_costs()

    def _load_costs(self) -> Dict[str, CostTracker]:
        """Load cost tracking data"""
        if self.cost_file.exists():
            try:
                with open(self.cost_file, 'r') as f:
                    data = json.load(f)

                costs = {}
                for key, cost_data in data.items():
                    costs[key] = CostTracker(
                        project_id=cost_data['project_id'],
                        date=cost_data['date'],
                        total_cost=cost_data['total_cost'],
                        api_calls=cost_data['api_calls'],
                        last_updated=datetime.fromisoformat(cost_data['last_updated'])
                    )
                return costs
            except Exception as e:
                print(f"{Colors.YELLOW}⚠️  Could not load cost data: {e}{Colors.END}")

        return {}

    def _save_costs(self):
        """Save cost tracking data"""
        try:
            data = {}
            for key, tracker in self.daily_costs.items():
                data[key] = {
                    'project_id': tracker.project_id,
                    'date': tracker.date,
                    'total_cost': tracker.total_cost,
                    'api_calls': tracker.api_calls,
                    'last_updated': tracker.last_updated.isoformat()
                }

            with open(self.cost_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"{Colors.RED}❌ Could not save cost data: {e}{Colors.END}")

    def _get_cost_key(self, project_id: str) -> str:
        """Get cost tracking key for today"""
        today = date.today().isoformat()
        return f"{project_id}:{today}"

    async def check_can_proceed(self, project_id: str, estimated_cost: float = 0.01) -> bool:
        """Check if we can proceed without exceeding daily limit"""
        cost_key = self._get_cost_key(project_id)

        if cost_key not in self.daily_costs:
            self.daily_costs[cost_key] = CostTracker(
                project_id=project_id,
                date=date.today().isoformat(),
                last_updated=datetime.now()
            )

        tracker = self.daily_costs[cost_key]

        if tracker.total_cost + estimated_cost > self.daily_limit:
            await self._send_limit_notification(project_id, tracker.total_cost)
            return False

        return True

    async def record_api_call(self, project_id: str, cost: float, tokens_used: int = 0):
        """Record an API call and its cost"""
        cost_key = self._get_cost_key(project_id)

        if cost_key not in self.daily_costs:
            self.daily_costs[cost_key] = CostTracker(
                project_id=project_id,
                date=date.today().isoformat(),
                last_updated=datetime.now()
            )

        tracker = self.daily_costs[cost_key]
        tracker.total_cost += cost
        tracker.api_calls += 1
        tracker.last_updated = datetime.now()

        # Check if we hit the limit
        if tracker.total_cost >= self.daily_limit:
            await self._send_limit_notification(project_id, tracker.total_cost)

        # Save to disk
        self._save_costs()

        print(f"{Colors.BLUE}💰 Cost: ${cost:.4f} | Daily total: ${tracker.total_cost:.4f}/{self.daily_limit}{Colors.END}")

    async def _send_limit_notification(self, project_id: str, current_cost: float):
        """Send Telegram notification when daily limit is reached"""
        message = f"""🚨 OOS Daily Cost Limit Reached

Project: {project_id}
Daily Spend: ${current_cost:.2f}
Limit: ${self.daily_limit:.2f}

OOS has stopped making API calls for this project today to stay within budget.

Reset tomorrow or increase limit in config."""

        print(f"{Colors.RED}🚨 COST LIMIT REACHED: {project_id} (${current_cost:.2f}){Colors.END}")
        print(message)

        # Send Telegram notification if configured
        if self.telegram_bot_token and self.telegram_chat_id:
            await self._send_telegram_message(message)

    async def _send_telegram_message(self, message: str):
        """Send notification via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"

            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        print(f"{Colors.GREEN}📱 Telegram notification sent{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}⚠️  Telegram notification failed: {response.status}{Colors.END}")

        except Exception as e:
            print(f"{Colors.RED}❌ Telegram notification error: {e}{Colors.END}")

    def get_daily_summary(self, project_id: str = None) -> Dict[str, Any]:
        """Get daily cost summary"""
        today = date.today().isoformat()

        if project_id:
            cost_key = f"{project_id}:{today}"
            tracker = self.daily_costs.get(cost_key)

            if tracker:
                return {
                    'project_id': project_id,
                    'date': today,
                    'total_cost': tracker.total_cost,
                    'api_calls': tracker.api_calls,
                    'limit': self.daily_limit,
                    'remaining': max(0, self.daily_limit - tracker.total_cost),
                    'percentage_used': (tracker.total_cost / self.daily_limit) * 100
                }
            else:
                return {
                    'project_id': project_id,
                    'date': today,
                    'total_cost': 0.0,
                    'api_calls': 0,
                    'limit': self.daily_limit,
                    'remaining': self.daily_limit,
                    'percentage_used': 0.0
                }
        else:
            # Summary across all projects today
            today_trackers = [t for t in self.daily_costs.values() if t.date == today]

            total_cost = sum(t.total_cost for t in today_trackers)
            total_calls = sum(t.api_calls for t in today_trackers)

            return {
                'date': today,
                'total_cost': total_cost,
                'total_calls': total_calls,
                'active_projects': len(today_trackers),
                'average_per_project': total_cost / len(today_trackers) if today_trackers else 0,
                'daily_limit': self.daily_limit
            }

    def estimate_openrouter_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for OpenRouter API call"""
        # Pricing for common models (as of 2024)
        model_pricing = {
            'google/gemini-2.0-flash-exp': {
                'input': 0.000001,   # $0.000001 per input token
                'output': 0.000003   # $0.000003 per output token
            },
            'anthropic/claude-3.5-sonnet': {
                'input': 0.000003,   # $0.000003 per input token
                'output': 0.000015   # $0.000015 per output token
            },
            'openai/gpt-4': {
                'input': 0.00003,    # $0.00003 per input token
                'output': 0.00006    # $0.00006 per output token
            }
        }

        # Default to Gemini Flash pricing
        pricing = model_pricing.get(model, model_pricing['google/gemini-2.0-flash-exp'])

        input_cost = input_tokens * pricing['input']
        output_cost = output_tokens * pricing['output']

        return input_cost + output_cost


# Global instance
_cost_manager = None


def get_cost_manager(config: Dict[str, Any]) -> CostManager:
    """Get or create cost manager instance"""
    global _cost_manager
    if _cost_manager is None:
        _cost_manager = CostManager(config)
    return _cost_manager


async def check_cost_limit(project_id: str, config: Dict[str, Any], estimated_cost: float = 0.01) -> bool:
    """Convenience function to check cost limits"""
    cost_manager = get_cost_manager(config)
    return await cost_manager.check_can_proceed(project_id, estimated_cost)


async def record_api_cost(project_id: str, config: Dict[str, Any], cost: float, tokens: int = 0):
    """Convenience function to record API costs"""
    cost_manager = get_cost_manager(config)
    await cost_manager.record_api_call(project_id, cost, tokens)


if __name__ == "__main__":
    # Test cost management
    async def test():
        config = {
            'daily_cost_limit': 1.0,
            'telegram_bot_token': 'demo-token',
            'telegram_chat_id': 'demo-chat'
        }

        cost_manager = CostManager(config)

        # Test cost tracking
        project_id = "test-project"

        print(f"{Colors.CYAN}Testing cost management...{Colors.END}")

        # Simulate some API calls
        for i in range(5):
            cost = 0.25  # 25 cents per call
            can_proceed = await cost_manager.check_can_proceed(project_id, cost)

            if can_proceed:
                await cost_manager.record_api_call(project_id, cost, 1000)
                print(f"Call {i+1}: Recorded ${cost}")
            else:
                print(f"Call {i+1}: BLOCKED - would exceed limit")
                break

        # Show summary
        summary = cost_manager.get_daily_summary(project_id)
        print(f"\n{Colors.CYAN}Daily Summary:{Colors.END}")
        print(f"  Cost: ${summary['total_cost']:.2f} / ${summary['limit']:.2f}")
        print(f"  Calls: {summary['api_calls']}")
        print(f"  Remaining: ${summary['remaining']:.2f}")

    asyncio.run(test())