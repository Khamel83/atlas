#!/usr/bin/env python3
"""
Simple Authentication Strategy using requests + session persistence
Avoids Playwright async issues while maintaining login sessions for paywall sites.
"""

import json
import random
import time
from pathlib import Path
from typing import Optional, Tuple
import requests
from bs4 import BeautifulSoup

from helpers.article_strategies import (
    ArticleFetchStrategy,
    FetchResult,
    ContentAnalyzer,
    USER_AGENT,
)
from helpers.utils import log_info, log_error


class SimpleAuthStrategy(ArticleFetchStrategy):
    """Simple authentication strategy using requests sessions with cookie persistence."""

    def __init__(self, config=None):
        self.config = config or {}
        self.nyt_username = self.config.get("NYTIMES_USERNAME")
        self.nyt_password = self.config.get("NYTIMES_PASSWORD")
        self.wsj_username = self.config.get("WSJ_USERNAME")
        self.wsj_password = self.config.get("WSJ_PASSWORD")

        # Session storage
        self.sessions_dir = Path("/home/ubuntu/dev/atlas/data/auth_sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Active sessions cache
        self._sessions = {}

        # Rate limiting
        self.last_request_time = 0

    def _get_session_file(self, site: str) -> Path:
        """Get session storage file for a site."""
        return self.sessions_dir / f"{site}_cookies.json"

    def _load_session(self, site: str) -> Optional[requests.Session]:
        """Load existing session with cookies for a site."""
        session_file = self._get_session_file(site)
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        if session_file.exists():
            try:
                with open(session_file, "r") as f:
                    cookies_data = json.load(f)

                # Check if session is not too old (6 hours)
                session_age = time.time() - cookies_data.get("created_at", 0)
                if session_age < 6 * 3600:  # 6 hours
                    # Load cookies into session
                    for cookie in cookies_data.get("cookies", []):
                        session.cookies.set(
                            cookie["name"], cookie["value"], domain=cookie["domain"]
                        )

                    log_info("", f"Loaded existing session for {site}")
                    return session
                else:
                    log_info("", f"Session for {site} expired, will create new one")
                    session_file.unlink()

            except Exception as e:
                log_error("", f"Failed to load session for {site}: {e}")

        return session

    def _save_session(self, site: str, session: requests.Session):
        """Save session cookies for a site."""
        cookies_data = {"cookies": [], "created_at": time.time(), "site": site}

        for cookie in session.cookies:
            cookies_data["cookies"].append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                }
            )

        session_file = self._get_session_file(site)
        try:
            with open(session_file, "w") as f:
                json.dump(cookies_data, f, indent=2)
            log_info("", f"Saved session for {site}")
        except Exception as e:
            log_error("", f"Failed to save session for {site}: {e}")

    def _rate_limit(self):
        """Apply rate limiting to avoid bans."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        min_delay, max_delay = 3, 8
        required_delay = random.uniform(min_delay, max_delay)

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

    def _login_nytimes(
        self,
        session: requests.Session,
        username: str,
        password: str,
        log_path: str = "",
    ) -> bool:
        """Login to NYTimes using requests session."""
        try:
            log_info(log_path, "Attempting NYTimes login via requests...")

            # Get login page
            login_url = "https://myaccount.nytimes.com/auth/login"
            response = session.get(login_url, timeout=15)

            if response.status_code != 200:
                log_error(
                    log_path,
                    f"Failed to access NYTimes login page: {response.status_code}",
                )
                return False

            # Parse login form
            soup = BeautifulSoup(response.text, "html.parser")

            # Find login form
            form = soup.find("form")
            if not form:
                log_error(log_path, "Could not find login form on NYTimes")
                return False

            # Prepare login data
            login_data = {"email": username, "password": password}

            # Look for hidden fields (CSRF tokens, etc.)
            hidden_inputs = soup.find_all("input", type="hidden")
            for hidden in hidden_inputs:
                name = hidden.get("name")
                value = hidden.get("value")
                if name and value:
                    login_data[name] = value

            # Submit login
            form_action = form.get("action", login_url)
            if not form_action.startswith("http"):
                form_action = "https://myaccount.nytimes.com" + form_action

            response = session.post(
                form_action, data=login_data, timeout=15, allow_redirects=True
            )

            # Check if login was successful
            if response.status_code == 200:
                # Look for indicators of successful login
                if "myaccount" in response.url or "subscriber" in response.text.lower():
                    log_info(log_path, "NYTimes login appears successful")
                    return True

            log_error(
                log_path,
                f"NYTimes login failed - Status: {response.status_code}, URL: {response.url}",
            )
            return False

        except Exception as e:
            log_error(log_path, f"NYTimes login error: {e}")
            return False

    def _login_wsj(
        self,
        session: requests.Session,
        username: str,
        password: str,
        log_path: str = "",
    ) -> bool:
        """Login to WSJ using requests session."""
        try:
            log_info(log_path, "Attempting WSJ login via requests...")

            # Get login page
            login_url = "https://accounts.wsj.com/login"
            response = session.get(login_url, timeout=15)

            if response.status_code != 200:
                log_error(
                    log_path, f"Failed to access WSJ login page: {response.status_code}"
                )
                return False

            # Parse login form
            soup = BeautifulSoup(response.text, "html.parser")

            # Find login form
            form = soup.find("form")
            if not form:
                log_error(log_path, "Could not find login form on WSJ")
                return False

            # Prepare login data
            login_data = {"username": username, "password": password}

            # Look for hidden fields
            hidden_inputs = soup.find_all("input", type="hidden")
            for hidden in hidden_inputs:
                name = hidden.get("name")
                value = hidden.get("value")
                if name and value:
                    login_data[name] = value

            # Submit login
            form_action = form.get("action", login_url)
            if not form_action.startswith("http"):
                form_action = "https://accounts.wsj.com" + form_action

            response = session.post(
                form_action, data=login_data, timeout=15, allow_redirects=True
            )

            # Check if login was successful
            if response.status_code == 200:
                if "wsj.com" in response.url and "login" not in response.url:
                    log_info(log_path, "WSJ login appears successful")
                    return True

            log_error(
                log_path,
                f"WSJ login failed - Status: {response.status_code}, URL: {response.url}",
            )
            return False

        except Exception as e:
            log_error(log_path, f"WSJ login error: {e}")
            return False

    def _test_authentication(
        self, session: requests.Session, site: str, log_path: str = ""
    ) -> bool:
        """Test if session is authenticated by accessing subscriber content."""
        try:
            if site == "nytimes":
                test_url = "https://www.nytimes.com/section/todayspaper"
                response = session.get(test_url, timeout=10)
                if response.status_code == 200:
                    content = response.text.lower()
                    return "subscriber" in content or "account" in content

            elif site == "wsj":
                test_url = "https://www.wsj.com/"
                response = session.get(test_url, timeout=10)
                if response.status_code == 200:
                    content = response.text.lower()
                    return "my account" in content or "subscriber" in content

            return False

        except Exception as e:
            log_info(log_path, f"Authentication test failed for {site}: {e}")
            return False

    def _get_authenticated_session(
        self, site: str, log_path: str = ""
    ) -> Optional[requests.Session]:
        """Get or create authenticated session for site."""

        # Check if we have a cached session
        if site in self._sessions:
            session = self._sessions[site]
            if self._test_authentication(session, site, log_path):
                log_info(log_path, f"Using cached {site} session")
                return session
            else:
                log_info(log_path, f"Cached {site} session invalid")
                del self._sessions[site]

        # Load or create new session
        session = self._load_session(site)

        # Test if loaded session is still valid
        if self._test_authentication(session, site, log_path):
            log_info(log_path, f"Loaded {site} session is valid")
            self._sessions[site] = session
            return session

        # Need to login
        credentials = self._get_credentials(site)
        if not credentials:
            return None

        username, password = credentials

        # Perform login
        login_success = False
        if site == "nytimes":
            login_success = self._login_nytimes(session, username, password, log_path)
        elif site == "wsj":
            login_success = self._login_wsj(session, username, password, log_path)

        if login_success:
            self._save_session(site, session)
            self._sessions[site] = session
            return session

        return None

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        """Fetch article using simple authentication."""
        site_type = self._get_site_type(url)
        if not site_type:
            return FetchResult(
                success=False,
                error="Not a supported paywall site",
                method="simple_auth",
            )

        credentials = self._get_credentials(site_type)
        if not credentials:
            return FetchResult(
                success=False,
                error=f"{site_type.upper()} credentials not configured",
                method="simple_auth",
            )

        try:
            log_info(
                log_path,
                f"Attempting simple authenticated fetch for {site_type.upper()}: {url}",
            )

            # Rate limiting
            self._rate_limit()

            # Get authenticated session
            session = self._get_authenticated_session(site_type, log_path)
            if not session:
                return FetchResult(
                    success=False,
                    error=f"Failed to authenticate with {site_type}",
                    method="simple_auth",
                )

            # Fetch article with authenticated session
            response = session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()

            content = response.text

            # Check content quality
            if len(content) > 1000:
                title = ContentAnalyzer.extract_title_from_html(content)
                is_truncated = ContentAnalyzer.is_truncated(content, log_path)

                return FetchResult(
                    success=True,
                    content=content,
                    method=f"{site_type}_simple_auth",
                    title=title,
                    is_truncated=is_truncated,
                    metadata={
                        "authenticated": True,
                        "site": site_type,
                        "status_code": response.status_code,
                    },
                )
            else:
                return FetchResult(
                    success=False, error="Content too short", method="simple_auth"
                )

        except Exception as e:
            log_error(
                log_path, f"{site_type.upper()} simple auth failed for {url}: {e}"
            )
            return FetchResult(success=False, error=str(e), method="simple_auth")

    def get_strategy_name(self) -> str:
        return "simple_auth"
