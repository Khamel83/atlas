#!/usr/bin/env python3
"""
PODEMOS Transcription System
Fast transcription pipeline using Whisper for Mac Mini integration.
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json
import time
import requests
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PodmosTranscriber:
    """Fast podcast transcription service optimized for Mac Mini."""

    def __init__(self, whisper_model: str = "base", temp_dir: str = "/tmp/podemos"):
        """
        Initialize transcriber.

        Args:
            whisper_model: Whisper model to use (tiny, base, small, medium, large)
            temp_dir: Directory for temporary files
        """
        self.whisper_model = whisper_model
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)

        # Check if Whisper is available
        self._check_whisper_availability()

    def _check_whisper_availability(self):
        """Check if Whisper is available and working."""
        try:
            # Check if whisper command exists
            result = subprocess.run(['whisper', '--help'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("✅ Whisper CLI detected")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        try:
            # Check if openai-whisper Python package is available
            import whisper
            logger.info("✅ Whisper Python package detected")
            return True
        except ImportError:
            pass

        logger.warning("⚠️ Whisper not detected - install with: pip install openai-whisper")
        return False

    def transcribe_audio_url(self, audio_url: str, episode_title: str = "Unknown") -> Optional[Dict]:
        """
        Transcribe audio from URL.

        Args:
            audio_url: URL to audio file
            episode_title: Episode title for logging

        Returns:
            Dictionary with transcription results or None if failed
        """
        try:
            logger.info(f"Starting transcription for: {episode_title}")
            start_time = time.time()

            # Download audio file
            audio_file = self._download_audio(audio_url, episode_title)
            if not audio_file:
                return None

            # Transcribe audio
            transcript_result = self._transcribe_file(audio_file)
            if not transcript_result:
                return None

            # Calculate processing time
            processing_time = time.time() - start_time

            # Clean up temporary file
            try:
                os.unlink(audio_file)
            except:
                pass

            result = {
                'episode_title': episode_title,
                'audio_url': audio_url,
                'transcript': transcript_result['text'],
                'segments': transcript_result.get('segments', []),
                'language': transcript_result.get('language', 'unknown'),
                'processing_time_seconds': processing_time,
                'transcribed_at': datetime.now().isoformat(),
                'whisper_model': self.whisper_model
            }

            logger.info(f"✅ Transcription completed in {processing_time:.1f}s: {episode_title}")
            return result

        except Exception as e:
            logger.error(f"Failed to transcribe {episode_title}: {e}")
            return None

    def _download_audio(self, audio_url: str, episode_title: str) -> Optional[str]:
        """Download audio file to temporary location."""
        try:
            logger.info(f"Downloading audio for: {episode_title}")

            # Create safe filename
            safe_title = "".join(c for c in episode_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]  # Limit length

            # Determine file extension from URL or use mp3 as default
            file_ext = '.mp3'
            if '.' in audio_url.split('/')[-1]:
                url_ext = '.' + audio_url.split('/')[-1].split('.')[-1].lower()
                if url_ext in ['.mp3', '.mp4', '.wav', '.m4a', '.ogg']:
                    file_ext = url_ext

            temp_file = self.temp_dir / f"podemos_{safe_title}_{int(time.time())}{file_ext}"

            # Download with streaming
            response = requests.get(audio_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Check file size (should be > 1MB for a real podcast episode)
            file_size = temp_file.stat().st_size
            if file_size < 1024 * 1024:
                logger.warning(f"Downloaded file seems too small ({file_size} bytes): {episode_title}")

            logger.info(f"Downloaded {file_size / 1024 / 1024:.1f}MB: {episode_title}")
            return str(temp_file)

        except Exception as e:
            logger.error(f"Failed to download audio for {episode_title}: {e}")
            return None

    def _transcribe_file(self, audio_file: str) -> Optional[Dict]:
        """Transcribe audio file using Whisper."""
        try:
            # Try Whisper CLI first (usually faster)
            result = self._transcribe_with_cli(audio_file)
            if result:
                return result

            # Fallback to Python Whisper package
            return self._transcribe_with_python(audio_file)

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def _transcribe_with_cli(self, audio_file: str) -> Optional[Dict]:
        """Transcribe using Whisper CLI."""
        try:
            output_dir = self.temp_dir / "whisper_output"
            output_dir.mkdir(exist_ok=True)

            # Run Whisper CLI with JSON output
            cmd = [
                'whisper', audio_file,
                '--model', self.whisper_model,
                '--output_dir', str(output_dir),
                '--output_format', 'json',
                '--language', 'en'  # Assume English podcasts
            ]

            logger.info(f"Running Whisper CLI: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout

            if result.returncode != 0:
                logger.warning(f"Whisper CLI failed: {result.stderr}")
                return None

            # Find output JSON file
            audio_name = Path(audio_file).stem
            json_file = output_dir / f"{audio_name}.json"

            if not json_file.exists():
                logger.warning(f"Whisper output file not found: {json_file}")
                return None

            # Load transcription result
            with open(json_file, 'r') as f:
                transcript_data = json.load(f)

            # Clean up output file
            try:
                os.unlink(json_file)
            except:
                pass

            return transcript_data

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Whisper CLI not available or timed out: {e}")
            return None

    def _transcribe_with_python(self, audio_file: str) -> Optional[Dict]:
        """Transcribe using Python Whisper package."""
        try:
            import whisper

            logger.info(f"Loading Whisper model: {self.whisper_model}")
            model = whisper.load_model(self.whisper_model)

            logger.info("Starting Whisper transcription...")
            result = model.transcribe(audio_file, language='en')

            return result

        except ImportError:
            logger.error("Whisper Python package not available")
            return None
        except Exception as e:
            logger.error(f"Python Whisper failed: {e}")
            return None

    def transcribe_episode_batch(self, episodes: List[Dict], max_concurrent: int = 2) -> List[Dict]:
        """
        Transcribe multiple episodes efficiently.

        Args:
            episodes: List of episode dictionaries with 'audio_url' and 'title'
            max_concurrent: Maximum concurrent transcriptions (Mac Mini resource limit)

        Returns:
            List of transcription results
        """
        results = []
        total_episodes = len(episodes)

        logger.info(f"Starting batch transcription of {total_episodes} episodes")

        for i, episode in enumerate(episodes):
            logger.info(f"Processing episode {i+1}/{total_episodes}")

            result = self.transcribe_audio_url(
                episode.get('audio_url', ''),
                episode.get('title', f'Episode {i+1}')
            )

            if result:
                result['episode_id'] = episode.get('id')
                results.append(result)

            # Brief pause between episodes to prevent overwhelming the system
            time.sleep(2)

        logger.info(f"Batch transcription completed: {len(results)}/{total_episodes} successful")
        return results

    def save_transcript(self, transcript_result: Dict, output_file: str = None) -> str:
        """Save transcript to file."""
        try:
            if not output_file:
                safe_title = "".join(c for c in transcript_result['episode_title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                output_file = f"transcript_{safe_title}_{int(time.time())}.txt"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Episode: {transcript_result['episode_title']}\n")
                f.write(f"Transcribed: {transcript_result['transcribed_at']}\n")
                f.write(f"Language: {transcript_result.get('language', 'unknown')}\n")
                f.write(f"Processing time: {transcript_result['processing_time_seconds']:.1f}s\n")
                f.write(f"Model: {transcript_result['whisper_model']}\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(transcript_result['transcript'])

            logger.info(f"Transcript saved to: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")
            return None

    def cleanup_temp_files(self):
        """Clean up temporary files."""
        try:
            for file_path in self.temp_dir.glob("podemos_*"):
                if file_path.is_file():
                    os.unlink(file_path)
            logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Failed to clean up temp files: {e}")

def create_test_transcript(output_file: str = "test_transcript.txt") -> str:
    """Create a test transcript file for ad detection testing."""
    test_content = """Episode: Test Podcast Episode
