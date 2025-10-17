#!/usr/bin/env python3
"""
Automated Model Discovery and Update Script

This script can be run monthly to:
1. Discover new free models
2. Test existing model availability
3. Update model recommendations
4. Generate usage reports
5. Suggest configuration optimizations
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests  # Added for OpenRouter API calls

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.config import load_config
from helpers.model_selector import (EnhancedModelSelector, ModelDiscovery)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("model_discovery_update.log"),
        logging.StreamHandler(),
    ],
)


class ModelDiscoveryUpdater:
    """Automated model discovery and update system"""

    def __init__(self):
        self.config = load_config()
        self.model_selector = EnhancedModelSelector()
        self.discovery = ModelDiscovery()  # Add this line
        self.logger = logging.getLogger(__name__)

    def discover_new_models(self) -> Dict[str, List[str]]:
        """Discover new free models using OpenRouter API"""
        try:
            # Get API key
            api_key = self.config.get("OPENROUTER_API_KEY")
            if not api_key:
                self.logger.warning(
                    "No OpenRouter API key found, using fallback discovery"
                )
                return self._get_fallback_discovery()

            # Call OpenRouter models API
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                "https://openrouter.ai/api/v1/models", headers=headers, timeout=30
            )

            if response.status_code != 200:
                self.logger.warning(
                    f"OpenRouter API returned {response.status_code}, using fallback"
                )
                return self._get_fallback_discovery()

            models_data = response.json()

            # Categorize models
            discovered_models = {
                "free_models": [],
                "new_free_models": [],
                "fast_models": [],
                "quality_models": [],
                "balanced_models": [],
                "provider_breakdown": {},
            }

            # Get existing free models for comparison
            existing_free = set(self.discovery.cache.get("free_models", []))

            # Process each model
            for model in models_data.get("data", []):
                model_id = model.get("id")
                pricing = model.get("pricing", {})
                context_length = model.get("context_length", 0)
                description = model.get("description", "").lower()

                if not model_id:
                    continue

                # Check if model is free
                is_free = (
                    str(pricing.get("prompt", "1")) == "0"
                    and str(pricing.get("completion", "1")) == "0"
                    and str(pricing.get("request", "1")) == "0"
                )

                if is_free:
                    discovered_models["free_models"].append(model_id)

                    # Check if it's a new free model
                    if model_id not in existing_free:
                        discovered_models["new_free_models"].append(model_id)

                    # Classify by performance characteristics
                    if self._is_fast_model(model_id, description, context_length):
                        discovered_models["fast_models"].append(model_id)
                    elif self._is_quality_model(model_id, description, context_length):
                        discovered_models["quality_models"].append(model_id)
                    else:
                        discovered_models["balanced_models"].append(model_id)

                    # Group by provider
                    if "/" in model_id:
                        provider = model_id.split("/")[0]
                        if provider not in discovered_models["provider_breakdown"]:
                            discovered_models["provider_breakdown"][provider] = []
                        discovered_models["provider_breakdown"][provider].append(
                            model_id
                        )

            self.logger.info(
                f"Discovered {len(discovered_models['free_models'])} free models"
            )
            self.logger.info(
                f"Found {len(discovered_models['new_free_models'])} new free models"
            )

            return discovered_models

        except Exception as e:
            self.logger.error(f"Failed to discover models via API: {e}")
            return self._get_fallback_discovery()

    def _get_fallback_discovery(self) -> Dict[str, List[str]]:
        """Fallback discovery when API fails"""
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

        return {
            "free_models": fallback_models,
            "new_free_models": [],
            "fast_models": [
                "google/gemma-2-9b-it:free",
                "mistralai/mistral-7b-instruct:free",
                "qwen/qwen-2.5-7b-instruct:free",
            ],
            "quality_models": [
                "deepseek/deepseek-r1:free",
                "deepseek/deepseek-v3:free",
                "meta-llama/llama-3.1-8b-instruct:free",
            ],
            "balanced_models": [
                "microsoft/phi-3-mini-128k-instruct:free",
                "microsoft/phi-3-medium-128k-instruct:free",
            ],
            "provider_breakdown": {
                "deepseek": ["deepseek/deepseek-r1:free", "deepseek/deepseek-v3:free"],
                "google": ["google/gemma-2-9b-it:free"],
                "mistralai": ["mistralai/mistral-7b-instruct:free"],
                "meta-llama": ["meta-llama/llama-3.1-8b-instruct:free"],
                "qwen": ["qwen/qwen-2.5-7b-instruct:free"],
                "microsoft": [
                    "microsoft/phi-3-mini-128k-instruct:free",
                    "microsoft/phi-3-medium-128k-instruct:free",
                ],
            },
        }

    def _is_fast_model(
        self, model_id: str, description: str, context_length: int
    ) -> bool:
        """Determine if a model is optimized for speed"""
        # Check model name patterns
        fast_patterns = ["7b", "mini", "small", "fast", "turbo", "lite", "quick"]

        model_lower = model_id.lower()
        for pattern in fast_patterns:
            if pattern in model_lower:
                return True

        # Check description
        if any(
            word in description
            for word in ["fast", "quick", "efficient", "lightweight"]
        ):
            return True

        # Smaller context lengths often indicate faster models
        if context_length > 0 and context_length <= 8192:
            return True

        return False

    def _is_quality_model(
        self, model_id: str, description: str, context_length: int
    ) -> bool:
        """Determine if a model is optimized for quality"""
        # Check model name patterns
        quality_patterns = [
            "70b",
            "34b",
            "13b",
            "large",
            "pro",
            "premium",
            "advanced",
            "r1",
            "v3",
        ]

        model_lower = model_id.lower()
        for pattern in quality_patterns:
            if pattern in model_lower:
                return True

        # Check description
        if any(
            word in description
            for word in ["advanced", "high-quality", "reasoning", "complex"]
        ):
            return True

        # Larger context lengths often indicate more capable models
        if context_length > 32768:
            return True

        return False

    def update_model_classifications(self, models: List[str]) -> Dict[str, List[str]]:
        """Update model classifications based on performance testing"""
        # This method is kept for backward compatibility but is now handled
        # by the API-based discovery
        return {"fast_models": [], "quality_models": [], "balanced_models": []}

    def generate_usage_report(self) -> Dict:
        """Generate comprehensive usage report"""
        self.logger.info("Generating usage report...")

        tracker = self.model_selector.usage_tracker
        summary = tracker.get_usage_summary()

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "model_details": {},
            "cost_analysis": {},
            "recommendations": [],
        }

        # Analyze each model
        for model, stats in tracker.usage_data.get("models", {}).items():
            report["model_details"][model] = {
                "total_requests": stats.get("total_requests", 0),
                "success_rate": stats.get("success_rate", 0),
                "total_cost": stats.get("total_cost", 0),
                "is_free": ":free" in model,
                "last_used": stats.get("last_used"),
            }

        # Cost analysis
        total_cost = sum(
            stats.get("total_cost", 0)
            for stats in tracker.usage_data.get("models", {}).values()
        )
        free_requests = sum(
            stats.get("total_requests", 0)
            for model, stats in tracker.usage_data.get("models", {}).items()
            if ":free" in model
        )
        total_requests = sum(
            stats.get("total_requests", 0)
            for stats in tracker.usage_data.get("models", {}).values()
        )

        report["cost_analysis"] = {
            "total_cost": total_cost,
            "free_usage_percentage": (
                (free_requests / total_requests * 100) if total_requests > 0 else 0
            ),
            "estimated_savings": (
                total_cost * (free_requests / total_requests)
                if total_requests > 0
                else 0
            ),
        }

        # Generate recommendations
        if report["cost_analysis"]["free_usage_percentage"] < 70:
            report["recommendations"].append(
                "Consider increasing free model usage to reduce costs"
            )

        if total_cost > 10:  # $10 threshold
            report["recommendations"].append(
                "High API costs detected - review model selection strategy"
            )

        return report

    def suggest_config_optimizations(
        self, available_models: List[str], classifications: Dict[str, List[str]]
    ) -> Dict:
        """Suggest configuration optimizations"""
        self.logger.info("Generating configuration suggestions...")

        suggestions = {
            "new_free_models": [],
            "tier_optimizations": {},
            "config_updates": {},
        }

        # Check for new models not in current config
        current_free_models = []
        for tier in ["premium", "fallback", "budget"]:
            for i in range(1, 4):
                key = f"MODEL_FREE_{tier.upper()}_{i}"
                model = self.config.get(key)
                if model:
                    current_free_models.append(model)

        new_models = [m for m in available_models if m not in current_free_models]
        suggestions["new_free_models"] = new_models

        # Suggest tier optimizations
        if classifications["fast"]:
            suggestions["tier_optimizations"]["budget"] = {
                "recommended_models": classifications["fast"][:3],
                "reason": "Fast models are ideal for budget tier bulk operations",
            }

        if classifications["quality"]:
            suggestions["tier_optimizations"]["premium"] = {
                "recommended_models": classifications["quality"][:3],
                "reason": "High-quality models are best for premium tier tasks",
            }

        if classifications["balanced"]:
            suggestions["tier_optimizations"]["fallback"] = {
                "recommended_models": classifications["balanced"][:3],
                "reason": "Balanced models work well for fallback tier",
            }

        # Generate config updates
        for tier, optimization in suggestions["tier_optimizations"].items():
            for i, model in enumerate(optimization["recommended_models"], 1):
                key = f"MODEL_FREE_{tier.upper()}_{i}"
                suggestions["config_updates"][key] = model

        return suggestions

    def create_env_update_script(self, suggestions: Dict) -> str:
        """Create a script to update .env file with new suggestions"""
        script_content = """#!/bin/bash
