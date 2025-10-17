"""
Article Fetching Strategies Module

This module contains different strategies for fetching articles, organized into separate classes
for better maintainability and testing. Each strategy implements a common interface.
"""

from abc import ABC, abstractmethod
from time import sleep
from typing import Any, Dict

import random
import time

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# No need for stealth when using legitimate credentials
from readability import Document

from helpers.utils import log_error, log_info

# --- Constants ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


def respectful_delay(min_seconds=2, max_seconds=8):
    """Add respectful delay to be a good citizen and avoid rate limiting"""
    delay = random.uniform(min_seconds, max_seconds)
    sleep(delay)


GOOGLEBOT_USER_AGENT = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
)
PAYWALL_PHRASES = [
    "subscribe to continue",
    "create a free account",
    "sign in to read",
    "unlock this story",
    "your free articles",
    "to continue reading",
    "subscribe now",
    "subscription required",
    "premium content",
    "members only",
    "register to continue",
    "paid subscribers only",
    "subscribe for full access",
    "subscribe for unlimited access",
    "login to read more",
    "create an account to continue",
    "please enable js",
    "please enable javascript",
    "disable any ad blocker",
    "javascript is disabled",
    "javascript required",
    "enable javascript",
    "this site requires javascript",
    "javascript must be enabled",
]
PAYWALL_ELEMENTS = [
    ".paywall",
    ".subscription-required",
    ".premium-content",
    ".register-wall",
    ".subscription-wall",
    ".paid-content",
    "#paywall",
    "#subscribe-overlay",
    "#subscription-overlay",
    "div[data-paywall]",
    "[data-require-auth]",
]
MIN_WORD_COUNT = 150
TITLE_CONTENT_RATIO_THRESHOLD = 0.1


class FetchResult:
    """Container for fetch results with metadata."""

    def __init__(
        self,
        success: bool,
        content: str = None,
        method: str = None,
        error: str = None,
        is_truncated: bool = False,
        metadata: Dict[str, Any] = None,
        title: str = None,
        strategy: str = None,
    ):
        self.success = success
        self.content = content
        # Accept both 'method' and 'strategy' for compatibility
        self.method = method or strategy
        self.strategy = strategy or method
        self.error = error
        self.is_truncated = is_truncated
        self.metadata = metadata or {}
        self.title = title


