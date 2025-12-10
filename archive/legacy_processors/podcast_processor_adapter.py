#!/usr/bin/env python3
"""
Podcast Processing Adapter for OOS Log-Stream System
Wraps existing podcast processing with log-stream events
"""

import subprocess
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from oos_logger import get_logger

class PodcastProcessor:
    """Podcast processor with log-stream events"""

    def __init__(self, log_file: str = "oos.log"):
        self.logger = get_logger(log_file)

    def process_episode(self, episode_url: str, podcast_name: str, episode_id: str) -> Dict[str, Any]:
        """Process a single episode with log events"""

        # Log discovery
        self.logger.discover(
            "podcast",
            podcast_name,
            episode_id,
            {
                "url": episode_url,
                "source": "rss_feed",
                "discovered_at": datetime.utcnow().isoformat()
            }
        )

        # Log processing start
        self.logger.process(
            "podcast",
            podcast_name,
            episode_id,
            {
                "processor": "single_episode_processor.py",
                "started_at": datetime.utcnow().isoformat()
            }
        )

        try:
            # Run existing processor
            result = subprocess.run([
                'python3', 'single_episode_processor.py',
                episode_id,
                episode_url,
                podcast_name
            ], capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                # Check if transcript was found
                if 'transcript found' in result.stdout.lower():
                    # Extract transcript details from output
                    transcript_info = self._extract_transcript_info(result.stdout)

                    # Log completion
                    self.logger.complete(
                        "podcast",
                        podcast_name,
                        episode_id,
                        {
                            "transcript_file": transcript_info.get('file', ''),
                            "word_count": transcript_info.get('word_count', 0),
                            "duration": transcript_info.get('duration', 0),
                            "processing_time": transcript_info.get('processing_time', 0),
                            "completed_at": datetime.utcnow().isoformat()
                        }
                    )

                    return {
                        'status': 'success',
                        'transcript_found': True,
                        'details': transcript_info
                    }
                else:
                    # Log no transcript found
                    self.logger.complete(
                        "podcast",
                        podcast_name,
                        episode_id,
                        {
                            "transcript_found": False,
                            "reason": "no_transcript_available",
                            "completed_at": datetime.utcnow().isoformat()
                        }
                    )

                    return {
                        'status': 'success',
                        'transcript_found': False,
                        'reason': 'no_transcript_available'
                    }
            else:
                # Log failure
                error_msg = result.stderr or 'Unknown error'
                self.logger.fail(
                    "podcast",
                    podcast_name,
                    episode_id,
                    {
                        "error": error_msg,
                        "exit_code": result.returncode,
                        "failed_at": datetime.utcnow().isoformat()
                    }
                )

                return {
                    'status': 'error',
                    'error': error_msg,
                    'exit_code': result.returncode
                }

        except subprocess.TimeoutExpired:
            # Log timeout
            self.logger.fail(
                "podcast",
                podcast_name,
                episode_id,
                {
                    "error": "timeout",
                    "timeout_seconds": 120,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )

            return {
                'status': 'timeout',
                'error': 'Processing timeout'
            }

        except Exception as e:
            # Log unexpected error
            self.logger.fail(
                "podcast",
                podcast_name,
                episode_id,
                {
                    "error": str(e),
                    "exception_type": type(e).__name__,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )

            return {
                'status': 'exception',
                'error': str(e)
            }

    def _extract_transcript_info(self, stdout: str) -> Dict[str, Any]:
        """Extract transcript information from processor output"""
        info = {
            'file': '',
            'word_count': 0,
            'duration': 0,
            'processing_time': 0
        }

        # Parse output lines
        for line in stdout.split('\n'):
            if 'transcript file:' in line.lower():
                info['file'] = line.split(':', 1)[1].strip()
            elif 'word count:' in line.lower():
                try:
                    info['word_count'] = int(line.split(':', 1)[1].strip())
                except:
                    pass
            elif 'duration:' in line.lower():
                try:
                    info['duration'] = int(line.split(':', 1)[1].strip())
                except:
                    pass
            elif 'processing time:' in line.lower():
                try:
                    info['processing_time'] = float(line.split(':', 1)[1].strip().replace('s', ''))
                except:
                    pass

        return info

    def process_batch(self, episodes: list, batch_size: int = 10) -> Dict[str, Any]:
        """Process a batch of episodes"""

        results = {
            'total': len(episodes),
            'success': 0,
            'failed': 0,
            'transcripts_found': 0,
            'details': []
        }

        for i, episode in enumerate(episodes):
            episode_url = episode.get('url', '')
            podcast_name = episode.get('podcast_name', '')
            episode_id = episode.get('id', f"{podcast_name}_{i}")

            print(f"Processing {i+1}/{len(episodes)}: {podcast_name}")

            result = self.process_episode(episode_url, podcast_name, episode_id)
            results['details'].append(result)

            if result['status'] == 'success':
                results['success'] += 1
                if result.get('transcript_found'):
                    results['transcripts_found'] += 1
            else:
                results['failed'] += 1

            # Small delay between episodes
            time.sleep(1)

            # Log batch progress
            if (i + 1) % batch_size == 0:
                self.logger.metrics(
                    "podcast_processor",
                    f"batch_{i//batch_size}",
                    {
                        "processed": i + 1,
                        "success": results['success'],
                        "failed": results['failed'],
                        "transcripts_found": results['transcripts_found'],
                        "progress_percentage": round((i + 1) / len(episodes) * 100, 1)
                    }
                )

        # Log batch completion
        self.logger.metrics(
            "podcast_processor",
            f"batch_complete_{len(episodes)}",
            {
                "total_processed": len(episodes),
                "total_success": results['success'],
                "total_failed": results['failed'],
                "total_transcripts_found": results['transcripts_found'],
                "success_rate": round(results['success'] / len(episodes) * 100, 1),
                "transcript_rate": round(results['transcripts_found'] / len(episodes) * 100, 1)
            }
        )

        return results

def main():
    """Test the podcast processor"""
    if len(sys.argv) < 2:
        print("Usage: python3 podcast_processor_adapter.py <episode_url> [podcast_name] [episode_id]")
        sys.exit(1)

    episode_url = sys.argv[1]
    podcast_name = sys.argv[2] if len(sys.argv) > 2 else "TestPodcast"
    episode_id = sys.argv[3] if len(sys.argv) > 3 else f"test_{int(time.time())}"

    processor = PodcastProcessor("test_oos.log")

    print(f"Processing episode: {podcast_name} - {episode_id}")
    print(f"URL: {episode_url}")
    print("-" * 50)

    result = processor.process_episode(episode_url, podcast_name, episode_id)

    print(f"Result: {result['status']}")
    if result['status'] == 'success':
        print(f"Transcript found: {result.get('transcript_found', False)}")
        if result.get('transcript_found'):
            details = result.get('details', {})
            print(f"Transcript file: {details.get('file', 'N/A')}")
            print(f"Word count: {details.get('word_count', 0)}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    print("-" * 50)
    print("✅ Podcast processor test completed")

if __name__ == "__main__":
    main()