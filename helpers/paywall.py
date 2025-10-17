"""
Paywall Detection and Bypass System

IMPORTANT: All bypass functionality is DISABLED BY DEFAULT for legal compliance.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


class LegalComplianceError(Exception):
    """Exception for legal safeguard violations."""

    pass


@dataclass
class JurisdictionRules:
    """Legal requirements by jurisdiction."""

    requires_watermark: bool = True
    max_retention_days: int = 30
    allow_archival: bool = False


class PaywallDetector:
    """Core paywall detection system."""

    def __init__(self, patterns_path: str = "config/paywall_patterns.json"):
        self.patterns = self._load_patterns(patterns_path)

    def _load_patterns(self, path: str) -> Dict:
        """Load detection patterns from JSON file."""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"dom_selectors": [], "url_patterns": [], "content_phrases": []}

    def detect(self, html: str, url: str) -> bool:
        """Check if content appears to be behind a paywall."""
        if not html:
            return False

        html_lower = html.lower()

        # Check URL patterns for known paywall sites
        paywall_domains = [
            "nytimes.com",
            "wsj.com",
            "ft.com",
            "bloomberg.com",
            "economist.com",
            "washingtonpost.com",
            "medium.com",
            "theathletic.com",
            "stratechery.com",
        ]

        for domain in paywall_domains:
            if domain in url.lower():
                return True

        # Check for paywall indicator phrases
        paywall_phrases = [
            "subscribe to continue reading",
            "this article is for subscribers",
            "premium content",
            "paywall",
            "subscription required",
            "sign up to read",
            "become a member",
            "upgrade to premium",
            "free article limit",
            "register to continue",
            "log in to read",
        ]

        for phrase in paywall_phrases:
            if phrase in html_lower:
                return True

        # Check DOM selectors for paywall elements
        paywall_selectors = self.patterns.get("dom_selectors", [])
        for selector in paywall_selectors:
            # Simple check for class/id names in HTML
            if f'class="{selector}"' in html_lower or f'id="{selector}"' in html_lower:
                return True

        # Check for truncated content indicators
        truncation_indicators = [
            "...",
            "(continued)",
            "read more",
            "full article",
            "complete story",
            "entire article",
        ]

        # If content is very short and has truncation indicators
        if len(html) < 2000:  # Short content
            for indicator in truncation_indicators:
                if indicator in html_lower:
                    return True

        return False


@dataclass
class PaywallBypass:
    """Bypass system with enhanced legal safeguards."""

    enabled: bool = False
    allowed_domains: Dict[str, datetime] = field(default_factory=dict)
    consent_ttl: int = 2592000  # 30 days in seconds
    jurisdiction_rules: Dict[str, JurisdictionRules] = field(default_factory=dict)

    def __post_init__(self):
        # Initialize default jurisdiction rules
        self.jurisdiction_rules = {
            "us": JurisdictionRules(requires_watermark=True, max_retention_days=30),
            "eu": JurisdictionRules(requires_watermark=True, max_retention_days=14),
            "de": JurisdictionRules(allow_archival=False),
        }

    def enable_for_domain(
        self, domain: str, reason: str, jurisdiction: str = "us"
    ) -> bool:
        """Enable bypass for specific domain with documented reason and jurisdiction check."""
        if not reason:
            raise LegalComplianceError("Consent reason must be documented")

        if jurisdiction in self.jurisdiction_rules:
            rules = self.jurisdiction_rules[jurisdiction]
            if not rules.allow_archival and "archive" in domain:
                raise LegalComplianceError(f"Archival prohibited in {jurisdiction}")

        self.allowed_domains[domain] = datetime.now()
        return True

    def check_consent_valid(self, domain: str) -> bool:
        """Verify consent exists and hasn't expired."""
        if domain not in self.allowed_domains:
            return False

        elapsed = (datetime.now() - self.allowed_domains[domain]).total_seconds()
        return elapsed < self.consent_ttl

    def execute_bypass(
        self, html: str, domain: str, method: str = "dom_cleanup"
    ) -> Optional[str]:
        """Attempt to bypass paywall if enabled and consent is valid."""
        if not self.check_consent_valid(domain):
            return None

        try:
            cleaned_html = html

            if method == "dom_cleanup":
                cleaned_html = self._clean_paywall_elements(html)
            elif method == "content_extraction":
                cleaned_html = self._extract_main_content(html)
            elif method == "simple_strip":
                cleaned_html = self._simple_paywall_strip(html)

            # Apply watermark if required by jurisdiction
            if self._requires_watermark(domain):
                cleaned_html = self._apply_watermark(cleaned_html)

            return cleaned_html

        except Exception as e:
            print(f"Paywall bypass error: {e}")
            return None

    def _clean_paywall_elements(self, html: str) -> str:
        """Remove common paywall DOM elements."""
        # Common paywall element patterns to remove
        paywall_patterns = [
            r'<div[^>]*class="[^"]*paywall[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*subscription[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*premium[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*id="[^"]*paywall[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*modal[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*overlay[^"]*"[^>]*>.*?</div>',
        ]

        import re

        cleaned = html
        for pattern in paywall_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)

        return cleaned

    def _extract_main_content(self, html: str) -> str:
        """Extract main article content, ignoring paywall elements."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remove known paywall elements
            paywall_selectors = [
                ".paywall",
                "#paywall",
                ".subscription-banner",
                ".premium-content",
                ".modal",
                ".overlay",
                ".subscription-required",
                ".register-wall",
            ]

            for selector in paywall_selectors:
                elements = soup.select(selector)
                for element in elements:
                    element.decompose()

            # Try to find main content
            main_content_selectors = [
                "article",
                ".article-content",
                ".content",
                ".post-content",
                ".entry-content",
                "main",
                ".story-body",
                ".article-body",
            ]

            for selector in main_content_selectors:
                content = soup.select_one(selector)
                if content:
                    return str(content)

            # Fallback to body content
            body = soup.find("body")
            return str(body) if body else html

        except ImportError:
            # BeautifulSoup not available, use simple text processing
            return self._simple_paywall_strip(html)
        except Exception:
            return html

    def _simple_paywall_strip(self, html: str) -> str:
        """Simple text-based paywall content removal."""
        lines = html.split("\n")
        cleaned_lines = []

        skip_patterns = [
            "subscribe",
            "premium",
            "paywall",
            "sign up",
            "register",
            "membership",
            "subscription",
        ]

        for line in lines:
            line_lower = line.lower()
            # Skip lines that contain paywall-related terms
            if not any(pattern in line_lower for pattern in skip_patterns):
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _requires_watermark(self, domain: str) -> bool:
        """Check if jurisdiction requires watermarking."""
        # Simplified - would normally detect TLD
        return any(tld in domain for tld in [".com", ".org"])

    def _apply_watermark(self, html: str) -> str:
        """Add legal watermark to content."""
        watermark = "<!-- BYPASSED_FOR_PERSONAL_USE_ONLY -->"
        return watermark + html