# Auto-generated model configuration update script
# Generated on: {date}

echo "Updating model configuration..."

# Backup current config
cp config/.env config/.env.backup.{timestamp}

# Add new model configurations
""".format(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
        )

        for key, value in suggestions.get("config_updates", {}).items():
            script_content += f'echo "{key}={value}" >> config/.env\n'

        script_content += """
echo "Model configuration updated!"
echo "Review the changes in config/.env"
echo "Backup saved as config/.env.backup.{timestamp}"
""".format(
            timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        )

        return script_content

    def run_full_update(self):
        """Run the complete model discovery and update process"""
        self.logger.info("Starting full model discovery update...")

        try:
            # Step 1: Discover new models
            available_models = self.discover_new_models()

            # Step 2: Classify models
            classifications = self.update_model_classifications(available_models)

            # Step 3: Generate usage report
            usage_report = self.generate_usage_report()

            # Step 4: Generate suggestions
            suggestions = self.suggest_config_optimizations(
                available_models, classifications
            )

            # Step 5: Create summary report
            summary_report = {
                "update_date": datetime.now().isoformat(),
                "available_models": available_models,
                "model_classifications": classifications,
                "usage_report": usage_report,
                "suggestions": suggestions,
            }

            # Save report
            report_file = f"model_discovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, "w") as f:
                json.dump(summary_report, f, indent=2)

            self.logger.info(f"Report saved to: {report_file}")

            # Create env update script
            if suggestions.get("config_updates"):
                script_content = self.create_env_update_script(suggestions)
                script_file = (
                    f"update_model_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"
                )
                with open(script_file, "w") as f:
                    f.write(script_content)
                os.chmod(script_file, 0o755)
                self.logger.info(f"Update script created: {script_file}")

            # Print summary
            self.print_summary(summary_report)

        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            import traceback

            traceback.print_exc()

    def print_summary(self, report: Dict):
        """Print a human-readable summary"""
        print("\n" + "=" * 60)
        print("🔍 MODEL DISCOVERY UPDATE SUMMARY")
        print("=" * 60)

        print(f"📅 Update Date: {report['update_date']}")
        print(f"🆓 Available Free Models: {len(report['available_models'])}")

        # Model classifications
        classifications = report["model_classifications"]
        print(f"⚡ Fast Models: {len(classifications['fast'])}")
        print(f"🎯 Quality Models: {len(classifications['quality'])}")
        print(f"⚖️ Balanced Models: {len(classifications['balanced'])}")

        # Usage statistics
        usage = report["usage_report"]
        print(f"💰 Total Cost: ${usage['cost_analysis']['total_cost']:.4f}")
        print(f"🆓 Free Usage: {usage['cost_analysis']['free_usage_percentage']:.1f}%")
        print(
            f"💵 Estimated Savings: ${usage['cost_analysis']['estimated_savings']:.4f}"
        )

        # Suggestions
        suggestions = report["suggestions"]
        print(f"🆕 New Models Found: {len(suggestions['new_free_models'])}")
        print(f"⚙️ Config Updates: {len(suggestions['config_updates'])}")

        if suggestions["new_free_models"]:
            print("\n🆕 NEW FREE MODELS DISCOVERED:")
            for model in suggestions["new_free_models"]:
                print(f"   • {model}")

        if suggestions["config_updates"]:
            print("\n⚙️ RECOMMENDED CONFIG UPDATES:")
            for key, value in suggestions["config_updates"].items():
                print(f"   • {key}={value}")

        print("\n" + "=" * 60)

    def run_monthly_update(self):
        """Run the complete monthly model discovery and update process"""
        self.logger.info("Starting monthly model discovery update...")

        try:
            # Step 1: Discover new models
            discovered_models = self.discover_new_models()

            # Step 2: Classify models by performance
            all_free_models = discovered_models["free_models"]

            # Step 3: Update model selector cache
            self.model_selector.discovery.cache["free_models"] = all_free_models
            self.model_selector.discovery.cache["last_updated"] = (
                datetime.now().isoformat()
            )
            self.model_selector.discovery._save_cache()

            # Step 4: Generate usage report
            usage_report = self.generate_usage_report()

            # Step 5: Generate recommendations
            recommendations = self.generate_recommendations(
                discovered_models, usage_report
            )

            # Step 6: Create comprehensive report
            monthly_report = self.create_monthly_report(
                discovered_models, usage_report, recommendations
            )

            # Step 7: Save report
            self.save_monthly_report(monthly_report)

            # Step 8: Update configuration if needed
            self.update_configuration(recommendations)

            self.logger.info("Monthly model discovery update completed successfully")

        except Exception as e:
            self.logger.error(f"Monthly update failed: {e}")
            raise

    def generate_recommendations(
        self, discovered_models: Dict[str, List[str]], usage_report: Dict
    ) -> Dict:
        """Generate recommendations based on discovered models and usage patterns"""
        recommendations = {
            "new_models_to_try": [],
            "tier_updates": {},
            "cost_optimization": {},
            "performance_improvements": {},
        }

        # Recommend new models to try
        new_models = discovered_models["new_free_models"]
        if new_models:
            recommendations["new_models_to_try"] = new_models[:5]  # Top 5 new models

        # Analyze current tier configurations

        # Recommend tier updates based on new fast models
        if discovered_models["fast_models"]:
            recommendations["tier_updates"]["budget"] = {
                "suggested_models": discovered_models["fast_models"][:3],
                "reason": "New fast models available for budget tier",
            }

        # Recommend tier updates based on new quality models
        if discovered_models["quality_models"]:
            recommendations["tier_updates"]["premium"] = {
                "suggested_models": discovered_models["quality_models"][:3],
                "reason": "New high-quality models available for premium tier",
            }

        # Cost optimization recommendations
        total_cost = usage_report.get("total_cost", 0)
        free_percentage = usage_report.get("free_usage_percentage", 0)

        if free_percentage < 80:
            recommendations["cost_optimization"]["increase_free_usage"] = {
                "current_percentage": free_percentage,
                "target_percentage": 85,
                "suggested_models": discovered_models["free_models"][:5],
            }

        if total_cost > 10:  # If spending more than $10/month
            recommendations["cost_optimization"]["reduce_paid_usage"] = {
                "current_cost": total_cost,
                "suggested_actions": [
                    "Increase free model usage",
                    "Use budget tier for non-critical tasks",
                    "Implement stricter rate limiting",
                ],
            }

        return recommendations

    def create_monthly_report(
        self,
        discovered_models: Dict[str, List[str]],
        usage_report: Dict,
        recommendations: Dict,
    ) -> Dict:
        """Create comprehensive monthly report"""
        return {
            "report_date": datetime.now().isoformat(),
            "discovery_summary": {
                "total_free_models": len(discovered_models["free_models"]),
                "new_free_models": len(discovered_models["new_free_models"]),
                "fast_models": len(discovered_models["fast_models"]),
                "quality_models": len(discovered_models["quality_models"]),
                "balanced_models": len(discovered_models["balanced_models"]),
                "provider_breakdown": {
                    provider: len(models)
                    for provider, models in discovered_models[
                        "provider_breakdown"
                    ].items()
                },
            },
            "discovered_models": discovered_models,
            "usage_analysis": usage_report,
            "recommendations": recommendations,
            "next_steps": [
                "Review new model recommendations",
                "Test suggested models for your use case",
                "Update tier configurations if needed",
                "Monitor cost optimization opportunities",
            ],
        }

    def save_monthly_report(self, report: Dict):
        """Save monthly report to file"""
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)

        report_file = (
            report_dir
            / f"model_discovery_report_{datetime.now().strftime('%Y%m')}.json"
        )

        try:
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)

            self.logger.info(f"Monthly report saved to {report_file}")

            # Also create a human-readable summary
            summary_file = (
                report_dir
                / f"model_discovery_summary_{datetime.now().strftime('%Y%m')}.md"
            )
            self.create_markdown_summary(report, summary_file)

        except Exception as e:
            self.logger.error(f"Failed to save monthly report: {e}")

    def create_markdown_summary(self, report: Dict, output_file: Path):
        """Create a human-readable markdown summary"""
        summary = f"""# Model Discovery Report - {datetime.now().strftime('%B %Y')}

