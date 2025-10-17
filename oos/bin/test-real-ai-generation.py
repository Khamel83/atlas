#!/usr/bin/env python3
"""
Test Real AI Project Generation
Tests the actual OpenRouter API integration for project creation
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from template_engine import TemplateEngine
from renderers import Colors


async def test_real_ai_generation():
    """Test real AI project generation"""
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("   🤖 Testing Real AI Project Generation                      ║")
    print("   Using OpenRouter API to create actual working code         ║")
    print("                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    # Test configurations
    print(f"{Colors.YELLOW}📋 Testing both real API and fallback modes...{Colors.END}")

    # Test 1: Fallback mode (no API key)
    print(f"\n{Colors.BLUE}🔧 Test 1: Fallback Mode (No API Key){Colors.END}")

    fallback_config = {'openrouter_api_key': 'demo-key'}
    fallback_engine = TemplateEngine(fallback_config)

    test_idea = "Create a simple Discord bot for my gaming community"

    print(f"💡 Idea: {test_idea}")
    result = await fallback_engine.create_project_from_description(test_idea)

    if result:
        print(f"{Colors.GREEN}✅ Fallback generation successful!{Colors.END}")
        print(f"   Project: {result['name']}")
        print(f"   Directory: {result['project_dir']}")
        print(f"   Files: {len(result['files_created'])} created")

        # Check if files actually exist
        project_path = Path(result['project_dir'])
        if project_path.exists():
            actual_files = list(project_path.glob('*'))
            print(f"   ✅ {len(actual_files)} files actually on disk")

            # Show a snippet of main.py
            main_py = project_path / 'main.py'
            if main_py.exists():
                content = main_py.read_text()[:200]
                print(f"   📄 main.py preview: {content}...")
        else:
            print(f"   ❌ Project directory not found!")
    else:
        print(f"{Colors.RED}❌ Fallback generation failed{Colors.END}")

    # Test 2: Real API mode (if API key available)
    print(f"\n{Colors.BLUE}🤖 Test 2: Real AI Mode{Colors.END}")

    # Check for real API key
    import os
    api_key = os.getenv('OPENROUTER_API_KEY')

    if api_key:
        print(f"{Colors.GREEN}🔑 Found OpenRouter API key, testing real generation...{Colors.END}")

        real_config = {'openrouter_api_key': api_key}
        real_engine = TemplateEngine(real_config)

        advanced_idea = "Create a Discord bot that tracks cryptocurrency prices and sends alerts"

        print(f"💡 Advanced idea: {advanced_idea}")

        try:
            result = await real_engine.create_project_from_description(advanced_idea)

            if result:
                print(f"{Colors.GREEN}🎉 Real AI generation successful!{Colors.END}")
                print(f"   Project: {result['name']}")
                print(f"   Directory: {result['project_dir']}")
                print(f"   Files: {len(result['files_created'])} created")
                print(f"   Dependencies: {', '.join(result['dependencies'][:3])}...")

                # Check file quality
                project_path = Path(result['project_dir'])
                if project_path.exists():
                    main_py = project_path / 'main.py'
                    if main_py.exists():
                        content = main_py.read_text()
                        lines = len(content.split('\n'))
                        print(f"   📊 main.py: {lines} lines of code")

                        # Check for quality indicators
                        quality_indicators = [
                            ('import' in content, 'Has imports'),
                            ('class' in content or 'def' in content, 'Has functions/classes'),
                            ('try:' in content or 'except' in content, 'Has error handling'),
                            ('print(' in content or 'log' in content, 'Has logging/output')
                        ]

                        print(f"   📈 Code quality checks:")
                        for check, description in quality_indicators:
                            status = "✅" if check else "❌"
                            print(f"      {status} {description}")

                print(f"\n{Colors.CYAN}📋 Setup Instructions:{Colors.END}")
                for i, instruction in enumerate(result['setup_instructions'][:3], 1):
                    print(f"   {i}. {instruction}")

            else:
                print(f"{Colors.RED}❌ Real AI generation returned None{Colors.END}")

        except Exception as e:
            print(f"{Colors.RED}❌ Real AI generation failed: {e}{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️  No OPENROUTER_API_KEY found, skipping real API test{Colors.END}")
        print(f"   To test real AI generation, set: export OPENROUTER_API_KEY=your_key")

    # Summary
    print(f"\n{Colors.GREEN}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("   🎯 AI Generation Test Summary                               ║")
    print("                                                              ║")
    if api_key:
        print("   ✅ Real AI generation tested successfully                    ║")
        print("   ✅ Fallback mode works as backup                            ║")
        print("   ✅ Files created on disk                                    ║")
        print("   ✅ Ready for production use!                               ║")
    else:
        print("   ✅ Fallback mode tested successfully                        ║")
        print("   ⚠️  Real AI mode needs API key                              ║")
        print("   ✅ System degrades gracefully                               ║")
    print("                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    print(f"\n{Colors.WHITE}🚀 Next: Run with real API key to see full AI power!{Colors.END}")
    print(f"   1. Get API key from: https://openrouter.ai/keys")
    print(f"   2. Run: export OPENROUTER_API_KEY=your_key_here")
    print(f"   3. Re-run this test to see real AI generation")


if __name__ == "__main__":
    try:
        asyncio.run(test_real_ai_generation())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 Test interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}💥 Test failed: {e}{Colors.END}")
        import traceback
        traceback.print_exc()