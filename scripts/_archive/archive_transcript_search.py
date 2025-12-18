#!/usr/bin/env python3
"""
Internet Archive Transcript Searcher

Searches Internet Archive for podcast transcripts and episode archives.
The Internet Archive has a vast collection of podcast episodes and associated files.
"""

import requests
import json
import re
from urllib.parse import urljoin, quote, unquote
import time
from bs4 import BeautifulSoup

class ArchiveTranscriptSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Atlas Archive Transcript Searcher 1.0 (Python/requests)'
        })

        # Internet Archive search API base URL
        self.ia_search_url = "https://archive.org/advancedsearch.php"
        self.ia_download_url = "https://archive.org/download"

        # Common transcript file extensions
        self.transcript_extensions = ['.txt', '.srt', '.vtt', '.transcript', '.text']

        # Audio file extensions (to identify podcast episodes)
        self.audio_extensions = ['.mp3', '.m4a', '.wav', '.ogg', '.flac']

    def construct_search_query(self, podcast_name, episode_title):
        """Construct search query for Internet Archive"""
        # Clean up search terms
        podcast_clean = podcast_name.replace("Podcast", "").strip()
        episode_clean = episode_title.strip()

        # Internet Archive search parameters
        search_params = {
            'q': f'"{podcast_clean}" "{episode_clean}"',
            'fl[]': ['identifier', 'title', 'description', 'date', 'creator'],
            'rows': 50,
            'page': 1,
            'output': 'json',
            'and[]': ['mediatype:audio']  # Focus on audio collections
        }

        return search_params

    def search_archive_items(self, podcast_name, episode_title):
        """Search Internet Archive for relevant items"""
        try:
            print(f"    📚 Searching Internet Archive for: {podcast_name} - {episode_title[:50]}...")

            search_params = self.construct_search_query(podcast_name, episode_title)

            response = self.session.get(self.ia_search_url, params=search_params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'response' not in data or 'docs' not in data['response']:
                print(f"    ❌ No results found in Internet Archive")
                return []

            items = data['response']['docs']
            num_found = data['response']['numFound']

            print(f"    📊 Found {num_found} items in Internet Archive")

            return items

        except Exception as e:
            print(f"    ❌ Error searching Internet Archive: {e}")
            return []

    def get_item_files(self, item_identifier):
        """Get list of files for a specific Internet Archive item"""
        try:
            # Get item metadata which includes file list
            metadata_url = f"https://archive.org/metadata/{item_identifier}"

            response = self.session.get(metadata_url, timeout=20)
            response.raise_for_status()

            metadata = response.json()

            if 'files' not in metadata:
                return []

            return metadata['files']

        except Exception as e:
            print(f"    ❌ Error getting files for {item_identifier}: {e}")
            return []

    def find_transcript_files(self, files):
        """Find transcript files in the list of files"""
        transcript_files = []

        for file_info in files:
            filename = file_info.get('name', '')
            filename_lower = filename.lower()

            # Check if this looks like a transcript file
            if any(ext in filename_lower for ext in self.transcript_extensions):
                # Additional checks for transcript-like names
                if any(keyword in filename_lower for keyword in ['transcript', 'text', 'caption', 'subtitle']):
                    transcript_files.append(file_info)

            # Also look for associated text files with audio files
            elif filename_lower.endswith('.txt') and any(keyword in filename_lower for keyword in ['episode', 'show', 'audio']):
                transcript_files.append(file_info)

        return transcript_files

    def download_transcript_file(self, item_identifier, file_info):
        """Download and extract transcript content from file"""
        try:
            filename = file_info.get('name', '')
            file_url = f"{self.ia_download_url}/{item_identifier}/{filename}"

            print(f"    📥 Downloading transcript file: {filename}")

            response = self.session.get(file_url, timeout=30)
            response.raise_for_status()

            # Handle different file types
            if filename.lower().endswith('.srt') or filename.lower().endswith('.vtt'):
                # Extract text from subtitle files
                content = self.extract_text_from_subtitles(response.text)
            else:
                # Plain text file
                content = response.text

            # Validate that this looks like transcript content
            if self.validate_transcript_content(content):
                print(f"    ✅ Downloaded transcript: {len(content)} characters")
                return content
            else:
                print(f"    ❌ File doesn't appear to contain transcript content")
                return None

        except Exception as e:
            print(f"    ❌ Error downloading transcript file: {e}")
            return None

    def extract_text_from_subtitles(self, subtitle_content):
        """Extract plain text from SRT/VTT subtitle files"""
        lines = subtitle_content.split('\n')
        text_lines = []

        for line in lines:
            line = line.strip()

            # Skip time codes and sequence numbers
            if re.match(r'^\d+$', line) or '-->' in line or re.match(r'^\d{2}:', line):
                continue

            # Skip empty lines and common subtitle artifacts
            if not line or line in ['WEBVTT', '']:
                continue

            # Clean up HTML tags and subtitle formatting
            clean_line = re.sub(r'<[^>]+>', '', line)
            clean_line = re.sub(r'\[.*?\]', '', clean_line)  # Remove stage directions

            if clean_line.strip():
                text_lines.append(clean_line.strip())

        return '\n'.join(text_lines)

    def validate_transcript_content(self, content):
        """Validate that content looks like a transcript"""
        if not content or len(content) < 500:
            return False

        content_lower = content.lower()

        # Check for transcript indicators
        transcript_indicators = [
            'transcript', 'conversation', 'interview', 'host:', 'guest:', 'speaker:',
            'welcome to', 'thanks for', 'that was', 'let me ask'
        ]

        # Check for speech patterns
        speech_patterns = [
            r'\b(i|you|we|they)\s+(think|believe|feel|said)',
            r'\b(well|so|yeah|right|okay)\b',
            r'\?.*\.',  # Question followed by statement
        ]

        positive_score = sum(1 for indicator in transcript_indicators if indicator in content_lower)

        for pattern in speech_patterns:
            matches = re.findall(pattern, content_lower)
            positive_score += len(matches) * 0.5

        # Should have conversational content
        return positive_score > 3

    def search_archive_transcripts(self, podcast_name, episode_title):
        """Main function to search Internet Archive for podcast transcripts"""
        print(f"🏛️ Searching Internet Archive for transcripts...")

        # Search for relevant items
        items = self.search_archive_items(podcast_name, episode_title)

        if not items:
            return None

        # Check each item for transcript files
        for item in items[:10]:  # Limit to first 10 items
            item_id = item.get('identifier', '')
            item_title = item.get('title', ['Unknown'])[0] if isinstance(item.get('title'), list) else item.get('title', 'Unknown')

            print(f"    📂 Checking item: {item_title[:60]}... (ID: {item_id})")

            # Get files for this item
            files = self.get_item_files(item_id)

            if not files:
                print(f"    ❌ No files found for item {item_id}")
                continue

            # Find transcript files
            transcript_files = self.find_transcript_files(files)

            if not transcript_files:
                print(f"    ❌ No transcript files found")
                continue

            print(f"    📄 Found {len(transcript_files)} potential transcript files")

            # Try to download transcript files
            for transcript_file in transcript_files:
                transcript_content = self.download_transcript_file(item_id, transcript_file)

                if transcript_content:
                    print(f"    ✅ Successfully found transcript in Internet Archive!")
                    return transcript_content

            # Rate limiting
            time.sleep(1)

        print(f"    ❌ No transcripts found in Internet Archive")
        return None

# Module-level function for easy import
def search_archive_transcripts(podcast_name, episode_title):
    """Search Internet Archive for transcript - main entry point"""
    searcher = ArchiveTranscriptSearcher()
    return searcher.search_archive_transcripts(podcast_name, episode_title)

if __name__ == "__main__":
    # Test with known examples
    test_cases = [
        ("This American Life", "episode 233"),
        ("This American Life", "Starting From Scratch"),
        ("Fresh Air", "Terry Gross interview"),
        ("RadioLab", "Colors")
    ]

    for podcast_name, episode_title in test_cases:
        print(f"\n{'='*70}")
        print(f"Testing: {podcast_name} - {episode_title}")
        print('='*70)

        result = search_archive_transcripts(podcast_name, episode_title)

        if result:
            print(f"\n✅ Success! Found transcript: {len(result)} characters")
            print(f"First 200 chars: {result[:200]}...")
        else:
            print(f"\n❌ No transcript found")

        print(f"\n{'='*70}")
        time.sleep(3)  # Rate limiting between tests