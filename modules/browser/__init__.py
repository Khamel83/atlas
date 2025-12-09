"""
Atlas Headless Browser Module

Provides a reusable headless browser for JavaScript-rendered pages.
Uses Playwright under the hood.

Usage:
    from modules.browser import Browser

    # Context manager (recommended)
    async with Browser() as browser:
        html = await browser.fetch("https://example.com")
        links = await browser.get_all_links("https://example.com")

    # Or manual control
    browser = Browser()
    await browser.start()
    html = await browser.fetch("https://example.com")
    await browser.stop()
"""

from .headless import Browser, fetch_page, get_page_content

__all__ = ["Browser", "fetch_page", "get_page_content"]
