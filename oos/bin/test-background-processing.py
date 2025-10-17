#!/usr/bin/env python3
"""
Test script for background idea processing
Demonstrates the OOS persistent assistant capabilities
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from background_processor import (
    BackgroundProcessor, Idea, get_background_processor,
    add_idea_for_processing
)
from oos_daemon import get_daemon, start_daemon
from renderers import Colors


async def test_background_processing():
    """Test the background idea processing engine"""
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("   🌱 OOS Background Processing Test                           ║")
    print("   Testing idea germination and background processing            ║")
    print("                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    # Test configuration
    config = {
        'google_enabled': False,
        'openrouter_api_key': 'test-key',
        'max_concurrent_ideas': 2
    }

    # Create background processor
    processor = BackgroundProcessor(config)

    # Start processor in background
    processor_task = asyncio.create_task(processor.start())

    # Test ideas
    test_ideas = [
        "Create a Discord bot that monitors server activity and sends notifications",
        "Build a web automation script to check Amazon prices and email when they drop",
        "Develop a personal assistant that manages my calendar and tasks",
        "Create a data analysis tool for sales reports with visualizations"
    ]

    print(f"{Colors.GREEN}🚀 Adding test ideas to processing queue...{Colors.END}")

    # Add ideas for processing
    idea_ids = []
    for i, idea_content in enumerate(test_ideas):
        idea_id = await add_idea_for_processing(
            content=idea_content,
            user_id=f"test_user_{i}",
            source="test_script",
            priority=8 - i,  # Higher priority for earlier ideas
            context={'test': True, 'batch': 1}
        )
        idea_ids.append(idea_id)
        print(f"{Colors.BLUE}✅ Added idea {i+1}: {idea_content[:50]}...{Colors.END}")

    print(f"\n{Colors.YELLOW}⏳ Monitoring idea processing for 60 seconds...{Colors.END}")

    # Monitor progress
    for minute in range(12):  # 5 seconds * 12 = 60 seconds
        await asyncio.sleep(5)

        print(f"\n{Colors.CYAN}📊 Status Check (minute {minute + 1}):{Colors.END}")

        for i, idea_id in enumerate(idea_ids):
            status = await processor.get_idea_status(idea_id)
            if status:
                progress = int(status['progress'] * 100)
                phase = status['phase']
                print(f"  Idea {i+1}: {progress}% - {phase}")

                if status.get('project'):
                    project = status['project']
                    print(f"    Project: {project['name']}")
                    print(f"    Files: {len(project['files_created'])} created")

        # Show active ideas count
        active_count = len(processor.active_ideas)
        print(f"  {Colors.WHITE}Active ideas: {active_count}/{processor.max_concurrent_ideas}{Colors.END}")

    print(f"\n{Colors.GREEN}🎉 Test completed!{Colors.END}")

    # Final status report
    print(f"\n{Colors.CYAN}📋 Final Status Report:{Colors.END}")
    completed_count = 0
    needs_input_count = 0
    processing_count = 0

    for i, idea_id in enumerate(idea_ids):
        status = await processor.get_idea_status(idea_id)
        if status:
            phase = status['phase']
            if phase == 'completed':
                completed_count += 1
            elif phase == 'needs_input':
                needs_input_count += 1
            else:
                processing_count += 1

            print(f"  Idea {i+1}: {phase} ({int(status['progress'] * 100)}%)")

    print(f"\n{Colors.WHITE}Summary:{Colors.END}")
    print(f"  ✅ Completed: {completed_count}")
    print(f"  ❓ Needs Input: {needs_input_count}")
    print(f"  ⚙️  Still Processing: {processing_count}")

    # Stop processor
    await processor.stop()
    await processor_task

    print(f"\n{Colors.GREEN}👋 Background processing test finished{Colors.END}")


async def test_daemon_integration():
    """Test daemon with background processing integration"""
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("   🚀 OOS Daemon Integration Test                            ║")
    print("   Testing daemon with background processing                    ║")
    print("                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    config_dir = Path.home() / '.oos'
    config_dir.mkdir(exist_ok=True)

    # Create test input
    input_file = config_dir / 'input.txt'
    test_idea = "Create a simple weather bot that tells me the forecast every morning"

    print(f"{Colors.YELLOW}💡 Writing test idea to input file...{Colors.END}")
    input_file.write_text(test_idea)

    # Start daemon
    print(f"{Colors.GREEN}🚀 Starting daemon for 30 seconds...{Colors.END}")
    daemon_task = asyncio.create_task(start_daemon(config_dir))

    # Let it run for 30 seconds
    await asyncio.sleep(30)

    # Check for processed ideas
    persistence_dir = config_dir / 'persistence'
    if persistence_dir.exists():
        idea_files = list(persistence_dir.glob('idea_*.json'))
        result_files = list(persistence_dir.glob('result_*.json'))

        print(f"\n{Colors.CYAN}📊 Daemon Results:{Colors.END}")
        print(f"  Ideas processed: {len(idea_files)}")
        print(f"  Results generated: {len(result_files)}")

        if result_files:
            # Show latest result
            latest_result = max(result_files, key=lambda f: f.stat().st_mtime)
            with open(latest_result, 'r') as f:
                result = json.load(f)
                print(f"  Latest status: {result.get('status', 'unknown')}")
                print(f"  Progress: {result.get('progress', 0) * 100:.0f}%")

    # Stop daemon
    print(f"\n{Colors.YELLOW}🛑 Stopping daemon...{Colors.END}")
    daemon = get_daemon(config_dir)
    daemon.running = False

    # Clean up
    if input_file.exists():
        input_file.unlink()

    print(f"{Colors.GREEN}✅ Daemon integration test completed{Colors.END}")


async def main():
    """Main test function"""
    try:
        # Test 1: Background processing
        await test_background_processing()

        print(f"\n{Colors.YELLOW}" + "="*60 + f"{Colors.END}\n")

        # Test 2: Daemon integration
        await test_daemon_integration()

    except Exception as e:
        print(f"{Colors.RED}❌ Test failed: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())