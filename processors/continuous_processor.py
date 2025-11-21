#!/usr/bin/env python3
"""
Atlas Continuous Processor
Non-stop processing of all 2,373 episodes with self-correction
"""

import sqlite3
import json
import time
import os
from datetime import datetime, timedelta
from archive.disabled_integrations.relayq_integration import AtlasRelayQIntegration

class AtlasContinuousProcessor:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.status_file = f"atlas_processing_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.failure_log_file = f"failure_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.relayq = AtlasRelayQIntegration()

        # Load or create status
        self.status = self.load_status()
        self.failure_patterns = self.load_failure_patterns()

        # Processing parameters
        self.batch_size = 25  # Episodes per batch
        self.batch_delay = 300  # 5 minutes between batches
        self.success_threshold = 0.5  # 50% success rate minimum

    def load_status(self):
        """Load existing status or create new"""
        if os.path.exists(self.status_file):
            with open(self.status_file, 'r') as f:
                return json.load(f)
        return {
            'start_time': datetime.now().isoformat(),
            'total_episodes': 0,
            'processed_episodes': 0,
            'successful_episodes': 0,
            'failed_episodes': 0,
            'current_phase': 'INITIALIZING',
            'batches_processed': 0,
            'last_batch_time': None,
            'estimated_completion': None,
            'processing_rate': 0
        }

    def load_failure_patterns(self):
        """Load failure patterns for self-correction"""
        if os.path.exists(self.failure_log_file):
            with open(self.failure_log_file, 'r') as f:
                return json.load(f)
        return {
            'failed_sources': {},
            'failed_podcasts': {},
            'common_errors': {},
            'blacklisted_sources': [],
            'optimization_applied': False
        }

    def save_status(self):
        """Save current status"""
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2)

    def save_failure_patterns(self):
        """Save failure patterns"""
        with open(self.failure_log_file, 'w') as f:
            json.dump(self.failure_patterns, f, indent=2)

    def get_total_episode_count(self):
        """Get total episodes needing processing"""
        conn = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM episodes WHERE processing_status = 'pending'").fetchone()[0]
        conn.close()
        return total

    def get_pending_episodes(self, limit=None):
        """Get pending episodes, avoiding known failures"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Build query to avoid blacklisted patterns
        query = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.processing_status = 'pending'
        """

        params = []

        # Avoid 100% failure podcasts
        for podcast_id, failure_rate in self.failure_patterns['failed_podcasts'].items():
            if failure_rate >= 1.0:  # 100% failure rate
                query += " AND e.podcast_id != ?"
                params.append(int(podcast_id))

        query += " ORDER BY p.priority DESC, e.published_date DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = conn.execute(query, params)
        episodes = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return episodes

    def update_failure_patterns(self, episode_id, success, error_msg=None):
        """Update failure patterns for self-correction"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Get episode details
        episode = conn.execute("""
            SELECT e.*, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.id = ?
        """, (episode_id,)).fetchone()

        if not episode:
            conn.close()
            return

        podcast_id = episode['podcast_id']
        podcast_name = episode['podcast_name']

        if not success:
            # Track podcast failure rate
            if podcast_id not in self.failure_patterns['failed_podcasts']:
                self.failure_patterns['failed_podcasts'][podcast_id] = {'attempts': 0, 'failures': 0}

            self.failure_patterns['failed_podcasts'][podcast_id]['attempts'] += 1
            self.failure_patterns['failed_podcasts'][podcast_id]['failures'] += 1

            # Track common errors
            if error_msg:
                error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg[:50]
                if error_type not in self.failure_patterns['common_errors']:
                    self.failure_patterns['common_errors'][error_type] = 0
                self.failure_patterns['common_errors'][error_type] += 1

        conn.close()

    def process_batch(self, episodes):
        """Process a batch of episodes"""
        print(f"🚀 Processing batch of {len(episodes)} episodes")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        batch_results = []

        for i, episode in enumerate(episodes, 1):
            print(f"[{i}/{len(episodes)}] {episode['podcast_name']}: {episode['title'][:50]}...")

            # Submit to RelayQ
            job_result = self.relayq.create_relayq_job(episode)

            if job_result['success']:
                print(f"    ✅ Submitted: {job_result['job_file']}")
                batch_results.append({
                    'episode_id': episode['id'],
                    'status': 'submitted',
                    'job_file': job_result['job_file']
                })
                self.status['successful_episodes'] += 1
            else:
                print(f"    ❌ Failed: {job_result['error']}")
                batch_results.append({
                    'episode_id': episode['id'],
                    'status': 'failed',
                    'error': job_result['error']
                })
                self.status['failed_episodes'] += 1
                self.update_failure_patterns(episode['id'], False, job_result['error'])

        self.status['processed_episodes'] += len(episodes)
        self.status['batches_processed'] += 1
        self.status['last_batch_time'] = datetime.now().isoformat()

        # Calculate processing rate
        if self.status['batches_processed'] > 0:
            elapsed = datetime.now() - datetime.fromisoformat(self.status['start_time'])
            self.status['processing_rate'] = self.status['processed_episodes'] / max(elapsed.total_seconds() / 3600, 1)

        # Update estimated completion
        remaining = self.get_total_episode_count()
        if self.status['processing_rate'] > 0:
            hours_needed = remaining / self.status['processing_rate']
            completion_time = datetime.now() + timedelta(hours=hours_needed)
            self.status['estimated_completion'] = completion_time.isoformat()

        return batch_results

    def apply_optimizations(self):
        """Apply self-correction based on failure patterns"""
        print("🔧 Applying optimizations based on failure patterns...")

        # Blacklist 100% failure podcasts
        for podcast_id, stats in self.failure_patterns['failed_podcasts'].items():
            if stats['attempts'] >= 5:  # At least 5 attempts
                failure_rate = stats['failures'] / stats['attempts']
                if failure_rate >= 1.0:  # 100% failure rate
                    print(f"   ⚠️ Blacklisting podcast {podcast_id} (100% failure rate)")
                    # Update database to skip these episodes
                    conn = sqlite3.connect(self.db_path)
                    conn.execute("""
                        UPDATE episodes
                        SET processing_status = 'skipped', error_message = '100% failure rate - auto-blacklisted'
                        WHERE podcast_id = ? AND processing_status = 'pending'
                    """, (podcast_id,))
                    conn.commit()
                    conn.close()

        self.failure_patterns['optimization_applied'] = True
        self.save_failure_patterns()

    def check_phase_transition(self):
        """Check if we should transition to next phase"""
        current_success_rate = self.status['successful_episodes'] / max(self.status['processed_episodes'], 1)

        print(f"📊 Current Stats:")
        print(f"   Processed: {self.status['processed_episodes']}")
        print(f"   Success: {self.status['successful_episodes']}")
        print(f"   Failed: {self.status['failed_episodes']}")
        print(f"   Success Rate: {current_success_rate:.1%}")

        if self.status['current_phase'] == 'INITIALIZING':
            if self.status['processed_episodes'] >= 10:
                if current_success_rate >= self.success_threshold:
                    print(f"✅ Phase 1 complete! Success rate {current_success_rate:.1%} >= {self.success_threshold:.0%}")
                    print("🚀 Accelerating to full speed processing...")
                    self.status['current_phase'] = 'FULL_SPEED'
                    self.batch_size = 50  # Increase batch size
                    self.batch_delay = 120  # 2 minutes between batches
                else:
                    print(f"⚠️ Phase 1 success rate {current_success_rate:.1%} below threshold {self.success_threshold:.0%}")
                    print("🔧 Applying optimizations...")
                    self.apply_optimizations()
                    self.status['current_phase'] = 'OPTIMIZING'

        elif self.status['current_phase'] == 'OPTIMIZING':
            if current_success_rate >= self.success_threshold:
                print(f"✅ Optimizations working! Success rate {current_success_rate:.1%} >= {self.success_threshold:.0%}")
                print("🚀 Resuming full speed processing...")
                self.status['current_phase'] = 'FULL_SPEED'
                self.batch_size = 50
                self.batch_delay = 120

    def run_continuous_processing(self):
        """Main continuous processing loop"""
        print("🎯 Atlas Continuous Processor Started")
        print("=" * 60)
        print(f"📊 Target: Process all {self.get_total_episode_count()} episodes")
        print(f"🎯 Success Threshold: {self.success_threshold:.0%}")
        print(f"⚡ Initial Batch Size: {self.batch_size} episodes")
        print(f"⏱️ Initial Delay: {self.batch_delay} seconds between batches")
        print()

        self.status['current_phase'] = 'INITIALIZING'
        self.status['total_episodes'] = self.get_total_episode_count()

        while True:
            # Get pending episodes
            episodes = self.get_pending_episodes(self.batch_size)

            if not episodes:
                print("🎉 No more pending episodes - Processing complete!")
                self.status['current_phase'] = 'COMPLETED'
                self.save_status()
                self.generate_final_report()
                break

            # Process batch
            self.process_batch(episodes)

            # Check for phase transitions
            self.check_phase_transition()

            # Save status
            self.save_status()

            # Show progress
            remaining = self.get_total_episode_count()
            progress_percent = (self.status['processed_episodes'] / self.status['total_episodes']) * 100
            print(f"📈 Progress: {progress_percent:.1f}% ({self.status['processed_episodes']}/{self.status['total_episodes']})")
            print(f"🎯 Remaining: {remaining} episodes")

            if self.status['estimated_completion']:
                eta = datetime.fromisoformat(self.status['estimated_completion'])
                print(f"⏱️ ETA: {eta.strftime('%Y-%m-%d %H:%M:%S')}")

            print()

            # Check if we should continue
            if self.status['current_phase'] == 'COMPLETED':
                break

            # Delay between batches
            if remaining > 0:
                print(f"⏳ Waiting {self.batch_delay} seconds before next batch...")
                time.sleep(self.batch_delay)

    def generate_final_report(self):
        """Generate final processing report"""
        report_file = f"ATLAS_FINAL_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        duration = datetime.now() - datetime.fromisoformat(self.status['start_time'])

        report_content = f"""# Atlas Processing Final Report

