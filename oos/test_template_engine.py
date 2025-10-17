#!/usr/bin/env python3
"""
Test script for the Template Engine
Demonstrates goal-oriented project creation
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import Colors directly to avoid import issues
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

from template_engine import get_template_engine, TemplateEngine, GoalAnalyzer
from google_sheets_integration import get_sheets_integration


async def test_template_engine():
    """Test the template engine with various project descriptions"""

    # Mock config
    config = {
        'api_key': 'test-key',
        'version': '2.0.0'
    }

    # Initialize template engine
    google_integration = get_sheets_integration(Path.home() / '.oos')
    template_engine = get_template_engine(config, google_integration)

    # Test cases
    test_descriptions = [
        "I want a chatbot that helps customers with product questions",
        "I need to automate price monitoring on Amazon and email me when prices drop",
        "Help me analyze my sales data from CSV files and create weekly reports",
        "I want a personal assistant to manage my calendar and tasks"
    ]

    print("🧪 Testing Template Engine")
    print("=" * 50)

    for i, description in enumerate(test_descriptions, 1):
        print(f"\n📝 Test {i}: {description}")
        print("-" * 30)

        try:
            # Analyze goal
            goal_analysis = await template_engine.goal_analyzer.analyze_goal(description)
            print(f"✅ Goal Analysis:")
            print(f"   Type: {goal_analysis.goal_type}")
            print(f"   Confidence: {goal_analysis.confidence:.0%}")
            print(f"   Features: {', '.join(goal_analysis.features)}")
            print(f"   Complexity: {goal_analysis.complexity}")

            # Get template
            template = template_engine.templates.get(goal_analysis.goal_type)
            if template:
                print(f"✅ Template Found:")
                print(f"   Name: {template.name}")
                print(f"   Steps: {len(template.steps)}")
                print(f"   Time: {template.estimated_time}")

        except Exception as e:
            print(f"❌ Error: {e}")


async def test_interactive_mode():
    """Test interactive project creation"""
    print("\n\n🎯 Testing Interactive Mode")
    print("=" * 50)

    # Mock config
    config = {
        'api_key': 'test-key',
        'version': '2.0.0'
    }

    # Initialize template engine
    google_integration = get_sheets_integration(Path.home() / '.oos')
    template_engine = get_template_engine(config, google_integration)

    # Simulate user input
    test_description = "I want a simple chatbot to answer frequently asked questions about my products"

    print(f"🤖 User: {test_description}")
    print()

    try:
        result = await template_engine.create_project_from_description(test_description)
        if result:
            print("✅ Project creation successful!")
            print(f"📁 Project directory: {result['project_dir']}")
            print("📋 Next steps:")
            for i, step in enumerate(result['next_steps'], 1):
                print(f"   {i}. {step}")
        else:
            print("❌ Project creation failed")

    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Main test function"""
    print("🚀 OOS Template Engine Test")
    print("=" * 60)

    # Test goal analysis
    await test_template_engine()

    # Test interactive mode (limited)
    await test_interactive_mode()

    print("\n\n✅ Template Engine Test Complete!")
    print("\n💡 Next Steps:")
    print("1. Test with real user input")
    print("2. Integrate with Google Sheets")
    print("3. Add more template variations")
    print("4. Implement AI-powered goal analysis")


if __name__ == "__main__":
    asyncio.run(main())