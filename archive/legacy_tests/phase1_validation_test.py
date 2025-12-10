#!/usr/bin/env python3
"""
Phase 1: 10 Episode Validation Test
Tests diverse podcast types to validate end-to-end processing
"""

import sqlite3
import json
import os
from datetime import datetime
from archive.disabled_integrations.relayq_integration import AtlasRelayQIntegration

class Phase1ValidationTest:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.test_results_file = f"phase1_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.test_report_file = f"PHASE1_TEST_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    def get_validation_episodes(self):
        """Get 10 diverse episodes for validation test"""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Specific validation episodes as per project plan
        validation_episodes = []

        # 1. Stratechery - Premium tech analysis
        query1 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Stratechery%' OR p.name LIKE '%Greatest Of All Talk%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        # 2. Acquired - Business content
        query2 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Acquired%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        # 3. Articles of Interest - BBC design content
        query3 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Articles of Interest%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        # 4. Lex Fridman Podcast - Technical interviews
        query4 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Lex Fridman%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        # 5. EconTalk - Economics discussions
        query5 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%EconTalk%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        # 6. Hard Fork - NYT tech podcast
        query6 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Hard Fork%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        # 7. Conversations with Tyler - Academic interviews
        query7 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Conversations with Tyler%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        # 8. Babbage - Economist science podcast
        query8 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Babbage%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        # 9. The Vergecast - Tech news
        query9 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Vergecast%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        # 10. Reply All - Internet culture
        query10 = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.name LIKE '%Reply All%'
        AND e.processing_status = 'pending'
        ORDER BY e.published_date DESC
        LIMIT 1
        """

        queries = [query1, query2, query3, query4, query5, query6, query7, query8, query9, query10]

        for i, query in enumerate(queries):
            cursor = conn.execute(query)
            episode = cursor.fetchone()
            if episode:
                validation_episodes.append(dict(episode))
            else:
                print(f"⚠️  No episode found for query {i+1}")

        conn.close()

        # If we have fewer than 10 episodes, fill with high-priority pending episodes
        if len(validation_episodes) < 10:
            remaining_needed = 10 - len(validation_episodes)
            fill_query = """
            SELECT e.*, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'pending'
            AND e.id NOT IN ({})
            ORDER BY p.priority DESC, e.published_date DESC
            LIMIT {}
            """.format(
                ','.join([str(ep['id']) for ep in validation_episodes]) if validation_episodes else '0',
                remaining_needed
            )

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(fill_query)
            validation_episodes.extend([dict(row) for row in cursor.fetchall()])
            conn.close()

        return validation_episodes[:10]  # Return exactly 10 episodes

    def run_validation_test(self):
        """Execute Phase 1 validation test"""

        print("🧪 Phase 1: 10 Episode Validation Test")
        print("=" * 60)
        print("Testing diverse podcast types to validate end-to-end processing")
        print()

        # Get validation episodes
        episodes = self.get_validation_episodes()

        print(f"🎯 Selected {len(episodes)} episodes for validation:")
        for i, episode in enumerate(episodes, 1):
            print(f"   {i}. {episode['podcast_name']}: {episode['title'][:60]}...")
            print(f"      Published: {episode['published_date']}")
            print(f"      Audio URL: {'✓' if episode.get('audio_url') else '✗'}")
            print()

        # Initialize RelayQ integration
        relayq = AtlasRelayQIntegration()

        # Process each episode
        results = []
        print("🚀 Starting Phase 1 Validation Processing")
        print(f"   Total episodes: {len(episodes)}")
        print(f"   Results file: {self.test_results_file}")
        print()

        for i, episode in enumerate(episodes, 1):
            print(f"[{i}/{len(episodes)}] Processing: {episode['podcast_name']}")
            print(f"    Episode: {episode['title'][:60]}...")
            print(f"    Published: {episode['published_date']}")
            print(f"    Audio URL: {'✓' if episode.get('audio_url') else '✗'}")

            # Submit to RelayQ
            job_result = relayq.create_relayq_job(episode)

            if job_result['success']:
                print(f"    💾 Success: {job_result['job_file']}")
                results.append({
                    'episode_id': episode['id'],
                    'podcast_name': episode['podcast_name'],
                    'episode_title': episode['title'],
                    'status': 'submitted',
                    'job_file': job_result['job_file'],
                    'job_url': job_result.get('job_url', 'N/A')
                })
            else:
                print(f"    ❌ Failed: {job_result['error']}")
                results.append({
                    'episode_id': episode['id'],
                    'podcast_name': episode['podcast_name'],
                    'episode_title': episode['title'],
                    'status': 'failed',
                    'error': job_result['error']
                })

            print()

        # Save results
        with open(self.test_results_file, 'w') as f:
            json.dump({
                'test_name': 'Phase 1 Validation Test',
                'timestamp': datetime.now().isoformat(),
                'total_episodes': len(episodes),
                'successful_submissions': len([r for r in results if r['status'] == 'submitted']),
                'failed_submissions': len([r for r in results if r['status'] == 'failed']),
                'results': results
            }, f, indent=2)

        # Create test report
        self.create_test_report(episodes, results)

        print("🎉 Phase 1 Validation Complete!")
        print(f"📊 Results: {len([r for r in results if r['status'] == 'submitted'])}/{len(episodes)} episodes submitted")
        print(f"📄 Report: {self.test_report_file}")
        print(f"💾 Details: {self.test_results_file}")
        print()
        print("🔍 What to check next:")
        print("   1. Review test report for submission status")
        print("   2. Monitor GitHub Issues for processing status")
        print("   3. Check database for transcript updates (24-48 hours)")
        print("   4. Validate 60% success rate target")

    def create_test_report(self, episodes, results):
        """Create detailed test report"""

        successful = [r for r in results if r['status'] == 'submitted']
        failed = [r for r in results if r['status'] == 'failed']

        report_content = f"""# Phase 1 Validation Test Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Test:** 10 Episode Validation - Diverse Podcast Types
