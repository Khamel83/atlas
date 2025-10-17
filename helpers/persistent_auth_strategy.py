#!/usr/bin/env python3
"""
Enhanced Persistent Authentication Strategy for Atlas
Maintains login sessions with cookie persistence for NYTimes, WSJ, and other paywall sites.
"""

import json
import random
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from playwright.sync_api import sync_playwright, BrowserContext, Page

from helpers.article_strategies import (
    ArticleFetchStrategy,
    FetchResult,
    ContentAnalyzer,
    USER_AGENT,
)
from helpers.utils import log_info, log_error


class PersistentAuthStrategy(ArticleFetchStrategy):
    """Enhanced authentication strategy with persistent cookie sessions."""

    def __init__(self, config=None):
        self.config = config or {}
        self.nyt_username = self.config.get("NYTIMES_USERNAME")
        self.nyt_password = self.config.get("NYTIMES_PASSWORD")
        self.wsj_username = self.config.get("WSJ_USERNAME")
        self.wsj_password = self.config.get("WSJ_PASSWORD")

        # Session persistence
        self.sessions_dir = Path("/home/ubuntu/dev/atlas/data/auth_sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting
        self.last_request_time = 0
        self.min_delay = 3
        self.max_delay = 17

        # Session cache
        self._active_contexts = {}

    def _get_session_file(self, site: str) -> Path:
        """Get session storage file for a site."""
        return self.sessions_dir / f"{site}_session.json"

    def _load_session(self, site: str) -> Optional[Dict]:
        """Load existing session data for a site."""
        session_file = self._get_session_file(site)
        if session_file.exists():
            try:
                with open(session_file, "r") as f:
                    session_data = json.load(f)

                # Check if session is not too old (24 hours)
                session_age = time.time() - session_data.get("created_at", 0)
                if session_age < 24 * 3600:  # 24 hours
                    return session_data
                else:
                    log_info("", f"Session for {site} expired, will create new one")
                    session_file.unlink()  # Delete old session
            except Exception as e:
                log_error("", f"Failed to load session for {site}: {e}")
        return None

    def _save_session(self, site: str, cookies: list, storage_state: dict = None):
        """Save session data for a site."""
        session_data = {
            "cookies": cookies,
            "storage_state": storage_state,
            "created_at": time.time(),
            "site": site,
        }

        session_file = self._get_session_file(site)
        try:
            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)
            log_info("", f"Saved session for {site}")
        except Exception as e:
            log_error("", f"Failed to save session for {site}: {e}")

    def _rate_limit(self):
        """Apply rate limiting to avoid bans."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        required_delay = random.uniform(self.min_delay, self.max_delay)

        if time_since_last < required_delay:
            sleep_time = required_delay - time_since_last
            log_info("", f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _get_site_type(self, url: str) -> Optional[str]:
        """Determine site type from URL."""
        url_lower = url.lower()
        if "nytimes.com" in url_lower:
            return "nytimes"
        elif "wsj.com" in url_lower:
            return "wsj"
        return None

    def _get_credentials(self, site: str) -> Optional[Tuple[str, str]]:
        """Get credentials for a site."""
        if site == "nytimes" and self.nyt_username and self.nyt_password:
            return (self.nyt_username, self.nyt_password)
        elif site == "wsj" and self.wsj_username and self.wsj_password:
            return (self.wsj_username, self.wsj_password)
        return None

    def _create_authenticated_context(
        self, site: str, log_path: str = ""
    ) -> Optional[BrowserContext]:
        """Create or restore an authenticated browser context."""

        # Check if we have a cached context
        if site in self._active_contexts:
            try:
                # Test if context is still valid
                context = self._active_contexts[site]
                page = context.new_page()
                page.close()
                log_info(log_path, f"Reusing existing {site} context")
                return context
            except Exception:
                log_info(log_path, f"Cached {site} context invalid, creating new one")
                del self._active_contexts[site]

        credentials = self._get_credentials(site)
        if not credentials:
            return None

        username, password = credentials

        try:
            # Create browser with stealth settings
            browser = (
                sync_playwright()
                .start()
                .chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                        "--disable-dev-shm-usage",
                        "--no-first-run",
                    ],
                )
            )

            # Try to load existing session
            session_data = self._load_session(site)

            if session_data:
                log_info(log_path, f"Loading existing {site} session")
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={"width": 1920, "height": 1080},
                    storage_state=session_data.get("storage_state"),
                )

                # Test if session is still valid
                page = context.new_page()
                test_result = self._test_authentication(page, site, log_path)

                if test_result:
                    log_info(log_path, f"Existing {site} session is valid")
                    self._active_contexts[site] = context
                    page.close()
                    return context
                else:
                    log_info(
                        log_path, f"Existing {site} session invalid, logging in fresh"
                    )
                    page.close()
                    context.close()

            # Create fresh context and login
            context = browser.new_context(
                user_agent=USER_AGENT, viewport={"width": 1920, "height": 1080}
            )

            page = context.new_page()

            # Perform login based on site
            login_success = False
            if site == "nytimes":
                login_success = self._login_nytimes(page, username, password, log_path)
            elif site == "wsj":
                login_success = self._login_wsj(page, username, password, log_path)

            if login_success:
                # Save session
                storage_state = context.storage_state()
                cookies = context.cookies()
                self._save_session(site, cookies, storage_state)

                self._active_contexts[site] = context
                page.close()
                log_info(log_path, f"Successfully logged into {site}")
                return context
            else:
                page.close()
                context.close()
                browser.close()
                return None

        except Exception as e:
            log_error(
                log_path, f"Failed to create authenticated context for {site}: {e}"
            )
            return None

    def _test_authentication(self, page: Page, site: str, log_path: str = "") -> bool:
        """Test if current session is authenticated."""
        try:
            if site == "nytimes":
                # Try to access subscriber content
                page.goto("https://www.nytimes.com/section/todayspaper", timeout=15000)
                time.sleep(3)

                # Check for subscriber indicators
                content = page.content().lower()
                if "subscriber" in content or "account" in content:
                    return True

            elif site == "wsj":
                # Try to access WSJ subscriber area
                page.goto("https://www.wsj.com/my/", timeout=15000)
                time.sleep(3)

                # Check if we're logged in
                content = page.content().lower()
                if "my account" in content or "dashboard" in content:
                    return True

            return False

        except Exception as e:
            log_info(log_path, f"Authentication test failed for {site}: {e}")
            return False

    def _login_nytimes(
        self, page: Page, username: str, password: str, log_path: str = ""
    ) -> bool:
        """Login to NYTimes."""
        try:
            log_info(log_path, "Attempting NYTimes login...")

            # Try multiple login approaches
            login_urls = [
                "https://myaccount.nytimes.com/auth/login",
                "https://www.nytimes.com/subscription/multiproduct/lp8KQUS.html",
            ]

            for login_url in login_urls:
                try:
                    page.goto(login_url, wait_until="domcontentloaded", timeout=20000)
                    time.sleep(3)

                    # Try different selector combinations
                    login_selectors = [
                        (
                            'input[data-testid="email"]',
                            'input[data-testid="password"]',
                            'button[data-testid="login-button"]',
                        ),
                        (
                            'input[name="email"]',
                            'input[name="password"]',
                            'button[type="submit"]',
                        ),
                        (
                            'input[type="email"]',
                            'input[type="password"]',
                            'button:has-text("Log in")',
                        ),
                        ("#email", "#password", 'button:has-text("Sign in")'),
                    ]

                    for email_sel, pass_sel, submit_sel in login_selectors:
                        try:
                            if page.locator(email_sel).is_visible():
                                log_info(
                                    log_path,
                                    f"Found login form with selector: {email_sel}",
                                )

                                page.fill(email_sel, username)
                                page.fill(pass_sel, password)
                                page.click(submit_sel)

                                # Wait for navigation
                                page.wait_for_load_state("networkidle", timeout=15000)
                                time.sleep(3)

                                # Check if login was successful
                                current_url = page.url.lower()
                                if (
                                    "myaccount" in current_url
                                    or "subscriber" in current_url
                                ):
                                    log_info(log_path, "NYTimes login successful")
                                    return True

                                # Test with content check
                                content = page.content().lower()
                                if "subscriber" in content and "dashboard" in content:
                                    log_info(
                                        log_path,
                                        "NYTimes login successful (content check)",
                                    )
                                    return True

                        except Exception as sel_error:
                            log_info(log_path, f"Selector attempt failed: {sel_error}")
                            continue

                except Exception as url_error:
                    log_info(log_path, f"Login URL {login_url} failed: {url_error}")
                    continue

            return False

        except Exception as e:
            log_error(log_path, f"NYTimes login failed: {e}")
            return False

    def _login_wsj(
        self, page: Page, username: str, password: str, log_path: str = ""
    ) -> bool:
        """Login to Wall Street Journal."""
        try:
            log_info(log_path, "Attempting WSJ login...")

            page.goto(
                "https://accounts.wsj.com/login",
                wait_until="domcontentloaded",
                timeout=20000,
            )
            time.sleep(3)

            # Try different selector combinations
            username_selectors = [
                'input[name="username"]',
                'input[type="email"]',
                "#username",
            ]
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                "#password",
            ]
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Sign In")',
            ]

            # Fill username
            for user_sel in username_selectors:
                if page.locator(user_sel).is_visible():
                    page.fill(user_sel, username)
                    break

            # Fill password
            for pass_sel in password_selectors:
                if page.locator(pass_sel).is_visible():
                    page.fill(pass_sel, password)
                    break

            # Submit
            for submit_sel in submit_selectors:
                if page.locator(submit_sel).is_visible():
                    page.click(submit_sel)
                    break

            # Wait for login to complete
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(3)

            # Check if login was successful
            current_url = page.url.lower()
            if "wsj.com" in current_url and "login" not in current_url:
                log_info(log_path, "WSJ login successful")
                return True

            return False

        except Exception as e:
            log_error(log_path, f"WSJ login failed: {e}")
            return False

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        """Fetch article using persistent authentication."""
        site_type = self._get_site_type(url)
        if not site_type:
            return FetchResult(
                success=False,
                error="Not a supported paywall site",
                method="persistent_auth",
            )

        credentials = self._get_credentials(site_type)
        if not credentials:
            return FetchResult(
                success=False,
                error=f"{site_type.upper()} credentials not configured",
                method="persistent_auth",
            )

        try:
            log_info(
                log_path,
                f"Attempting persistent authenticated fetch for {site_type.upper()}: {url}",
            )

            # Rate limiting
            self._rate_limit()

            # Get or create authenticated context
            context = self._create_authenticated_context(site_type, log_path)
            if not context:
                return FetchResult(
                    success=False,
                    error=f"Failed to authenticate with {site_type}",
                    method="persistent_auth",
                )

            # Use context to fetch article
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(2, 4))  # Let article load

            content = page.content()
            page.close()

            # Check content quality
            if len(content) > 1000:  # Basic quality check
                title = ContentAnalyzer.extract_title_from_html(content)
                is_truncated = ContentAnalyzer.is_truncated(content, log_path)

                return FetchResult(
                    success=True,
                    content=content,
                    method=f"{site_type}_persistent_auth",
                    title=title,
                    is_truncated=is_truncated,
                    metadata={
                        "authenticated": True,
                        "site": site_type,
                        "session_persisted": True,
                    },
                )
            else:
                return FetchResult(
                    success=False, error="Content too short", method="persistent_auth"
                )

        except Exception as e:
            log_error(
                log_path, f"{site_type.upper()} persistent auth failed for {url}: {e}"
            )
            return FetchResult(success=False, error=str(e), method="persistent_auth")

    def get_strategy_name(self) -> str:
        return "persistent_auth"

    def cleanup(self):
        """Clean up browser contexts."""
        for site, context in self._active_contexts.items():
            try:
                context.close()
            except Exception:
                pass
        self._active_contexts.clear()

    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup()
