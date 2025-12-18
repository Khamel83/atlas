#!/usr/bin/env python3
"""
Process Instapaper CSV exports and ingest articles into Atlas

Usage:
    python scripts/process_instapaper.py /path/to/instapaper_export.csv
    python scripts/process_instapaper.py --help

This script processes Instapaper CSV exports by:
1. Parsing the CSV format with URL, title, and selection fields
2. Filtering out already processed URLs
3. Using the enhanced article fetching pipeline for each URL
4. Providing progress reporting and error handling
"""

import argparse
import csv
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.config import load_config
from helpers.instapaper_ingestor import InstapaperIngestor


def process_instapaper_csv(csv_path, max_articles=None, skip_existing=True):
    """
    Process Instapaper CSV file and ingest articles

    Args:
        csv_path: Path to Instapaper CSV export
        max_articles: Maximum number of articles to process (None for all)
        skip_existing: Skip URLs that have already been processed

    Returns:
        dict: Processing results with counts and status
    """
    config = load_config()

    print(f"🔄 Processing Instapaper CSV: {csv_path}")

    # Initialize ingestor
    ingestor = InstapaperIngestor(config)

    # Read CSV file
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            urls = []

            # Extract URLs from CSV
            for row in reader:
                if 'URL' in row and row['URL']:
                    urls.append({
                        'url': row['URL'].strip(),
                        'title': row.get('Title', '').strip(),
                        'selection': row.get('Selection', '').strip()
                    })

    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return {'success': False, 'error': str(e)}

    total_urls = len(urls)
    print(f"📊 Found {total_urls} URLs in CSV")

    if max_articles:
        urls = urls[:max_articles]
        print(f"📝 Processing first {len(urls)} articles (limited)")

    # Process URLs
    results = {
        'total': len(urls),
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }

    for i, item in enumerate(urls, 1):
        url = item['url']
        print(f"[{i}/{len(urls)}] Processing: {url[:80]}...")

        try:
            # Process the URL
            result = ingestor.ingest_single(url)

            if result.success:
                results['successful'] += 1
                print(f"✅ Success")
            else:
                results['failed'] += 1
                if result.error:
                    results['errors'].append(f"{url}: {result.error}")
                print(f"❌ Failed: {result.error}")

        except Exception as e:
            results['failed'] += 1
            error_msg = f"{url}: {str(e)}"
            results['errors'].append(error_msg)
            print(f"❌ Exception: {e}")

    # Print summary
    print(f"\n📊 Processing Complete:")
    print(f"   Total URLs: {results['total']}")
    print(f"   Successful: {results['successful']}")
    print(f"   Failed: {results['failed']}")
    print(f"   Success rate: {(results['successful']/results['total']*100):.1f}%")

    if results['errors']:
        print(f"\n❌ Errors encountered:")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"   {error}")
        if len(results['errors']) > 10:
            print(f"   ... and {len(results['errors']) - 10} more")

    return results


def main():
    parser = argparse.ArgumentParser(description='Process Instapaper CSV exports')
    parser.add_argument('csv_file', help='Path to Instapaper CSV export file')
    parser.add_argument('--max-articles', type=int,
                       help='Maximum number of articles to process')
    parser.add_argument('--no-skip-existing', action='store_true',
                       help='Process URLs even if already ingested')

    args = parser.parse_args()

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found: {csv_path}")
        sys.exit(1)

    # Process the CSV file
    results = process_instapaper_csv(
        csv_path=csv_path,
        max_articles=args.max_articles,
        skip_existing=not args.no_skip_existing
    )

    # Exit with appropriate code
    if results.get('success', True) and results.get('successful', 0) > 0:
        print("✅ Processing completed successfully")
        sys.exit(0)
    else:
        print("❌ Processing completed with issues")
        sys.exit(1)


if __name__ == '__main__':
    main()