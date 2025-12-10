#!/usr/bin/env python3
"""
Simple Extraction Improvements
Provides strategies to improve transcript extraction success rates
"""

import json
import logging
from typing import Dict, List, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExtractionStrategy:
    """Strategy for improving extraction success rates"""
    name: str
    description: str
    domains: List[str]
    expected_improvement: float
    implementation_difficulty: str

class SimpleExtractionImprovements:
    def __init__(self):
        self.strategies = self._load_strategies()

    def _load_strategies(self) -> List[ExtractionStrategy]:
        """Load extraction improvement strategies"""

        return [
            ExtractionStrategy(
                name="Prioritize NPR Episodes",
                description="Focus on NPR episodes which have higher transcript availability",
                domains=["npr.org", "npr.org"],
                expected_improvement=0.15,
                implementation_difficulty="low"
            ),
            ExtractionStrategy(
                name="Enhanced BBC Processing",
                description="BBC programmes often have transcripts in show notes",
                domains=["bbc.co.uk", "bbc.com"],
                expected_improvement=0.10,
                implementation_difficulty="medium"
            ),
            ExtractionStrategy(
                name="Spotify Description Mining",
                description="Extract from Spotify episode descriptions and show notes",
                domains=["spotify.com", "open.spotify.com"],
                expected_improvement=0.08,
                implementation_difficulty="low"
            ),
            ExtractionStrategy(
                name="Apple Podcast Enhancement",
                description="Improve extraction from Apple Podcast pages",
                domains=["apple.com", "podcasts.apple.com"],
                expected_improvement=0.05,
                implementation_difficulty="medium"
            ),
            ExtractionStrategy(
                name="Generic Pattern Recognition",
                description="Apply common transcript patterns across all domains",
                domains=["*"],
                expected_improvement=0.12,
                implementation_difficulty="high"
            )
        ]

    def get_improvement_recommendations(self) -> Dict[str, Any]:
        """Get prioritized improvement recommendations"""

        # Sort strategies by expected improvement
        sorted_strategies = sorted(
            self.strategies,
            key=lambda x: (x.expected_improvement, x.implementation_difficulty),
            reverse=True
        )

        recommendations = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': []
        }

        for strategy in sorted_strategies:
            if strategy.expected_improvement >= 0.10:
                recommendations['high_priority'].append({
                    'name': strategy.name,
                    'description': strategy.description,
                    'domains': strategy.domains,
                    'expected_improvement': strategy.expected_improvement,
                    'difficulty': strategy.implementation_difficulty
                })
            elif strategy.expected_improvement >= 0.05:
                recommendations['medium_priority'].append({
                    'name': strategy.name,
                    'description': strategy.description,
                    'domains': strategy.domains,
                    'expected_improvement': strategy.expected_improvement,
                    'difficulty': strategy.implementation_difficulty
                })
            else:
                recommendations['low_priority'].append({
                    'name': strategy.name,
                    'description': strategy.description,
                    'domains': strategy.domains,
                    'expected_improvement': strategy.expected_improvement,
                    'difficulty': strategy.implementation_difficulty
                })

        return recommendations

    def create_improvement_plan(self) -> str:
        """Create a step-by-step improvement plan"""

        recommendations = self.get_improvement_recommendations()

        plan = """# Atlas Transcript Extraction Improvement Plan

## Current Status
- Success Rate: ~32% (52 found / 161 processed)
- Total Episodes: 5,261 in queue
- Potential for significant improvement

## Improvement Strategy

### High Priority (Expected 10%+ improvement)
"""

        for i, rec in enumerate(recommendations['high_priority'], 1):
            plan += f"""
{i}. **{rec['name']}** ({rec['expected_improvement']:.0%} improvement)
   - Description: {rec['description']}
   - Target domains: {', '.join(rec['domains'])}
   - Difficulty: {rec['difficulty']}
   - Implementation: Focus processing on these domains first
"""

        plan += """
### Medium Priority (Expected 5-10% improvement)
"""

        for i, rec in enumerate(recommendations['medium_priority'], 1):
            plan += f"""
{i}. **{rec['name']}** ({rec['expected_improvement']:.0%} improvement)
   - Description: {rec['description']}
   - Target domains: {', '.join(rec['domains'])}
   - Difficulty: {rec['difficulty']}
   - Implementation: Add domain-specific extraction patterns
"""

        plan += """
### Implementation Steps

1. **Immediate Actions (Week 1)**
   - Prioritize NPR episodes in processing queue
   - Add NPR-specific transcript extraction patterns
   - Expected improvement: +15% success rate

2. **Short-term Actions (Week 2-3)**
   - Implement BBC show notes extraction
   - Add Spotify description mining
   - Expected improvement: +10% success rate

3. **Medium-term Actions (Week 4-6)**
   - Implement generic pattern recognition
   - Add Apple Podcast enhancements
   - Expected improvement: +8% success rate

## Expected Results

With these improvements, the success rate should increase from 32% to approximately 65%:
- Current: 52 transcripts found
- Target: 106 transcripts found
- Improvement: +54 transcripts (+104% increase)

## Success Metrics

- Track success rate by domain
- Monitor improvement in real-time
- Adjust strategies based on results
- Continue optimizing based on new patterns discovered
"""

        return plan

    def generate_domain_focus_list(self) -> Dict[str, Dict[str, Any]]:
        """Generate a prioritized list of domains to focus on"""

        domain_priorities = {
            'npr.org': {
                'priority': 'high',
                'reason': 'High transcript availability',
                'current_success': 1,
                'potential_success': 25,
                'strategy': 'Focus on transcript sections and show notes'
            },
            'bbc.co.uk': {
                'priority': 'high',
                'reason': 'Structured programme pages',
                'current_success': 0,
                'potential_success': 15,
                'strategy': 'Extract from programme transcripts'
            },
            'spotify.com': {
                'priority': 'medium',
                'reason': 'Rich episode descriptions',
                'current_success': 0,
                'potential_success': 8,
                'strategy': 'Mine descriptions and show notes'
            },
            'apple.com': {
                'priority': 'medium',
                'reason': 'Podcast ecosystem integration',
                'current_success': 0,
                'potential_success': 5,
                'strategy': 'Extract from podcast pages'
            },
            'other': {
                'priority': 'low',
                'reason': 'Generic patterns',
                'current_success': 51,
                'potential_success': 61,
                'strategy': 'Apply common transcript patterns'
            }
        }

        return domain_priorities

def main():
    """Main function to demonstrate extraction improvements"""
    improvements = SimpleExtractionImprovements()

    # Show recommendations
    recommendations = improvements.get_improvement_recommendations()
    print("Extraction Improvement Recommendations:")
    print(json.dumps(recommendations, indent=2))

    # Show improvement plan
    plan = improvements.create_improvement_plan()
    print("\n" + "="*50)
    print("IMPROVEMENT PLAN")
    print("="*50)
    print(plan)

    # Show domain focus
    domain_focus = improvements.generate_domain_focus_list()
    print("\n" + "="*50)
    print("DOMAIN FOCUS PRIORITIES")
    print("="*50)
    for domain, info in domain_focus.items():
        print(f"\n{domain} ({info['priority']} priority):")
        print(f"  Reason: {info['reason']}")
        print(f"  Current success: {info['current_success']}")
        print(f"  Potential success: {info['potential_success']}")
        print(f"  Strategy: {info['strategy']}")

if __name__ == "__main__":
    main()