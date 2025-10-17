"""
Skyvern-Enhanced Article Ingestor

This module provides an intelligent browser automation ingestor that can:
1. Enhance existing article scraping with AI-powered web interaction
2. Handle complex sites that traditional scrapers can't access
3. Provide fallback for failed API or standard scraping attempts
"""

import hashlib
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import requests

    OPENROUTER_AVAILABLE = True
except ImportError:
    OPENROUTER_AVAILABLE = False

from helpers.base_ingestor import BaseIngestor
from helpers.metadata_manager import ContentMetadata, ContentType
from helpers.utils import convert_html_to_markdown


class SkyvernEnhancedIngestor(BaseIngestor):
    """Enhanced article ingestor with Skyvern AI browser automation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, ContentType.ARTICLE, "skyvern_enhanced_ingestor")
        self._post_init()

        # OpenRouter AI configuration for content extraction
        self.ai_enabled = (
            config.get("SKYVERN_ENABLED", False)
            and config.get("OPENROUTER_API_KEY")
            and OPENROUTER_AVAILABLE
        )
        if self.ai_enabled:
            self.openrouter_api_key = config.get("OPENROUTER_API_KEY")
            self.openrouter_base_url = "https://openrouter.ai/api/v1"
            self.model = config.get("llm_model", "google/gemini-2.0-flash-lite-001")
        else:
            self.openrouter_api_key = None

        # Fallback strategies
        self.use_traditional_scraping = config.get("USE_TRADITIONAL_SCRAPING", True)
        self.max_retries = config.get("SKYVERN_MAX_RETRIES", 2)

        print(
            f"[{self.module_name}] Initialized - AI Enhancement {'enabled' if self.ai_enabled else 'disabled'}"
        )

    def get_content_type(self) -> ContentType:
        return ContentType.ARTICLE

    def get_module_name(self) -> str:
        return self.module_name

    def is_supported_source(self, source: str) -> bool:
        """Check if source is a valid URL."""
        parsed = urlparse(source)
        return parsed.scheme in ["http", "https"]

    def fetch_content(
        self, source: str, metadata: ContentMetadata
    ) -> Tuple[bool, Optional[str]]:
        """
        Intelligent content fetching with multiple strategies.

        Strategy priority:
        1. Traditional requests (fast, works for most sites)
        2. Skyvern AI automation (handles complex cases)
        3. Enhanced extraction prompts for specific sites
        """
        strategies = []

        # Always try traditional first (fastest)
        if self.use_traditional_scraping:
            strategies.append(("traditional", self._fetch_traditional))

        # Add AI-enhanced strategies based on URL patterns
        if self.ai_enabled:
            if self._is_complex_site(source):
                strategies.append(("ai_enhanced", self._fetch_with_ai_extraction))
            if self._is_paywall_site(source):
                strategies.append(("ai_paywall", self._fetch_paywall_content))

        # Try each strategy in order
        for strategy_name, strategy_func in strategies:
            try:
                print(
                    f"[{self.module_name}] Trying {strategy_name} strategy for {source}"
                )
                success, result = strategy_func(source, metadata)
                if success:
                    metadata.fetch_method = strategy_name
                    return True, result
                else:
                    print(f"[{self.module_name}] {strategy_name} failed: {result}")
            except Exception as e:
                print(f"[{self.module_name}] {strategy_name} error: {str(e)}")

        return False, "All fetching strategies failed"

    def _fetch_traditional(
        self, source: str, metadata: ContentMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Traditional requests-based fetching."""
        try:
            import requests
            from readability import Document

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(source, headers=headers, timeout=30)
            response.raise_for_status()

            # Use readability to extract main content
            doc = Document(response.text)
            content = doc.content()

            return True, content

        except Exception as e:
            return False, f"Traditional fetch failed: {str(e)}"

    def _fetch_with_ai_extraction(
        self, source: str, metadata: ContentMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Use AI to intelligently extract and enhance content."""
        if not self.openrouter_api_key:
            return False, "OpenRouter API key not available"

        try:
            # First get the raw HTML content
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(source, headers=headers, timeout=30)
            response.raise_for_status()
            raw_html = response.text

            # Use AI to extract and clean the content
            extraction_prompt = self._generate_extraction_prompt(source, metadata)
            enhanced_content = self._extract_content_with_ai(
                raw_html, extraction_prompt
            )

            if enhanced_content and len(enhanced_content) > 500:
                return True, enhanced_content
            else:
                return False, "AI extraction returned insufficient content"

        except Exception as e:
            return False, f"AI extraction error: {str(e)}"

    def _fetch_paywall_content(
        self, source: str, metadata: ContentMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Handle paywall sites by delegating to existing authentication strategies."""
        # Delegate to existing PaywallAuthenticatedStrategy from article_strategies
        try:
            from helpers.article_strategies import PaywallAuthenticatedStrategy

            paywall_strategy = PaywallAuthenticatedStrategy(self.config)
            result = paywall_strategy.fetch(source)
            success = result.success
            content = result.content

            if success and content:
                # Enhance with AI if content is raw HTML
                if "<html" in content.lower():
                    extraction_prompt = self._generate_extraction_prompt(
                        source, metadata
                    )
                    enhanced_content = self._extract_content_with_ai(
                        content, extraction_prompt
                    )
                    return True, enhanced_content if enhanced_content else content
                return True, content
            else:
                return False, "Paywall authentication failed"

        except Exception as e:
            return False, f"Paywall handling error: {str(e)}"

    def _generate_extraction_prompt(self, url: str, metadata: ContentMetadata) -> str:
        """Generate intelligent extraction prompts based on site and content type."""
        domain = urlparse(url).netloc

        # Site-specific prompts
        site_prompts = {
            "medium.com": """
            1. Navigate to the article page
            2. If there's a paywall popup, try to close it or find a "continue reading" option
            3. Scroll down to load the full article content
            4. Extract the article title, subtitle, author, and full text content
            5. Ignore claps, comments, and recommended articles
            """,
            "nytimes.com": """
            1. Navigate to the article page
            2. Handle any cookie consent banners
            3. If there's a subscription popup, try to find ways to access the article
            4. Extract the headline, byline, date, and full article text
            5. Stop at the end of the main article content
            """,
            "reddit.com": """
            1. Navigate to the Reddit post
            2. Load all comments by clicking "load more" if present
            3. Extract the post title, content, and top-level comments
            4. Include comment scores and timestamps
            """,
        }

        # Use site-specific prompt or generic one
        if domain in site_prompts:
            return site_prompts[domain]
        else:
            return f"""
            1. Navigate to {url}
            2. Handle any popups, cookie banners, or overlays
            3. Scroll to ensure all content is loaded
            4. Identify and extract the main article content
            5. Include title, author, date, and full text
            6. Ignore navigation, ads, and sidebar content
            """

    def _extract_content_with_ai(
        self, html_content: str, extraction_prompt: str
    ) -> Optional[str]:
        """Use LLM router for intelligent, cost-optimized HTML content extraction."""
        try:
            # Use the router for cost optimization and intelligent model selection
            from helpers.llm_router import get_llm_router, TaskSpec, TaskKind

            router = get_llm_router(self.config)

            # Prepare the AI prompt for content extraction
            system_prompt = f"""You are an expert content extractor. {extraction_prompt}

Extract the main article content from the provided HTML, returning clean markdown format.
Focus on:
1. Article title, author, and publication date
2. Main article text and paragraphs
3. Important quotes, lists, and formatting
4. Exclude navigation, ads, comments, and sidebars

Return only the clean article content in markdown format."""

            # Truncate HTML to avoid token limits (keep first 50000 chars)
            truncated_html = (
                html_content[:50000] if len(html_content) > 50000 else html_content
            )

            full_prompt = f"Extract content from this HTML:\n\n{truncated_html}"

            # Create task spec for HTML content extraction
            task_spec = TaskSpec(
                kind=TaskKind.REWRITE,  # HTML -> Markdown conversion
                input_tokens=len(system_prompt + full_prompt) // 4,
                content_type="html",
                requires_long_ctx=True,  # Large HTML input
                strict_json=False,  # Output is markdown, not JSON
                priority="normal"
            )

            # Use router for intelligent model selection (Economy->Balanced->Premium)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ]

            router_result = router.execute_task(
                spec=task_spec,
                messages=messages
            )

            if router_result.get('success'):
                return router_result.get('content')
            else:
                print(f"Router extraction failed: {router_result.get('error')}")
                return None

        except Exception as e:
            print(f"AI extraction error: {e}")
            # Fallback to direct API call if router fails
            try:
                return self._extract_content_with_direct_api(html_content, extraction_prompt)
            except:
                return None

    def _extract_content_with_direct_api(self, html_content: str, extraction_prompt: str) -> Optional[str]:
        """Fallback: Direct API call without router."""
        system_prompt = f"""You are an expert content extractor. {extraction_prompt}

Extract the main article content from the provided HTML, returning clean markdown format.
Focus on:
1. Article title, author, and publication date
2. Main article text and paragraphs
3. Important quotes, lists, and formatting
4. Exclude navigation, ads, comments, and sidebars

Return only the clean article content in markdown format."""

        truncated_html = (
            html_content[:50000] if len(html_content) > 50000 else html_content
        )

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "meta-llama/llama-3.1-8b-instruct",  # Start with economy model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract content from this HTML:\n\n{truncated_html}"},
            ],
            "max_tokens": 4000,
            "temperature": 0.1,
        }

        response = requests.post(
            f"{self.openrouter_base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"Direct API error: {response.status_code} - {response.text}")
            return None

    def _is_complex_site(self, url: str) -> bool:
        """Detect if site likely needs AI automation."""
        complex_domains = [
            "medium.com",
            "substack.com",
            "notion.so",
            "github.com",
            "stackoverflow.com",
            "reddit.com",
        ]
        domain = urlparse(url).netloc
        return any(d in domain for d in complex_domains)

    def _is_paywall_site(self, url: str) -> bool:
        """Detect if site likely has paywall."""
        paywall_domains = [
            "nytimes.com",
            "wsj.com",
            "ft.com",
            "bloomberg.com",
            "economist.com",
            "washingtonpost.com",
        ]
        domain = urlparse(url).netloc
        return any(d in domain for d in paywall_domains)

    def _get_site_credentials(self, domain: str) -> Optional[Dict[str, str]]:
        """Get stored credentials for a specific site."""
        # This would load from secure credential storage
        credentials_map = {
            "nytimes.com": {
                "username": self.config.get("NYTIMES_USERNAME"),
                "password": self.config.get("NYTIMES_PASSWORD"),
            },
            # Add more sites as needed
        }

        if domain in credentials_map:
            creds = credentials_map[domain]
            if creds["username"] and creds["password"]:
                return creds
        return None

    def process_content(self, content: str, metadata: ContentMetadata) -> bool:
        """Process extracted content into markdown."""
        try:
            # Convert HTML to markdown
            markdown_content = convert_html_to_markdown(content, metadata.source)

            # Save to temporary file for metadata processing
            temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False
            )
            temp_file.write(markdown_content)
            temp_file.close()

            # Store content in metadata
            metadata.type_specific["content"] = markdown_content
            metadata.type_specific["content_length"] = len(markdown_content)
            metadata.type_specific["processing_method"] = metadata.fetch_method

            # Generate summary if content is substantial
            if len(markdown_content) > 500:
                try:
                    from process.evaluate import summarize_content

                    metadata.type_specific["summary"] = summarize_content(
                        markdown_content[:4000], self.config
                    )
                except Exception as e:
                    print(f"[{self.module_name}] Summary generation failed: {e}")
                    metadata.type_specific["summary"] = markdown_content[:500] + "..."
            else:
                metadata.type_specific["summary"] = markdown_content

            # Clean up temp file
            os.unlink(temp_file.name)

            return True

        except Exception as e:
            print(f"[{self.module_name}] Content processing error: {e}")
            return False