class ArticleFetchStrategy(ABC):
    """Abstract base class for article fetching strategies."""

    @abstractmethod
    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        """Fetch content from the given URL."""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of this strategy."""
        pass


class ContentAnalyzer:
    """Utility class for analyzing content quality and detecting paywalls."""

    @staticmethod
    def is_truncated(html_content: str, log_path: str) -> bool:
        """
        Checks if the content is likely truncated or behind a paywall using multiple heuristics.
        """
        if not html_content:
            return False

        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text().lower()

        # 1. Check for paywall phrases
        for phrase in PAYWALL_PHRASES:
            if phrase in text:
                log_info(log_path, f"Paywall phrase '{phrase}' detected.")
                return True

        # 2. Check for paywall HTML elements
        for selector in PAYWALL_ELEMENTS:
            if soup.select(selector):
                log_info(log_path, f"Paywall element '{selector}' detected.")
                return True

        # 3. Extract title and check title-to-content ratio
        title_tag = soup.find("title")
        if title_tag and title_tag.text:
            title_length = len(title_tag.text.strip())
            content_length = len(text)

            if content_length > 0:
                ratio = title_length / content_length
                if ratio > TITLE_CONTENT_RATIO_THRESHOLD:
                    log_info(
                        log_path,
                        f"Suspicious title-to-content ratio: {ratio:.2f}. Likely truncated.",
                    )
                    return True

        # 4. Check for login forms near the top of the page
        form_tags = soup.find_all("form")
        for form in form_tags[:3]:  # Check only the first few forms
            form_text = form.get_text().lower()
            if any(
                word in form_text
                for word in ["login", "sign in", "subscribe", "register"]
            ):
                log_info(
                    log_path,
                    "Login/subscription form detected near the top of the page.",
                )
                return True

        # 5. Check word count from readability's summary
        try:
            summary_html = Document(html_content).summary()
            summary_text = BeautifulSoup(summary_html, "html.parser").get_text()
            word_count = len(summary_text.split())
            if word_count < MIN_WORD_COUNT:
                log_info(
                    log_path,
                    f"Content is very short ({word_count} words). Likely a teaser.",
                )
                return True
        except Exception:
            # If readability fails, fall back to raw text word count
            word_count = len(text.split())
            if word_count < MIN_WORD_COUNT:
                log_info(
                    log_path,
                    f"Content is very short ({word_count} words). Likely a teaser.",
                )
                return True

        return False

    @staticmethod
    def is_likely_paywall(html_content: str, log_path: str = "") -> bool:
        # Minimal check for test compatibility: keyword or very short content
        if not html_content:
            return False
        text = html_content.lower()
        if any(phrase in text for phrase in PAYWALL_PHRASES):
            return True
        if len(text) < 10 or len(text.split()) < 5:
            return True
        return False

    @staticmethod
    def extract_title_from_html(html: str) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        if title_tag and title_tag.text.strip():
            return title_tag.text.strip()
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.text.strip():
            return h1_tag.text.strip()
        return "Untitled"


class DirectFetchStrategy(ArticleFetchStrategy):
    """Standard HTTP request strategy."""

    def __init__(self):
        self.headers = {"User-Agent": USER_AGENT}

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting direct fetch for {url}")
            response = requests.get(
                url, headers=self.headers, timeout=30, allow_redirects=True
            )
            response.raise_for_status()

            content = response.text
            is_truncated = ContentAnalyzer.is_truncated(content, log_path)
            title = ContentAnalyzer.extract_title_from_html(content)

            return FetchResult(
                success=True,
                content=content,
                method="direct",
                is_truncated=is_truncated,
                metadata={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                },
                title=title,
            )
        except (requests.exceptions.RequestException, Exception) as e:
            log_error(log_path, f"Direct fetch failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="direct")

    def get_strategy_name(self) -> str:
        return "direct"


class PaywallBypassStrategy(ArticleFetchStrategy):
    """Enhanced paywall bypass strategy with multiple alternatives to 12ft.io (shut down July 2025)."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        # List of 12ft.io alternatives from 2025 research
        bypass_services = [
            ("removepaywalls.com", "https://removepaywalls.com/{url}"),
            ("smry.ai", "https://smry.ai/{url}"),
            ("paywall.vip", "https://paywall.vip/{url}"),
            ("outline.com", "https://outline.com/{url}"),
        ]

        for service_name, url_template in bypass_services:
            try:
                log_info(log_path, f"Attempting {service_name} bypass for {url}")
                respectful_delay(2, 5)  # Be a good citizen
                bypass_url = url_template.format(url=url)
                headers = {"User-Agent": USER_AGENT}
                response = requests.get(bypass_url, headers=headers, timeout=20)
                response.raise_for_status()

                # Check if we got meaningful content
                if len(response.text) > 1000:  # Basic content check
                    return FetchResult(
                        success=True,
                        content=response.text,
                        method=f"{service_name}_bypass",
                        metadata={
                            "bypass_url": bypass_url,
                            "status_code": response.status_code,
                            "service": service_name,
                        },
                    )
                else:
                    log_info(
                        log_path,
                        f"{service_name} returned minimal content, trying next service...",
                    )

            except requests.exceptions.RequestException as e:
                log_error(log_path, f"{service_name} bypass failed for {url}: {e}")
                continue  # Try next service

        # If all services failed
        return FetchResult(
            success=False,
            error="All paywall bypass services failed",
            method="paywall_bypass",
        )

    def get_strategy_name(self) -> str:
        return "paywall_bypass"


