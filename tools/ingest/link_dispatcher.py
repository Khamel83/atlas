import csv
import os
import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from helpers.dedupe import link_uid
from helpers.retry_queue import enqueue
from helpers.utils import log_error, log_info

# URL pattern matchers
YOUTUBE_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
    r"(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)",
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)",
]

PODCAST_PATTERNS = [
    r"(?:https?://)?(?:www\.)?podcasts\.apple\.com/.*?/podcast/.*?/id(\d+)",
    r"(?:https?://)?(?:www\.)?open\.spotify\.com/episode/([a-zA-Z0-9]+)",
    r"(?:https?://)?(?:www\.)?anchor\.fm/.*?/episodes/([a-zA-Z0-9_-]+)",
    r"(?:https?://)?(?:www\.)?soundcloud\.com/([^/]+)/([^/]+)",
]


def detect_url_type(url: str) -> str:
    """
    Determine the type of content the URL points to.

    Args:
        url: The URL to analyze

    Returns:
        str: One of 'youtube', 'podcast', 'article', or 'unknown'
    """
    # Check for YouTube URLs
    for pattern in YOUTUBE_PATTERNS:
        if re.match(pattern, url):
            return "youtube"

    # Check for podcast URLs
    for pattern in PODCAST_PATTERNS:
        if re.match(pattern, url):
            return "podcast"

    # Check for common article indicators
    parsed = urlparse(url)
    if parsed.netloc and parsed.path:
        # Most article URLs have paths with sections, dates, or slugs
        if (
            re.search(r"/\d{4}/\d{2}/", parsed.path)  # Date pattern
            or re.search(r"/[a-z0-9-]{10,}/", parsed.path)  # Slug pattern
            or "/article/" in parsed.path
            or "/post/" in parsed.path
            or "/story/" in parsed.path
        ):
            return "article"

    # Default to article for most web URLs with a path
    if parsed.netloc and parsed.path and parsed.path != "/":
        return "article"

    return "unknown"


def is_duplicate(url: str, config: Dict) -> bool:
    """
    Check if a URL has already been processed by checking against existing files.

    Args:
        url: The URL to check
        config: The application configuration dictionary

    Returns:
        bool: True if the URL is a duplicate, False otherwise
    """
    # Generate the unique ID for the URL
    uid = link_uid(url)

    # Check in article metadata
    article_meta_path = os.path.join(
        config["article_output_path"], "metadata", f"{uid}.json"
    )
    if os.path.exists(article_meta_path):
        return True

    # Check in YouTube metadata
    youtube_meta_path = os.path.join(
        config["youtube_output_path"], "metadata", f"{uid}.json"
    )
    if os.path.exists(youtube_meta_path):
        return True

    # Check in podcast metadata (less likely but possible for direct episode URLs)
    podcast_meta_path = os.path.join(
        config["podcast_output_path"], "metadata", f"{uid}.json"
    )
    if os.path.exists(podcast_meta_path):
        return True

    return False


def dispatch_url(url: str, config: Dict) -> Tuple[bool, str]:
    """
    Process a single URL by detecting its type and dispatching it to the appropriate handler.

    Args:
        url: The URL to process
        config: The application configuration dictionary

    Returns:
        Tuple[bool, str]: (success, message)
    """
    log_path = os.path.join(
        config.get("data_directory", "output"), "link_dispatcher.log"
    )

    # Skip empty URLs
    if not url or not url.strip():
        return False, "Empty URL provided"

    # Normalize and deduplicate
    url = url.strip()

    if is_duplicate(url, config):
        log_info(log_path, f"Skipping duplicate URL: {url}")
        return True, "Skipped (duplicate)"

    # Detect URL type
    url_type = detect_url_type(url)
    log_info(log_path, f"Detected URL type: {url_type} for {url}")

    try:
        # Dispatch to the appropriate handler
        if url_type == "youtube":
            # Import here to avoid circular imports
            from helpers.youtube_ingestor import ingest_youtube_video

            success = ingest_youtube_video(url, config)
            return success, f"Processed as YouTube video: {success}"

        elif url_type == "podcast":
            # Currently podcast URLs are handled through OPML files, not direct URLs
            # This is a placeholder for future direct podcast URL handling
            log_info(
                log_path, f"Direct podcast URL handling not implemented yet: {url}"
            )
            enqueue(
                {
                    "type": "podcast_url",
                    "url": url,
                    "error": "Direct podcast URL handling not implemented",
                    "timestamp": None,
                }
            )
            return False, "Podcast URL handling not implemented"

        elif url_type == "article":
            # Import here to avoid circular imports
            from helpers.article_fetcher import fetch_and_save_article

            success = fetch_and_save_article(url, config)
            return success, f"Processed as article: {success}"

        else:
            log_error(log_path, f"Unknown URL type: {url}")
            # Default to article for unknown types
            from helpers.article_fetcher import fetch_and_save_article

            success = fetch_and_save_article(url, config)
            return success, f"Processed as article (unknown type): {success}"

    except Exception as e:
        log_error(log_path, f"Error dispatching URL {url}: {str(e)}")
        # Add to retry queue
        enqueue(
            {
                "type": "url_dispatch",
                "url": url,
                "url_type": url_type,
                "error": str(e),
                "timestamp": None,
            }
        )
        return False, f"Error: {str(e)}"


