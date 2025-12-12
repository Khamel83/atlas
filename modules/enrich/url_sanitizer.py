"""
URL Sanitizer - Strip tracking parameters from URLs while keeping content.

Unlike ad removal which removes entire sponsor blocks, this:
1. Finds URLs in content
2. Strips tracking parameters (utm_*, ref, etc.)
3. Keeps the URL and surrounding content intact

Does NOT strip:
- Auth parameters needed for access (tokens, keys)
- Essential parameters (page, id, etc.)
"""

import re
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Set, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


# Tracking parameters to remove
TRACKING_PARAMS = {
    # UTM parameters (Google Analytics)
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'utm_id', 'utm_source_platform', 'utm_creative_format',

    # Facebook
    'fbclid', 'fb_action_ids', 'fb_action_types', 'fb_source', 'fb_ref',

    # Twitter/X
    'twclid', 's', 't',  # Twitter share params

    # Google
    'gclid', 'gclsrc', 'dclid',

    # Microsoft/Bing
    'msclkid',

    # Email marketing
    'mc_cid', 'mc_eid',  # Mailchimp
    'oly_anon_id', 'oly_enc_id',  # Ontraport

    # Affiliate/referral (generic)
    'ref', 'ref_', 'referer', 'referrer', 'source', 'src',
    'affiliate', 'aff', 'partner',

    # Analytics
    '_ga', '_gl', '_hsenc', '_hsmi', 'hsCtaTracking',

    # Social
    'igshid',  # Instagram
    'si',  # YouTube share

    # Other common tracking
    'mkt_tok', 'trk', 'trkCampaign', 'sc_campaign', 'sc_channel',
    'ns_campaign', 'ns_mchannel',
}

# Parameters to KEEP (auth/functional)
KEEP_PARAMS = {
    # Auth
    'token', 'key', 'api_key', 'apikey', 'auth', 'access_token',
    'session', 'sid', 'ticket',

    # Functional
    'page', 'p', 'id', 'v', 'q', 'query', 'search',
    'start', 'offset', 'limit', 'sort', 'order',
    'lang', 'language', 'locale', 'hl',
    'format', 'type', 'category', 'tag',
    't', 'time',  # YouTube timestamp

    # Required for content
    'article', 'post', 'story', 'doc',
}


def should_remove_param(param: str) -> bool:
    """Check if a URL parameter should be removed."""
    param_lower = param.lower()

    # Keep if in whitelist
    if param_lower in KEEP_PARAMS:
        return False

    # Remove if in tracking list
    if param_lower in TRACKING_PARAMS:
        return True

    # Remove if starts with utm_
    if param_lower.startswith('utm_'):
        return True

    # Remove if starts with tracking prefixes
    tracking_prefixes = ('fb_', 'mc_', 'oly_', 'ns_', 'sc_', 'trk', 'mkt_')
    if param_lower.startswith(tracking_prefixes):
        return True

    # Keep everything else
    return False


def sanitize_url(url: str) -> Tuple[str, bool]:
    """
    Remove tracking parameters from a URL.

    Returns (cleaned_url, was_modified).
    """
    try:
        parsed = urlparse(url)

        # Skip if no query string
        if not parsed.query:
            return url, False

        # Parse query parameters
        params = parse_qs(parsed.query, keep_blank_values=True)

        # Filter out tracking params
        cleaned_params = {}
        removed_any = False

        for key, values in params.items():
            if should_remove_param(key):
                removed_any = True
            else:
                cleaned_params[key] = values

        if not removed_any:
            return url, False

        # Rebuild URL
        new_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ''
        cleaned = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

        return cleaned, True

    except Exception as e:
        logger.debug(f"Error sanitizing URL {url}: {e}")
        return url, False


# Regex to find URLs in text
URL_PATTERN = re.compile(
    r'https?://[^\s<>\[\]\"\')\]]+',
    re.IGNORECASE
)

# Markdown link pattern: [text](url)
MD_LINK_PATTERN = re.compile(
    r'\[([^\]]+)\]\(([^)]+)\)'
)


def sanitize_text(text: str) -> Tuple[str, int]:
    """
    Sanitize all URLs in text, removing tracking parameters.

    Returns (cleaned_text, urls_modified).
    """
    urls_modified = 0

    def replace_url(match):
        nonlocal urls_modified
        url = match.group(0)
        cleaned, modified = sanitize_url(url)
        if modified:
            urls_modified += 1
        return cleaned

    def replace_md_link(match):
        nonlocal urls_modified
        text = match.group(1)
        url = match.group(2)
        cleaned, modified = sanitize_url(url)
        if modified:
            urls_modified += 1
        return f'[{text}]({cleaned})'

    # First handle markdown links
    result = MD_LINK_PATTERN.sub(replace_md_link, text)

    # Then handle bare URLs
    result = URL_PATTERN.sub(replace_url, result)

    return result, urls_modified


def sanitize_file(filepath: Path) -> Tuple[int, int]:
    """
    Sanitize URLs in a file.

    Returns (urls_found, urls_modified).
    """
    try:
        text = filepath.read_text(encoding='utf-8')
        urls_found = len(URL_PATTERN.findall(text)) + len(MD_LINK_PATTERN.findall(text))

        cleaned, modified = sanitize_text(text)

        if modified > 0:
            filepath.write_text(cleaned, encoding='utf-8')

        return urls_found, modified

    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        return 0, 0


# CLI
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Sanitize tracking URLs in content')
    parser.add_argument('path', nargs='?', help='File or directory to process')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes')
    parser.add_argument('--clean-dir', action='store_true', help='Process data/clean/')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.clean_dir:
        # Process all clean files
        clean_dir = Path('data/clean')
        files = list(clean_dir.rglob('*.md'))
        print(f'Processing {len(files)} files in data/clean/')

        total_found = 0
        total_modified = 0

        for f in files:
            if args.dry_run:
                text = f.read_text()
                _, modified = sanitize_text(text)
                if modified > 0:
                    print(f'  Would modify: {f} ({modified} URLs)')
                    total_modified += modified
            else:
                found, modified = sanitize_file(f)
                total_found += found
                total_modified += modified

        print(f'\nTotal: {total_modified} URLs {"would be " if args.dry_run else ""}sanitized')

    elif args.path:
        path = Path(args.path)
        if path.is_file():
            found, modified = sanitize_file(path)
            print(f'URLs found: {found}, modified: {modified}')
        else:
            print(f'Error: {path} not found')
    else:
        # Demo
        test = '''
Check out [this article](https://example.com/post?utm_source=twitter&utm_campaign=launch&id=123)
and https://news.com/story?fbclid=abc123&page=2 for more.
        '''
        cleaned, count = sanitize_text(test)
        print('Original:')
        print(test)
        print('\nCleaned:')
        print(cleaned)
        print(f'\nURLs sanitized: {count}')
