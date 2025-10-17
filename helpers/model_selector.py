"""
Enhanced Model Selector with Free-First Logic, Usage Tracking, and Rate Limiting
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import litellm
import requests

from helpers.config import load_config

# Configuration
USAGE_TRACKING_FILE = "model_usage_tracking.json"
MODEL_DISCOVERY_FILE = "model_discovery_cache.json"
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
DEFAULT_RATE_LIMIT = 100  # requests per hour per model


class ModelUsageTracker:
    """Track model usage, costs, and rate limits"""

    def __init__(self, tracking_file: str = USAGE_TRACKING_FILE):
        self.tracking_file = tracking_file
        self.usage_data = self._load_usage_data()

    def _load_usage_data(self) -> Dict:
        """Load usage data from file"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load usage data: {e}")

        return {
            "models": {},
            "daily_totals": {},
            "monthly_totals": {},
            "rate_limits": {},
            "last_updated": datetime.now().isoformat(),
        }

    def _save_usage_data(self):
        """Save usage data to file"""
        try:
            self.usage_data["last_updated"] = datetime.now().isoformat()
            with open(self.tracking_file, "w") as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save usage data: {e}")

    def record_usage(
        self, model: str, tokens_used: int = 0, cost: float = 0.0, success: bool = True
    ):
        """Record model usage"""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        # Initialize model data if not exists
        if model not in self.usage_data["models"]:
            self.usage_data["models"][model] = {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "success_rate": 0.0,
                "last_used": None,
                "failures": 0,
                "daily_usage": {},
                "hourly_usage": {},
            }

        # Update model stats
        model_data = self.usage_data["models"][model]
        model_data["total_requests"] += 1
        model_data["total_tokens"] += tokens_used
        model_data["total_cost"] += cost
        model_data["last_used"] = datetime.now().isoformat()

        if not success:
            model_data["failures"] += 1

        # Calculate success rate
        model_data["success_rate"] = (
            model_data["total_requests"] - model_data["failures"]
        ) / model_data["total_requests"]

        # Update daily usage
        if today not in model_data["daily_usage"]:
            model_data["daily_usage"][today] = {"requests": 0, "tokens": 0, "cost": 0.0}

        model_data["daily_usage"][today]["requests"] += 1
        model_data["daily_usage"][today]["tokens"] += tokens_used
        model_data["daily_usage"][today]["cost"] += cost

        # Update hourly usage for rate limiting
        hour = datetime.now().strftime("%Y-%m-%d-%H")
        if hour not in model_data["hourly_usage"]:
            model_data["hourly_usage"][hour] = 0
        model_data["hourly_usage"][hour] += 1

        # Update daily totals
        if today not in self.usage_data["daily_totals"]:
            self.usage_data["daily_totals"][today] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0,
            }

        self.usage_data["daily_totals"][today]["requests"] += 1
        self.usage_data["daily_totals"][today]["tokens"] += tokens_used
        self.usage_data["daily_totals"][today]["cost"] += cost

        # Update monthly totals
        if month not in self.usage_data["monthly_totals"]:
            self.usage_data["monthly_totals"][month] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0,
            }

        self.usage_data["monthly_totals"][month]["requests"] += 1
        self.usage_data["monthly_totals"][month]["tokens"] += tokens_used
        self.usage_data["monthly_totals"][month]["cost"] += cost

        self._save_usage_data()

    def is_rate_limited(self, model: str, limit: int = DEFAULT_RATE_LIMIT) -> bool:
        """Check if model is rate limited"""
        if model not in self.usage_data["models"]:
            return False

        model_data = self.usage_data["models"][model]
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")

        # Clean old hourly data (older than 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        cutoff_hour = cutoff_time.strftime("%Y-%m-%d-%H")

        old_hours = [h for h in model_data["hourly_usage"].keys() if h < cutoff_hour]
        for hour in old_hours:
            del model_data["hourly_usage"][hour]

        # Check current hour usage
        current_usage = model_data["hourly_usage"].get(current_hour, 0)
        return current_usage >= limit

    def get_model_stats(self, model: str) -> Dict:
        """Get statistics for a specific model"""
        return self.usage_data["models"].get(model, {})

    def get_usage_summary(self) -> Dict:
        """Get overall usage summary"""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        return {
            "today": self.usage_data["daily_totals"].get(today, {}),
            "this_month": self.usage_data["monthly_totals"].get(month, {}),
            "total_models": len(self.usage_data["models"]),
            "active_models": len(
                [m for m in self.usage_data["models"].values() if m.get("last_used")]
            ),
        }


