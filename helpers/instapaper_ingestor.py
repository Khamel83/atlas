import hashlib
import json
import os
from time import sleep

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from helpers.base_ingestor import BaseIngestor
from helpers.error_handler import AtlasErrorHandler
from helpers.metadata_manager import ContentType

from .utils import (calculate_hash, convert_html_to_markdown,
                    generate_markdown_summary, log_error, log_info)


class InstapaperIngestor(BaseIngestor):
    def get_content_type(self) -> ContentType:
        return ContentType.INSTAPAPER

    def get_module_name(self) -> str:
        return "instapaper_ingestor"

    def fetch_content(self, source, metadata):
        """
        Not used for Instapaper, as it scrapes a list of articles.
        """
        log_error(
            self.log_path,
            "fetch_content should not be called directly on InstapaperIngestor.",
        )
        return False, "InstapaperIngestor does not fetch individual articles."

    def process_content(self, content, metadata):
        """
        Not used for Instapaper, as processing is part of the scrape.
        """
        log_error(
            self.log_path,
            "process_content should not be called directly on InstapaperIngestor.",
        )
        return False

    def __init__(self, config):
        super().__init__(config, ContentType.INSTAPAPER, "instapaper_ingestor")
        self.error_handler = AtlasErrorHandler(config)
        self.login = config.get("INSTAPAPER_LOGIN")
        self.password = config.get("INSTAPAPER_PASSWORD")
        self.output_path = config["article_output_path"]
        self.meta_save_dir = os.path.join(self.output_path, "metadata")
        self.md_save_dir = os.path.join(self.output_path, "markdown")
        self.html_save_dir = os.path.join(self.output_path, "html")
        self.log_path = os.path.join(self.output_path, "ingest.log")
        os.makedirs(self.meta_save_dir, exist_ok=True)
        os.makedirs(self.md_save_dir, exist_ok=True)
        os.makedirs(self.html_save_dir, exist_ok=True)

    def ingest_articles(self, limit: int = 0):
        if not all([self.login, self.password]):
            log_error(
                self.log_path,
                "Instapaper credentials not found in .env file. Skipping.",
            )
            return
        log_info(self.log_path, "Starting Instapaper scraping session...")
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = context.new_page()
                page.set_default_navigation_timeout(120_000)
                page.set_default_timeout(120_000)
                log_info(self.log_path, "Navigating to Instapaper login page.")
                page.goto("https://www.instapaper.com/user/login", timeout=60000)
                log_info(self.log_path, "Submitting credentials.")
                page.fill('input[name="username"]', self.login)
                page.fill('input[name="password"]', self.password)
                page.click('button[type="submit"]')
                page.wait_for_url("https://www.instapaper.com/u", timeout=60000)
                log_info(self.log_path, "Login successful.")
                processed_count = 0
                while True:
                    try:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        sleep(2)
                    except Exception:
                        pass
                    article_links = page.locator("a.article_title").all()
                    if not article_links:
                        log_info(self.log_path, "No more articles found on this page.")
                        break
                    log_info(
                        self.log_path,
                        f"Found {len(article_links)} articles on the current page.",
                    )
                    for link_element in article_links:
                        if limit > 0 and processed_count >= limit:
                            log_info(
                                self.log_path,
                                f"Reached processing limit of {limit} articles.",
                            )
                            break
                        title = link_element.inner_text()
                        original_url = link_element.get_attribute("href")
                        article_container = page.locator(
                            f'div.article_item:has(a[href="{original_url}"])'
                        )
                        text_view_url_path = article_container.locator(
                            "a.js_text_control"
                        ).get_attribute("href")
                        text_view_url = (
                            f"https://www.instapaper.com{text_view_url_path}"
                        )
                        file_id = hashlib.sha1(
                            original_url.encode("utf-8")
                        ).hexdigest()[:16]
                        md_path = os.path.join(self.md_save_dir, f"{file_id}.md")
                        meta_path = os.path.join(self.meta_save_dir, f"{file_id}.json")
                        html_path = os.path.join(self.html_save_dir, f"{file_id}.html")
                        if os.path.exists(meta_path):
                            log_info(
                                self.log_path,
                                f"Article '{title}' ({file_id}) already processed. Skipping.",
                            )
                            continue
                        try:
                            log_info(
                                self.log_path,
                                f"Fetching content for '{title}' from {text_view_url}",
                            )
                            content_page = context.new_page()
                            content_page.goto(text_view_url, timeout=60000)
                            story_div = content_page.locator("div.story")
                            html_content = story_div.inner_html()
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(html_content)
                            markdown_content = convert_html_to_markdown(
                                html_content, original_url
                            )
                            md = generate_markdown_summary(
                                title=title,
                                source=original_url,
                                date="",
                                tags=["instapaper"],
                                notes=[],
                                content=markdown_content,
                            )
                            with open(md_path, "w", encoding="utf-8") as mdf:
                                mdf.write(md)
                            meta = {
                                "uid": file_id,
                                "title": title,
                                "source": original_url,
                                "date": "",
                                "tags": ["instapaper"],
                                "status": "success",
                                "content_path": md_path,
                                "source_hash": calculate_hash(md_path),
                            }
                            with open(meta_path, "w", encoding="utf-8") as mf:
                                json.dump(meta, mf, indent=2)
                            log_info(
                                self.log_path,
                                f"Successfully processed and saved '{title}'.",
                            )
                            processed_count += 1
                            content_page.close()
                            sleep(1)
                        except PlaywrightTimeoutError:
                            log_error(
                                self.log_path,
                                f"Timeout loading content for '{title}'. Skipping.",
                            )
                        except Exception as e:
                            self.error_handler.handle_error(
                                Exception(f"Error processing article '{title}': {e}"),
                                self.log_path,
                            )
                    if limit > 0 and processed_count >= limit:
                        break
                    next_button = page.locator('a:has-text("Next")')
                    if next_button.count() > 0:
                        log_info(self.log_path, "Navigating to next page.")
                        try:
                            next_button.click()
                            page.wait_for_url(
                                "https://www.instapaper.com/u/page/*", timeout=120000
                            )
                        except PlaywrightTimeoutError:
                            log_error(
                                self.log_path,
                                "Timeout while navigating to the next page. Ending scrape.",
                            )
                            break
                    else:
                        log_info(
                            self.log_path,
                            "No 'Next' button found. Reached the end of articles.",
                        )
                        break
            except PlaywrightTimeoutError:
                log_error(
                    self.log_path,
                    "Timeout during login or navigation. Check credentials or network.",
                )
                page.screenshot(path="instapaper_error.png")
                log_info(self.log_path, "Screenshot saved to instapaper_error.png")
            except Exception as e:
                self.error_handler.handle_error(
                    Exception(
                        f"An unexpected error occurred during the Instapaper scrape: {e}"
                    ),
                    self.log_path,
                )
            finally:
                if "browser" in locals() and browser.is_connected():
                    browser.close()
                log_info(self.log_path, "Instapaper scraping session finished.")


def ingest_instapaper_articles(config: dict, limit: int = 0):
    ingestor = InstapaperIngestor(config)
    ingestor.ingest_articles(limit=limit)