**Objective:** Validate end-to-end processing pipeline

## 📊 Test Results Summary

- **Total Episodes:** {len(episodes)}
- **Successful Submissions:** {len(successful)}
- **Failed Submissions:** {len(failed)}
- **Success Rate:** {len(successful)/len(episodes)*100:.1f}%

## 🎯 Validation Episodes

### Successfully Submitted ({len(successful)})
"""

        for result in successful:
            report_content += f"""
1. **{result['podcast_name']}**
   - Episode: {result['episode_title'][:80]}...
   - Status: ✅ Submitted to RelayQ
   - Job File: {result['job_file']}
   - Job URL: {result['job_url']}
"""

        if failed:
            report_content += f"""
### Failed Submissions ({len(failed)})
"""
            for result in failed:
                report_content += f"""
1. **{result['podcast_name']}**
   - Episode: {result['episode_title'][:80]}...
   - Status: ❌ Failed
   - Error: {result['error']}
"""

        report_content += f"""
## 📈 Success Criteria Validation

### Phase 1 Target: 6+ out of 10 episodes successful (60%)
- **Actual Result:** {len(successful)}/{len(episodes)} ({len(successful)/len(episodes)*100:.1f}%)
- **Status:** {'✅ PASS' if len(successful) >= 6 else '❌ FAIL'}

### Expected Processing Timeline
- **Transcript Discovery:** 24-48 hours
- **Quality Validation:** Upon completion
- **Final Assessment:** After processing completes

## 🔍 Next Steps

1. **Monitor Processing:** Check GitHub Issues for job status
2. **Check Results:** Verify transcript updates in Atlas database
3. **Quality Assessment:** Validate transcript completeness and accuracy
4. **Phase 2 Decision:** Proceed with high-value target processing if 60% success achieved

## 📞 Support

If processing fails or success rate is below 60%:
- Review job submission errors in this report
- Check GitHub Actions workflow logs
- Verify RelayQ runner connectivity
- Consult Atlas system documentation

---

**Test Infrastructure:** Atlas-RelayQ Integration via GitHub Actions
**Processing Platform:** Self-hosted runner (macmini)
**Success Definition:** End-to-end transcript discovery and storage
"""

        with open(self.test_report_file, 'w') as f:
            f.write(report_content)

if __name__ == "__main__":
    test = Phase1ValidationTest()
    test.run_validation_test()