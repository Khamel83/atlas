#!/usr/bin/env python3
"""
iPhone/Mac Integration Setup Helper

This script creates simple shortcuts and bookmarks for easy Atlas integration.
Run this after starting Atlas to get your iPhone/Mac setup instructions.
"""

import json
import socket
import webbrowser
from pathlib import Path


def get_local_ip():
    """Get the local IP address for network access"""
    try:
        # Connect to a remote server to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except:
        return "localhost"


def generate_bookmarklet(server_url):
    """Generate a bookmarklet for saving pages"""
    bookmarklet_code = f"""javascript:(function(){{
    var url=window.location.href;
    var title=document.title;
    fetch('{server_url}/content',{{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{url:url,title:title}})
    }}).then(function(){{
        alert('Saved to Atlas!');
    }}).catch(function(){{
        alert('Failed to save. Make sure Atlas is running!');
    }});
}})();"""

    return bookmarklet_code


def generate_shortcut_instructions(server_url):
    """Generate iPhone shortcut instructions"""
    return f"""
IPHONE SHORTCUT SETUP:

1. Open the Shortcuts app on your iPhone
2. Tap the '+' button to create a new shortcut
3. Tap 'Add Action'
4. Search for "URL" and select it
5. Enter: {server_url}/content
6. Tap 'Add Action' again
7. Search for "Get Contents of URL" and select it
8. Change method to "POST"
9. Tap "Show More"
10. For "Request Body", choose "JSON"
11. Add this JSON:
{{
  "content": "Your text or article content here",
  "title": "Article Title"
}}
12. Tap "Done"
13. Tap the arrow at the top
14. Name your shortcut "Save to Atlas"
15. Tap "Done"

HOW TO USE:
- In Safari or any app, tap the Share button
- Scroll down and tap "Save to Atlas"
- Your content will be saved to Atlas!

TIP: You can also share text directly to this shortcut from Notes, Messages, etc.
"""


def generate_bookmark_instructions(server_url):
    """Generate bookmark instructions"""
    bookmarklet = generate_bookmarklet(server_url)

    return f"""
BOOKMARKLET SETUP (Mac/PC):

1. In your browser (Safari/Chrome/Firefox):
2. Right-click on your bookmarks bar and select "Add Page..."
3. Name it: "Save to Atlas"
4. For the URL, copy and paste this entire line:
{bookmarklet}

HOW TO USE:
- Visit any webpage you want to save
- Click the "Save to Atlas" bookmark in your bookmarks bar
- The page will be automatically saved to your Atlas!

ALTERNATIVE METHOD:
1. Create a new bookmark
2. Name it: "Save to Atlas"
3. Copy the bookmarklet code above
4. Paste it as the URL
5. Save and drag to your bookmarks bar
"""


def main():
    """Main setup function"""
    print("=" * 60)
    print("📱 ATLAS IPHONE/MAC SETUP HELPER")
    print("=" * 60)
    print()

    # Get server information
    local_ip = get_local_ip()
    server_url = f"http://{local_ip}:8000"

    print(f"🌐 Your Atlas server is running at: {server_url}")
    print()

    # Create setup instructions file
    instructions = f"""ATLAS MOBILE INTEGRATION SETUP
===============================

Server URL: {server_url}

{generate_shortcut_instructions(server_url)}

{generate_bookmark_instructions(server_url)}

TESTING YOUR SETUP:
------------------
1. Start Atlas: python3 start_web.py
2. Try the bookmarklet on any webpage
3. Check http://localhost:8000 to see your saved content
4. Try the iPhone shortcut if you set it up

TROUBLESHOOTING:
---------------
- Make sure Atlas is running (python3 start_web.py)
- Check that port 8000 is available
- Ensure your Mac allows incoming connections (System Preferences > Security & Firewall)
- Both devices must be on the same WiFi network

FOR IPHONE ACCESS:
-----------------
Use your computer's IP address instead of localhost:
{server_url}

This lets your iPhone access Atlas from the same WiFi network.
"""

    # Save instructions to file
    with open("MOBILE_SETUP.txt", "w") as f:
        f.write(instructions)

    print("✅ Created mobile setup instructions: MOBILE_SETUP.txt")
    print()

    # Display quick instructions
    print("🚀 QUICK SETUP:")
    print()
    print("📱 IPHONE:")
    print("   1. Open Shortcuts app")
    print("   2. Create new shortcut")
    print("   3. Add URL action:", server_url + "/api/content")
    print("   4. Add 'Get Contents of URL' (POST, JSON)")
    print("   5. Name it 'Save to Atlas'")
    print()

    print("💻 MAC/PC:")
    print("   1. Create bookmark named 'Save to Atlas'")
    print("   2. Use this bookmarklet code:")
    print("   " + generate_bookmarklet(server_url)[:80] + "...")
    print()

    # Ask if user wants to open the detailed instructions
    try:
        response = input("\n📖 Open detailed instructions? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            # Try to open the instructions file
            if Path("MOBILE_SETUP.txt").exists():
                webbrowser.open(f"file://{Path.cwd()}/MOBILE_SETUP.txt")
            else:
                print("\n" + instructions)
    except KeyboardInterrupt:
        print("\n\n👋 Setup complete! See MOBILE_SETUP.txt for detailed instructions.")

    print(f"\n🎉 Setup complete! Your Atlas is ready for mobile integration.")
    print(f"📱 iPhone/Mac can access Atlas at: {server_url}")


if __name__ == "__main__":
    main()