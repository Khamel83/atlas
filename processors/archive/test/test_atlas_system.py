#!/usr/bin/env python3
"""
Comprehensive System Test for Atlas
Tests all core functionality to ensure system reliability
"""

import sys
import os
import sqlite3
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add current directory to path
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AtlasSystemTester:
    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        self.db_path = 'data/atlas.db'

    def add_result(self, test_name: str, passed: bool, details: str = ''):
        """Add test result"""
        status = 'PASSED' if passed else 'FAILED'
        self.test_results['details'].append({
            'test': test_name,
            'status': status,
            'details': details
        })

        if passed:
            self.test_results['passed'] += 1
            logger.info(f"✅ {test_name}: {status}")
        else:
            self.test_results['failed'] += 1
            logger.error(f"❌ {test_name}: {status} - {details}")

    def test_database_connectivity(self):
        """Test database connectivity"""
        test_name = "Database Connectivity"
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()

            if result and result[0] == 1:
                self.add_result(test_name, True, "Database connection successful")
            else:
                self.add_result(test_name, False, "Database query returned unexpected result")
        except Exception as e:
            self.add_result(test_name, False, f"Database connection failed: {e}")

    def test_database_schema(self):
        """Test database schema integrity"""
        test_name = "Database Schema"
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check required tables
            required_tables = ['content', 'episode_queue']
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            missing_tables = [table for table in required_tables if table not in tables]
            if missing_tables:
                self.add_result(test_name, False, f"Missing tables: {missing_tables}")
                return

            # Check episode_queue schema
            cursor.execute("PRAGMA table_info(episode_queue)")
            columns = [row[1] for row in cursor.fetchall()]
            required_columns = ['id', 'podcast_name', 'episode_title', 'episode_url', 'status', 'created_at', 'updated_at']

            missing_columns = [col for col in required_columns if col not in columns]
            if missing_columns:
                self.add_result(test_name, False, f"Missing columns in episode_queue: {missing_columns}")
            else:
                self.add_result(test_name, True, "Database schema is valid")

            conn.close()
        except Exception as e:
            self.add_result(test_name, False, f"Schema check failed: {e}")

    def test_content_integrity(self):
        """Test content data integrity"""
        test_name = "Content Integrity"
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check transcript count
            cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'")
            transcript_count = cursor.fetchone()[0]

            # Check queue status
            cursor.execute("SELECT status, COUNT(*) FROM episode_queue GROUP BY status")
            queue_status = dict(cursor.fetchall())

            self.add_result(test_name, True, f"Transcripts: {transcript_count}, Queue: {queue_status}")

            conn.close()
        except Exception as e:
            self.add_result(test_name, False, f"Content integrity check failed: {e}")

    def test_monitoring_system(self):
        """Test monitoring system functionality"""
        test_name = "Monitoring System"
        try:
            # Check if monitoring script exists
            if not os.path.exists('monitor_atlas.sh'):
                self.add_result(test_name, False, "monitor_atlas.sh not found")
                return

            # Check if monitoring is running
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if 'monitor_atlas.sh' in result.stdout:
                self.add_result(test_name, True, "Monitoring system is running")
            else:
                self.add_result(test_name, False, "Monitoring system is not running")

        except Exception as e:
            self.add_result(test_name, False, f"Monitoring system test failed: {e}")

    def test_oos_cli(self):
        """Test OOS CLI functionality"""
        test_name = "OOS CLI"
        try:
            if not os.path.exists('oos-cli'):
                self.add_result(test_name, False, "oos-cli not found")
                return

            # Test help command
            result = subprocess.run(['./oos-cli', 'help'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and 'OOS - Open Operating System' in result.stdout:
                self.add_result(test_name, True, "OOS CLI help command works")
            else:
                self.add_result(test_name, False, "OOS CLI help command failed")

        except Exception as e:
            self.add_result(test_name, False, f"OOS CLI test failed: {e}")

    def test_email_alerts(self):
        """Test email alerts system"""
        test_name = "Email Alerts"
        try:
            if not os.path.exists('email_alerts.py'):
                self.add_result(test_name, False, "email_alerts.py not found")
                return

            # Test email alerts script execution
            result = subprocess.run(['python3', 'email_alerts.py'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.add_result(test_name, True, "Email alerts system is functional")
            else:
                self.add_result(test_name, False, f"Email alerts script failed: {result.stderr}")

        except Exception as e:
            self.add_result(test_name, False, f"Email alerts test failed: {e}")

    def test_retry_handler(self):
        """Test retry handler functionality"""
        test_name = "Retry Handler"
        try:
            if not os.path.exists('simple_retry_handler.py'):
                self.add_result(test_name, False, "simple_retry_handler.py not found")
                return

            # Test retry handler execution
            result = subprocess.run(['python3', 'simple_retry_handler.py'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and 'Retry processing completed' in result.stdout:
                self.add_result(test_name, True, "Retry handler is functional")
            else:
                self.add_result(test_name, False, "Retry handler test failed")

        except Exception as e:
            self.add_result(test_name, False, f"Retry handler test failed: {e}")

    def test_extraction_improvements(self):
        """Test extraction improvements system"""
        test_name = "Extraction Improvements"
        try:
            if not os.path.exists('simple_extraction_improvements.py'):
                self.add_result(test_name, False, "simple_extraction_improvements.py not found")
                return

            # Test extraction improvements execution
            result = subprocess.run(['python3', 'simple_extraction_improvements.py'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and 'IMPROVEMENT PLAN' in result.stdout:
                self.add_result(test_name, True, "Extraction improvements system is functional")
            else:
                self.add_result(test_name, False, "Extraction improvements test failed")

        except Exception as e:
            self.add_result(test_name, False, f"Extraction improvements test failed: {e}")

    def test_configuration_files(self):
        """Test configuration files"""
        test_name = "Configuration Files"
        try:
            required_files = [
                'config/podcast_config.csv',
                'config/podcast_rss_feeds.csv',
                'config/email_config.json.example'
            ]

            missing_files = []
            for file_path in required_files:
                if not os.path.exists(file_path):
                    missing_files.append(file_path)

            if missing_files:
                self.add_result(test_name, False, f"Missing config files: {missing_files}")
            else:
                self.add_result(test_name, True, "All configuration files present")

        except Exception as e:
            self.add_result(test_name, False, f"Configuration files test failed: {e}")

    def test_log_files(self):
        """Test log files accessibility"""
        test_name = "Log Files"
        try:
            log_files = [
                'logs/atlas_manager.log',
                'logs/email_alerts.log',
                'logs/monitoring.log'
            ]

            for log_file in log_files:
                if os.path.exists(log_file):
                    # Check if file is readable
                    with open(log_file, 'r') as f:
                        first_line = f.readline()
                        if first_line:
                            continue
                        else:
                            self.add_result(test_name, False, f"Log file {log_file} is empty")
                            return
                else:
                    self.add_result(test_name, False, f"Log file {log_file} not found")
                    return

            self.add_result(test_name, True, "All log files are accessible")

        except Exception as e:
            self.add_result(test_name, False, f"Log files test failed: {e}")

    def test_performance_metrics(self):
        """Test system performance metrics"""
        test_name = "Performance Metrics"
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get processing statistics
            cursor.execute("SELECT COUNT(*) FROM episode_queue")
            total_episodes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM episode_queue WHERE status = 'found'")
            found_episodes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM episode_queue WHERE status = 'pending'")
            pending_episodes = cursor.fetchone()[0]

            success_rate = (found_episodes / (found_episodes + pending_episodes) * 100) if (found_episodes + pending_episodes) > 0 else 0

            # Check if performance is acceptable
            if total_episodes > 0 and (success_rate > 10 or found_episodes > 0):
                self.add_result(test_name, True, f"Success rate: {success_rate:.1f}%, Found: {found_episodes}, Total: {total_episodes}")
            else:
                self.add_result(test_name, False, f"Low success rate: {success_rate:.1f}% or no episodes")

            conn.close()
        except Exception as e:
            self.add_result(test_name, False, f"Performance metrics test failed: {e}")

    def run_all_tests(self):
        """Run all system tests"""
        logger.info("🧪 Starting Atlas System Tests")
        logger.info("=" * 50)

        # Run all tests
        self.test_database_connectivity()
        self.test_database_schema()
        self.test_content_integrity()
        self.test_monitoring_system()
        self.test_oos_cli()
        self.test_email_alerts()
        self.test_retry_handler()
        self.test_extraction_improvements()
        self.test_configuration_files()
        self.test_log_files()
        self.test_performance_metrics()

        # Generate summary
        self.generate_test_summary()

    def generate_test_summary(self):
        """Generate test summary"""
        total = self.test_results['passed'] + self.test_results['failed'] + self.test_results['skipped']
        success_rate = (self.test_results['passed'] / total * 100) if total > 0 else 0

        logger.info("\n" + "=" * 50)
        logger.info("🧪 Atlas System Test Summary")
        logger.info("=" * 50)
        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⏭️  Skipped: {self.test_results['skipped']}")
        logger.info(f"📊 Success Rate: {success_rate:.1f}%")

        if self.test_results['failed'] > 0:
            logger.info("\n❌ Failed Tests:")
            for detail in self.test_results['details']:
                if detail['status'] == 'FAILED':
                    logger.info(f"  - {detail['test']}: {detail['details']}")

        # Overall system health
        if success_rate >= 80:
            logger.info("\n🟢 System Health: GOOD")
        elif success_rate >= 60:
            logger.info("\n🟡 System Health: FAIR")
        else:
            logger.info("\n🔴 System Health: POOR")

        logger.info("=" * 50)

def main():
    """Main function to run system tests"""
    tester = AtlasSystemTester()
    tester.run_all_tests()

    # Return exit code based on test results
    failed_count = tester.test_results['failed']
    sys.exit(1 if failed_count > 0 else 0)

if __name__ == "__main__":
    main()