class ArchiveTodayStrategy(ArticleFetchStrategy):
    """Enhanced Archive.today strategy with mirror domains and rate limiting."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        # Archive.today mirror domains (research from 2025)
        archive_mirrors = [
            "archive.today",
            "archive.is",
            "archive.li",
            "archive.fo",
            "archive.ph",
        ]

        for mirror in archive_mirrors:
            try:
                log_info(log_path, f"Attempting {mirror} for {url}")
                respectful_delay(1, 3)  # Be respectful between mirror attempts

                # First check if archive already exists
                search_url = f"https://{mirror}/newest/{url}"
                headers = {"User-Agent": USER_AGENT}
                response = requests.get(search_url, headers=headers, timeout=15)

                if response.status_code == 200 and mirror in response.url:
                    log_info(log_path, f"Found existing archive on {mirror} for {url}")
                    return FetchResult(
                        success=True,
                        content=response.text,
                        method=f"archive_today_existing_{mirror}",
                        metadata={"archive_url": response.url, "mirror": mirror},
                    )

                # If no existing archive, try to create one (only on first mirror to avoid spam)
                if mirror == archive_mirrors[0]:
                    log_info(
                        log_path,
                        f"No existing archive found, creating new archive for {url}",
                    )
                    submit_url = f"https://{mirror}/submit/"
                    submit_data = {"url": url}

                    response = requests.post(
                        submit_url, data=submit_data, headers=headers, timeout=30
                    )

                    if response.status_code in [200, 302]:
                        # Archive creation initiated, wait and try to access
                        sleep(5)  # Give archive time to process

                        # Try to access the newly created archive
                        response = requests.get(search_url, headers=headers, timeout=15)
                        if response.status_code == 200:
                            return FetchResult(
                                success=True,
                                content=response.text,
                                method=f"archive_today_new_{mirror}",
                                metadata={
                                    "archive_url": response.url,
                                    "mirror": mirror,
                                },
                            )
                    elif response.status_code == 429:
                        log_info(
                            log_path, f"Rate limited on {mirror}, trying next mirror..."
                        )
                        continue
                    else:
                        log_info(
                            log_path,
                            f"Archive creation failed on {mirror} with status {response.status_code}",
                        )

            except requests.exceptions.RequestException as e:
                log_error(log_path, f"{mirror} failed for {url}: {e}")
                continue  # Try next mirror

        # If all mirrors failed
        return FetchResult(
            success=False,
            error="All archive.today mirrors failed or returned low-quality content",
            method="archive_today",
        )

    def get_strategy_name(self) -> str:
        return "archive_today"


class GooglebotStrategy(ArticleFetchStrategy):
    """Googlebot user agent spoofing strategy."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Googlebot spoof for {url}")
            headers = {"User-Agent": GOOGLEBOT_USER_AGENT}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            return FetchResult(
                success=True,
                content=response.text,
                method="googlebot_spoof",
                metadata={"status_code": response.status_code},
            )
        except requests.exceptions.RequestException as e:
            log_error(log_path, f"Googlebot spoof failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="googlebot_spoof")

    def get_strategy_name(self) -> str:
        return "googlebot_spoof"


class PlaywrightStrategy(ArticleFetchStrategy):
    """Playwright headless browser strategy."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Playwright fetch for {url}")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context()
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                sleep(3)
                content = page.content()
                browser.close()
                return FetchResult(
                    success=True,
                    content=content,
                    method="playwright",
                    metadata={"url": url},
                )
        except Exception as e:
            log_error(log_path, f"Playwright fetch failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="playwright")

    def get_strategy_name(self) -> str:
        return "playwright"


class PaywallAuthenticatedStrategy(ArticleFetchStrategy):
    """Authenticated fetch strategy for paywall sites (NYTimes, WSJ, etc)."""

    def __init__(self, config=None):
        self.config = config or {}
        self.nyt_username = self.config.get("NYTIMES_USERNAME")
        self.nyt_password = self.config.get("NYTIMES_PASSWORD")
        self.wsj_username = self.config.get("WSJ_USERNAME")
        self.wsj_password = self.config.get("WSJ_PASSWORD")
        self.last_request_time = 0

    def _add_rate_limiting(self):
        """Add random delay to avoid being banned"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        # Wait 3-17 seconds between requests
        min_delay = 3
        max_delay = 17
        required_delay = random.uniform(min_delay, max_delay)

        if time_since_last < required_delay:
            sleep_time = required_delay - time_since_last
            log_info(
                "",
                f"Rate limiting: sleeping for {sleep_time:.1f} seconds to avoid bans",
            )
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        site_type = self._get_site_type(url)
        if not site_type:
            return FetchResult(
                success=False,
                error="Not a supported paywall site",
                method="paywall_auth",
            )

        credentials = self._get_credentials(site_type)
        if not credentials:
            return FetchResult(
                success=False,
                error=f"{site_type.upper()} credentials not configured",
                method="paywall_auth",
            )

        username, password = credentials

        try:
            log_info(
                log_path,
                f"Attempting {site_type.upper()} authenticated fetch for {url}",
            )

            # Rate limiting to avoid bans
            self._add_rate_limiting()

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                    ],
                )
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={"width": 1920, "height": 1080},
                    java_script_enabled=True,
                    accept_downloads=False,
                )
                page = context.new_page()

                # Login based on site type
                if site_type == "nytimes":
                    log_info(log_path, "Trying NYTimes login approach...")

                    # Try different NYTimes login URLs and approaches
                    login_attempts = [
                        "https://www.nytimes.com/subscription/multiproduct/lp8KQUS.html",
                        "https://myaccount.nytimes.com/auth/login",
                        "https://www.nytimes.com/section/todayspaper",  # Try going to subscriber page
                    ]

                    for login_url in login_attempts:
                        try:
                            log_info(log_path, f"Trying login URL: {login_url}")
                            page.goto(
                                login_url, wait_until="domcontentloaded", timeout=20000
                            )
                            time.sleep(3)

                            # Look for login form with various selectors
                            login_selectors = [
                                (
                                    'input[data-testid="email"], input[name="email"]',
                                    'input[data-testid="password"], input[name="password"]',
                                ),
                                ('input[type="email"]', 'input[type="password"]'),
                                ("#email", "#password"),
                                (".email-input", ".password-input"),
                            ]

                            for email_sel, pass_sel in login_selectors:
                                try:
                                    if page.is_visible(email_sel):
                                        log_info(
                                            log_path,
                                            f"Found login form with selector: {email_sel}",
                                        )
                                        page.fill(email_sel, username)
                                        page.fill(pass_sel, password)

                                        # Try to submit
                                        submit_selectors = [
                                            'button[data-testid="login-button"]',
                                            'button[type="submit"]',
                                            'input[type="submit"]',
                                            'button:has-text("Log in")',
                                            'button:has-text("Sign in")',
                                        ]

                                        for submit_sel in submit_selectors:
                                            if page.is_visible(submit_sel):
                                                page.click(submit_sel)
                                                break

                                        # Wait and check if login worked
                                        page.wait_for_load_state(
                                            "networkidle", timeout=10000
                                        )
                                        time.sleep(2)

                                        # If we're logged in, break out of all loops
                                        current_url = page.url
                                        if (
                                            "myaccount" in current_url
                                            or "subscriber" in current_url
                                        ):
                                            log_info(
                                                log_path,
                                                "NYTimes login appears successful",
                                            )
                                            break

                                except Exception as sel_error:
                                    log_info(
                                        log_path,
                                        f"Selector {email_sel} failed: {sel_error}",
                                    )
                                    continue
                            else:
                                continue
                            break  # If we got here, login worked
                        except Exception as url_error:
                            log_info(
                                log_path, f"Login URL {login_url} failed: {url_error}"
                            )
                            continue

                elif site_type == "wsj":
                    log_info(log_path, "Trying WSJ login...")
                    page.goto(
                        "https://accounts.wsj.com/login",
                        wait_until="domcontentloaded",
                        timeout=20000,
                    )
                    time.sleep(3)

                    # Try various WSJ selectors
                    try:
                        # Look for username/email field
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

                        for user_sel in username_selectors:
                            if page.is_visible(user_sel):
                                page.fill(user_sel, username)
                                break

                        for pass_sel in password_selectors:
                            if page.is_visible(pass_sel):
                                page.fill(pass_sel, password)
                                break

                        # Submit
                        submit_selectors = [
                            'button[type="submit"]',
                            'input[type="submit"]',
                            'button:has-text("Sign In")',
                        ]
                        for submit_sel in submit_selectors:
                            if page.is_visible(submit_sel):
                                page.click(submit_sel)
                                break

                        page.wait_for_load_state("networkidle", timeout=10000)
                        time.sleep(2)

                    except Exception as wsj_error:
                        log_info(log_path, f"WSJ login form error: {wsj_error}")

                # Give login time to complete
                time.sleep(random.uniform(3, 6))

                # Navigate to the article
                log_info(log_path, f"Navigating to article: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(random.uniform(2, 4))  # Let article load

                content = page.content()
                browser.close()

                return FetchResult(
                    success=True,
                    content=content,
                    method=f"{site_type}_auth",
                    metadata={
                        "authenticated": True,
                        "site": site_type,
                        "login_used": True,
                    },
                )

        except Exception as e:
            log_error(
                log_path,
                f"{site_type.upper()} authenticated fetch failed for {url}: {e}",
            )
            return FetchResult(success=False, error=str(e), method=f"{site_type}_auth")

    def _get_site_type(self, url: str) -> str:
        url_lower = url.lower()
        if "nytimes.com" in url_lower:
            return "nytimes"
        elif "wsj.com" in url_lower:
            return "wsj"
        return None

    def _get_credentials(self, site_type: str):
        if site_type == "nytimes" and self.nyt_username and self.nyt_password:
            return (self.nyt_username, self.nyt_password)
        elif site_type == "wsj" and self.wsj_username and self.wsj_password:
            return (self.wsj_username, self.wsj_password)
        return None

    def get_strategy_name(self) -> str:
        return "12ft"


class TwelveFtStrategy(ArticleFetchStrategy):
    """12ft.io strategy for paywall bypass"""

    def __init__(self):
        self.name = "12ft"
        self.priority = 7

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"12ft.io strategy attempting: {url}")
            twelve_ft_url = f"https://12ft.io/proxy?q={url}"
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(twelve_ft_url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            content = soup.get_text()
            if len(content.strip()) > 500:
                log_info(log_path, f"12ft.io SUCCESS for: {url}")
                return FetchResult(
                    success=True, content=content.strip(), strategy=self.name
                )
            else:
                log_info(log_path, f"12ft.io content too short for: {url}")
                return FetchResult(
                    success=False,
                    content="",
                    error="Content too short",
                    strategy=self.name,
                )
        except Exception as e:
            log_error(log_path, f"12ft.io fetch failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), strategy=self.name)

    def get_strategy_name(self) -> str:
        return "12ft"


class ReaderModeStrategy(ArticleFetchStrategy):
    """Simulate browser reader mode extraction for paywall bypass."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Reader Mode strategy for {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ReaderBot/1.0; +http://www.reader.com/bot.html)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
            response.raise_for_status()

            # Extract content using readability library (simulates reader mode)
            doc = Document(response.content)
            title = doc.title()
            content = doc.summary()

            if not content or len(content.strip()) < MIN_WORD_COUNT:
                return FetchResult(success=False, error="Reader mode content too short", method="reader_mode")

            return FetchResult(
                success=True,
                content=content,
                title=title,
                metadata={"url": url, "strategy": "reader_mode"},
            )

        except Exception as e:
            log_error(log_path, f"Reader mode fetch failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="reader_mode")

    def get_strategy_name(self) -> str:
        return "reader_mode"


class JSDisabledStrategy(ArticleFetchStrategy):
    """Retry with JavaScript disabled to bypass client-side paywalls."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting JS Disabled strategy for {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            # Use requests without JavaScript execution
            response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Remove common paywall scripts
            for script in soup.find_all("script"):
                if any(keyword in script.get_text().lower() for keyword in
                      ["paywall", "subscription", "premium", "auth", "login"]):
                    script.decompose()

            # Extract title
            title_elem = soup.find("title")
            title = title_elem.get_text().strip() if title_elem else "Untitled"

            # Use readability to extract main content
            doc = Document(str(soup))
            content = doc.summary()

            if not content or len(content.strip()) < MIN_WORD_COUNT:
                return FetchResult(success=False, error="JS disabled content too short", method="js_disabled")

            return FetchResult(
                success=True,
                content=content,
                title=title,
                metadata={"url": url, "strategy": "js_disabled"},
            )

        except Exception as e:
            log_error(log_path, f"JS disabled fetch failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="js_disabled")

    def get_strategy_name(self) -> str:
        return "js_disabled"


class RefreshStopStrategy(ArticleFetchStrategy):
    """Load page and stop before paywall script executes."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Refresh Stop strategy for {url}")

            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }

            # Make request with very short timeout to interrupt before scripts load
            try:
                response = requests.get(url, headers=headers, timeout=3, allow_redirects=True, stream=True)

                # Read only partial content to avoid paywall scripts
                content_chunks = []
                total_size = 0
                max_size = 100000  # 100KB limit to stop before heavy scripts

                for chunk in response.iter_content(chunk_size=1024):
                    content_chunks.append(chunk)
                    total_size += len(chunk)
                    if total_size > max_size:
                        break

                partial_content = b''.join(content_chunks)

            except requests.exceptions.Timeout:
                # Timeout is expected - we want to stop early
                partial_content = response.content if 'response' in locals() else b''

            if not partial_content:
                return FetchResult(success=False, error="No content retrieved", method="refresh_stop")

            soup = BeautifulSoup(partial_content, "html.parser")

            # Extract title
            title_elem = soup.find("title")
            title = title_elem.get_text().strip() if title_elem else "Untitled"

            # Extract content from what we got before paywall loaded
            doc = Document(partial_content)
            content = doc.summary()

            if not content or len(content.strip()) < MIN_WORD_COUNT:
                return FetchResult(success=False, error="Refresh stop content too short", method="refresh_stop")

            return FetchResult(
                success=True,
                content=content,
                title=title,
                metadata={"url": url, "strategy": "refresh_stop"},
            )

        except Exception as e:
            log_error(log_path, f"Refresh stop fetch failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="refresh_stop")

    def get_strategy_name(self) -> str:
        return "refresh_stop"


class InspectElementStrategy(ArticleFetchStrategy):
    """Remove paywall DOM elements programmatically."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Inspect Element strategy for {url}")

            headers = {"User-Agent": USER_AGENT}
            response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Remove common paywall elements
            paywall_selectors = [
                "[class*='paywall']", "[id*='paywall']",
                "[class*='subscription']", "[id*='subscription']",
                "[class*='premium']", "[id*='premium']",
                "[class*='overlay']", "[id*='overlay']",
                "[class*='modal']", "[id*='modal']",
                "[class*='popup']", "[id*='popup']",
                "[data-paywall]", "[data-subscription]",
                ".blur", ".blurred", "[style*='blur']",
                "[class*='truncated']", "[class*='fade']",
            ]

            for selector in paywall_selectors:
                for element in soup.select(selector):
                    element.decompose()

            # Remove style elements that might hide content
            for style in soup.find_all("style"):
                style_text = style.get_text().lower()
                if any(keyword in style_text for keyword in ["paywall", "subscription", "blur", "hidden"]):
                    style.decompose()

            # Remove scripts that might create paywalls
            for script in soup.find_all("script"):
                script_text = script.get_text().lower()
                if any(keyword in script_text for keyword in
                      ["paywall", "subscription", "premium", "auth", "login", "modal"]):
                    script.decompose()

            # Extract title
            title_elem = soup.find("title")
            title = title_elem.get_text().strip() if title_elem else "Untitled"

            # Use readability on cleaned HTML
            doc = Document(str(soup))
            content = doc.summary()

            if not content or len(content.strip()) < MIN_WORD_COUNT:
                return FetchResult(success=False, error="Inspect element content too short", method="inspect_element")

            return FetchResult(
                success=True,
                content=content,
                title=title,
                metadata={"url": url, "strategy": "inspect_element"},
            )

        except Exception as e:
            log_error(log_path, f"Inspect element fetch failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="inspect_element")

    def get_strategy_name(self) -> str:
        return "inspect_element"


class EnhancedWaybackMachineStrategy(ArticleFetchStrategy):
    """Enhanced Internet Archive Wayback Machine strategy with multiple date attempts."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Enhanced Wayback Machine for {url}")

            # Try multiple timeframes for better coverage
            timeframes = [
                "",  # Latest snapshot
                "20231201",  # Recent
                "20220101",  # 2022
                "20210101",  # 2021
                "20200101",  # 2020
                "20190101",  # 2019
                "20180101",  # 2018
                "20150101",  # 2015
                "20120101",  # 2012
                "20100101",  # 2010
            ]

            headers = {"User-Agent": USER_AGENT}

            for timeframe in timeframes:
                try:
                    if timeframe:
                        api_url = f"https://archive.org/wayback/available?url={url}&timestamp={timeframe}"
                    else:
                        api_url = f"https://archive.org/wayback/available?url={url}"

                    response = requests.get(api_url, headers=headers, timeout=15)
                    response.raise_for_status()

                    data = response.json()
                    if not data.get("archived_snapshots", {}).get("closest"):
                        continue

                    snapshot_url = data["archived_snapshots"]["closest"]["url"]
                    timestamp = data["archived_snapshots"]["closest"]["timestamp"]

                    log_info(
                        log_path,
                        f"Found Wayback snapshot from {timestamp}: {snapshot_url}",
                    )

                    # Fetch the archived content
                    response = requests.get(snapshot_url, headers=headers, timeout=25)
                    response.raise_for_status()

                    # Check if content looks good
                    if len(response.text) > 1000:  # Basic quality check
                        return FetchResult(
                            success=True,
                            content=response.text,
                            method="wayback_machine_enhanced",
                            metadata={
                                "snapshot_url": snapshot_url,
                                "timestamp": timestamp,
                                "timeframe_used": timeframe or "latest",
                            },
                        )

                except Exception as timeframe_error:
                    log_info(
                        log_path, f"Timeframe {timeframe} failed: {timeframe_error}"
                    )
                    continue

            raise Exception("No archived snapshots found in any timeframe")

        except Exception as e:
            log_error(log_path, f"Enhanced Wayback Machine failed for {url}: {e}")
            return FetchResult(
                success=False, error=str(e), method="wayback_machine_enhanced"
            )

    def get_strategy_name(self) -> str:
        return "wayback_machine_enhanced"


class WaybackMachineStrategy(ArticleFetchStrategy):
    """Internet Archive Wayback Machine strategy."""

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        try:
            log_info(log_path, f"Attempting Wayback Machine for {url}")

            # Get the latest snapshot
            api_url = f"https://archive.org/wayback/available?url={url}"
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            if not data.get("archived_snapshots", {}).get("closest"):
                raise Exception("No archived snapshots found")

            snapshot_url = data["archived_snapshots"]["closest"]["url"]
            log_info(log_path, f"Found Wayback snapshot: {snapshot_url}")

            # Fetch the archived content
            response = requests.get(snapshot_url, headers=headers, timeout=20)
            response.raise_for_status()

            return FetchResult(
                success=True,
                content=response.text,
                method="wayback_machine",
                metadata={
                    "snapshot_url": snapshot_url,
                    "timestamp": data["archived_snapshots"]["closest"]["timestamp"],
                },
            )
        except Exception as e:
            log_error(log_path, f"Wayback Machine failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="wayback_machine")

    def get_strategy_name(self) -> str:
        return "12ft"


class ArticleFetcher:
    """Main article fetcher that orchestrates different strategies."""

    def __init__(self, config=None):
        self.config = config or {}

        # Import SimpleAuthStrategy (avoiding Playwright async conflicts)
        try:
            from helpers.simple_auth_strategy import SimpleAuthStrategy

            auth_strategy = SimpleAuthStrategy(config)
        except ImportError:
            # Fallback to original if import fails
            auth_strategy = PaywallAuthenticatedStrategy(config)

        # Import Firecrawl as final fallback (with usage limits)
        try:
            from helpers.firecrawl_strategy import FirecrawlStrategy

            firecrawl = FirecrawlStrategy(config)
        except ImportError:
            firecrawl = None

        self.strategies = [
            DirectFetchStrategy(),
            auth_strategy,  # Simple authentication for paywall sites (no Playwright conflicts)
            ReaderModeStrategy(),  # Community technique: Reader mode extraction
            JSDisabledStrategy(),  # Community technique: JavaScript disabled
            RefreshStopStrategy(),  # Community technique: Stop before paywall loads
            InspectElementStrategy(),  # Community technique: Remove paywall elements
            PaywallBypassStrategy(),
            ArchiveTodayStrategy(),
            GooglebotStrategy(),
            # PlaywrightStrategy(),  # Disabled due to async conflicts
            EnhancedWaybackMachineStrategy(),  # Enhanced multi-date Wayback
            WaybackMachineStrategy(),  # Original Wayback fallback
        ]

        # Add Firecrawl as final fallback if available and has usage remaining
        if firecrawl and firecrawl._check_usage_limit():
            self.strategies.append(firecrawl)  # Last resort - 500/month limit

    def fetch_with_fallbacks(self, url: str, log_path: str) -> FetchResult:
        """
        Attempt to fetch content using multiple strategies in order.
        Returns the first successful result with good content quality.
        """
        for strategy in self.strategies:
            result = strategy.fetch(url, log_path)

            if result.success:
                # Check if content is truncated or low quality for ALL strategies
                is_truncated = ContentAnalyzer.is_truncated(result.content, log_path)

                if is_truncated:
                    log_info(
                        log_path,
                        f"{strategy.get_strategy_name()} succeeded but content appears truncated/low quality, trying next strategy...",
                    )
                    result.is_truncated = True
                    continue

                log_info(
                    log_path,
                    f"Successfully fetched {url} using {strategy.get_strategy_name()}",
                )
                return result

        # All strategies failed or returned low-quality content
        # GOOGLE SEARCH FALLBACK - The Ultimate Safety Net
        log_error(
            log_path,
            f"All fetch strategies failed or returned low-quality content for {url}. Attempting Google Search fallback...",
        )

        # Try Google Search fallback to find alternative URLs
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from helpers.google_search_fallback import search_with_google_fallback
            import asyncio

            # Extract title from the URL for better search results
            # We can parse the URL path or use a simple extraction
            from urllib.parse import urlparse, unquote
            parsed_url = urlparse(url)

            # Try to extract meaningful search terms from URL
            path_parts = [part for part in parsed_url.path.split('/') if part and not part.isdigit()]
            if path_parts:
                # Use the last meaningful part of the path as search query
                search_query = unquote(path_parts[-1]).replace('-', ' ').replace('_', ' ')
            else:
                # Fallback to using the domain
                search_query = f"article {parsed_url.netloc}"

            log_info(log_path, f"Google Search fallback: searching for '{search_query}'")

            # Run async search in sync context
            if hasattr(asyncio, '_nest_patched'):
                # Already in async context (Jupyter/etc), use existing loop
                loop = asyncio.get_event_loop()
                alternative_url = loop.run_until_complete(search_with_google_fallback(search_query, priority=2))
            else:
                # Create new event loop
                alternative_url = asyncio.run(search_with_google_fallback(search_query, priority=2))

            if alternative_url and alternative_url != url:
                log_info(log_path, f"Google Search found alternative URL: {alternative_url}")

                # Try to fetch the alternative URL with our strategies
                for strategy in self.strategies[:3]:  # Only try top 3 strategies for alternative URL
                    result = strategy.fetch(alternative_url, log_path)
                    if result.success and not ContentAnalyzer.is_truncated(result.content, log_path):
                        log_info(log_path, f"Successfully fetched alternative URL using {strategy.get_strategy_name()}")
                        result.metadata = result.metadata or {}
                        result.metadata['google_search_fallback'] = True
                        result.metadata['original_url'] = url
                        result.metadata['alternative_url'] = alternative_url
                        return result

                log_info(log_path, f"Alternative URL found but could not fetch content successfully")
            else:
                log_info(log_path, "Google Search fallback did not find alternative URL")

        except Exception as e:
            log_error(log_path, f"Google Search fallback failed: {e}")

        return FetchResult(
            success=False, error="All strategies including Google Search fallback failed"
        )