class ModelDiscovery:
    """Discover and validate available models"""

    def __init__(self, cache_file: str = MODEL_DISCOVERY_FILE):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.config = load_config()

    def _load_cache(self) -> Dict:
        """Load model discovery cache"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load model cache: {e}")

        return {
            "last_updated": None,
            "available_models": {},
            "free_models": [],
            "paid_models": [],
            "model_status": {},
        }

    def _save_cache(self):
        """Save model discovery cache"""
        try:
            self.cache["last_updated"] = datetime.now().isoformat()
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save model cache: {e}")

    def discover_free_models(self) -> List[str]:
        """Discover available free models using OpenRouter API"""
        try:
            # Get API key
            api_key = self.config.get("OPENROUTER_API_KEY")
            if not api_key:
                logging.warning(
                    "No OpenRouter API key found, using fallback model list"
                )
                return self._get_fallback_free_models()

            # Call OpenRouter models API
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                "https://openrouter.ai/api/v1/models", headers=headers, timeout=30
            )

            if response.status_code != 200:
                logging.warning(
                    f"OpenRouter API returned {response.status_code}, using fallback"
                )
                return self._get_fallback_free_models()

            models_data = response.json()
            free_models = []
            paid_models = []

            # Process model data
            for model in models_data.get("data", []):
                model_id = model.get("id")
                pricing = model.get("pricing", {})

                if not model_id:
                    continue

                # Check if model is free (all pricing fields are "0" or 0)
                is_free = (
                    str(pricing.get("prompt", "1")) == "0"
                    and str(pricing.get("completion", "1")) == "0"
                    and str(pricing.get("request", "1")) == "0"
                )

                # Store model info
                model_info = {
                    "id": model_id,
                    "name": model.get("name", model_id),
                    "pricing": pricing,
                    "context_length": model.get("context_length", 0),
                    "description": model.get("description", ""),
                    "is_free": is_free,
                    "discovered_at": datetime.now().isoformat(),
                }

                self.cache["available_models"][model_id] = model_info

                if is_free:
                    free_models.append(model_id)
                else:
                    paid_models.append(model_id)

            # Update cache
            self.cache["free_models"] = free_models
            self.cache["paid_models"] = paid_models
            self._save_cache()

            logging.info(
                f"Discovered {len(free_models)} free models and {len(paid_models)} paid models"
            )
            return free_models

        except Exception as e:
            logging.error(f"Failed to discover models via API: {e}")
            return self._get_fallback_free_models()

    def _get_fallback_free_models(self) -> List[str]:
        """Fallback list of known free models when API fails"""
        fallback_models = [
            "deepseek/deepseek-r1:free",
            "deepseek/deepseek-v3:free",
            "google/gemma-2-9b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "qwen/qwen-2.5-7b-instruct:free",
            "microsoft/phi-3-mini-128k-instruct:free",
            "microsoft/phi-3-medium-128k-instruct:free",
            "huggingface/zephyr-7b-beta:free",
            "openchat/openchat-7b:free",
        ]

        # Test availability of fallback models
        available_models = []
        for model in fallback_models:
            if self.test_model_availability(model):
                available_models.append(model)

        self.cache["free_models"] = available_models
        self._save_cache()
        return available_models

    def get_model_info(self, model_id: str) -> Dict:
        """Get detailed information about a specific model"""
        return self.cache["available_models"].get(model_id, {})

    def get_free_models_by_provider(self) -> Dict[str, List[str]]:
        """Get free models grouped by provider"""
        free_models = self.cache.get("free_models", [])
        providers = {}

        for model in free_models:
            if "/" in model:
                provider = model.split("/")[0]
                if provider not in providers:
                    providers[provider] = []
                providers[provider].append(model)

        return providers

    def test_model_availability(self, model: str) -> bool:
        """Test if a model is available and working"""
        try:
            # Try a minimal completion
            litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1,
                timeout=10,
            )

            self.cache["model_status"][model] = {
                "available": True,
                "last_tested": datetime.now().isoformat(),
                "error": None,
            }
            self._save_cache()
            return True

        except Exception as e:
            self.cache["model_status"][model] = {
                "available": False,
                "last_tested": datetime.now().isoformat(),
                "error": str(e),
            }
            self._save_cache()
            return False

    def should_update_cache(self, max_age_days: int = 7) -> bool:
        """Check if cache should be updated"""
        if not self.cache.get("last_updated"):
            return True

        last_updated = datetime.fromisoformat(self.cache["last_updated"])
        age = datetime.now() - last_updated
        return age.days >= max_age_days


class EnhancedModelSelector:
    """Enhanced model selector with free-first logic and intelligent fallbacks"""

    def __init__(self):
        self.config = load_config()
        self.usage_tracker = ModelUsageTracker()
        self.discovery = ModelDiscovery()
        self.logger = logging.getLogger(__name__)

        # Initialize tier mapping
        self.tier_map = self._build_tier_map()

        # Performance classifications
        self.fast_models = {
            "google/gemma-2-9b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "qwen/qwen-2.5-7b-instruct:free",
        }

        self.high_quality_models = {
            "deepseek/deepseek-r1:free",
            "deepseek/deepseek-v3:free",
            "meta-llama/llama-3.1-8b-instruct:free",
        }

    def _build_tier_map(self) -> Dict:
        """Build tier mapping from configuration"""
        return {
            "premium": {
                "free": [
                    self.config.get(
                        "MODEL_FREE_PREMIUM_1", "deepseek/deepseek-r1:free"
                    ),
                    self.config.get(
                        "MODEL_FREE_PREMIUM_2", "deepseek/deepseek-v3:free"
                    ),
                    self.config.get(
                        "MODEL_FREE_PREMIUM_3", "meta-llama/llama-3.1-8b-instruct:free"
                    ),
                ],
                "paid": self.config.get(
                    "MODEL_PREMIUM", "google/gemini-2.0-flash-lite-001"
                ),
            },
            "fallback": {
                "free": [
                    self.config.get(
                        "MODEL_FREE_FALLBACK_1", "google/gemma-2-9b-it:free"
                    ),
                    self.config.get(
                        "MODEL_FREE_FALLBACK_2", "mistralai/mistral-7b-instruct:free"
                    ),
                    self.config.get(
                        "MODEL_FREE_FALLBACK_3", "qwen/qwen-2.5-7b-instruct:free"
                    ),
                ],
                "paid": self.config.get(
                    "MODEL_FALLBACK", "google/gemini-2.0-flash-lite-001"
                ),
            },
            "budget": {
                "free": [
                    self.config.get(
                        "MODEL_FREE_BUDGET_1", "mistralai/mistral-7b-instruct:free"
                    ),
                    self.config.get(
                        "MODEL_FREE_BUDGET_2", "qwen/qwen-2.5-7b-instruct:free"
                    ),
                    self.config.get("MODEL_FREE_BUDGET_3", "google/gemma-2-9b-it:free"),
                ],
                "paid": self.config.get(
                    "MODEL_BUDGET", "mistralai/mistral-7b-instruct"
                ),
            },
        }

    def select_model(
        self,
        tier: str = "fallback",
        require_fast: bool = False,
        require_quality: bool = False,
    ) -> Tuple[str, str]:
        """
        Select the best available model for a tier with constraints

        Args:
            tier: Model tier (premium, fallback, budget)
            require_fast: Prefer fast models for time-sensitive tasks
            require_quality: Prefer high-quality models for important tasks

        Returns:
            Tuple of (model_name, model_type) where model_type is 'free' or 'paid'
        """
        tier_config = self.tier_map.get(tier, self.tier_map["fallback"])
        free_models = tier_config.get("free", [])
        paid_model = tier_config.get("paid")

        # Filter models based on requirements
        if require_fast:
            free_models = [m for m in free_models if m in self.fast_models]
        elif require_quality:
            free_models = [m for m in free_models if m in self.high_quality_models]

        # Try free models first
        for model in free_models:
            if self._is_model_usable(model):
                self.logger.info(f"Selected free model: {model} (tier: {tier})")
                return model, "free"

        # Fallback to paid model
        if paid_model and self._is_model_usable(paid_model):
            self.logger.info(f"Falling back to paid model: {paid_model} (tier: {tier})")
            return paid_model, "paid"

        # Last resort - use default
        default_model = self.config.get("llm_model", "mistralai/mistral-7b-instruct")
        self.logger.warning(f"Using default model: {default_model} (tier: {tier})")
        return default_model, "paid"

    def _is_model_usable(self, model: str) -> bool:
        """Check if a model is currently usable"""
        if not model:
            return False

        # Check rate limits
        if self.usage_tracker.is_rate_limited(model):
            self.logger.debug(f"Model {model} is rate limited")
            return False

        # Check model availability (from cache)
        model_status = self.discovery.cache.get("model_status", {}).get(model, {})
        if model_status.get("available") is False:
            self.logger.debug(f"Model {model} is not available")
            return False

        # Check success rate
        model_stats = self.usage_tracker.get_model_stats(model)
        if model_stats.get("success_rate", 1.0) < 0.7:  # Less than 70% success rate
            self.logger.debug(
                f"Model {model} has low success rate: {model_stats.get('success_rate')}"
            )
            return False

        return True

    def record_model_usage(
        self, model: str, tokens_used: int = 0, cost: float = 0.0, success: bool = True
    ):
        """Record model usage for tracking"""
        self.usage_tracker.record_usage(model, tokens_used, cost, success)

    def get_usage_summary(self) -> Dict:
        """Get usage summary"""
        return self.usage_tracker.get_usage_summary()

    def update_model_discovery(self, force: bool = False):
        """Update model discovery cache"""
        if force or self.discovery.should_update_cache():
            self.logger.info("Updating model discovery cache...")
            self.discovery.discover_free_models()
            self.logger.info("Model discovery cache updated")

    def get_model_recommendations(self) -> Dict:
        """Get model recommendations based on usage patterns"""
        summary = self.usage_tracker.get_usage_summary()
        recommendations = {
            "cost_savings": 0.0,
            "free_usage_percentage": 0.0,
            "most_used_models": [],
            "recommendations": [],
        }

        # Calculate cost savings and usage patterns
        total_requests = summary.get("this_month", {}).get("requests", 0)
        if total_requests > 0:
            free_requests = sum(
                stats.get("total_requests", 0)
                for model, stats in self.usage_tracker.usage_data["models"].items()
                if ":free" in model
            )
            recommendations["free_usage_percentage"] = (
                free_requests / total_requests
            ) * 100

        # Get most used models
        model_usage = [
            (model, stats.get("total_requests", 0))
            for model, stats in self.usage_tracker.usage_data["models"].items()
        ]
        recommendations["most_used_models"] = sorted(
            model_usage, key=lambda x: x[1], reverse=True
        )[:5]

        return recommendations


# Global instance
model_selector = EnhancedModelSelector()


def select_model(
    tier: str = "fallback", require_fast: bool = False, require_quality: bool = False
) -> str:
    """
    Convenience function to select a model

    Args:
        tier: Model tier (premium, fallback, budget)
        require_fast: Prefer fast models for time-sensitive tasks
        require_quality: Prefer high-quality models for important tasks

    Returns:
        Selected model name
    """
    model, model_type = model_selector.select_model(tier, require_fast, require_quality)
    return model


def record_model_usage(
    model: str, tokens_used: int = 0, cost: float = 0.0, success: bool = True
):
    """Record model usage for tracking"""
    model_selector.record_model_usage(model, tokens_used, cost, success)


def get_usage_summary() -> Dict:
    """Get usage summary"""
    return model_selector.get_usage_summary()
