#!/usr/bin/env python3
"""
PODEMOS Audio Cutter
Remove advertisement segments from podcast audio files using FFmpeg.
"""

import subprocess
import tempfile
import os
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from datetime import datetime
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PodmosAudioCutter:
    """Audio cutting system for removing ads from podcast episodes."""

    def __init__(self, temp_dir: str = "/tmp/podemos_audio", quality: str = "high"):
        """
        Initialize audio cutter.

        Args:
            temp_dir: Directory for temporary files
            quality: Audio quality level (high, medium, low)
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.quality = quality

        # Quality settings for FFmpeg
        self.quality_settings = {
            "high": ["-c:a", "libmp3lame", "-b:a", "128k"],
            "medium": ["-c:a", "libmp3lame", "-b:a", "96k"],
            "low": ["-c:a", "libmp3lame", "-b:a", "64k"]
        }

        self._check_ffmpeg_availability()

    def _check_ffmpeg_availability(self):
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("✅ FFmpeg detected")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        logger.error("❌ FFmpeg not found - install with: sudo apt install ffmpeg")
        raise RuntimeError("FFmpeg is required for audio processing")

    def remove_ads(self, audio_file_or_url: str, ad_segments: List[Tuple[float, float]],
                   output_file: str = None) -> Optional[str]:
        """
        Remove advertisement segments from audio file.

        Args:
            audio_file_or_url: Path to audio file or URL
            ad_segments: List of (start_time, end_time) tuples in seconds
            output_file: Output file path (auto-generated if None)

        Returns:
            Path to cleaned audio file or None if failed
        """
        try:
            logger.info(f"Starting ad removal from: {audio_file_or_url}")
            logger.info(f"Removing {len(ad_segments)} ad segments")

            # Download or copy input file
            input_file = self._prepare_input_file(audio_file_or_url)
            if not input_file:
                return None

            # Generate output filename if not provided
            if not output_file:
                input_name = Path(input_file).stem
                output_file = self.temp_dir / f"{input_name}_clean_{int(datetime.now().timestamp())}.mp3"
            else:
                output_file = Path(output_file)

            # Sort segments by start time
            sorted_segments = sorted(ad_segments, key=lambda x: x[0])

            # Create segments to keep (between ads)
            keep_segments = self._calculate_keep_segments(input_file, sorted_segments)

            if not keep_segments:
                logger.warning("No content segments found - returning original audio")
                return input_file

            # Cut and concatenate segments
            clean_file = self._cut_and_concatenate(input_file, keep_segments, output_file)

            # Clean up temporary input file if it was downloaded
            if input_file != audio_file_or_url:
                try:
                    os.unlink(input_file)
                except:
                    pass

            if clean_file:
                logger.info(f"✅ Created clean audio file: {clean_file}")

                # Log processing stats
                original_size = Path(input_file).stat().st_size if Path(input_file).exists() else 0
                clean_size = Path(clean_file).stat().st_size
                savings = ((original_size - clean_size) / original_size * 100) if original_size > 0 else 0

                logger.info(f"File size reduction: {savings:.1f}%")

            return str(clean_file)

        except Exception as e:
            logger.error(f"Failed to remove ads: {e}")
            return None

    def _prepare_input_file(self, audio_file_or_url: str) -> Optional[str]:
        """Download or prepare input audio file."""
        try:
            # Check if it's a URL
            if audio_file_or_url.startswith(('http://', 'https://')):
                logger.info(f"Downloading audio from URL...")

                # Download to temporary file
                response = requests.get(audio_file_or_url, stream=True, timeout=60)
                response.raise_for_status()

                # Determine file extension
                content_type = response.headers.get('content-type', '')
                if 'mp3' in content_type:
                    ext = '.mp3'
                elif 'mp4' in content_type or 'mpeg' in content_type:
                    ext = '.mp4'
                else:
                    ext = '.mp3'  # Default

                temp_file = self.temp_dir / f"input_{int(datetime.now().timestamp())}{ext}"

                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"Downloaded {temp_file.stat().st_size / 1024 / 1024:.1f}MB")
                return str(temp_file)

            else:
                # Local file
                if not Path(audio_file_or_url).exists():
                    logger.error(f"Audio file not found: {audio_file_or_url}")
                    return None

                return audio_file_or_url

        except Exception as e:
            logger.error(f"Failed to prepare input file: {e}")
            return None

    def _calculate_keep_segments(self, input_file: str, ad_segments: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Calculate segments to keep (content between ads)."""
        try:
            # Get total duration of audio file
            duration = self._get_audio_duration(input_file)
            if duration is None:
                return []

            keep_segments = []
            current_time = 0.0

            for ad_start, ad_end in ad_segments:
                # Skip invalid segments
                if ad_start >= ad_end or ad_start < 0:
                    continue

                # Add content segment before this ad
                if current_time < ad_start:
                    keep_segments.append((current_time, min(ad_start, duration)))

                # Move to end of ad
                current_time = min(ad_end, duration)

            # Add final content segment after last ad
            if current_time < duration:
                keep_segments.append((current_time, duration))

            # Filter out very short segments (< 2 seconds)
            keep_segments = [(start, end) for start, end in keep_segments if end - start >= 2.0]

            logger.info(f"Calculated {len(keep_segments)} content segments to keep")
            return keep_segments

        except Exception as e:
            logger.error(f"Failed to calculate keep segments: {e}")
            return []

    def _get_audio_duration(self, input_file: str) -> Optional[float]:
        """Get duration of audio file using FFprobe."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', input_file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"FFprobe failed: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])

            logger.info(f"Audio duration: {duration:.1f} seconds")
            return duration

        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return None

    def _cut_and_concatenate(self, input_file: str, keep_segments: List[Tuple[float, float]],
                           output_file: Path) -> Optional[str]:
        """Cut audio segments and concatenate them."""
        try:
            if len(keep_segments) == 1:
                # Single segment - just trim
                start, end = keep_segments[0]
                return self._trim_audio(input_file, start, end, output_file)

            # Multiple segments - cut and concatenate
            segment_files = []

            # Cut each segment
            for i, (start, end) in enumerate(keep_segments):
                segment_file = self.temp_dir / f"segment_{i}_{int(datetime.now().timestamp())}.mp3"

                if self._trim_audio(input_file, start, end, segment_file):
                    segment_files.append(segment_file)
                else:
                    logger.warning(f"Failed to cut segment {i}: {start}-{end}")

            if not segment_files:
                logger.error("No segments were successfully cut")
                return None

            # Concatenate segments
            result_file = self._concatenate_segments(segment_files, output_file)

            # Clean up segment files
            for segment_file in segment_files:
                try:
                    os.unlink(segment_file)
                except:
                    pass

            return result_file

        except Exception as e:
            logger.error(f"Failed to cut and concatenate: {e}")
            return None

    def _trim_audio(self, input_file: str, start_time: float, end_time: float,
                   output_file: Path) -> Optional[str]:
        """Trim audio file to specific time range."""
        try:
            cmd = [
                'ffmpeg', '-y',  # Overwrite output
                '-ss', str(start_time),  # Start time
                '-t', str(end_time - start_time),  # Duration
                '-i', input_file,  # Input file
            ]

            # Add quality settings
            cmd.extend(self.quality_settings[self.quality])

            # Add output file
            cmd.append(str(output_file))

            logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0 and output_file.exists():
                return str(output_file)
            else:
                logger.error(f"FFmpeg trim failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Failed to trim audio: {e}")
            return None

    def _concatenate_segments(self, segment_files: List[Path], output_file: Path) -> Optional[str]:
        """Concatenate multiple audio segments."""
        try:
            # Create file list for FFmpeg concat
            concat_file = self.temp_dir / f"concat_{int(datetime.now().timestamp())}.txt"

            with open(concat_file, 'w') as f:
                for segment_file in segment_files:
                    f.write(f"file '{segment_file.absolute()}'\n")

            # Run FFmpeg concat
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
            ]

            # Add quality settings
            cmd.extend(self.quality_settings[self.quality])

            # Add output file
            cmd.append(str(output_file))

            logger.debug(f"Running concat: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            # Clean up concat file
            try:
                os.unlink(concat_file)
            except:
                pass

            if result.returncode == 0 and output_file.exists():
                return str(output_file)
            else:
                logger.error(f"FFmpeg concat failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Failed to concatenate segments: {e}")
            return None

    def batch_process_episodes(self, episodes: List[Dict], max_concurrent: int = 1) -> List[Dict]:
        """
        Process multiple episodes for ad removal.

        Args:
            episodes: List of episode dicts with 'audio_url' and 'ad_segments'
            max_concurrent: Max concurrent processing (limited for resource management)

        Returns:
            List of processing results
        """
        results = []

        for i, episode in enumerate(episodes):
            logger.info(f"Processing episode {i+1}/{len(episodes)}: {episode.get('title', 'Unknown')}")

            clean_file = self.remove_ads(
                episode['audio_url'],
                episode.get('ad_segments', [])
            )

            results.append({
                'episode': episode,
                'clean_audio_file': clean_file,
                'success': bool(clean_file),
                'processed_at': datetime.now().isoformat()
            })

        logger.info(f"Batch processing completed: {sum(1 for r in results if r['success'])}/{len(episodes)} successful")
        return results

    def cleanup_temp_files(self):
        """Clean up temporary files."""
        try:
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    os.unlink(file_path)
            logger.info("Cleaned up temporary audio files")
        except Exception as e:
            logger.warning(f"Failed to clean up temp files: {e}")

def remove_ads(audio_file: str, ad_segments: List[Tuple[float, float]]) -> Optional[str]:
    """
    Convenience function for removing ads from audio file.
    This matches the required API from the acceptance criteria.
    """
    try:
        cutter = PodmosAudioCutter()
        return cutter.remove_ads(audio_file, ad_segments)
    except Exception as e:
        logger.error(f"Failed to remove ads: {e}")
        return None

def create_test_audio():
    """Create a simple test audio file for testing."""
    try:
        # Create a simple 10-second audio file with FFmpeg
        test_file = "test.mp3"

        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'sine=frequency=440:duration=10',
            '-c:a', 'libmp3lame',
            test_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info(f"Created test audio file: {test_file}")
            return test_file
        else:
            logger.error(f"Failed to create test audio: {result.stderr}")
            return None

    except Exception as e:
        logger.error(f"Failed to create test audio: {e}")
        return None

def main():
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="PODEMOS Audio Cutter")
    parser.add_argument('--audio', help='Audio file or URL to process')
    parser.add_argument('--ads', help='Ad segments as JSON: [[start1,end1],[start2,end2]]')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--test', action='store_true', help='Run test with generated audio')
    args = parser.parse_args()

    if args.test:
        # Create test audio and process
        test_file = create_test_audio()
        if test_file:
            # Test removing ads from seconds 2-4 and 6-8
            test_segments = [(2.0, 4.0), (6.0, 8.0)]
            clean_file = remove_ads(test_file, test_segments)

            if clean_file:
                print(f"✅ Test successful - created clean file: {clean_file}")
            else:
                print("❌ Test failed")
        return

    if args.audio and args.ads:
        try:
            # Parse ad segments
            ad_segments = json.loads(args.ads)
            ad_segments = [(float(start), float(end)) for start, end in ad_segments]

            # Process audio
            cutter = PodmosAudioCutter()
            clean_file = cutter.remove_ads(args.audio, ad_segments, args.output)

            if clean_file:
                print(f"Success: {clean_file}")
            else:
                print("Failed to process audio")

        except Exception as e:
            print(f"Error: {e}")

    else:
        print("Usage:")
        print('  python podemos_audio_cutter.py --audio <file> --ads "[[60,90],[300,330]]"')
        print("  python podemos_audio_cutter.py --test")

if __name__ == "__main__":
    main()