def process_url_list(urls: List[str], config: Dict) -> Dict[str, List[str]]:
    """
    Process a list of URLs, dispatching each to the appropriate handler.

    Args:
        urls: List of URLs to process
        config: The application configuration dictionary

    Returns:
        Dict with lists of successful and failed URLs
    """
    results = {"successful": [], "failed": [], "duplicate": [], "unknown": []}

    for url in urls:
        success, message = dispatch_url(url, config)
        if success:
            if "duplicate" in message.lower():
                results["duplicate"].append(url)
            else:
                results["successful"].append(url)
        else:
            if "not implemented" in message.lower():
                results["unknown"].append(url)
            else:
                results["failed"].append(url)

    return results


def process_url_file(file_path: str, config: Dict) -> Dict[str, List[str]]:
    """
    Process URLs from a file, one URL per line.

    Args:
        file_path: Path to the file containing URLs
        config: The application configuration dictionary

    Returns:
        Dict with lists of successful and failed URLs
    """
    if not os.path.exists(file_path):
        log_error(
            os.path.join(config.get("data_directory", "output"), "link_dispatcher.log"),
            f"URL file not found: {file_path}",
        )
        return {"successful": [], "failed": [], "duplicate": [], "unknown": []}

    with open(file_path, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    return process_url_list(urls, config)


def process_instapaper_csv(file_path: str, config: Dict) -> Dict[str, List[str]]:
    """
    Process URLs from a clean Instapaper CSV file.

    Args:
        file_path: Path to the Instapaper CSV file
        config: The application configuration dictionary

    Returns:
        Dict with lists of successful and failed URLs
    """
    if not os.path.exists(file_path):
        log_error(
            os.path.join(config.get("data_directory", "output"), "link_dispatcher.log"),
            f"Instapaper CSV file not found: {file_path}",
        )
        return {"successful": [], "failed": [], "duplicate": [], "unknown": []}

    urls = []
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle both "URL" and "url" column names
            url = row.get("URL") or row.get("url")
            if url and not url.startswith("instapaper-private://"):
                urls.append(url)

    return process_url_list(urls, config)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    import sys

    from helpers.config import load_config

    config = load_config()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--instapaper":
            if len(sys.argv) > 2:
                results = process_instapaper_csv(sys.argv[2], config)
                print(f"Processed {len(results['successful'])} URLs successfully.")
                print(f"Skipped {len(results['duplicate'])} duplicate URLs.")
                print(f"Failed to process {len(results['failed'])} URLs.")
                print(f"Unsupported URL types: {len(results['unknown'])}")
            else:
                print("Usage: python -m ingest.link_dispatcher --instapaper <csv_file>")
        # Process a file of URLs
        elif os.path.exists(sys.argv[1]):
            results = process_url_file(sys.argv[1], config)
            print(f"Processed {len(results['successful'])} URLs successfully.")
            print(f"Skipped {len(results['duplicate'])} duplicate URLs.")
            print(f"Failed to process {len(results['failed'])} URLs.")
            print(f"Unsupported URL types: {len(results['unknown'])}")
        else:
            # Process a single URL from the command line
            url = sys.argv[1]
            success, message = dispatch_url(url, config)
            print(f"URL: {url}")
            print(f"Success: {success}")
            print(f"Message: {message}")
    else:
        print(
            "Usage: python -m ingest.link_dispatcher <url_or_file> or --instapaper <csv_file>"
        )