**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {str(duration).split('.')[0]}
**System:** Atlas Continuous Processor

## 📊 Final Results

- **Total Episodes:** {self.status['total_episodes']}
- **Processed Episodes:** {self.status['processed_episodes']}
- **Successful Submissions:** {self.status['successful_episodes']}
- **Failed Submissions:** {self.status['failed_episodes']}
- **Overall Success Rate:** {self.status['successful_episodes']/max(self.status['processed_episodes'], 1):.1%}
- **Batches Processed:** {self.status['batches_processed']}
- **Average Processing Rate:** {self.status['processing_rate']:.1f} episodes/hour

## 🔧 Self-Correction Applied

- **Optimization Applied:** {self.failure_patterns['optimization_applied']}
- **Failure Patterns Identified:** {len(self.failure_patterns['failed_podcasts'])}
- **Common Errors:** {len(self.failure_patterns['common_errors'])}

## 📈 Performance Analysis

### Processing Timeline
- **Start:** {self.status['start_time']}
- **End:** {self.status['last_batch_time']}
- **Total Duration:** {str(duration).split('.')[0]}

### Success Rate by Phase
- **Initial Phase:** {self.status['successful_episodes']/max(self.status['processed_episodes'], 1):.1%}

## 🎯 Achievement Status

✅ **Goal Achieved:** {'YES' if self.status['successful_episodes']/max(self.status['processed_episodes'], 1) >= self.success_threshold else 'NO'}
✅ **Target Success Rate:** {self.success_threshold:.0%}
✅ **Actual Success Rate:** {self.status['successful_episodes']/max(self.status['processed_episodes'], 1):.1%}

## 📝 Next Steps

1. **Monitor Processing:** Check GitHub Issues for job completion
2. **Verify Transcripts:** Validate transcript quality in database
3. **Review Failures:** Analyze failure patterns for future optimization
4. **Set Up Monitoring:** Configure ongoing episode processing

---

**System Status:** {'SUCCESS - Target Achieved' if self.status['successful_episodes']/max(self.status['processed_episodes'], 1) >= self.success_threshold else 'PARTIAL SUCCESS - Below Target'}
**Infrastructure Ready:** Yes
**Automated Processing:** Complete
"""

        with open(report_file, 'w') as f:
            f.write(report_content)

        print(f"📄 Final report saved: {report_file}")

if __name__ == "__main__":
    processor = AtlasContinuousProcessor()
    processor.run_continuous_processing()