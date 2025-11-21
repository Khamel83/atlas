#!/usr/bin/env python3
"""
Quick Atlas Validation Test
Fast validation of core system functionality for testing phase.
"""

import json
import os
import sqlite3
import sys
import time
import requests
from pathlib import Path

class QuickAtlasValidator:
    """Quick validation of Atlas core systems."""

    def __init__(self):
        self.results = {}
        self.start_time = time.time()

    def log(self, message, status="INFO"):
        print(f"[{status}] {message}")

    def test_database_availability(self):
        """Test that databases exist and are accessible."""
        self.log("Testing database availability...")

        databases = {
            'main': 'data/atlas.db',
            'search': 'data/enhanced_search.db',
            'processed': 'data/processed_content.db'
        }

        results = {}
        for name, path in databases.items():
            if os.path.exists(path):
                try:
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
                    table_count = cursor.fetchone()[0]
                    conn.close()
                    results[name] = {'status': 'available', 'tables': table_count}
                    self.log(f"  ✅ {name} DB: {table_count} tables")
                except Exception as e:
                    results[name] = {'status': 'error', 'error': str(e)}
                    self.log(f"  ❌ {name} DB: {e}", "ERROR")
            else:
                results[name] = {'status': 'missing'}
                self.log(f"  ⚠️ {name} DB: missing")

        self.results['databases'] = results
        return results

    def test_content_count(self):
        """Test content availability in main database."""
        self.log("Testing content availability...")

        if not os.path.exists('data/atlas.db'):
            self.log("  ❌ Main database missing", "ERROR")
            return {'status': 'error', 'reason': 'database_missing'}

        try:
            conn = sqlite3.connect('data/atlas.db')
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM content;")
            total_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT content_type) FROM content;")
            type_count = cursor.fetchone()[0]

            cursor.execute("SELECT content_type, COUNT(*) FROM content GROUP BY content_type ORDER BY COUNT(*) DESC LIMIT 5;")
            top_types = cursor.fetchall()

            conn.close()

            result = {
                'total_items': total_count,
                'content_types': type_count,
                'top_types': dict(top_types)
            }

            self.log(f"  ✅ Total content items: {total_count:,}")
            self.log(f"  ✅ Content types: {type_count}")
            for content_type, count in top_types[:3]:
                self.log(f"    - {content_type}: {count:,} items")

            self.results['content'] = result
            return result

        except Exception as e:
            self.log(f"  ❌ Content test failed: {e}", "ERROR")
            return {'status': 'error', 'error': str(e)}

    def test_api_endpoints(self):
        """Test that API endpoints are responding."""
        self.log("Testing API endpoints...")

        endpoints = [
            '/api/v1/health',
            '/api/v1/content/',
            '/api/v1/search/',
            '/api/v1/dashboard/',
        ]

        results = {}
        base_url = 'http://localhost:8000'

        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                if response.status_code < 500:
                    results[endpoint] = {'status': 'responding', 'code': response.status_code}
                    self.log(f"  ✅ {endpoint}: HTTP {response.status_code}")
                else:
                    results[endpoint] = {'status': 'error', 'code': response.status_code}
                    self.log(f"  ❌ {endpoint}: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                results[endpoint] = {'status': 'unreachable', 'error': str(e)}
                self.log(f"  ❌ {endpoint}: {e}", "ERROR")

        self.results['api_endpoints'] = results
        return results

    def test_background_processes(self):
        """Test background processes are running appropriately."""
        self.log("Testing background processes...")

        import subprocess
        try:
            # Get Atlas-related processes
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.split('\n')

            atlas_processes = []
            for line in lines:
                if ('atlas' in line.lower() or 'python' in line) and 'grep' not in line:
                    if any(term in line for term in ['atlas_', 'uvicorn', 'scheduler']):
                        atlas_processes.append(line.strip())

            result = {
                'process_count': len(atlas_processes),
                'processes': atlas_processes
            }

            self.log(f"  ✅ Atlas processes running: {len(atlas_processes)}")
            for proc in atlas_processes[:3]:  # Show first 3
                process_info = ' '.join(proc.split()[10:])[:60] + '...'
                self.log(f"    - {process_info}")

            self.results['processes'] = result
            return result

        except Exception as e:
            self.log(f"  ❌ Process check failed: {e}", "ERROR")
            return {'status': 'error', 'error': str(e)}

    def test_file_system_health(self):
        """Test file system availability and key directories."""
        self.log("Testing file system health...")

        critical_paths = [
            'data/',
            'output/',
            'helpers/',
            'api/',
            'atlas_venv/',
        ]

        results = {}
        for path in critical_paths:
            if os.path.exists(path):
                if os.path.isdir(path):
                    file_count = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
                    results[path] = {'status': 'exists', 'files': file_count}
                    self.log(f"  ✅ {path}: {file_count} files")
                else:
                    results[path] = {'status': 'exists', 'type': 'file'}
                    self.log(f"  ✅ {path}: file")
            else:
                results[path] = {'status': 'missing'}
                self.log(f"  ❌ {path}: missing", "ERROR")

        # Check disk space
        import shutil
        total, used, free = shutil.disk_usage('.')
        free_gb = free // (1024**3)
        results['disk_space'] = {'free_gb': free_gb}

        if free_gb < 5:
            self.log(f"  ⚠️ Disk space: {free_gb}GB free (WARNING: <5GB)", "WARN")
        else:
            self.log(f"  ✅ Disk space: {free_gb}GB free")

        self.results['filesystem'] = results
        return results

    def generate_report(self):
        """Generate validation report."""
        elapsed = time.time() - self.start_time

        self.log("=" * 60)
        self.log(f"🎯 QUICK VALIDATION COMPLETE ({elapsed:.1f}s)")
        self.log("=" * 60)

        # Calculate overall health score
        scores = []

        # Database availability (25 points)
        db_results = self.results.get('databases', {})
        available_dbs = sum(1 for db in db_results.values() if db.get('status') == 'available')
        db_score = (available_dbs / len(db_results)) * 25 if db_results else 0
        scores.append(db_score)

        # Content availability (25 points)
        content = self.results.get('content', {})
        content_score = 25 if content.get('total_items', 0) > 1000 else content.get('total_items', 0) / 40
        scores.append(content_score)

        # API endpoints (25 points)
        api_results = self.results.get('api_endpoints', {})
        responding_apis = sum(1 for api in api_results.values() if api.get('status') == 'responding')
        api_score = (responding_apis / len(api_results)) * 25 if api_results else 0
        scores.append(api_score)

        # System health (25 points)
        fs_results = self.results.get('filesystem', {})
        healthy_paths = sum(1 for path in fs_results.values() if isinstance(path, dict) and path.get('status') == 'exists')
        fs_score = (healthy_paths / 5) * 25  # 5 critical paths
        scores.append(fs_score)

        overall_score = sum(scores)

        self.log(f"📊 OVERALL HEALTH SCORE: {overall_score:.1f}/100")
        self.log(f"   Database Health: {db_score:.1f}/25")
        self.log(f"   Content Health: {content_score:.1f}/25")
        self.log(f"   API Health: {api_score:.1f}/25")
        self.log(f"   System Health: {fs_score:.1f}/25")

        if overall_score >= 90:
            self.log("🎉 SYSTEM STATUS: EXCELLENT - Production ready!")
        elif overall_score >= 75:
            self.log("✅ SYSTEM STATUS: GOOD - Minor issues to address")
        elif overall_score >= 50:
            self.log("⚠️ SYSTEM STATUS: FAIR - Several issues need attention")
        else:
            self.log("❌ SYSTEM STATUS: POOR - Major repairs needed")

        # Save results
        report_path = 'quick_validation_report.json'
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'elapsed_seconds': elapsed,
                'overall_score': overall_score,
                'component_scores': {
                    'database': db_score,
                    'content': content_score,
                    'api': api_score,
                    'filesystem': fs_score
                },
                'detailed_results': self.results
            }, f, indent=2)

        self.log(f"📄 Report saved to: {report_path}")
        return overall_score

def main():
    validator = QuickAtlasValidator()

    # Run all tests
    validator.test_database_availability()
    validator.test_content_count()
    validator.test_api_endpoints()
    validator.test_background_processes()
    validator.test_file_system_health()

    # Generate report
    score = validator.generate_report()

    # Exit with appropriate code
    sys.exit(0 if score >= 75 else 1)

if __name__ == "__main__":
    main()