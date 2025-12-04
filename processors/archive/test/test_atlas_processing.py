#!/usr/bin/env python3
"""
Atlas Processing Test Script
Test batch with episodes from different phases to validate the system
"""

import sqlite3
import json
import os
from datetime import datetime
from archive.disabled_integrations.relayq_integration import AtlasRelayQIntegration

class AtlasProcessingTest:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.test_results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    def create_test_batch(self):
        """Create a diverse test batch with episodes from different phases"""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Phase 1: High-value targets
        phase1_query = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Acquired%'
           OR p.name LIKE '%Stratechery%'
           OR p.name LIKE '%Sharp Tech%'
        ORDER BY p.priority DESC, e.published_date DESC
        LIMIT 2
        """

        # Phase 2: Major publications
        phase2_query = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Economist%'
           OR p.name LIKE '%Articles%'
           OR e.title LIKE '%New York Times%'
        ORDER BY p.priority DESC, e.published_date DESC
        LIMIT 2
        """

        # Phase 3: General content
        phase3_query = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name NOT LIKE '%Acquired%'
           AND p.name NOT LIKE '%Stratechery%'
           AND p.name NOT LIKE '%Sharp Tech%'
           AND p.name NOT LIKE '%Economist%'
           AND p.name NOT LIKE '%Articles%'
        ORDER BY RANDOM()
        LIMIT 2
        """

        # Execute queries
        phase1_episodes = [dict(row) for row in conn.execute(phase1_query).fetchall()]
        phase2_episodes = [dict(row) for row in conn.execute(phase2_query).fetchall()]
        phase3_episodes = [dict(row) for row in conn.execute(phase3_query).fetchall()]

        conn.close()

        # Combine test batch
        test_batch = phase1_episodes + phase2_episodes + phase3_episodes

        print(f"🧪 Test Batch Created:")
        print(f"   Phase 1 (High-value): {len(phase1_episodes)} episodes")
        for ep in phase1_episodes:
            print(f"     - {ep['podcast_name']}: {ep['title'][:50]}...")

        print(f"   Phase 2 (Major pubs): {len(phase2_episodes)} episodes")
        for ep in phase2_episodes:
            print(f"     - {ep['podcast_name']}: {ep['title'][:50]}...")

        print(f"   Phase 3 (General): {len(phase3_episodes)} episodes")
        for ep in phase3_episodes:
            print(f"     - {ep['podcast_name']}: {ep['title'][:50]}...")

        return test_batch

    def run_test_batch(self, test_batch):
        """Submit test batch and track results"""

        print(f"\n🚀 Starting Test Batch Processing")
        print(f"   Total episodes: {len(test_batch)}")
        print(f"   Results file: {self.test_results_file}")

        integration = AtlasRelayQIntegration()
        results = []

        for i, episode in enumerate(test_batch):
            print(f"\n[{i+1}/{len(test_batch)}] Processing: {episode['podcast_name']}")
            print(f"    Episode: {episode['title'][:60]}...")
            print(f"    Published: {episode['published_date']}")
            print(f"    Audio URL: {'✓' if episode.get('audio_url') else '✗'}")

            try:
                # Submit to RelayQ
                result = integration.create_relayq_job(episode)

                episode_result = {
                    'episode_id': episode['id'],
                    'podcast': episode['podcast_name'],
                    'title': episode['title'],
                    'published_date': episode['published_date'],
                    'audio_url': episode.get('audio_url'),
                    'processing_result': result,
                    'timestamp': datetime.now().isoformat()
                }

                results.append(episode_result)

                if result.get('success'):
                    method = result.get('method', 'unknown')
                    if method == 'github_api':
                        print(f"    ✅ Success: {result['issue_url']}")
                    else:
                        print(f"    💾 Success: {result['job_file']}")
                else:
                    print(f"    ❌ Failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                error_result = {
                    'episode_id': episode['id'],
                    'podcast': episode['podcast_name'],
                    'title': episode['title'],
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                results.append(error_result)
                print(f"    ❌ Exception: {str(e)}")

        # Save results
        with open(self.test_results_file, 'w') as f:
            json.dump(results, f, indent=2)

        return results

    def generate_test_report(self, results):
        """Generate comprehensive test report"""

        success_count = sum(1 for r in results if r.get('processing_result', {}).get('success'))
        total_count = len(results)

        report = f"""
# Atlas Processing Test Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 Test Results Summary
- **Total Episodes:** {total_count}
- **Successfully Submitted:** {success_count}
- **Success Rate:** {(success_count/total_count)*100:.1f}%

## 🎯 Episodes Tested

"""

        for i, result in enumerate(results, 1):
            podcast = result.get('podcast', 'Unknown')
            title = result.get('title', 'Unknown')
            status = "✅ Success" if result.get('processing_result', {}).get('success') else "❌ Failed"

            report += f"### {i}. {status} - {podcast}\n"
            report += f"**Episode:** {title[:80]}...\n"
            report += f"**Published:** {result.get('published_date', 'Unknown')}\n"

            if result.get('processing_result'):
                pr = result['processing_result']
                if pr.get('success'):
                    method = pr.get('method', 'unknown')
                    if method == 'github_api':
                        report += f"**GitHub Issue:** {pr['issue_url']}\n"
                    else:
                        report += f"**Local Job:** {pr['job_file']}\n"
                else:
                    report += f"**Error:** {pr.get('error', 'Unknown error')}\n"
            elif result.get('error'):
                report += f"**Exception:** {result['error']}\n"

            report += "\n---\n\n"

        report += f"""
## 🔍 Analysis Results

### Success by Phase:
- **High-value podcasts:** TBD
- **Major publications:** TBD
- **General content:** TBD

### Processing Methods:
- **GitHub API:** {sum(1 for r in results if r.get('processing_result', {}).get('method') == 'github_api')}
- **Local files:** {sum(1 for r in results if r.get('processing_result', {}).get('method') == 'local_file')}

### Next Steps:
1. **Monitor GitHub Issues** for processing status
2. **Check transcript discovery** success rates in 24-48 hours
3. **Evaluate best sources** by podcast type
4. **Scale up** based on successful test results

## 📁 Files Created:
- **Test Results:** `{self.test_results_file}`
- **RelayQ Jobs:** Created in `relayq_jobs/` directory
- **Database Updates:** Episode statuses marked as submitted

---
**Test completed:** {datetime.now().isoformat()}
"""

        # Save report
        report_file = f"ATLAS_TEST_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)

        return report_file

def main():
    print("🧪 Atlas Processing Test Suite")
    print("=" * 50)

    test = AtlasProcessingTest()

    # Step 1: Create diverse test batch
    test_batch = test.create_test_batch()

    if not test_batch:
        print("❌ No episodes found for testing!")
        return

    # Step 2: Run test batch
    results = test.run_test_batch(test_batch)

    # Step 3: Generate report
    report_file = test.generate_test_report(results)

    print(f"\n🎉 Test Suite Complete!")
    print(f"📊 Results: {len(results)} episodes processed")
    print(f"📄 Report: {report_file}")
    print(f"💾 Details: {test.test_results_file}")

    print(f"\n🔍 What to check next:")
    print(f"   1. Review test report: {report_file}")
    print(f"   2. Check relayq_jobs/ directory for submitted jobs")
    print(f"   3. Monitor GitHub Issues for processing status")
    print(f"   4. Wait 24-48 hours for transcript discovery results")

if __name__ == "__main__":
    main()