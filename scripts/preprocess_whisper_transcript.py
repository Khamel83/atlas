#!/usr/bin/env python3
"""
Preprocess Whisper transcripts for Atlas.

Whisper/MacWhisper outputs transcripts as a single continuous line.
This script:
1. Adds paragraph breaks at natural points
2. Removes known ad patterns (iHeart, medication disclaimers, etc.)
3. Outputs clean markdown ready for the podcast system

Usage:
    python scripts/preprocess_whisper_transcript.py input.txt output.md
    python scripts/preprocess_whisper_transcript.py --all  # Process all in whisper_queue
"""

import argparse
import re
import logging
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# iHeart Podcast Ad Patterns - Using START/END marker approach
# ============================================================================

# Ad block START markers - when we see these, start removing
AD_BLOCK_STARTS = [
    # iHeart branding
    r"This is an iHeart [Pp]odcast",

    # T-Mobile/Supermobile
    r"In today'?s super competitive business environment",
    r"With Supermobile, your performance",
    r"performance,? built-?in security,? and seamless satellite coverage",

    # Coca-Cola HBCU
    r"What a matchup we got,? y'?all",

    # Bosch
    r"You'?ve probably heard me say this\.? Connection is one of the biggest keys",

    # EBCLIS/Evglyss medication
    r"Eczema isn'?t always obvious,? but it'?s real",

    # Earsay podcast promo
    r"Hey,? audiobook lovers",

    # Pushkin promos (at end of episodes)
    r"To find more Pushkin podcasts,? listen on",
    r"if you'?d like to listen ad-?free",
]

# Ad block END markers - stop removing when we see these
AD_BLOCK_ENDS = [
    # Phone numbers (medication ads always end with these)
    r"1-800-[0-9]{3}-[0-9]{4}",
    r"1-800-545-5979",
    r"1-800-LILY-RX",

    # URL endings
    r"\.com\.",
    r"1H 2025\.?",  # T-Mobile ad ending
    r"HBCU pride going\.?",  # Coca-Cola ending
    r"BoschHomeUS\.com\.?",  # Bosch ending

    # Podcast promo endings
    r"iHeart[Rr]adio app today\.?",
    r"Apple show page\.?",
    r"audiobooks are sold\.?",

    # Show content resumption markers
    r"Pushkin\.",  # Show brand before content
    r"I'?m Michael Lewis",
    r"I'?m back with",
    r"And we'?re back",
    r"Welcome back",
]

# Simple patterns for standalone removal
SIMPLE_AD_PATTERNS = [
    r"This is an iHeart [Pp]odcast\.?\s*Guaranteed human\.?",
    r"Guaranteed human\.?",
    r"We'?ll be right back\.?",

    # Orphaned ad fragments (tails that remain after block removal)
    r"Seamless coverage with compatible devices[^.]*1H 2025\.?\s*\.?",
    r"Best business plan based on[^.]*1H 2025\.?\s*\.?",
    r"Best network based on analysis[^.]*1H 2025\.?\s*\.?",
]

# Shorter patterns that indicate ad transitions
AD_TRANSITION_PATTERNS = [
    r"We'?ll be right back\.?",
    r"When we (?:come|return) back from the break",
    r"After the break",
    r"When we return",
    r"Stay tuned",
    r"More after this",
]

# Sentence break patterns - add newlines here for readability
SENTENCE_BREAK_AFTER = [
    r'(?<=[.!?])\s+(?=[A-Z])',  # After sentence ending punctuation before capital
    r'(?<=\.)\s+(?=And\s)',     # Period before "And"
    r'(?<=\.)\s+(?=But\s)',     # Period before "But"
    r'(?<=\.)\s+(?=So\s)',      # Period before "So"
    r'(?<=\.)\s+(?=I\s)',       # Period before "I"
    r'(?<=\.)\s+(?=You\s)',     # Period before "You"
    r'(?<=\.)\s+(?=We\s)',      # Period before "We"
    r'(?<=\.)\s+(?=The\s)',     # Period before "The"
    r'(?<=\.)\s+(?=This\s)',    # Period before "This"
    r'(?<=\.)\s+(?=That\s)',    # Period before "That"
]

