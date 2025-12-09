#!/usr/bin/env python3
"""
Stratechery Magic Link Cookie Capture

This script helps capture Stratechery session cookies for transcript access.
It opens a browser where you can complete the magic link login, then saves
the cookies for use by the transcript fetcher.

Usage:
    1. Run this script: python scripts/stratechery_login.py
    2. The script will request a magic link to your email
    3. Check your email and click the magic link in the browser window
    4. Cookies are automatically saved when login completes
"""

import asyncio
import json
import os
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright not installed. Run: pip install playwright && playwright install")
    sys.exit(1)


COOKIES_PATH = Path.home() / ".config/atlas/stratechery_cookies.json"
EMAIL = os.environ.get("STRATECHERY_EMAIL", "")


async def request_magic_link(page, email: str) -> bool:
    """Request a magic link login email"""
    try:
        # Navigate to login page
        await page.goto("https://stratechery.com/login/")
        await page.wait_for_load_state("networkidle")

        # Look for email input field
        email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]')
        if await email_input.count() > 0:
            await email_input.first.fill(email)
            print(f"✅ Entered email: {email}")

            # Find and click submit button
            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Sign In"), button:has-text("Log In"), button:has-text("Send")')
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
                print("📧 Magic link requested! Check your email...")
                return True

        print("⚠️  Could not find login form - you may need to navigate manually")
        return False

    except Exception as e:
        print(f"⚠️  Error requesting magic link: {e}")
        return False


async def wait_for_login(page, timeout_minutes: int = 10) -> bool:
    """Wait for successful login by monitoring cookies"""
    print(f"⏳ Waiting for login (timeout: {timeout_minutes} min)...")
    print("   Click the magic link in your email when it arrives")

    start_url = page.url

    for _ in range(timeout_minutes * 12):  # Check every 5 seconds
        await asyncio.sleep(5)

        # Check if we've been redirected away from login
        current_url = page.url
        if "login" not in current_url.lower() and current_url != start_url:
            print(f"✅ Redirected to: {current_url}")
            return True

        # Check for authentication cookies
        cookies = await page.context.cookies()
        auth_cookies = [c for c in cookies if any(
            keyword in c['name'].lower()
            for keyword in ['session', 'auth', 'passport', 'logged', 'wordpress_logged_in']
        )]

        if auth_cookies:
            print("✅ Authentication cookies detected!")
            return True

    return False


async def save_cookies(context, path: Path):
    """Save browser cookies to file"""
    cookies = await context.cookies()

    # Filter to Stratechery domain
    stratechery_cookies = [c for c in cookies if 'stratechery' in c.get('domain', '')]

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(stratechery_cookies, f, indent=2)

    print(f"💾 Saved {len(stratechery_cookies)} cookies to {path}")
    return len(stratechery_cookies)


async def main():
    email = EMAIL
    if not email:
        email = input("Enter your Stratechery email: ").strip()

    if not email:
        print("❌ Email required")
        return False

    print(f"\n🔐 Stratechery Magic Link Login")
    print(f"   Email: {email}")
    print(f"   Cookies will be saved to: {COOKIES_PATH}\n")

    async with async_playwright() as p:
        # Launch visible browser for user interaction
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Request the magic link
        await request_magic_link(page, email)

        # Wait for user to complete login
        if await wait_for_login(page):
            # Save cookies
            count = await save_cookies(context, COOKIES_PATH)
            if count > 0:
                print("\n✅ Login successful! Cookies saved.")
                print(f"   The transcript fetcher will use: {COOKIES_PATH}")

                # Also save in Netscape format for compatibility
                netscape_path = COOKIES_PATH.with_suffix('.txt')
                with open(netscape_path, 'w') as f:
                    f.write("# Netscape HTTP Cookie File\n")
                    cookies = await context.cookies()
                    for c in cookies:
                        if 'stratechery' in c.get('domain', ''):
                            secure = "TRUE" if c.get('secure') else "FALSE"
                            http_only = "TRUE" if c.get('httpOnly') else "FALSE"
                            expiry = int(c.get('expires', 0))
                            f.write(f"{c['domain']}\tTRUE\t{c['path']}\t{secure}\t{expiry}\t{c['name']}\t{c['value']}\n")
                print(f"   Also saved Netscape format: {netscape_path}")
            else:
                print("\n⚠️  No Stratechery cookies found - login may have failed")
        else:
            print("\n❌ Login timed out")

        await browser.close()

    return True


if __name__ == "__main__":
    asyncio.run(main())
