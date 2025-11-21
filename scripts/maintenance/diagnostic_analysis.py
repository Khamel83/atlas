#!/usr/bin/env python3
"""
Atlas Diagnostic Analysis
Comprehensive investigation of the duplicate submission problem
"""

import sqlite3
import json
import os
from datetime import datetime

class AtlasDiagnostic:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.output_file = f"ATLAS_DIAGNOSTIC_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    def analyze_database_status(self):
        """Comprehensive database analysis"""
        print("🔍 ANALYZING DATABASE STATUS")
        print("=" * 50)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Status breakdown
        status_query = """
        SELECT processing_status, COUNT(*) as count
        FROM episodes
        GROUP BY processing_status
        ORDER BY count DESC
        """
        status_breakdown = dict(conn.execute(status_query).fetchall())

        # Sample episodes by status
        samples = {}
        for status in status_breakdown.keys():
            sample_query = f"""
            SELECT id, title, processing_status, last_attempt
            FROM episodes
            WHERE processing_status = '{status}'
            LIMIT 3
            """
            samples[status] = [dict(row) for row in conn.execute(sample_query).fetchall()]

        # Processing attempts distribution
        attempts_query = """
        SELECT processing_attempts, COUNT(*) as count
        FROM episodes
        WHERE processing_attempts IS NOT NULL
        GROUP BY processing_attempts
        ORDER BY processing_attempts DESC
        """
        attempts_breakdown = dict(conn.execute(attempts_query).fetchall())

        conn.close()

        return {
            'status_breakdown': status_breakdown,
            'status_samples': samples,
            'attempts_breakdown': attempts_breakdown
        }

    def analyze_job_files(self):
        """Comprehensive job file analysis"""
        print("🔍 ANALYZING JOB FILES")
        print("=" * 50)

        if not os.path.exists('relayq_jobs/'):
            return {'error': 'No relayq_jobs directory'}

        job_files = os.listdir('relayq_jobs/')

        # Extract episode IDs from filenames
        episode_ids = []
        duplicate_episodes = {}

        for job_file in job_files:
            if job_file.startswith('job_') and '_' in job_file:
                parts = job_file.split('_')
                if len(parts) >= 2:
                    try:
                        episode_id = int(parts[1])
                        episode_ids.append(episode_id)

                        # Track duplicates
                        if episode_id not in duplicate_episodes:
                            duplicate_episodes[episode_id] = []
                        duplicate_episodes[episode_id].append(job_file)
                    except ValueError:
                        continue

        # Find duplicates
        duplicates = {eid: files for eid, files in duplicate_episodes.items() if len(files) > 1}

        # Sample job content
        sample_jobs = []
        if job_files:
            sample_files = job_files[:5]
            for job_file in sample_files:
                try:
                    with open(f'relayq_jobs/{job_file}', 'r') as f:
                        content = f.read()
                        # Extract episode ID from content
                        lines = content.split('\n')
                        episode_id_line = [line for line in lines if 'Episode ID:' in line]
                        episode_id = episode_id_line[0].split(':')[-1].strip() if episode_id_line else 'Unknown'

                        sample_jobs.append({
                            'filename': job_file,
                            'episode_id': episode_id,
                            'content_preview': content[:200] + '...'
                        })
                except:
                    continue

        return {
            'total_job_files': len(job_files),
            'unique_episode_ids': len(set(episode_ids)),
            'duplicate_episodes': len(duplicates),
            'duplicate_details': dict(list(duplicates.items())[:10]),  # First 10 duplicates
            'sample_jobs': sample_jobs
        }

    def cross_reference_analysis(self):
        """Cross-reference database and job files"""
        print("🔍 CROSS-REFERENCING DATABASE AND JOB FILES")
        print("=" * 50)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Get all episodes from database
        db_episodes = conn.execute("SELECT id, processing_status FROM episodes").fetchall()
        conn.close()

        # Get all job files
        job_files = os.listdir('relayq_jobs/') if os.path.exists('relayq_jobs/') else []
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

        # Find mismatches
        db_episode_ids = {ep['id'] for ep in db_episodes}

        # Episodes with jobs but not marked as submitted in DB
        jobs_not_in_db = job_episode_ids - set(ep['id'] for ep in db_episodes if ep['processing_status'] in ['relayq_submitted', 'processing', 'completed'])

        # Episodes marked as submitted but no job file
        db_submitted_no_jobs = set(ep['id'] for ep in db_episodes if ep['processing_status'] in ['relayq_submitted', 'processing', 'completed']) - job_episode_ids

        # Episodes with jobs that are still pending
        pending_with_jobs = set(ep['id'] for ep in db_episodes if ep['processing_status'] == 'pending') & job_episode_ids

        return {
            'total_db_episodes': len(db_episodes),
            'total_job_files': len(job_files),
            'episodes_with_jobs': len(job_episode_ids),
            'jobs_not_in_db': list(jobs_not_in_db)[:20],  # First 20
            'db_submitted_no_jobs': list(db_submitted_no_jobs)[:20],  # First 20
            'pending_with_jobs': list(pending_with_jobs)[:20],  # First 20
            'sync_status': {
                'perfect_sync': len(jobs_not_in_db) == 0 and len(db_submitted_no_jobs) == 0,
                'jobs_missing_in_db': len(jobs_not_in_db),
                'db_missing_jobs': len(db_submitted_no_jobs),
                'pending_jobs_mismatch': len(pending_with_jobs)
            }
        }

    def identify_root_cause(self):
        """Identify the root cause of the problem"""
        print("🔍 IDENTIFYING ROOT CAUSE")
        print("=" * 50)

        db_analysis = self.analyze_database_status()
        job_analysis = self.analyze_job_files()
        cross_ref = self.cross_reference_analysis()

        # Analyze patterns
        issues = []

        # Check for massive duplication
        if job_analysis.get('total_job_files', 0) > 5000:
            issues.append({
                'severity': 'CRITICAL',
                'type': 'MASSIVE_DUPLICATION',
                'description': f"Found {job_analysis['total_job_files']} job files for only {db_analysis['status_breakdown'].get('pending', 0) + db_analysis['status_breakdown'].get('processing', 0) + db_analysis['status_breakdown'].get('relayq_submitted', 0)} pending episodes",
                'impact': 'Job queue overwhelmed'
            })

        # Check for sync issues
        if not cross_ref['sync_status']['perfect_sync']:
            issues.append({
                'severity': 'HIGH',
                'type': 'DATABASE_SYNC_ISSUE',
                'description': f"Database and job files are out of sync: {cross_ref['sync_status']['jobs_missing_in_db']} jobs not in DB, {cross_ref['sync_status']['db_missing_jobs']} DB entries without jobs",
                'impact': 'Duplicate submissions and missed episodes'
            })

        # Check for processing logic issues
        if job_analysis.get('duplicate_episodes', 0) > 100:
            issues.append({
                'severity': 'HIGH',
                'type': 'DUPLICATION_LOGIC_ERROR',
                'description': f"Found {job_analysis['duplicate_episodes']} episodes with multiple job files",
                'impact': 'Runner processes same episode multiple times'
            })

        return {
            'issues': issues,
            'root_cause': self.determine_root_cause(issues, db_analysis, job_analysis, cross_ref),
            'recommended_fix': self.recommend_fix(issues)
        }

    def determine_root_cause(self, issues, db_analysis, job_analysis, cross_ref):
        """Determine the actual root cause"""
        if not issues:
            return "No issues detected"

        # Check specific patterns
        if any(issue['type'] == 'MASSIVE_DUPLICATION' for issue in issues):
            return "SUBMISSION_LOGIC_NOT_CHECKING_EXISTING_JOBS"

        if any(issue['type'] == 'DATABASE_SYNC_ISSUE' for issue in issues):
            return "DATABASE_STATUS_NOT_UPDATED_AFTER_SUBMISSION"

        if any(issue['type'] == 'DUPLICATION_LOGIC_ERROR' for issue in issues):
            return "DEDUPLICATION_LOGIC_INSUFFICIENT"

        return "UNKNOWN_MULTIPLE_FACTORS"

    def recommend_fix(self, issues):
        """Recommend the best fix"""
        if not issues:
            return "System is working correctly"

        critical_issues = [i for i in issues if i['severity'] == 'CRITICAL']
        if critical_issues:
            return """
COMPLETE_SYSTEM_RESET:
1. Stop all processors
2. Clean duplicate job files
3. Reset database status for affected episodes
4. Implement proper deduplication
5. Restart with corrected logic
"""

        high_issues = [i for i in issues if i['severity'] == 'HIGH']
        if high_issues:
            return """
SYNC_FIX:
1. Synchronize database with actual job file status
2. Implement job file existence checking
3. Update database status after successful submission
4. Add proper error handling
"""

        return """
MINOR_FIXES:
1. Add better logging
2. Implement retry logic
3. Add status monitoring
"""

    def run_full_diagnostic(self):
        """Run complete diagnostic analysis"""
        print("🏥 ATLAS DIAGNOSTIC ANALYSIS")
        print("=" * 60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        results = {
            'timestamp': datetime.now().isoformat(),
            'database_analysis': self.analyze_database_status(),
            'job_analysis': self.analyze_job_files(),
            'cross_reference': self.cross_reference_analysis(),
            'root_cause_analysis': self.identify_root_cause()
        }

        # Save detailed results
        with open(self.output_file, 'w') as f:
            json.dump(results, f, indent=2)

        # Print summary
        print("📊 DIAGNOSTIC SUMMARY")
        print("=" * 50)
        print(f"Database Episodes: {results['database_analysis']['status_breakdown']}")
        print(f"Job Files: {results['job_analysis'].get('total_job_files', 0)}")
        print(f"Unique Episodes with Jobs: {results['job_analysis'].get('unique_episode_ids', 0)}")
        print(f"Duplicate Episodes: {results['job_analysis'].get('duplicate_episodes', 0)}")
        print(f"Sync Status: {results['cross_reference']['sync_status']}")
        print(f"Root Cause: {results['root_cause_analysis']['root_cause']}")
        print(f"Issues Found: {len(results['root_cause_analysis']['issues'])}")
        print()
        print(f"📄 Full diagnostic saved: {self.output_file}")

        return results

if __name__ == "__main__":
    diagnostic = AtlasDiagnostic()
    diagnostic.run_full_diagnostic()