#!/usr/bin/env python3
"""
Task 2.4: Database Performance & Backup Systems Testing

Tests database performance, backup integrity, and restoration procedures
for all Atlas databases including SQLite optimization and backup validation.
"""

import os
import sys
import time
import sqlite3
import shutil
import threading
import concurrent.futures
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DatabasePerformanceBackupTester:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Database files to test
        self.databases = [
            "atlas.db",
            "enhanced_search.db",
            "atlas_search.db",
            "search.db"
        ]

        self.results = {
            'database_performance': {},
            'backup_tests': {},
            'recovery_tests': {},
            'concurrent_access': {}
        }

    def test_database_performance(self):
        """Test database performance for all Atlas databases"""
        print("🚀 Database Performance Testing")
        print("=" * 50)

        for db_name in self.databases:
            db_path = self.project_root / db_name
            if not db_path.exists():
                print(f"⚠️ Database not found: {db_name}")
                continue

            print(f"\n📊 Testing {db_name}")
            print("-" * 30)

            try:
                # Test connection time
                start_time = time.time()
                conn = sqlite3.connect(str(db_path))
                connection_time = (time.time() - start_time) * 1000

                # Get database size
                db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB

                # Test query performance
                cursor = conn.cursor()

                # Get table count
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                table_count = len(tables)

                # Test query performance on largest table
                largest_table = None
                max_rows = 0

                for table in tables:
                    table_name = table[0]
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = cursor.fetchone()[0]
                        if row_count > max_rows:
                            max_rows = row_count
                            largest_table = table_name
                    except Exception:
                        continue

                # Performance tests on largest table
                query_performance = {}
                if largest_table and max_rows > 0:
                    # SELECT performance
                    start_time = time.time()
                    cursor.execute(f"SELECT * FROM {largest_table} LIMIT 100")
                    results = cursor.fetchall()
                    select_time = (time.time() - start_time) * 1000

                    # COUNT performance
                    start_time = time.time()
                    cursor.execute(f"SELECT COUNT(*) FROM {largest_table}")
                    count_result = cursor.fetchone()[0]
                    count_time = (time.time() - start_time) * 1000

                    query_performance = {
                        'select_100_rows': select_time,
                        'count_all_rows': count_time,
                        'total_rows': count_result
                    }

                conn.close()

                # Store results
                self.results['database_performance'][db_name] = {
                    'connection_time_ms': connection_time,
                    'size_mb': db_size,
                    'table_count': table_count,
                    'largest_table': largest_table,
                    'max_rows': max_rows,
                    'query_performance': query_performance,
                    'status': 'healthy'
                }

                print(f"   ✅ Connection: {connection_time:.1f}ms")
                print(f"   📊 Size: {db_size:.1f}MB")
                print(f"   📋 Tables: {table_count}")
                print(f"   🗃️ Largest table: {largest_table} ({max_rows:,} rows)")
                if query_performance:
                    print(f"   ⚡ SELECT 100 rows: {query_performance['select_100_rows']:.1f}ms")
                    print(f"   🔢 COUNT all rows: {query_performance['count_all_rows']:.1f}ms")

            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.results['database_performance'][db_name] = {
                    'error': str(e),
                    'status': 'error'
                }

    def test_backup_systems(self):
        """Test database backup creation and integrity"""
        print("\n💾 Database Backup Testing")
        print("=" * 50)

        for db_name in self.databases:
            db_path = self.project_root / db_name
            if not db_path.exists():
                continue

            print(f"\n📋 Backup test: {db_name}")
            print("-" * 30)

            try:
                # Create backup
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{db_name.replace('.db', '')}_{timestamp}_backup.db"
                backup_path = self.backup_dir / backup_filename

                start_time = time.time()
                shutil.copy2(db_path, backup_path)
                backup_time = (time.time() - start_time) * 1000

                # Verify backup integrity
                original_size = os.path.getsize(db_path)
                backup_size = os.path.getsize(backup_path)

                # Test backup can be opened
                conn = sqlite3.connect(str(backup_path))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                backup_tables = len(cursor.fetchall())
                conn.close()

                # Verify checksums match (simple size check)
                integrity_ok = (original_size == backup_size)

                self.results['backup_tests'][db_name] = {
                    'backup_time_ms': backup_time,
                    'original_size': original_size,
                    'backup_size': backup_size,
                    'integrity_check': integrity_ok,
                    'table_count': backup_tables,
                    'backup_path': str(backup_path),
                    'status': 'success' if integrity_ok else 'integrity_failed'
                }

                print(f"   ✅ Backup created: {backup_time:.1f}ms")
                print(f"   📊 Size match: {integrity_ok}")
                print(f"   📋 Tables: {backup_tables}")
                print(f"   💾 Path: {backup_filename}")

            except Exception as e:
                print(f"   ❌ Backup failed: {e}")
                self.results['backup_tests'][db_name] = {
                    'error': str(e),
                    'status': 'failed'
                }

    def test_recovery_procedures(self):
        """Test database recovery from backup"""
        print("\n🔄 Database Recovery Testing")
        print("=" * 50)

        for db_name, backup_info in self.results['backup_tests'].items():
            if backup_info.get('status') != 'success':
                continue

            print(f"\n🔧 Recovery test: {db_name}")
            print("-" * 30)

            try:
                backup_path = Path(backup_info['backup_path'])

                # Create test recovery location
                recovery_path = self.backup_dir / f"recovery_test_{db_name}"

                # Test recovery
                start_time = time.time()
                shutil.copy2(backup_path, recovery_path)
                recovery_time = (time.time() - start_time) * 1000

                # Verify recovered database works
                conn = sqlite3.connect(str(recovery_path))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                recovered_tables = len(cursor.fetchall())

                # Test a simple query
                if recovered_tables > 0:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                    first_table = cursor.fetchone()[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {first_table}")
                    row_count = cursor.fetchone()[0]
                else:
                    row_count = 0

                conn.close()

                # Cleanup test recovery file
                os.remove(recovery_path)

                self.results['recovery_tests'][db_name] = {
                    'recovery_time_ms': recovery_time,
                    'table_count': recovered_tables,
                    'row_count': row_count,
                    'status': 'success'
                }

                print(f"   ✅ Recovery: {recovery_time:.1f}ms")
                print(f"   📋 Tables: {recovered_tables}")
                print(f"   📊 Sample rows: {row_count:,}")

            except Exception as e:
                print(f"   ❌ Recovery failed: {e}")
                self.results['recovery_tests'][db_name] = {
                    'error': str(e),
                    'status': 'failed'
                }

    def test_concurrent_access(self):
        """Test concurrent database access performance"""
        print("\n🔄 Concurrent Access Testing")
        print("=" * 50)

        # Test with the largest database
        largest_db = None
        largest_size = 0

        for db_name, perf_data in self.results['database_performance'].items():
            if perf_data.get('status') == 'healthy':
                size = perf_data.get('size_mb', 0)
                if size > largest_size:
                    largest_size = size
                    largest_db = db_name

        if not largest_db:
            print("⚠️ No suitable database for concurrent testing")
            return

        print(f"📊 Testing concurrent access: {largest_db}")
        print("-" * 30)

        db_path = self.project_root / largest_db

        def perform_concurrent_query(thread_id):
            try:
                start_time = time.time()
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # Get a table to query
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                table_result = cursor.fetchone()
                if table_result:
                    table_name = table_result[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                else:
                    count = 0

                conn.close()
                end_time = time.time()

                return {
                    'thread_id': thread_id,
                    'time_ms': (end_time - start_time) * 1000,
                    'count': count,
                    'success': True
                }
            except Exception as e:
                return {
                    'thread_id': thread_id,
                    'error': str(e),
                    'success': False
                }

        # Test with 10 concurrent connections
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(perform_concurrent_query, i) for i in range(10)]
            results = [f.result() for f in futures]

        successful_queries = [r for r in results if r['success']]
        failed_queries = [r for r in results if not r['success']]

        if successful_queries:
            avg_time = sum(r['time_ms'] for r in successful_queries) / len(successful_queries)
            max_time = max(r['time_ms'] for r in successful_queries)
            min_time = min(r['time_ms'] for r in successful_queries)
        else:
            avg_time = max_time = min_time = 0

        self.results['concurrent_access'][largest_db] = {
            'successful_queries': len(successful_queries),
            'failed_queries': len(failed_queries),
            'avg_time_ms': avg_time,
            'max_time_ms': max_time,
            'min_time_ms': min_time,
            'total_queries': len(results)
        }

        print(f"   ✅ Successful: {len(successful_queries)}/10")
        print(f"   ❌ Failed: {len(failed_queries)}/10")
        print(f"   ⚡ Average time: {avg_time:.1f}ms")
        print(f"   📊 Range: {min_time:.1f}ms - {max_time:.1f}ms")

    def generate_report(self):
        """Generate comprehensive database performance and backup report"""
        print("\n📊 DATABASE PERFORMANCE & BACKUP REPORT")
        print("=" * 60)

        # Overall status
        total_dbs = len([db for db in self.databases if (self.project_root / db).exists()])
        healthy_dbs = len([db for db, info in self.results['database_performance'].items()
                          if info.get('status') == 'healthy'])
        successful_backups = len([db for db, info in self.results['backup_tests'].items()
                                 if info.get('status') == 'success'])
        successful_recoveries = len([db for db, info in self.results['recovery_tests'].items()
                                   if info.get('status') == 'success'])

        print(f"\n🎯 SUMMARY")
        print(f"   📊 Databases tested: {healthy_dbs}/{total_dbs}")
        print(f"   💾 Backup success: {successful_backups}/{total_dbs}")
        print(f"   🔄 Recovery success: {successful_recoveries}/{successful_backups}")

        # Performance summary
        if self.results['database_performance']:
            total_size = sum(info.get('size_mb', 0) for info in self.results['database_performance'].values())
            total_tables = sum(info.get('table_count', 0) for info in self.results['database_performance'].values())
            total_rows = sum(info.get('max_rows', 0) for info in self.results['database_performance'].values())

            print(f"   📊 Total data: {total_size:.1f}MB, {total_tables} tables, {total_rows:,} rows")

        # Overall assessment
        if healthy_dbs == total_dbs and successful_backups == total_dbs and successful_recoveries >= successful_backups:
            status = "✅ EXCELLENT"
        elif healthy_dbs >= total_dbs * 0.8:
            status = "⚠️ GOOD"
        else:
            status = "❌ NEEDS WORK"

        print(f"\n🎯 Overall Status: {status}")
        print(f"✅ Task 2.4 {'COMPLETED' if status.startswith('✅') else 'NEEDS WORK'}: Database Performance & Backup Systems")

        return status.startswith('✅')

def main():
    """Run comprehensive database performance and backup testing"""
    tester = DatabasePerformanceBackupTester()

    # Run all tests
    tester.test_database_performance()
    tester.test_backup_systems()
    tester.test_recovery_procedures()
    tester.test_concurrent_access()

    # Generate report
    success = tester.generate_report()

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())