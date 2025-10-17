#!/usr/bin/env python3
"""
Configuration loader for OOS Consultant
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

def load_config(config_name: str) -> Dict[str, Any]:
    """Load configuration by name"""
    config_paths = [
        Path(f"config/{config_name}.yaml"),
        Path(f"config/{config_name}.yml"),
        Path(f"config/{config_name}.json"),
        Path.home() / '.oos' / f'{config_name}.json'
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    if config_path.suffix in ['.yaml', '.yml']:
                        return yaml.safe_load(f)
                    else:
                        return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")
                continue

    # Return default configuration if no files found
    return get_default_config(config_name)

def get_default_config(config_name: str) -> Dict[str, Any]:
    """Get default configuration for given config name"""
    if config_name == "consultant":
        return {
            "intake_questions": {
                "goal": {"text": "What's the primary goal or desired outcome?", "required": True},
                "current_state": {"text": "What's the current state?", "required": True},
                "stakeholders": {"text": "Who are the key stakeholders?", "required": True},
                "constraints": {"text": "What are the constraints?", "required": False},
                "risks": {"text": "What are the risks?", "required": False},
                "assets": {"text": "What assets can we reuse?", "required": False}
            },
            "scoring": {
                "rice_weights": {
                    "reach_weight": 1.0,
                    "impact_weight": 1.0,
                    "confidence_weight": 1.0,
                    "effort_weight": 1.0
                },
                "impact_effort_thresholds": {
                    "high_impact": 7.0,
                    "high_effort": 7.0,
                    "low_impact": 4.0,
                    "low_effort": 4.0
                }
            },
            "output": {
                "base_path": "./consulting",
                "artifacts": {
                    "a3": "a3.md",
                    "issue_tree": "issues.yaml",
                    "ost": "ost.mmd",
                    "impact_effort": "impact_effort.csv",
                    "rice_scores": "rice.csv",
                    "plan": "plan.md",
                    "sources": "sources.json",
                    "intake": "intake.json"
                }
            },
            "portfolio": {
                "max_quick_wins": 3,
                "max_big_bets": 2
            },
            "external": {
                "allow_web": False
            },
            "planning": {
                "time_horizons": ["30 days", "60 days", "90 days"]
            }
        }
    else:
        return {}