## Discovery Summary
- **Total Free Models**: {report['discovery_summary']['total_free_models']}
- **New Free Models**: {report['discovery_summary']['new_free_models']}
- **Fast Models**: {report['discovery_summary']['fast_models']}
- **Quality Models**: {report['discovery_summary']['quality_models']}
- **Balanced Models**: {report['discovery_summary']['balanced_models']}

## Provider Breakdown
"""

        for provider, count in report["discovery_summary"][
            "provider_breakdown"
        ].items():
            summary += f"- **{provider}**: {count} models\n"

        summary += f"""
## Usage Analysis
- **Total Requests**: {report['usage_analysis'].get('total_requests', 0)}
- **Total Cost**: ${report['usage_analysis'].get('total_cost', 0):.2f}
- **Free Usage**: {report['usage_analysis'].get('free_usage_percentage', 0):.1f}%

## New Models to Try
"""

        for model in report["recommendations"].get("new_models_to_try", []):
            summary += f"- `{model}`\n"

        summary += """
## Recommendations
"""

        for category, rec in report["recommendations"].items():
            if category != "new_models_to_try":
                summary += f"### {category.replace('_', ' ').title()}\n"
                if isinstance(rec, dict):
                    for key, value in rec.items():
                        summary += f"- **{key}**: {value}\n"
                summary += "\n"

        try:
            with open(output_file, "w") as f:
                f.write(summary)
            self.logger.info(f"Markdown summary saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save markdown summary: {e}")

    def update_configuration(self, recommendations: Dict):
        """Update configuration based on recommendations"""
        # This would update the .env file with new model recommendations
        # For now, just log the recommendations
        self.logger.info("Configuration update recommendations:")

        for category, rec in recommendations.items():
            if category == "tier_updates":
                for tier, update in rec.items():
                    self.logger.info(f"  {tier} tier: {update['suggested_models']}")
            elif category == "new_models_to_try":
                self.logger.info(f"  New models: {rec}")


def main():
    """Main entry point"""
    updater = ModelDiscoveryUpdater()
    updater.run_monthly_update()


if __name__ == "__main__":
    main()
