#!/usr/bin/env python3
"""
Quick Transcript Source Validator
Rapidly tests which podcasts have working transcript sources
Returns fast feedback for decision making
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class QuickTranscriptValidator:
    """Fast validation of podcast transcript sources"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")

        # Load user-provided sources
        with open(self.root_dir / "podcast_transcript_sources.json", "r") as f:
            self.sources = json.load(f)

        # Simple requests session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Results tracking
        self.results = {}

    def test_single_podcast(self, podcast_name, source_config):
        """Quick test of a single podcast source"""
        try:
            primary_url = source_config.get('primary', '')
            reliable = source_config.get('reliable', False)

            if not primary_url:
                return {
                    'status': 'NO_URL',
                    'error': 'No primary URL provided',
                    'reliable': reliable
                }

            logger.info(f"🔍 Testing: {podcast_name}")

            # Quick HEAD request first
            try:
                head_response = self.session.head(primary_url, timeout=5)
                status_code = head_response.status_code
            except:
                # If HEAD fails, try GET
                try:
                    response = self.session.get(primary_url, timeout=5)
                    status_code = response.status_code
                except Exception as e:
                    return {
                        'status': 'FAILED',
                        'error': str(e),
                        'reliable': reliable
                    }

            # Quick content check for transcript indicators
            try:
                response = self.session.get(primary_url, timeout=10)
                if response.status_code == 200:
                    content = response.text.lower()
                    transcript_indicators = ['transcript', 'episode', 'podcast', 'listen']
                    found_indicators = [word for word in transcript_indicators if word in content]

                    return {
                        'status': 'SUCCESS',
                        'status_code': status_code,
                        'indicators': found_indicators,
                        'content_length': len(content),
                        'reliable': reliable
                    }
                else:
                    return {
                        'status': 'HTTP_ERROR',
                        'status_code': status_code,
                        'reliable': reliable
                    }
            except Exception as e:
                return {
                    'status': 'CONTENT_ERROR',
                    'error': str(e),
                    'reliable': reliable
                }

        except Exception as e:
            return {
                'status': 'CONFIG_ERROR',
                'error': str(e),
                'reliable': False
            }

    def test_all_podcasts(self):
        """Test all podcasts with rapid feedback"""
        all_sources = self.sources['podcast_sources']
        total = len(all_sources)

        logger.info(f"🚀 Quick validation of {total} podcast transcript sources")
        logger.info("=" * 60)

        success_count = 0
        fail_count = 0

        for i, (podcast_name, config) in enumerate(all_sources.items(), 1):
            result = self.test_single_podcast(podcast_name, config)
            self.results[podcast_name] = result

            # Quick status report
            status = result['status']
            if status == 'SUCCESS':
                success_count += 1
                logger.info(f"✅ {i}/{total} {podcast_name}: SUCCESS (code: {result.get('status_code')})")
            else:
                fail_count += 1
                error_msg = result.get('error', 'Unknown error')
                logger.info(f"❌ {i}/{total} {podcast_name}: {status} - {error_msg}")

            # Small delay to be respectful
            time.sleep(0.5)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 SUMMARY")
        logger.info(f"✅ Successful: {success_count}/{total}")
        logger.info(f"❌ Failed: {fail_count}/{total}")

        # List successful ones
        successful = [name for name, result in self.results.items() if result['status'] == 'SUCCESS']
        if successful:
            logger.info(f"\n🎯 WORKING SOURCES ({len(successful)}):")
            for name in successful[:10]:  # Show first 10
                logger.info(f"   ✅ {name}")
            if len(successful) > 10:
                logger.info(f"   ... and {len(successful) - 10} more")

        # Save results
        self.save_results()

        return success_count, fail_count

    def save_results(self):
        """Save validation results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.root_dir / f"validation_results_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'total_tested': len(self.results),
                'results': self.results
            }, f, indent=2)

        logger.info(f"\n💾 Results saved: {results_file}")

def main():
    validator = QuickTranscriptValidator()
    success, fail = validator.test_all_podcasts()

    logger.info(f"\n🎯 Quick validation complete: {success} working sources out of {success + fail}")

    if success > 0:
        logger.info("✅ Ready to proceed with transcript ingestion from working sources!")
    else:
        logger.info("⚠️  Need to investigate source configurations")

if __name__ == "__main__":
    main()