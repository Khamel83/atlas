import csv
import os
from time import sleep
from typing import Dict, List

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .utils import log_error, log_info

DEFAULT_CSV_PATH = os.path.join("data", "instapaper_links.csv")


def harvest_instapaper_links(
    config: dict, csv_path: str = DEFAULT_CSV_PATH, max_pages: int = 0
):
    """Harvests all article links from an Instapaper account and saves them to a CSV.

    Args:
        config: Global configuration dictionary (must include INSTAPAPER_LOGIN & INSTAPAPER_PASSWORD).
        csv_path: Where to write the CSV (default: data/instapaper_links.csv).
        max_pages: Optional hard limit on pages to visit (0 = no limit).
    """
    login = config.get("INSTAPAPER_LOGIN")
    password = config.get("INSTAPAPER_PASSWORD")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    # Prepare log path next to CSV for easy inspection
    log_path = os.path.splitext(csv_path)[0] + ".log"

    if not all([login, password]):
        log_error(
            log_path,
            "Instapaper credentials missing. Set INSTAPAPER_LOGIN and INSTAPAPER_PASSWORD in .env",
        )
        return

    collected: List[Dict[str, str]] = []

    log_info(log_path, "Starting Instapaper link-harvest session…")

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X)"
            )
            page = context.new_page()
            page.set_default_navigation_timeout(120_000)
            page.set_default_timeout(120_000)

            # Login
            log_info(log_path, "Navigating to login page…")
            page.goto("https://www.instapaper.com/user/login")
            page.fill("input[name='username']", login)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            page.wait_for_url("https://www.instapaper.com/u", timeout=120_000)
            log_info(log_path, "Login successful.")

            current_page = 1
            while True:
                # Optional page cap
                if max_pages and current_page > max_pages:
                    break

                # Lazy-load all items on page
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                sleep(2)

                items = page.locator("div.article_item").all()
                log_info(
                    log_path, f"Harvesting {len(items)} items on page {current_page}…"
                )

                for item in items:
                    try:
                        title = item.locator("a.article_title").inner_text()
                        original_url = item.locator("a.article_title").get_attribute(
                            "href"
                        )
                        text_url_path = item.locator("a.js_text_control").get_attribute(
                            "href"
                        )
                        text_view_url = (
                            f"https://www.instapaper.com{text_url_path}"
                            if text_url_path
                            else None
                        )
                        collected.append(
                            {
                                "title": title,
                                "original_url": original_url,
                                "instapaper_text_url": text_view_url,
                            }
                        )
                    except Exception as e:
                        log_error(
                            log_path,
                            f"Failed harvesting an item on page {current_page}: {e}",
                        )

                # Pagination
                next_button = page.locator("a:has-text('Next')")
                if next_button.count() > 0:
                    log_info(log_path, "Going to next page…")
                    try:
                        next_button.click()
                        page.wait_for_url(
                            "https://www.instapaper.com/u/page/*", timeout=120_000
                        )
                        current_page += 1
                    except PlaywrightTimeoutError:
                        log_error(
                            log_path,
                            "Timeout navigating to next page. Stopping harvest.",
                        )
                        break
                else:
                    log_info(log_path, "No further pages. Harvest complete.")
                    break
        finally:
            if browser:
                browser.close()

    # Write CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["title", "original_url", "instapaper_text_url"]
        )
        writer.writeheader()
        writer.writerows(collected)
    log_info(log_path, f"Saved {len(collected)} records to {csv_path}")

    print(f"Harvest finished. Collected {len(collected)} links → {csv_path}")