Transcribed: 2025-09-08T15:00:00
Language: en
Processing time: 45.2s
Model: base

==================================================

Welcome back to the Test Podcast. I'm your host John Smith, and today we have an amazing episode lined up for you.

But first, let me tell you about today's sponsor, NordVPN. NordVPN is the world's leading VPN service that protects your online privacy. Use code TESTPOD for 30% off your first month. That's NordVPN dot com slash TESTPOD.

Now, let's dive into today's topic about artificial intelligence and machine learning. Our guest today is Dr. Sarah Johnson, a leading researcher in the field of neural networks.

Dr. Johnson, thank you for joining us today. Can you tell us about your latest research?

Thank you John, it's great to be here. Our latest work focuses on transformer architectures and their applications in natural language processing.

That's fascinating. And speaking of language, let me take a quick moment to tell you about Grammarly. Grammarly helps you write with confidence and clarity. Whether you're writing emails, documents, or social media posts, Grammarly catches your mistakes and suggests improvements. Try Grammarly free today at grammarly dot com.

Now back to our conversation with Dr. Johnson. Can you explain how transformer models work?

Certainly. Transformers use attention mechanisms to process sequences of data. The key innovation was the self-attention mechanism that allows the model to weigh the importance of different parts of the input.

This is incredibly technical stuff. Before we continue, I want to mention our Patreon supporters. This podcast is made possible by listeners like you who support us on Patreon. Visit patreon dot com slash testpodcast to become a patron and get exclusive content.

Dr. Johnson, what do you see as the future of AI research?

I think we'll see continued advances in multimodal AI systems that can understand both text and images, and better integration of AI into everyday applications.

That's all the time we have for today. Thank you Dr. Johnson for this enlightening conversation.

Thank you for having me, John.

And thank you to our listeners for tuning in. Don't forget to subscribe and leave a review. This episode was sponsored by NordVPN and Grammarly. Until next time, this is John Smith signing off."""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    logger.info(f"Created test transcript: {output_file}")
    return output_file

def main():
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="PODEMOS Transcription System")
    parser.add_argument('--audio-url', help='Audio URL to transcribe')
    parser.add_argument('--test', action='store_true', help='Create test transcript')
    parser.add_argument('--model', default='base', help='Whisper model to use')
    args = parser.parse_args()

    if args.test:
        create_test_transcript()
        print("Created test transcript: test_transcript.txt")
        return

    if args.audio_url:
        transcriber = PodmosTranscriber(whisper_model=args.model)
        result = transcriber.transcribe_audio_url(args.audio_url, "Test Episode")

        if result:
            output_file = transcriber.save_transcript(result)
            print(f"Transcription completed: {output_file}")
            print(f"Processing time: {result['processing_time_seconds']:.1f} seconds")
        else:
            print("Transcription failed")
    else:
        print("Usage: python podemos_transcription.py --audio-url <URL> [--model base]")
        print("       python podemos_transcription.py --test")

if __name__ == "__main__":
    main()