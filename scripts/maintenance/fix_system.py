#!/usr/bin/env python3
"""
Atlas System Fix
Complete solution to the duplication problem
"""

import sqlite3
import os
import shutil
from datetime import datetime

class AtlasSystemFix:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.backup_dir = f"atlas_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def backup_current_state(self):
        """Backup everything before fixing"""
        print("💾 CREATING BACKUP")
        print("=" * 40)

        os.makedirs(self.backup_dir, exist_ok=True)

        # Backup database
        shutil.copy2(self.db_path, f"{self.backup_dir}/podcast_processing.db")
        print("✅ Database backed up")

        # Backup job files
        if os.path.exists('relayq_jobs/'):
            shutil.copytree('relayq_jobs/', f"{self.backup_dir}/relayq_jobs")
            print("✅ Job files backed up")

        print(f"📁 Backup saved to: {self.backup_dir}")

    def clean_duplicate_job_files(self):
        """Remove duplicate job files, keep only the newest for each episode"""
        print("🧹 CLEANING DUPLICATE JOB FILES")
        print("=" * 40)

        if not os.path.exists('relayq_jobs/'):
            print("❌ No relayq_jobs directory")
            return

        # Group job files by episode ID
        episode_jobs = {}

        for job_file in os.listdir('relayq_jobs/'):
            if job_file.startswith('job_') and '_' in job_file:
                parts = job_file.split('_')
                if len(parts) >= 3:
                    try:
                        episode_id = int(parts[1])
                        timestamp = parts[2].replace('.md', '')

                        if episode_id not in episode_jobs:
                            episode_jobs[episode_id] = []
                        episode_jobs[episode_id].append({
                            'filename': job_file,
                            'timestamp': timestamp
                        })
                    except ValueError:
                        continue

        # For each episode, keep only the newest job file
        removed_count = 0
        kept_count = 0

        for episode_id, jobs in episode_jobs.items():
            if len(jobs) > 1:
                # Sort by timestamp, keep the newest
                jobs.sort(key=lambda x: x['timestamp'], reverse=True)
                newest_job = jobs[0]
                duplicate_jobs = jobs[1:]

                # Remove duplicates
                for duplicate in duplicate_jobs:
                    os.remove(f'relayq_jobs/{duplicate["filename"]}')
                    removed_count += 1

                kept_count += 1
                print(f"   Episode {episode_id}: Kept {newest_job['filename']}, removed {len(duplicate_jobs)} duplicates")
            else:
                kept_count += 1

        print(f"🧹 Cleaned: {removed_count} duplicates removed, {kept_count} unique jobs kept")

    def synchronize_database_with_jobs(self):
        """Update database to match actual job file status"""
        print("🔄 SYNCHRONIZING DATABASE WITH JOB FILES")
        print("=" * 40)

        # Get all existing job files
        job_episode_ids = set()
        if os.path.exists('relayq_jobs/'):
            for job_file in os.listdir('relayq_jobs/'):
                if job_file.startswith('job_') and '_' in job_file:
                    parts = job_file.split('_')
                    if len(parts) >= 2:
                        try:
                            episode_id = int(parts[1])
                            job_episode_ids.add(episode_id)
                        except ValueError:
                            continue

        conn = sqlite3.connect(self.db_path)

        # Update episodes that have job files but aren't marked as submitted
        update_query = """
        UPDATE episodes
        SET processing_status = 'relayq_submitted',
            last_attempt = ?
        WHERE id = ? AND processing_status = 'pending'
        """

        updated_count = 0
        for episode_id in job_episode_ids:
            cursor = conn.execute(update_query, (datetime.now().isoformat(), episode_id))
            if cursor.rowcount > 0:
                updated_count += 1

        conn.commit()
        conn.close()

        print(f"🔄 Updated {updated_count} episodes to 'relayq_submitted' status")

    def reset_failed_episodes(self):
        """Reset failed episodes to pending for retry"""
        print("🔄 RESETTING FAILED EPISODES")
        print("=" * 40)

        conn = sqlite3.connect(self.db_path)

        # Reset failed episodes to pending
        cursor = conn.execute("""
            UPDATE episodes
            SET processing_status = 'pending',
                processing_attempts = 0,
                error_message = NULL
            WHERE processing_status = 'failed'
        """)

        reset_count = cursor.rowcount
        conn.commit()
        conn.close()

        print(f"🔄 Reset {reset_count} failed episodes to 'pending'")

    def verify_fix(self):
        """Verify that the fix worked"""
        print("✅ VERIFYING FIX")
        print("=" * 40)

        # Check job files
        job_files = []
        if os.path.exists('relayq_jobs/'):
            job_files = os.listdir('relayq_jobs/')

        # Get unique episode IDs from job files
        job_episode_ids = set()
        for job_file in job_files:
            if job_file.startswith('job_') and '_' in job_file:
                parts = job_file.split('_')
                if len(parts) >= 2:
                    try:
                        episode_id = int(parts[1])
                        job_episode_ids.add(episode_id)
                    except ValueError:
                        continue

        # Check database
        conn = sqlite3.connect(self.db_path)
        db_status = dict(conn.execute("SELECT processing_status, COUNT(*) FROM episodes GROUP BY processing_status").fetchall())
        conn.close()

        # Check for duplicates
        duplicates = len(job_files) - len(job_episode_ids)

        print(f"📊 Verification Results:")
        print(f"   Total job files: {len(job_files)}")
        print(f"   Unique episodes with jobs: {len(job_episode_ids)}")
        print(f"   Duplicate job files: {duplicates}")
        print(f"   Database status: {db_status}")

        if duplicates == 0:
            print("✅ NO DUPLICATES - Fix successful!")
        else:
            print(f"⚠️ Still have {duplicates} duplicates")

        return duplicates == 0

    def run_complete_fix(self):
        """Run the complete system fix"""
        print("🔧 ATLAS SYSTEM FIX - COMPLETE SOLUTION")
        print("=" * 60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Step 1: Backup
        self.backup_current_state()
        print()

        # Step 2: Clean duplicates
        self.clean_duplicate_job_files()
        print()

        # Step 3: Synchronize database
        self.synchronize_database_with_jobs()
        print()

        # Step 4: Reset failed episodes
        self.reset_failed_episodes()
        print()

        # Step 5: Verify
        success = self.verify_fix()
        print()

        if success:
            print("🎉 SYSTEM FIX COMPLETE - Ready for corrected processing!")
        else:
            print("⚠️ Fix partially successful - manual review needed")

        return success

if __name__ == "__main__":
    fix = AtlasSystemFix()
    fix.run_complete_fix()