#!/usr/bin/env python3
"""
Normalize Accidental Tech Podcast (ATP) speaker labels.

ATP transcripts have Pyannote diarization in this format:
    ⏹️
    ▶️
    Casey
    Can I give you a little bit of...
    ⏹️
    ▶️
    Marco
    I was going to say...

This script normalizes them to standard format:
    **Casey:** Can I give you a little bit of...

    **Marco:** I was going to say...
"""

import argparse
import logging
import re
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Known ATP speakers
ATP_SPEAKERS = {'Casey', 'Marco', 'John'}


def parse_atp_transcript(content: str) -> List[Tuple[str, str]]:
    """
    Parse ATP transcript into (speaker, text) segments.

    Returns list of (speaker, text) tuples.
    """
    segments = []

    # Split on ▶️ which starts each speaker segment
    parts = content.split('▶️')

    for part in parts[1:]:  # Skip first part (header before any ▶️)
        # Remove trailing ⏹️ marker
        part = part.replace('⏹️', '').strip()

        if not part:
            continue

        lines = part.split('\n')
        if len(lines) < 2:
            continue

        # First line should be speaker name
        speaker_line = lines[0].strip()

        # Handle multi-speaker lines like "Casey, John"
        if ',' in speaker_line:
            speaker = speaker_line.split(',')[0].strip()
        else:
            speaker = speaker_line

        # Check if it's a known speaker
        if speaker not in ATP_SPEAKERS:
            # Might be noise or misidentification, try to clean
            for known in ATP_SPEAKERS:
                if known.lower() in speaker.lower():
                    speaker = known
                    break
            else:
                # Unknown speaker, skip or use as-is
                if len(speaker) > 20 or not speaker[0].isupper():
                    continue  # Probably noise, skip

        # Rest of lines are the text
        text = ' '.join(line.strip() for line in lines[1:] if line.strip())

        # Clean up common artifacts from transcription
        text = re.sub(r'\*\*[A-Za-z ]+\*\*', '', text)  # Remove **Name** artifacts
        text = re.sub(r'\*\*[A-Za-z]+', '', text)  # Remove incomplete **Name
        text = re.sub(r'[A-Za-z]+\*\*', '', text)  # Remove Name** fragments
        text = re.sub(r'^(Rob|Matt|Adam|Dan|David|Mike|Tom|Ben|Chris|Steve)\s+[A-Z][a-z]+\s*', '', text)  # Remove "FirstName LastName" at start
        text = re.sub(r'^\s*Stauffer\s*', '', text)  # Remove orphan "Stauffer"
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()

        if text and speaker and len(text) > 2:
            segments.append((speaker, text))

    return segments


def format_normalized_transcript(segments: List[Tuple[str, str]], header: str) -> str:
    """
    Format segments into standard markdown format.

    Combines consecutive segments from the same speaker.
    """
    lines = [header.strip()]
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Transcript')
    lines.append('')

    current_speaker = None
    current_text = []

    for speaker, text in segments:
        if speaker == current_speaker:
            # Same speaker, accumulate text
            current_text.append(text)
        else:
            # New speaker, flush previous
            if current_speaker and current_text:
                lines.append(f"**{current_speaker}:** {' '.join(current_text)}")
                lines.append('')
            current_speaker = speaker
            current_text = [text]

    # Flush final speaker
    if current_speaker and current_text:
        lines.append(f"**{current_speaker}:** {' '.join(current_text)}")

    return '\n'.join(lines)


def extract_header(content: str) -> str:
    """Extract the header portion before the transcript."""
    # Find where the transcript content starts (first ▶️)
    idx = content.find('▶️')
    if idx == -1:
        return ''

    header = content[:idx].strip()

    # Remove trailing ⏹️ from header
    header = header.rstrip('⏹️').strip()

    return header


def normalize_file(input_path: Path, output_path: Path, dry_run: bool = False) -> bool:
    """
    Normalize a single ATP transcript file.

    Returns True if file was normalized, False if skipped.
    """
    content = input_path.read_text(encoding='utf-8')

    # Check if it has the ATP format
    if '▶️' not in content:
        logger.debug(f"Skipping {input_path.name} - no ▶️ markers")
        return False

    # Parse segments
    segments = parse_atp_transcript(content)

    if not segments:
        logger.warning(f"No segments parsed from {input_path.name}")
        return False

    # Extract header
    header = extract_header(content)

    # Format normalized transcript
    normalized = format_normalized_transcript(segments, header)

    if dry_run:
        logger.info(f"Would normalize: {input_path.name} ({len(segments)} segments)")
        # Show sample
        for speaker, text in segments[:3]:
            logger.info(f"  {speaker}: {text[:50]}...")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(normalized, encoding='utf-8')
        logger.info(f"Normalized: {input_path.name} ({len(segments)} segments)")

    return True


def normalize_all(source_dir: Path, output_dir: Path, dry_run: bool = False, limit: int = 0):
    """Normalize all ATP transcripts."""

    source_path = source_dir / 'accidental-tech-podcast' / 'transcripts'
    output_path = output_dir / 'accidental-tech-podcast' / 'transcripts'

    if not source_path.exists():
        logger.error(f"Source path not found: {source_path}")
        return

    # Find all markdown files
    files = list(source_path.glob('*.md'))

    if limit > 0:
        files = files[:limit]

    logger.info(f"Processing {len(files)} ATP transcripts")

    normalized = 0
    skipped = 0

    for f in files:
        output_file = output_path / f.name
        if normalize_file(f, output_file, dry_run):
            normalized += 1
        else:
            skipped += 1

    print(f"\nNormalization complete:")
    print(f"  Normalized: {normalized}")
    print(f"  Skipped: {skipped}")


def main():
    parser = argparse.ArgumentParser(description='Normalize ATP speaker labels')
    parser.add_argument('--source-dir', '-s', default='data/podcasts',
                        help='Source directory with raw transcripts')
    parser.add_argument('--output-dir', '-o', default='data/clean/podcasts',
                        help='Output directory for normalized transcripts')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would be done')
    parser.add_argument('--limit', '-l', type=int, default=0,
                        help='Limit number of files to process')
    args = parser.parse_args()

    normalize_all(
        Path(args.source_dir),
        Path(args.output_dir),
        args.dry_run,
        args.limit
    )


if __name__ == '__main__':
    main()
