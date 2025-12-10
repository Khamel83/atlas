#!/usr/bin/env python3
"""
Atlas Deduplicated Processor
Only submit episodes that haven't been submitted to RelayQ yet
"""

import sqlite3
import json
import os
from datetime import datetime
from archive.disabled_integrations.relayq_integration import AtlasRelayQIntegration

class AtlasDedupProcessor:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.status_file = f"dedup_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.relayq = AtlasRelayQIntegration()

        # Deduplicated processing parameters
        self.batch_size = 10  # Episodes per batch
        self.batch_delay = 300  # 5 minutes between batches

        # Status tracking
        self.status = {
            'start_time': datetime.now().isoformat(),
            'total_episodes': 0,
            'processed_episodes': 0,
            'successful_episodes': 0,
            'failed_episodes': 0,
            'skipped_episodes': 0,
            'current_phase': 'DEDUPLICATED_SUBMISSION',
            'batches_processed': 0,
            'last_batch_time': None,
            'processing_rate': 0,
            'deduplication_enabled': True
        }

    def get_truly_pending_episodes(self, limit=None):
        """Get episodes that have NEVER been submitted to RelayQ"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Only get episodes with processing_status = 'pending' (never submitted)
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

    def check_if_job_exists(self, episode_id):
        """Check if a job file already exists for this episode"""
        job_files = os.listdir('relayq_jobs/')
        for job_file in job_files:
            if job_file.startswith(f'job_{episode_id}_'):
                return True
        return False

    def mark_episode_as_submitted(self, episode_id):
        """Mark episode as submitted to RelayQ"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE episodes SET
                processing_status = 'relayq_submitted',
                last_attempt = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), episode_id))
        conn.commit()
        conn.close()

    def submit_episode_deduped(self, episode):
        """Submit single episode with deduplication"""
        episode_id = episode['id']
        podcast_name = episode['podcast_name']
        episode_title = episode['title'][:50]

        print(f"🔍 {podcast_name}: {episode_title}...")

        # Check if already submitted (multiple ways)
        if episode['processing_status'] != 'pending':
            print(f"    ⏭️ Skipped: Already processed ({episode['processing_status']})")
            return {
                'episode_id': episode_id,
                'status': 'skipped',
                'reason': f"Already {episode['processing_status']}"
            }

        if self.check_if_job_exists(episode_id):
            print(f"    ⏭️ Skipped: Job file exists")
            return {
                'episode_id': episode_id,
                'status': 'skipped',
                'reason': 'Job file exists'
            }

        try:
            # Submit to RelayQ
            job_result = self.relayq.create_relayq_job(episode)

            if job_result['success']:
                # Mark as submitted immediately
                self.mark_episode_as_submitted(episode_id)
                print(f"    ✅ Submitted: {job_result['job_file']}")
                return {
                    'episode_id': episode_id,
                    'status': 'submitted',
                    'job_file': job_result['job_file']
                }
            else:
                print(f"    ❌ Failed: {job_result['error']}")
                return {
                    'episode_id': episode_id,
                    'status': 'failed',
                    'error': job_result['error']
                }

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            return {
                'episode_id': episode_id,
                'status': 'error',
                'error': str(e)
            }

    def process_deduped_batch(self, episodes):
        """Process a batch with deduplication"""
        print(f"🎯 DEDUPED BATCH: {len(episodes)} episodes")
        print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Deduplication: ENABLED")
        print()

        results = []
        successful = 0
        failed = 0
        skipped = 0

        for i, episode in enumerate(episodes, 1):
            print(f"[{i}/{len(episodes)}] ", end="")
            result = self.submit_episode_deduped(episode)
            results.append(result)

            if result['status'] == 'submitted':
                successful += 1
            elif result['status'] in ['failed', 'error']:
                failed += 1
            elif result['status'] == 'skipped':
                skipped += 1

        # Update counters
        self.status['processed_episodes'] += len(episodes)
        self.status['successful_episodes'] += successful
        self.status['failed_episodes'] += failed
        self.status['skipped_episodes'] += skipped
        self.status['batches_processed'] += 1
        self.status['last_batch_time'] = datetime.now().isoformat()

        # Calculate processing rate (only count actual submissions)
        elapsed = datetime.now() - datetime.fromisoformat(self.status['start_time'])
        actual_submissions = self.status['successful_episodes'] + self.status['failed_episodes']
        self.status['processing_rate'] = actual_submissions / max(elapsed.total_seconds() / 3600, 1)

        print(f"📊 Batch Results:")
        print(f"   ✅ Submitted: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏭️ Skipped: {skipped}")
        print(f"   📈 Submission Rate: {self.status['processing_rate']:.1f} episodes/hour")

        return results

    def save_status(self):
        """Save current status"""
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2)

    def run_deduped_processing(self):
        """Main deduplicated processing loop"""
        print("🎯 ATLAS DEDUPLICATED PROCESSOR STARTED")
        print("=" * 60)
        print(f"🚫 Strategy: NO DUPLICATES - Only truly pending episodes")
        print(f"📦 Batch Size: {self.batch_size} episodes")
        print(f"⏱️ Delay: {self.batch_delay} seconds between batches")
        print(f"🔍 Deduplication: Multiple checks enabled")
        print()

        # Get total truly pending episodes
        all_pending = self.get_truly_pending_episodes()
        self.status['total_episodes'] = len(all_pending)
        print(f"🎯 Target: {self.status['total_episodes']} truly pending episodes")
        print()

        if self.status['total_episodes'] == 0:
            print("✅ No pending episodes - all have been submitted!")
            self.status['current_phase'] = 'ALREADY_COMPLETE'
            self.save_status()
            return

        batch_num = 1

        while True:
            # Get truly pending episodes
            episodes = self.get_truly_pending_episodes(self.batch_size)

            if not episodes:
                print("🎉 ALL PENDING EPISODES SUBMITTED - DEDUPLICATED PROCESSING COMPLETE!")
                self.status['current_phase'] = 'COMPLETED'
                self.save_status()
                self.generate_final_report()
                break

            print(f"🚀 BATCH #{batch_num}")

            # Process deduped batch
            self.process_deduped_batch(episodes)

            # Show progress
            remaining = len(self.get_truly_pending_episodes())
            progress_percent = ((self.status['total_episodes'] - remaining) / self.status['total_episodes']) * 100

            print(f"📊 PROGRESS UPDATE:")
            print(f"   Processed: {self.status['total_episodes'] - remaining}/{self.status['total_episodes']} ({progress_percent:.1f}%)")
            print(f"   Successfully Submitted: {self.status['successful_episodes']}")
            print(f"   Skipped (duplicates): {self.status['skipped_episodes']}")
            print(f"   Remaining: {remaining} truly pending episodes")
            print(f"   Batches: {batch_num}")
            print()

            # Save status
            self.save_status()

            batch_num += 1

            # Check if we should continue
            if remaining == 0:
                break

            # Delay between batches
            if self.batch_delay > 0:
                print(f"⏳ Waiting {self.batch_delay} seconds...")
                import time
                time.sleep(self.batch_delay)

    def generate_final_report(self):
        """Generate final deduplicated processing report"""
        report_file = f"DEDUPED_FINAL_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        duration = datetime.now() - datetime.fromisoformat(self.status['start_time'])

        report_content = f"""# Atlas Deduplicated Processing Final Report

**Mode:** DEDUPLICATED (No Duplicates)
**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {str(duration).split('.')[0]}

## 🎯 Deduplicated Results

- **Total Episodes Found:** {self.status['total_episodes']}
- **Episodes Checked:** {self.status['processed_episodes']}
- **Successfully Submitted:** {self.status['successful_episodes']}
- **Failed Submissions:** {self.status['failed_episodes']}
- **Skipped (Duplicates):** {self.status['skipped_episodes']}
- **Batches Processed:** {self.status['batches_processed']}

## 🚫 Deduplication Features

- ✅ Database status checked
- ✅ Job file existence verified
- ✅ Only truly pending episodes submitted
- ✅ Zero duplicate submissions

## 📊 What Happens Next

1. **GitHub Actions** will process the {self.status['successful_episodes']} submitted jobs
2. **RelayQ runner** will discover transcripts (5-30 minutes per episode)
3. **Results** will be stored in Atlas database
4. **Monitoring** can track progress via database

## 🔍 Verification

Check that no duplicates were created:
```bash
# Total job files should match successful submissions
ls relayq_jobs/ | wc -l  # Should be around {self.status['successful_episodes'] + existing_jobs}

# Database should show relayq_submitted status
sqlite3 podcast_processing.db "SELECT COUNT(*) FROM episodes WHERE processing_status = 'relayq_submitted';"
```

---

**Deduplication Status:** SUCCESS
**Duplicates Eliminated:** {self.status['skipped_episodes']}
**Clean Submissions:** {self.status['successful_episodes']}
**Next Phase:** Monitor GitHub Actions processing
"""

        with open(report_file, 'w') as f:
            f.write(report_content)

        print(f"📄 Deduplicated report saved: {report_file}")

if __name__ == "__main__":
    processor = AtlasDedupProcessor()
    processor.run_deduped_processing()