class AIInstapaperEnhancer:
    """Enhance Instapaper scraping with AI intelligence."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_enabled = (
            config.get("SKYVERN_ENABLED", False)
            and config.get("OPENROUTER_API_KEY")
            and OPENROUTER_AVAILABLE
        )
        if self.ai_enabled:
            self.openrouter_api_key = config.get("OPENROUTER_API_KEY")
            self.openrouter_base_url = "https://openrouter.ai/api/v1"
            self.model = config.get("llm_model", "google/gemini-2.0-flash-lite-001")

    def scrape_instapaper_intelligently(
        self, login: str, password: str
    ) -> List[Dict[str, Any]]:
        """Use AI to scrape Instapaper reading list intelligently."""
        if not self.ai_enabled:
            raise RuntimeError("AI enhancement not available for Instapaper scraping")

        # For now, delegate to existing Instapaper strategies
        # Future enhancement could use browser automation with AI guidance
        try:
            from helpers.instapaper_ingestor import InstapaperIngestor

            ingestor = InstapaperIngestor(self.config)
            # Use existing scraping with AI enhancement for content extraction
            articles = ingestor.fetch_reading_list()
            return articles

        except Exception as e:
            raise RuntimeError(f"AI Instapaper scraping error: {str(e)}")

    def _parse_instapaper_results(self, task_result) -> List[Dict[str, Any]]:
        """Parse Skyvern results into structured article data."""
        # This would depend on Skyvern's actual response format
        # For now, return mock structure
        articles = []

        # Parse the extracted data from Skyvern
        if hasattr(task_result, "extracted_data"):
            for item in task_result.extracted_data:
                article = {
                    "title": item.get("title", "Unknown Title"),
                    "url": item.get("url", ""),
                    "date_added": item.get("date", ""),
                    "tags": item.get("tags", []),
                    "bookmark_id": hashlib.sha1(
                        item.get("url", "").encode()
                    ).hexdigest()[:16],
                }
                articles.append(article)

        return articles


def create_skyvern_enhanced_ingestor(config: Dict[str, Any]) -> SkyvernEnhancedIngestor:
    """Create and return a SkyvernEnhancedIngestor instance."""
    return SkyvernEnhancedIngestor(config)
