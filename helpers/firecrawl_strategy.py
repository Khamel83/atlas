#!/usr/bin/env python3
"""
Firecrawl Strategy for Atlas - Final fallback with usage tracking
Uses Firecrawl MCP Server as last resort with 500/month limit tracking.
"""

import json
from pathlib import Path
from typing import Dict, Any
import requests
from datetime import datetime

from helpers.article_strategies import (
    ArticleFetchStrategy,
    FetchResult,
    ContentAnalyzer,
)
from helpers.utils import log_info, log_error


class FirecrawlStrategy(ArticleFetchStrategy):
    """Firecrawl MCP strategy with usage tracking and 500/month limit."""

    def __init__(self, config=None):
        self.config = config or {}
        self.api_key = self.config.get("FIRECRAWL_API_KEY")
        self.base_url = "https://api.firecrawl.dev/v0"

        # Usage tracking
        self.usage_file = Path("/home/ubuntu/dev/atlas/data/firecrawl_usage.json")
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)

        # Monthly limit
        self.monthly_limit = 500

    def _load_usage_data(self) -> Dict[str, Any]:
        """Load monthly usage data."""
        if not self.usage_file.exists():
            return {
                "month": datetime.now().strftime("%Y-%m"),
                "usage_count": 0,
                "total_used": 0,
                "last_reset": datetime.now().isoformat(),
                "successful_requests": 0,
                "failed_requests": 0,
            }

        try:
            with open(self.usage_file, "r") as f:
                data = json.load(f)

            current_month = datetime.now().strftime("%Y-%m")

            # Reset if new month
            if data.get("month") != current_month:
                log_info(
                    "",
                    f"Resetting Firecrawl usage counter for new month: {current_month}",
                )
                data = {
                    "month": current_month,
                    "usage_count": 0,
                    "total_used": data.get("total_used", 0),
                    "last_reset": datetime.now().isoformat(),
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "previous_month_usage": data.get("usage_count", 0),
                }
                self._save_usage_data(data)

            return data

        except Exception as e:
            log_error("", f"Failed to load Firecrawl usage data: {e}")
            return self._load_usage_data()  # Return default

    def _save_usage_data(self, data: Dict[str, Any]):
        """Save usage data to file."""
        try:
            with open(self.usage_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log_error("", f"Failed to save Firecrawl usage data: {e}")

    def _increment_usage(self, successful: bool = True):
        """Increment usage counter."""
        data = self._load_usage_data()
        data["usage_count"] += 1
        data["total_used"] += 1

        if successful:
            data["successful_requests"] += 1
        else:
            data["failed_requests"] += 1

        data["last_used"] = datetime.now().isoformat()
        self._save_usage_data(data)

    def _check_usage_limit(self) -> bool:
        """Check if we're under the monthly limit."""
        data = self._load_usage_data()
        current_usage = data.get("usage_count", 0)

        if current_usage >= self.monthly_limit:
            log_info(
                "",
                f"Firecrawl monthly limit reached: {current_usage}/{self.monthly_limit}",
            )
            return False

        log_info(
            "", f"Firecrawl usage: {current_usage}/{self.monthly_limit} this month"
        )
        return True

    def fetch(self, url: str, log_path: str = "") -> FetchResult:
        """Fetch article using Firecrawl API."""

        # Check API key
        if not self.api_key:
            return FetchResult(
                success=False,
                error="Firecrawl API key not configured",
                method="firecrawl",
            )

        # Check usage limit
        if not self._check_usage_limit():
            return FetchResult(
                success=False,
                error="Firecrawl monthly limit exceeded",
                method="firecrawl",
            )

        try:
            log_info(log_path, f"Attempting Firecrawl scrape for {url}")

            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "url": url,
                "formats": ["markdown", "html"],
                "includeTags": ["title", "meta", "article", "main", "content"],
                "excludeTags": ["nav", "footer", "aside", "ads"],
                "waitFor": 2000,  # Wait 2 seconds for dynamic content
                "timeout": 30000,  # 30 second timeout
            }

            # Make API request
            response = requests.post(
                f"{self.base_url}/scrape", headers=headers, json=payload, timeout=45
            )

            # Increment usage regardless of outcome
            self._increment_usage(response.status_code == 200)

            if response.status_code == 200:
                data = response.json()

                if data.get("success"):
                    # Extract content
                    content = data.get("data", {})
                    markdown_content = content.get("markdown", "")
                    html_content = content.get("html", "")
                    metadata = content.get("metadata", {})

                    # Prefer markdown, fallback to HTML
                    final_content = (
                        markdown_content if markdown_content else html_content
                    )

                    if len(final_content) > 500:  # Quality check
                        title = metadata.get(
                            "title"
                        ) or ContentAnalyzer.extract_title_from_html(html_content)

                        # Check if content looks good
                        is_truncated = ContentAnalyzer.is_likely_paywall(
                            final_content, log_path
                        )

                        return FetchResult(
                            success=True,
                            content=final_content,
                            method="firecrawl",
                            title=title,
                            is_truncated=is_truncated,
                            metadata={
                                "firecrawl_metadata": metadata,
                                "content_type": (
                                    "markdown" if markdown_content else "html"
                                ),
                                "api_response": data,
                            },
                        )
                    else:
                        return FetchResult(
                            success=False,
                            error="Firecrawl returned minimal content",
                            method="firecrawl",
                        )
                else:
                    error_msg = data.get("error", "Unknown Firecrawl error")
                    return FetchResult(
                        success=False,
                        error=f"Firecrawl API error: {error_msg}",
                        method="firecrawl",
                    )
            else:
                return FetchResult(
                    success=False,
                    error=f"Firecrawl HTTP {response.status_code}: {response.text}",
                    method="firecrawl",
                )

        except Exception as e:
            # Still increment usage for failed requests due to our error
            self._increment_usage(False)
            log_error(log_path, f"Firecrawl request failed for {url}: {e}")
            return FetchResult(success=False, error=str(e), method="firecrawl")

    def get_strategy_name(self) -> str:
        return "firecrawl"

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        data = self._load_usage_data()
        return {
            "current_month": data.get("month"),
            "usage_this_month": data.get("usage_count", 0),
            "monthly_limit": self.monthly_limit,
            "remaining": self.monthly_limit - data.get("usage_count", 0),
            "total_used": data.get("total_used", 0),
            "successful_requests": data.get("successful_requests", 0),
            "failed_requests": data.get("failed_requests", 0),
            "success_rate": (
                data.get("successful_requests", 0) / max(1, data.get("usage_count", 1))
            )
            * 100,
        }