# Paragraph break patterns - add double newlines here
PARAGRAPH_BREAK_AFTER = [
    r'(?<=\?)\s+(?=[A-Z][a-z])',  # Question mark before new sentence
    r'(?<=[.!?])\s+(?=So,?\s)',    # New topic with "So"
    r'(?<=[.!?])\s+(?=Now,?\s)',   # New topic with "Now"
    r'(?<=[.!?])\s+(?=Okay\.?\s)', # New topic with "Okay"
    r'(?<=[.!?])\s+(?=All right\.?\s)', # New topic with "All right"
]


def find_ad_block_end(text: str, start_pos: int, max_search: int = 3000) -> int:
    """
    Find the end of an ad block starting at start_pos.
    Returns the position after the ad block ends.
    """
    search_text = text[start_pos:start_pos + max_search]

    # Try each end marker
    best_end = None
    for pattern in AD_BLOCK_ENDS:
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            end_pos = start_pos + match.end()
            if best_end is None or end_pos < best_end:
                best_end = end_pos

    # If no end marker found, use a fixed limit (500 chars)
    if best_end is None:
        best_end = min(start_pos + 500, len(text))

    return best_end


def format_text(text: str) -> str:
    """
    Format single-line Whisper output into readable paragraphs.

    NOTE: Ad removal is NOT done here - that happens in the normal
    enrichment pipeline (run_enrichment.py) which processes ALL content
    uniformly using the patterns in modules/enrich/ad_stripper.py
    """
    # Just clean up excessive whitespace
    text = re.sub(r'\s{2,}', ' ', text)
    text = text.strip()
    return text


def add_paragraph_breaks(text: str) -> str:
    """Add paragraph breaks at natural points for readability."""

    # First, add single newlines after sentences (creates line breaks)
    for pattern in SENTENCE_BREAK_AFTER:
        text = re.sub(pattern, '\n', text)

    # Add double newlines for paragraph breaks at topic changes
    for pattern in PARAGRAPH_BREAK_AFTER:
        text = re.sub(pattern, '\n\n', text)

    # Add paragraph breaks around speaker changes (if detected)
    # Pattern: "Name: " or "SPEAKER:" style
    text = re.sub(r'(?<=[.!?])\s+(?=[A-Z][a-z]+:)', '\n\n', text)

    # Add breaks before/after ad transition phrases (if any remain)
    for pattern in AD_TRANSITION_PATTERNS:
        text = re.sub(f'({pattern})', r'\n\n\1\n\n', text, flags=re.IGNORECASE)

    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def extract_show_markers(text: str) -> dict:
    """Extract show structure markers (intro, segments, outro)."""
    markers = {}

    # Find "Pushkin" intro marker (common in Pushkin podcasts)
    pushkin_match = re.search(r'\bPushkin\.?\s*', text)
    if pushkin_match:
        markers['intro_end'] = pushkin_match.end()

    # Find host introductions
    host_patterns = [
        r"I'?m ([A-Z][a-z]+ [A-Z][a-z]+)\.",
        r"This is ([A-Z][a-z]+ [A-Z][a-z]+)\.",
        r"([A-Z][a-z]+ [A-Z][a-z]+) here\.",
    ]
    for pattern in host_patterns:
        match = re.search(pattern, text)
        if match:
            markers.setdefault('hosts', []).append(match.group(1))

    return markers


