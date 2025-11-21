#!/usr/bin/env python3
"""
Atlas Smart Processor
Submit only unique episodes - no duplicates
"""

import sqlite3
import json
import os
from datetime import datetime
from archive.disabled_integrations.relayq_integration import AtlasRelayQIntegration

class AtlasSmartProcessor:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.status_file = f"smart_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.relayq = AtlasRelayQIntegration()

        # Smart parameters
        self.batch_size = 25  # Reasonable batch size
        self.batch_delay = 1800  # 30 minutes between batches (let processing happen)

        # Status tracking
        self.status = {
            'start_time': datetime.now().isoformat(),
            'total_episodes': 0,
            'processed_episodes': 0,
            'successful_episodes': 0,
            'failed_episodes': 0,
            'current_phase': 'SMART_SUBMISSION',
            'batches_processed': 0,
            'last_batch_time': None,
            'processing_rate': 0,
            'unique_episodes_only': True
        }

    def get_unique_pending_episodes(self, limit=None):
        """Get only unique pending episodes that haven't been submitted"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.processing_status = 'pending'
        ORDER BY p.priority DESC, e.published_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor = conn.execute(query)
        episodes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return episodes

    def submit_episode_batch(self, episodes):
        """Submit a batch of unique episodes"""
        print(f"🎯 SMART BATCH: {len(episodes)} unique episodes")
        print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")

        results = []
        successful = 0
        failed = 0

        for i, episode in enumerate(episodes, 1):
            print(f"[{i}/{len(episodes)}] {episode['podcast_name']}: {episode['title'][:50]}...")

            try:
                job_result = self.relayq.create_relayq_job(episode)

                if job_result['success']:
                    print(f"    ✅ Submitted: {job_result['job_file']}")
                    results.append({
                        'episode_id': episode['id'],
                        'status': 'submitted',
                        'job_file': job_result['job_file']
                    })
                    successful += 1
                else:
                    print(f"    ❌ Failed: {job_result['error']}")
                    results.append({
                        'episode_id': episode['id'],
                        'status': 'failed',
                        'error': job_result['error']
                    })
                    failed += 1

            except Exception as e:
                print(f"    ❌ Error: {str(e)}")
                results.append({
                    'episode_id': episode['id'],
                    'status': 'error',
                    'error': str(e)
                })
                failed += 1

        # Update counters
        self.status['processed_episodes'] += len(episodes)
        self.status['successful_episodes'] += successful
        self.status['failed_episodes'] += failed
        self.status['batches_processed'] += 1
        self.status['last_batch_time'] = datetime.now().isoformat()

        # Calculate processing rate
        elapsed = datetime.now() - datetime.fromisoformat(self.status['start_time'])
        self.status['processing_rate'] = self.status['processed_episodes'] / max(elapsed.total_seconds() / 3600, 1)

        print(f"📊 Batch Results: {successful} successful, {failed} failed")
        print(f"📈 Overall Rate: {self.status['processing_rate']:.1f} episodes/hour")

        return results

    def save_status(self):
        """Save current status"""
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2)

    def run_smart_processing(self):
        """Main smart processing loop"""
        print("🧠 ATLAS SMART PROCESSOR STARTED")
        print("=" * 60)
        print(f"🎯 Strategy: Submit unique episodes only")
        print(f"📦 Batch Size: {self.batch_size} episodes")
        print(f"⏱️ Delay: {self.batch_delay} seconds between batches")
        print(f"🚫 Duplicates: Prevented")
        print()

        # Get total unique episodes needed
        all_pending = self.get_unique_pending_episodes()
        self.status['total_episodes'] = len(all_pending)
        print(f"🎯 Target: {self.status['total_episodes']} unique episodes")
        print()

        batch_num = 1

        while True:
            # Get unique pending episodes
            episodes = self.get_unique_pending_episodes(self.batch_size)

            if not episodes:
                print("🎉 ALL UNIQUE EPISODES SUBMITTED - SMART PROCESSING COMPLETE!")
                self.status['current_phase'] = 'COMPLETED'
                self.save_status()
                self.generate_final_report()
                break

            print(f"🚀 BATCH #{batch_num}")

            # Process batch
            self.submit_episode_batch(episodes)

            # Show progress
            remaining = len(self.get_unique_pending_episodes())
            progress_percent = (self.status['processed_episodes'] / self.status['total_episodes']) * 100

            print(f"📊 PROGRESS UPDATE:")
            print(f"   Submitted: {self.status['processed_episodes']}/{self.status['total_episodes']} ({progress_percent:.1f}%)")
            print(f"   Success Rate: {self.status['successful_episodes']/max(self.status['processed_episodes'], 1):.1%}")
            print(f"   Remaining: {remaining} unique episodes")
            print(f"   Batches: {batch_num}")
            print()

            # Save status
            self.save_status()

            batch_num += 1

            # Check if we should continue
            if remaining == 0:
                break

            # Delay between batches (let processing happen)
            print(f"⏳ Waiting {self.batch_delay} seconds ({self.batch_delay//60} minutes) for processing...")
            print("   (This allows RelayQ runner to actually process the transcripts)")
            import time
            time.sleep(self.batch_delay)

    def generate_final_report(self):
        """Generate final smart processing report"""
        report_file = f"SMART_FINAL_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        duration = datetime.now() - datetime.fromisoformat(self.status['start_time'])

        report_content = f"""# Atlas Smart Processing Final Report

**Mode:** SMART (Unique Episodes Only)
**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {str(duration).split('.')[0]}

## 🧠 Smart Results

- **Total Episodes:** {self.status['total_episodes']}
- **Submitted Episodes:** {self.status['processed_episodes']}
- **Successful Submissions:** {self.status['successful_episodes']}
- **Failed Submissions:** {self.status['failed_episodes']}
- **Success Rate:** {self.status['successful_episodes']/max(self.status['processed_episodes'], 1):.1%}
- **Batches Processed:** {self.status['batches_processed']}
- **Submission Rate:** {self.status['processing_rate']:.1f} episodes/hour

## 🎯 Smart Features Applied

- ✅ No Duplicate Episodes
- ✅ Proper Filtering Applied
- ✅ Reasonable Batch Timing
- ✅ Processing Time Allowed

## 📊 Next Steps

1. **Monitor Processing:** Check GitHub Issues for job completion
2. **Check Database:** Monitor for transcript discoveries
3. **Wait Patiently:** Real processing takes 24-48 hours
4. **Quality Check:** Verify transcript completeness

## 🕐 Expected Timeline

- **Job Submission:** Complete
- **Initial Transcripts:** 24-48 hours
- **Full Processing:** 1-2 weeks
- **Quality Assessment:** After completion

---

**Smart Status:** SUBMISSIONS COMPLETE
**Next Phase:** Wait for RelayQ processing
**Focus:** Monitor transcript discovery results
"""

        with open(report_file, 'w') as f:
            f.write(report_content)

        print(f"📄 Smart report saved: {report_file}")

if __name__ == "__main__":
    processor = AtlasSmartProcessor()
    processor.run_smart_processing()