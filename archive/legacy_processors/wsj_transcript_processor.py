#!/usr/bin/env python3
"""
WSJ Transcript Processor with Authentication
Uses provided WSJ credentials to access paywalled content
"""

import asyncio
import os
from pathlib import Path
import json
import sqlite3
from datetime import datetime
import logging

from playwright.async_api import async_playwright
from crawl4ai import AsyncWebCrawler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WSJTranscriptProcessor:
    """Process WSJ transcripts using authentication"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.transcripts_dir = self.root_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)

        # Database
        self.db_path = self.root_dir / "podcast_processing.db"

        # Load WSJ credentials from environment
        self.wsj_username = os.getenv("WSJ_USERNAME")
        self.wsj_password = os.getenv("WSJ_PASSWORD")

        if not self.wsj_username or not self.wsj_password:
            raise ValueError("WSJ credentials not found in environment variables")

        self.authenticated = False

    async def authenticate_with_wsj(self):
        """Authenticate with WSJ using Playwright"""
        logger.info("🔐 Authenticating with WSJ...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Go to WSJ login page
                await page.goto("https://wsj.com/", timeout=30000)
                await page.wait_for_timeout(2000)

                # Look for login button
                login_button = await page.query_selector("button[data-testid='login-button'], .login-button")
                if login_button:
                    await login_button.click()
                    await page.wait_for_timeout(2000)

                # Enter credentials
                await page.fill("input[name='username'], input[type='email']", self.wsj_username)
                await page.fill("input[name='password'], input[type='password']", self.wsj_password)

                # Submit login
                submit_button = await page.query_selector("button[type='submit'], .login-submit")
                if submit_button:
                    await submit_button.click()
                    await page.wait_for_timeout(5000)

                # Check if authentication succeeded
                # Look for user profile or logged-in indicators
                user_element = await page.query_selector(".user-menu, [data-testid='user-menu']")
                if user_element:
                    self.authenticated = True
                    logger.info("✅ WSJ authentication successful")

                    # Save cookies for future use
                    cookies = await context.cookies()
                    await self.save_wsj_cookies(cookies)
                else:
                    logger.error("❌ WSJ authentication failed")

            except Exception as e:
                logger.error(f"❌ Error during WSJ authentication: {e}")

            finally:
                await browser.close()

    async def save_wsj_cookies(self, cookies):
        """Save WSJ cookies for future use"""
        cookies_file = self.root_dir / "wsj_cookies.json"
        with open(cookies_file, 'w') as f:
            json.dump(cookies, f)
        logger.info(f"💾 WSJ cookies saved to {cookies_file}")

    async def load_wsj_cookies(self):
        """Load saved WSJ cookies"""
        cookies_file = self.root_dir / "wsj_cookies.json"
        if cookies_file.exists():
            with open(cookies_file, 'r') as f:
                return json.load(f)
        return []

    async def process_wsj_bad_bets(self):
        """Process Bad Bets podcast transcripts using WSJ authentication"""
        logger.info("🎯 Processing WSJ Bad Bets transcripts")

        if not self.authenticated:
            await self.authenticate_with_wsj()

        if not self.authenticated:
            logger.error("❌ Cannot process WSJ content without authentication")
            return 0

        # Initialize Crawl4AI with WSJ cookies
        cookies = await self.load_wsj_cookies()

        crawler = AsyncWebCrawler(
            headless=True,
            verbose=False,
            browser_type="chromium",
            cookies=cookies,
            delay_between_requests=5.0,
            max_concurrent_requests=1
        )

        processed_count = 0

        try:
            await crawler.acrawl()

            # Get Bad Bets episodes from database
            conn = sqlite3.connect(str(self.db_path))
            query = """
                SELECT e.id, e.title, p.name as podcast_name
                FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE p.name LIKE '%Bad Bets%'
                AND e.transcript_found = FALSE
                ORDER BY e.id DESC
                LIMIT 10
            """
            cursor = conn.execute(query)
            episodes = cursor.fetchall()
            conn.close()

            for episode_id, episode_title, podcast_name in episodes:
                # Search for WSJ Bad Bets episode page
                search_url = f"https://www.wsj.com/search?q={episode_title.replace(' ', '+')}+Bad+Bets"

                try:
                    result = await crawler.arun(
                        url=search_url,
                        word_count_threshold=50,
                        delay_before_return_html=3,
                        page_timeout=25000
                    )

                    if result.success and result.cleaned_text:
                        transcript_content = self.clean_transcript_content(result.cleaned_text)

                        if len(transcript_content) > 500:
                            if self.save_transcript(
                                episode_id, podcast_name, episode_title,
                                transcript_content, search_url, method="WSJ_Auth"
                            ):
                                processed_count += 1
                                logger.info(f"✅ Saved: {episode_title}")

                    # Rate limiting
                    await asyncio.sleep(8)

                except Exception as e:
                    logger.error(f"❌ Error processing episode {episode_title}: {e}")

        finally:
            await crawler.aclose()

        logger.info(f"🏆 WSJ Bad Bets processing complete: {processed_count} transcripts")
        return processed_count

    def clean_transcript_content(self, content: str) -> str:
        """Clean WSJ transcript content"""
        if not content:
            return ""

        # Remove WSJ-specific boilerplate
        lines = content.split('\n')
        cleaned_lines = []

        skip_phrases = [
            'wall street journal',
            'subscribe to wsj',
            'copy & paste',
            'terms of use',
            'privacy policy',
            'cookie policy'
        ]

        for line in lines:
            line = line.strip()
            if (len(line) > 30 and
                not any(phrase in line.lower() for phrase in skip_phrases)):
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def save_transcript(self, episode_id: int, podcast_name: str, episode_title: str,
                       content: str, source_url: str, method: str = "Crawl4AI") -> bool:
        """Save transcript to file and update database"""
        try:
            import re

            safe_title = re.sub(r'[^\w\s-]', '', episode_title[:60])
            filename = f"{episode_id} - {safe_title}.md"
            filepath = self.transcripts_dir / filename

            markdown_content = f"""# {episode_title}

**Podcast:** {podcast_name}
**Episode ID:** {episode_id}
**Source URL:** {source_url}
**Method:** {method}
**Downloaded:** {datetime.now().isoformat()}

## Transcript

{content}
"""

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            # Update database
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                UPDATE episodes
                SET transcript_found = ?, transcript_source = ?
                WHERE id = ?
            """, (True, source_url, episode_id))
            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"❌ Error saving transcript: {e}")
            return False

async def main():
    """Main execution"""
    processor = WSJTranscriptProcessor()
    total = await processor.process_wsj_bad_bets()

    logger.info(f"\n🎉 WSJ Bad Bets processing complete! {total} transcripts downloaded")

if __name__ == "__main__":
    asyncio.run(main())