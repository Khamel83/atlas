#!/usr/bin/env python3
"""
YouTube Login - Opens browser for login, saves cookies when done.

Usage:
    DISPLAY=:99 python scripts/youtube_login.py

The browser will stay open. After logging in:
    touch /tmp/youtube_login_done

Cookies will be saved and browser will close.
"""

import os
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

SIGNAL_FILE = Path("/tmp/youtube_login_done")
COOKIES_PATH = Path("data/youtube_cookies.json")

def main():
    # Clean up signal file
    if SIGNAL_FILE.exists():
        SIGNAL_FILE.unlink()

    print("=" * 50)
    print("YOUTUBE LOGIN")
    print("=" * 50)
    print()
    print("1. Connect VNC to 192.168.7.10:5900")
    print("2. Log in to YouTube in the browser")
    print("3. Make sure you can see your watch history")
    print("4. Run: touch /tmp/youtube_login_done")
    print()
    print("Waiting for login...")
    print("=" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        page.goto("https://www.youtube.com")

        # Wait for signal file
        while not SIGNAL_FILE.exists():
            time.sleep(1)

        print("Signal received! Saving cookies...")

        # Navigate to history to ensure we have cookies
        page.goto("https://www.youtube.com/feed/history")
        time.sleep(3)

        # Save cookies
        cookies = context.cookies()
        COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(COOKIES_PATH, "w") as f:
            json.dump(cookies, f, indent=2)

        print(f"Saved {len(cookies)} cookies to {COOKIES_PATH}")

        browser.close()

    # Clean up
    SIGNAL_FILE.unlink()
    print("Done! You can now run the scraper.")

if __name__ == "__main__":
    main()
