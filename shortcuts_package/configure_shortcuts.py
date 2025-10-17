#!/usr/bin/env python3
"""
Atlas Shortcuts Configuration Helper
Helps users configure their shortcuts with the correct server URL
"""

import json
import os
import sys
from pathlib import Path

def get_atlas_server_url():
    """Get the Atlas server URL from user or detect automatically"""

    # Try to detect from config
    try:
        from helpers.config import load_config
        config = load_config()
        host = config.get('WEB_HOST', 'localhost')
        port = config.get('WEB_PORT', 8000)
        default_url = f"http://{host}:{port}"
    except:
        default_url = "http://localhost:8000"

    print(f"🔧 Atlas Shortcuts Configuration")
    print(f"================================")
    print("")
    print(f"Current detected server: {default_url}")
    print("")

    response = input(f"Use this URL? (y/n) [y]: ").strip().lower()

    if response in ['n', 'no']:
        custom_url = input("Enter your Atlas server URL: ").strip()
        return custom_url

    return default_url

def create_configuration_instructions(server_url):
    """Create instructions for manually configuring shortcuts"""

    instructions = f"""
# Manual Shortcut Configuration

Since shortcuts are binary files that can't be automatically configured,
you'll need to manually update the server URL in each shortcut.

## Your Atlas Server URL
{server_url}

## Steps to Configure Each Shortcut:

1. Open the **Shortcuts** app
2. Find an Atlas shortcut (e.g., "Capture Thought")
3. Tap **"Edit"** in the top right
4. Look for a **"Text"** action containing "http://localhost:8000"
5. Tap on that text field
6. Replace with: **{server_url}**
7. Tap **"Done"**

## Repeat for All Shortcuts:
- capture_thought
- log_meal
- log_mood
- start_focus
- capture_evening_thought
- log_home_activity_context
- log_work_task_context

## Test Your Configuration:
1. Run "Capture Thought" shortcut
2. Enter a test message
3. Check your Atlas dashboard: {server_url}/ask/html

If you see your test message, configuration is successful! 🎉
"""

    return instructions

def main():
    """Main configuration helper"""

    # Get server URL
    server_url = get_atlas_server_url()

    # Create configuration instructions
    instructions = create_configuration_instructions(server_url)

    # Save instructions to file
    config_file = Path("shortcuts_package/CONFIGURATION_INSTRUCTIONS.md")
    config_file.write_text(instructions)

    print("")
    print("✅ Configuration instructions created!")
    print(f"📄 Saved to: {config_file}")
    print("")
    print("📋 Next steps:")
    print("   1. Install shortcuts using install_shortcuts.sh")
    print("   2. Follow CONFIGURATION_INSTRUCTIONS.md to set server URL")
    print("   3. Test with 'Hey Siri, Capture Thought'")

if __name__ == "__main__":
    main()