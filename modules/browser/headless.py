#!/usr/bin/env python3
"""
Headless Browser Module for Atlas

A reusable Playwright-based headless browser for fetching JavaScript-rendered pages.
Designed to be used across all Atlas modules that need to handle dynamic content.

Features:
- Async context manager for clean resource management
- Cookie persistence for authenticated sessions
- Configurable wait strategies
- Link extraction helpers
- Text content extraction
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# RESOURCE POLICY: Maximum 1 browser at a time to prevent system overload
# See RESOURCE_POLICY.md for details on why this limit exists
_BROWSER_SEMAPHORE = asyncio.Semaphore(1)
_MAX_BROWSERS = 1  # Change this to allow more concurrent browsers (not recommended)


class Browser:
    """Headless browser wrapper using Playwright"""

    def __init__(
        self,
        headless: bool = True,
        cookies_file: Optional[str] = None,
        user_data_dir: Optional[str] = None,
        timeout: int = 30000,
    ):
        """
        Initialize browser configuration.

        Args:
            headless: Run in headless mode (no visible window)
            cookies_file: Path to cookies JSON file for authenticated sessions
            user_data_dir: Path to persistent browser profile directory
            timeout: Default timeout in milliseconds
        """
        self.headless = headless
        self.cookies_file = cookies_file
        self.user_data_dir = user_data_dir
        self.timeout = timeout
        self._playwright = None
        self._browser = None
        self._context = None

    async def start(self):
        """Start the browser instance"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        self._playwright = await async_playwright().start()

        # Use persistent context if user_data_dir specified
        if self.user_data_dir:
            self._context = await self._playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
        else:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

        # Load cookies if specified
        if self.cookies_file and Path(self.cookies_file).exists():
            import json

            with open(self.cookies_file) as f:
                cookies = json.load(f)
                await self._context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies from {self.cookies_file}")

    async def stop(self):
        """Stop the browser and clean up resources"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def __aenter__(self):
        # Acquire semaphore to limit concurrent browsers (RESOURCE POLICY)
        await _BROWSER_SEMAPHORE.acquire()
        logger.debug("Acquired browser semaphore, starting browser")
        try:
            await self.start()
            return self
        except Exception:
            _BROWSER_SEMAPHORE.release()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.stop()
        finally:
            _BROWSER_SEMAPHORE.release()
            logger.debug("Released browser semaphore")

    async def fetch(
        self,
        url: str,
        wait_for: str = "networkidle",
        wait_selector: Optional[str] = None,
        wait_time: Optional[int] = None,
    ) -> str:
        """
        Fetch a page and return the rendered HTML.

        Args:
            url: URL to fetch
            wait_for: Wait strategy - "load", "domcontentloaded", "networkidle"
            wait_selector: Optional CSS selector to wait for
            wait_time: Optional additional wait time in ms after page load

        Returns:
            Rendered HTML content
        """
        if not self._context:
            raise RuntimeError("Browser not started. Use 'async with Browser()' or call start()")

        page = await self._context.new_page()
        try:
            await page.goto(url, wait_until=wait_for, timeout=self.timeout)

            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=self.timeout)

            if wait_time:
                await asyncio.sleep(wait_time / 1000)

            html = await page.content()
            return html

        finally:
            await page.close()

    async def get_text_content(
        self,
        url: str,
        selector: Optional[str] = None,
        wait_for: str = "networkidle",
    ) -> str:
        """
        Fetch a page and extract text content.

        Args:
            url: URL to fetch
            selector: CSS selector for content (defaults to body)
            wait_for: Wait strategy

        Returns:
            Text content from the page
        """
        if not self._context:
            raise RuntimeError("Browser not started")

        page = await self._context.new_page()
        try:
            await page.goto(url, wait_until=wait_for, timeout=self.timeout)

            if selector:
                element = await page.query_selector(selector)
                if element:
                    return await element.text_content()
                return ""
            else:
                return await page.evaluate("document.body.innerText")

        finally:
            await page.close()

    async def get_all_links(
        self,
        url: str,
        pattern: Optional[str] = None,
        wait_for: str = "networkidle",
    ) -> List[str]:
        """
        Fetch a page and extract all links, optionally filtered by pattern.

        Args:
            url: URL to fetch
            pattern: Optional regex pattern to filter links
            wait_for: Wait strategy

        Returns:
            List of absolute URLs
        """
        if not self._context:
            raise RuntimeError("Browser not started")

        page = await self._context.new_page()
        try:
            await page.goto(url, wait_until=wait_for, timeout=self.timeout)

            # Extract all links
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .filter(href => href.startsWith('http'))
            """)

            # Filter by pattern if specified
            if pattern:
                regex = re.compile(pattern)
                links = [link for link in links if regex.search(link)]

            # Deduplicate
            return list(set(links))

        finally:
            await page.close()

    async def save_cookies(self, filepath: str):
        """Save current cookies to a JSON file"""
        if not self._context:
            raise RuntimeError("Browser not started")

        import json

        cookies = await self._context.cookies()
        with open(filepath, "w") as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"Saved {len(cookies)} cookies to {filepath}")


# Convenience functions for one-off usage
async def fetch_page(url: str, **kwargs) -> str:
    """Fetch a single page with a temporary browser instance"""
    async with Browser() as browser:
        return await browser.fetch(url, **kwargs)


async def get_page_content(url: str, selector: Optional[str] = None) -> str:
    """Get text content from a page with a temporary browser instance"""
    async with Browser() as browser:
        return await browser.get_text_content(url, selector)


# CLI for testing
if __name__ == "__main__":
    import sys

    async def main():
        url = sys.argv[1] if len(sys.argv) > 1 else "https://www.dwarkesh.com/podcast"

        print(f"Fetching: {url}")
        print("=" * 60)

        # Use longer timeout for slow sites
        async with Browser(timeout=60000) as browser:
            # Get all links - use "load" instead of "networkidle" for Substack
            links = await browser.get_all_links(url, pattern=r"/p/", wait_for="load")
            print(f"\nFound {len(links)} links matching /p/:")
            for link in links[:10]:
                print(f"  {link}")

            if links:
                # Fetch first episode content - use "load" for faster response
                print(f"\n\nFetching first episode: {links[0]}")
                print("=" * 60)
                content = await browser.get_text_content(links[0], wait_for="load")
                print(content[:2000] if content else "No content found")

    asyncio.run(main())
