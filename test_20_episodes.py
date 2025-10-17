#!/usr/bin/env python3
"""
Test the enhanced Atlas system with 20 random podcast episodes
"""

import sqlite3
import subprocess
import sys
import time
from datetime import datetime

def test_20_episodes():
    """Test the enhanced system with 20 random episodes"""

    print("🧪 TESTING ENHANCED ATLAS SYSTEM WITH 20 RANDOM EPISODES")
    print("=" * 70)

    # Get 20 random episodes from the queue
    conn = sqlite3.connect('data/atlas.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, episode_url, podcast_name, episode_title
        FROM episode_queue
        WHERE status = 'pending'
        ORDER BY RANDOM()
        LIMIT 20
    """)

    episodes = cursor.fetchall()
    conn.close()

    if not episodes:
        print("❌ No pending episodes found in database")
        return

    print(f"📋 Testing {len(episodes)} random episodes...")
    print()

    results = {
        'total': len(episodes),
        'success': 0,
        'failed': 0,
        'quality_scores': [],
        'sources': {},
        'podcasts': {}
    }

    start_time = time.time()

    for i, (episode_id, url, podcast, title) in enumerate(episodes, 1):
        print(f"🎬 [{i}/{len(episodes)}] Testing: {podcast} - {title[:50]}...")
        print(f"🔗 URL: {url[:80]}...")

        try:
            # Test the episode
            result = subprocess.run([
                'python3', 'single_episode_processor.py',
                str(episode_id), url, podcast
            ], capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                # Check if transcript was found
                if "TRANSCRIPT FOUND AND STORED" in result.stdout:
                    results['success'] += 1
                    print("✅ SUCCESS: Transcript found and stored")

                    # Extract quality score if available
                    for line in result.stdout.split('\n'):
                        if "Quality Score:" in line:
                            try:
                                score = float(line.split('%')[0].split()[-1].strip())
                                results['quality_scores'].append(score)
                                print(f"   📊 Quality: {score}%")
                            except:
                                pass
                        elif "Source:" in line and "google_search:" in line:
                            source = line.split("google_search:")[1].strip()
                            results['sources'][source] = results['sources'].get(source, 0) + 1
                            print(f"   🔍 Source: {source}")

                else:
                    results['failed'] += 1
                    print("❌ FAILED: No transcript found")
            else:
                results['failed'] += 1
                print("❌ FAILED: Processing error")

        except subprocess.TimeoutExpired:
            results['failed'] += 1
            print("❌ FAILED: Timeout")
        except Exception as e:
            results['failed'] += 1
            print(f"❌ FAILED: {e}")

        # Track podcast success
        results['podcasts'][podcast] = results['podcasts'].get(podcast, {'success': 0, 'failed': 0})
        if "TRANSCRIPT FOUND AND STORED" in result.stdout:
            results['podcasts'][podcast]['success'] += 1
        else:
            results['podcasts'][podcast]['failed'] += 1

        print()

    # Calculate statistics
    end_time = time.time()
    duration = end_time - start_time

    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"🎯 Total Episodes Tested: {results['total']}")
    print(f"✅ Successful: {results['success']} ({results['success']/results['total']*100:.1f}%)")
    print(f"❌ Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    print(f"⏱️  Total Time: {duration:.1f} seconds")
    print(f"⚡ Average Time: {duration/results['total']:.1f} seconds per episode")

    if results['quality_scores']:
        avg_quality = sum(results['quality_scores']) / len(results['quality_scores'])
        min_quality = min(results['quality_scores'])
        max_quality = max(results['quality_scores'])

        print(f"\n📈 QUALITY SCORES:")
        print(f"   Average: {avg_quality:.1f}%")
        print(f"   Minimum: {min_quality:.1f}%")
        print(f"   Maximum: {max_quality:.1f}%")
        print(f"   Valid Scores: {len(results['quality_scores'])}")

    if results['sources']:
        print(f"\n🔍 TOP SOURCES:")
        sorted_sources = sorted(results['sources'].items(), key=lambda x: x[1], reverse=True)
        for source, count in sorted_sources[:5]:
            print(f"   {source}: {count}")

    if results['podcasts']:
        print(f"\n🎙️  PODCAST BREAKDOWN:")
        sorted_podcasts = sorted(results['podcasts'].items(), key=lambda x: x[1]['success'], reverse=True)
        for podcast, stats in sorted_podcasts[:10]:
            total = stats['success'] + stats['failed']
            success_rate = stats['success'] / total * 100 if total > 0 else 0
            print(f"   {podcast}: {stats['success']}/{total} ({success_rate:.0f}%)")

    # Save results to file
    with open('test_results_20_episodes.json', 'w') as f:
        import json
        json.dump({
            'test_date': datetime.now().isoformat(),
            'results': results,
            'duration': duration
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: test_results_20_episodes.json")

    return results

if __name__ == "__main__":
    test_20_episodes()