def preprocess_whisper_transcript(input_text: str) -> Tuple[str, dict]:
    """
    Main preprocessing function - FORMAT ONLY, no ad removal.

    Ad removal happens later in the normal enrichment pipeline
    (run_enrichment.py) which processes ALL content uniformly.

    Returns: (formatted_text, stats_dict)
    """
    stats = {
        'original_chars': len(input_text),
        'original_words': len(input_text.split()),
    }

    # Step 1: Basic formatting (clean whitespace)
    text = format_text(input_text)

    # Step 2: Add paragraph breaks for readability
    text = add_paragraph_breaks(text)

    # Step 3: Final cleanup
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n +', '\n', text)

    stats['final_chars'] = len(text)
    stats['final_words'] = len(text.split())
    stats['chars_removed'] = stats['original_chars'] - stats['final_chars']
    stats['percent_removed'] = (stats['chars_removed'] / stats['original_chars'] * 100) if stats['original_chars'] > 0 else 0
    stats['ad_blocks_removed'] = 0  # Ad removal happens in enrichment pipeline, not here

    return text, stats


def process_file(input_path: Path, output_path: Path = None, dry_run: bool = False) -> dict:
    """Process a single file."""

    if not input_path.exists():
        logger.error(f"File not found: {input_path}")
        return None

    content = input_path.read_text(encoding='utf-8')
    cleaned, stats = preprocess_whisper_transcript(content)

    if output_path is None:
        output_path = input_path.with_suffix('.md')

    if dry_run:
        logger.info(f"Would process: {input_path.name}")
        logger.info(f"  Original: {stats['original_words']:,} words")
        logger.info(f"  After cleanup: {stats['final_words']:,} words")
        logger.info(f"  Removed: {stats['chars_removed']:,} chars ({stats['percent_removed']:.1f}%)")
        logger.info(f"  Ad blocks removed: {stats['ad_blocks_removed']}")
    else:
        output_path.write_text(cleaned, encoding='utf-8')
        logger.info(f"Processed: {input_path.name} -> {output_path.name}")
        logger.info(f"  Removed {stats['ad_blocks_removed']} ad blocks ({stats['percent_removed']:.1f}% of content)")

    stats['input_file'] = str(input_path)
    stats['output_file'] = str(output_path) if not dry_run else None
    return stats


def process_all(queue_dir: Path, dry_run: bool = False) -> List[dict]:
    """Process all .txt files in the whisper queue."""

    results = []
    search_dirs = [
        queue_dir / 'transcripts',
        queue_dir / 'audio',
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for txt_file in search_dir.glob('*.txt'):
            # Skip files that start with . (Mac hidden files)
            if txt_file.name.startswith('.'):
                continue

            # Output goes to transcripts/ folder with .md extension
            output_dir = queue_dir / 'transcripts'
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / txt_file.with_suffix('.md').name

            stats = process_file(txt_file, output_path, dry_run)
            if stats:
                results.append(stats)

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Preprocess Whisper transcripts for Atlas',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process a single file
    python scripts/preprocess_whisper_transcript.py input.txt output.md

    # Process all files in whisper queue
    python scripts/preprocess_whisper_transcript.py --all

    # Dry run to see what would happen
    python scripts/preprocess_whisper_transcript.py --all --dry-run
        """
    )

    parser.add_argument('input', nargs='?', help='Input .txt file')
    parser.add_argument('output', nargs='?', help='Output .md file (optional)')
    parser.add_argument('--all', action='store_true', help='Process all files in whisper_queue')
    parser.add_argument('--queue-dir', default='data/whisper_queue', help='Queue directory')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show what would be done')

    args = parser.parse_args()

    if args.all:
        queue_dir = Path(args.queue_dir)
        results = process_all(queue_dir, args.dry_run)

        print(f"\n{'DRY RUN: ' if args.dry_run else ''}Processed {len(results)} files")

        total_removed = sum(r.get('chars_removed', 0) for r in results)
        total_ads = sum(r.get('ad_blocks_removed', 0) for r in results)

        if results:
            print(f"Total characters removed: {total_removed:,}")
            print(f"Total ad blocks removed: {total_ads}")

    elif args.input:
        input_path = Path(args.input)
        output_path = Path(args.output) if args.output else None
        process_file(input_path, output_path, args.dry_run)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
