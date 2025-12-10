#!/usr/bin/env python3
"""
Atlas GitHub Actions Processor
Submit unique jobs to RelayQ via GitHub Actions (the right way)
"""

import sqlite3
import json
import time
import os
from datetime import datetime
from archive.disabled_integrations.relayq_integration import AtlasRelayQIntegration

class AtlasGitHubProcessor:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.status_file = f"github_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.relayq = AtlasRelayQIntegration()

        # GitHub Actions optimized parameters
        self.batch_size = 10  # Episodes per batch
        self.batch_delay = 600  # 10 minutes between batches (lets GitHub Actions process)

        # Status tracking
        self.status = {
            'start_time': datetime.now().isoformat(),
            'total_episodes': 0,
            'processed_episodes': 0,
            'successful_episodes': 0,
            'failed_episodes': 0,
            'current_phase': 'GITHUB_SUBMISSION',
            'batches_processed': 0,
            'last_batch_time': None,
            'processing_rate': 0,
            'github_actions_ready': True
        }

    def get_unique_pending_episodes(self, limit=None):
        """Get only episodes that haven't been submitted to GitHub yet"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Get episodes that are pending AND haven't been submitted recently
        query = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.processing_status = 'pending'
        AND (e.last_attempt IS NULL OR e.last_attempt < datetime('now', '-1 hour'))
        ORDER BY p.priority DESC, e.published_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor = conn.execute(query)
        episodes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return episodes

    def submit_to_github_actions(self, episodes):
        """Submit episodes to RelayQ via GitHub Actions"""
        print(f"🚀 GITHUB BATCH: {len(episodes)} episodes")
        print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Platform: GitHub Actions + RelayQ")
        print(f"   Expected processing: 5-30 minutes per episode")
        print()

        results = []
        successful = 0
        failed = 0

        for i, episode in enumerate(episodes, 1):
            print(f"[{i}/{len(episodes)}] {episode['podcast_name']}: {episode['title'][:50]}...")

            try:
                # Submit to RelayQ (which creates GitHub Issue/Action)
                job_result = self.relayq.create_relayq_job(episode)

                if job_result['success']:
                    print(f"    ✅ Submitted to GitHub: {job_result['job_file']}")
                    results.append({
                        'episode_id': episode['id'],
                        'status': 'submitted',
                        'job_file': job_result['job_file'],
                        'platform': 'GitHub Actions'
                    })
                    successful += 1
                else:
                    print(f"    ❌ Submission failed: {job_result['error']}")
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

        print(f"📊 Batch Results: {successful} submitted, {failed} failed")
        print(f"📈 Overall Rate: {self.status['processing_rate']:.1f} episodes/hour")
        print(f"⏱️ Processing will happen on GitHub Actions in 5-30 minutes")

        return results

    def save_status(self):
        """Save current status"""
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2)

    def run_github_processing(self):
        """Main GitHub Actions processing loop"""
        print("🚀 ATLAS GITHUB ACTIONS PROCESSOR STARTED")
        print("=" * 60)
        print(f"🎯 Strategy: Submit to GitHub Actions (proper infrastructure)")
        print(f"📦 Batch Size: {self.batch_size} episodes")
        print(f"⏱️ Delay: {self.batch_delay} seconds between batches")
        print(f"⚡ Expected Processing: 5-30 minutes per episode")
        print(f"🔄 Platform: GitHub Actions + RelayQ + Your macmini runner")
        print()

        # Get total unique episodes
        all_pending = self.get_unique_pending_episodes()
        self.status['total_episodes'] = len(all_pending)
        print(f"🎯 Target: {self.status['total_episodes']} unique episodes")
        print()

        batch_num = 1

        while True:
            # Get unique pending episodes
            episodes = self.get_unique_pending_episodes(self.batch_size)

            if not episodes:
                print("🎉 ALL EPISODES SUBMITTED TO GITHUB ACTIONS!")
                print("📊 Processing will continue on RelayQ runner")
                self.status['current_phase'] = 'SUBMISSIONS_COMPLETE'
                self.save_status()
                self.generate_final_report()
                break

            print(f"🚀 BATCH #{batch_num}")

            # Submit to GitHub Actions
            self.submit_to_github_actions(episodes)

            # Show progress
            remaining = len(self.get_unique_pending_episodes())
            progress_percent = (self.status['processed_episodes'] / self.status['total_episodes']) * 100

            print(f"📊 PROGRESS UPDATE:")
            print(f"   Submitted: {self.status['processed_episodes']}/{self.status['total_episodes']} ({progress_percent:.1f}%)")
            print(f"   Success Rate: {self.status['successful_episodes']/max(self.status['processed_episodes'], 1):.1%}")
            print(f"   Remaining: {remaining} episodes")
            print(f"   Batches: {batch_num}")
            print()

            # Save status
            self.save_status()

            batch_num += 1

            # Check if we should continue
            if remaining == 0:
                break

            # Delay between batches (lets GitHub Actions process)
            print(f"⏳ Waiting {self.batch_delay} seconds ({self.batch_delay//60} minutes)")
            print("   (This allows GitHub Actions to process the current batch)")
            print("   (Your macmini runner will handle transcript discovery)")
            time.sleep(self.batch_delay)

    def generate_final_report(self):
        """Generate final GitHub processing report"""
        report_file = f"GITHUB_FINAL_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        duration = datetime.now() - datetime.fromisoformat(self.status['start_time'])

        report_content = f"""# Atlas GitHub Actions Processing Report

**Platform:** GitHub Actions + RelayQ
**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {str(duration).split('.')[0]}

## 🚀 GitHub Submission Results

- **Total Episodes:** {self.status['total_episodes']}
- **Submitted Episodes:** {self.status['processed_episodes']}
- **Successful Submissions:** {self.status['successful_episodes']}
- **Failed Submissions:** {self.status['failed_episodes']}
- **Success Rate:** {self.status['successful_episodes']/max(self.status['processed_episodes'], 1):.1%}
- **Batches Processed:** {self.status['batches_processed']}
- **Submission Rate:** {self.status['processing_rate']:.1f} episodes/hour

## ⚡ Processing Pipeline

### What Happens Next:
1. **GitHub Actions** triggers automatically
2. **RelayQ runner** (your macmini) processes jobs
3. **Transcript discovery** runs (5-30 minutes per episode)
4. **Results stored** in Atlas database
5. **Complete archive** becomes searchable

## 📊 Expected Timeline

- **Job Submission:** Complete ✅
- **Initial Processing:** 5-30 minutes per batch
- **Full Archive Processing:** 1-3 days
- **Quality Assessment:** Ongoing

## 🔍 Monitoring

Check progress with:
```bash
# Database status
python3 atlas_data_provider.py stats

# Job submissions
ls -la relayq_jobs/ | wc -l

# Status file
cat github_status_*.json
```

---

**GitHub Status:** All jobs submitted to professional infrastructure
**Next Phase:** Monitor RelayQ processing on your macmini
**Processing:** 5-30 minutes per episode (as expected)
"""

        with open(report_file, 'w') as f:
            f.write(report_content)

        print(f"📄 GitHub report saved: {report_file}")

if __name__ == "__main__":
    processor = AtlasGitHubProcessor()
    processor.run_github_processing()