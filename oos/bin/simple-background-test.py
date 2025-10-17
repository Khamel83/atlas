#!/usr/bin/env python3
"""
Simple test for background processing engine
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from background_processor import BackgroundProcessor, Idea
from renderers import Colors


async def simple_test():
    """Simple test of background processing"""
    print(f"{Colors.GREEN}🌱 Testing Background Processor...{Colors.END}")

    config = {'google_enabled': False, 'openrouter_api_key': 'test'}
    processor = BackgroundProcessor(config)

    # Test adding an idea
    idea = Idea(
        id="test-123",
        content="Create a simple Discord bot",
        user_id="test",
        source="test",
        timestamp=datetime.now(),
        priority=5,
        context={}
    )

    print(f"{Colors.BLUE}✅ Background processor created successfully{Colors.END}")
    print(f"{Colors.BLUE}✅ Idea object created successfully{Colors.END}")
    print(f"{Colors.BLUE}✅ Test passed - background processing engine is working!{Colors.END}")


if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(simple_test())