#!/usr/bin/env python3
"""
Test script for database connection pool
"""

import sys
import time
import threading
import json
from pathlib import Path

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.database_config import DatabaseManager, DatabasePool

def test_basic_connection():
    """Test basic database connection and settings"""
    print("Testing basic database connection...")

    db_manager = DatabaseManager("data/test_oos.db")

    try:
        # Test connection
        with db_manager.pool.get_connection() as conn:
            # Check WAL mode
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            print(f"  ✓ Journal mode: {journal_mode}")

            # Check synchronous setting
            sync_mode = conn.execute("PRAGMA synchronous").fetchone()[0]
            print(f"  ✓ Synchronous mode: {sync_mode}")

            # Check cache size
            cache_size = conn.execute("PRAGMA cache_size").fetchone()[0]
            print(f"  ✓ Cache size: {cache_size}")

            # Check busy timeout
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            print(f"  ✓ Busy timeout: {busy_timeout}ms")

            # Test basic operations
            conn.execute("INSERT OR REPLACE INTO system_info (key, value) VALUES (?, ?)",
                        ("test_key", "test_value"))

            result = conn.execute("SELECT value FROM system_info WHERE key = ?",
                                ("test_key",)).fetchone()

            if result and result[0] == "test_value":
                print("  ✓ Basic database operations working")
            else:
                print("  ✗ Basic database operations failed")

    finally:
        db_manager.shutdown()

def test_connection_pool():
    """Test connection pool functionality"""
    print("\nTesting connection pool...")

    db_manager = DatabaseManager("data/test_oos.db")

    try:
        # Test pool stats
        stats = db_manager.pool.get_stats()
        print(f"  ✓ Pool created with {stats['max_connections']} max connections")
        print(f"  ✓ Available connections: {stats['available_connections']}")

        # Test multiple concurrent connections
        def worker(worker_id):
            try:
                with db_manager.pool.get_connection() as conn:
                    # Simulate some work
                    conn.execute("INSERT INTO health_checks (check_type, status, details) VALUES (?, ?, ?)",
                               (f"pool_test_{worker_id}", "success", f"Worker {worker_id} test"))
                    time.sleep(0.1)  # Simulate work

                    # Query data
                    count = conn.execute("SELECT COUNT(*) FROM health_checks").fetchone()[0]
                    print(f"    Worker {worker_id}: {count} health checks in database")

            except Exception as e:
                print(f"    Worker {worker_id} failed: {e}")

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check final stats
        final_stats = db_manager.pool.get_stats()
        print(f"  ✓ Final available connections: {final_stats['available_connections']}")
        print(f"  ✓ Active connections: {final_stats['active_connections']}")

    finally:
        db_manager.shutdown()

def test_integrity_check():
    """Test database integrity checking"""
    print("\nTesting integrity check...")

    db_manager = DatabaseManager("data/test_oos.db")

    try:
        result = db_manager.check_integrity()

        print(f"  Integrity status: {result['status']}")
        print(f"  Check duration: {result['duration']:.3f}s")

        if result['status'] == 'healthy':
            print("  ✓ Database integrity check passed")
        else:
            print("  ✗ Database integrity check failed")
            if result['errors']:
                for error in result['errors']:
                    print(f"    Error: {error}")

        if result['warnings']:
            for warning in result['warnings']:
                print(f"    Warning: {warning}")

        if 'database_info' in result:
            info = result['database_info']
            print(f"  Database info:")
            print(f"    Pages: {info['page_count']}")
            print(f"    Page size: {info['page_size']} bytes")
            print(f"    Total size: {info['size_bytes']} bytes")

    finally:
        db_manager.shutdown()

def test_backup_system():
    """Test backup creation and restoration"""
    print("\nTesting backup system...")

    db_manager = DatabaseManager("data/test_oos.db")

    try:
        # Create some test data
        with db_manager.pool.get_connection() as conn:
            conn.execute("INSERT INTO system_info (key, value) VALUES (?, ?)",
                        ("backup_test", "original_value"))

        # Create backup
        print("  Creating backup...")
        backup_result = db_manager.create_backup("test_backup.db")

        if backup_result['success']:
            print(f"  ✓ Backup created: {backup_result['backup_name']}")
            print(f"  ✓ Backup size: {backup_result['size_bytes']} bytes")
        else:
            print(f"  ✗ Backup failed: {backup_result['error']}")
            return

        # Modify data
        with db_manager.pool.get_connection() as conn:
            conn.execute("UPDATE system_info SET value = ? WHERE key = ?",
                        ("modified_value", "backup_test"))

        # Verify modification
        with db_manager.pool.get_connection() as conn:
            result = conn.execute("SELECT value FROM system_info WHERE key = ?",
                                ("backup_test",)).fetchone()
            if result[0] == "modified_value":
                print("  ✓ Data modified successfully")

        # Restore from backup
        print("  Restoring from backup...")
        restore_result = db_manager.restore_from_backup("test_backup.db")

        if restore_result['success']:
            print("  ✓ Restore completed successfully")

            # Verify restoration
            with db_manager.pool.get_connection() as conn:
                result = conn.execute("SELECT value FROM system_info WHERE key = ?",
                                    ("backup_test",)).fetchone()
                if result and result[0] == "original_value":
                    print("  ✓ Data restored correctly")
                else:
                    print(f"  ✗ Data not restored correctly: {result}")
        else:
            print(f"  ✗ Restore failed: {restore_result['error']}")

    finally:
        db_manager.shutdown()

def test_vacuum():
    """Test database vacuum functionality"""
    print("\nTesting vacuum functionality...")

    db_manager = DatabaseManager("data/test_oos.db")

    try:
        # Create some data to test vacuum
        with db_manager.pool.get_connection() as conn:
            # Insert and delete data to create fragmentation
            for i in range(100):
                conn.execute("INSERT INTO health_checks (check_type, status, details) VALUES (?, ?, ?)",
                           (f"vacuum_test_{i}", "success", f"Test data {i}"))

            # Delete half the data
            conn.execute("DELETE FROM health_checks WHERE check_type LIKE 'vacuum_test_%' AND CAST(SUBSTR(check_type, 13) AS INTEGER) % 2 = 0")

        # Vacuum database
        vacuum_result = db_manager.vacuum_database()

        if vacuum_result['success']:
            if vacuum_result['vacuum_performed']:
                print(f"  ✓ Vacuum completed in {vacuum_result['duration']:.3f}s")
                if 'fragmentation_before' in vacuum_result:
                    print(f"  Fragmentation before: {vacuum_result['fragmentation_before']:.1f}%")
                if 'fragmentation_after' in vacuum_result:
                    print(f"  Fragmentation after: {vacuum_result['fragmentation_after']:.1f}%")
            else:
                print("  ✓ Vacuum skipped (fragmentation below threshold)")
        else:
            print(f"  ✗ Vacuum failed: {vacuum_result['error']}")

    finally:
        db_manager.shutdown()

def test_performance():
    """Test database performance"""
    print("\nTesting database performance...")

    db_manager = DatabaseManager("data/test_oos.db")

    try:
        # Test insert performance
        start_time = time.time()

        with db_manager.pool.get_connection() as conn:
            for i in range(1000):
                conn.execute("INSERT INTO health_checks (check_type, status, details) VALUES (?, ?, ?)",
                           (f"perf_test_{i}", "success", f"Performance test {i}"))

        insert_time = time.time() - start_time
        print(f"  Insert performance: 1000 records in {insert_time:.3f}s ({1000/insert_time:.0f} records/sec)")

        # Test query performance
        start_time = time.time()

        with db_manager.pool.get_connection() as conn:
            for i in range(100):
                result = conn.execute("SELECT COUNT(*) FROM health_checks WHERE check_type LIKE 'perf_test_%'").fetchone()

        query_time = time.time() - start_time
        print(f"  Query performance: 100 queries in {query_time:.3f}s ({100/query_time:.0f} queries/sec)")

    finally:
        db_manager.shutdown()

def run_all_tests():
    """Run all database tests"""
    print("Database Pool Test Suite")
    print("=" * 50)

    try:
        test_basic_connection()
        test_connection_pool()
        test_integrity_check()
        test_backup_system()
        test_vacuum()
        test_performance()

        print("\n🎉 All database tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database Pool Tests")
    parser.add_argument("--test", choices=["basic", "pool", "integrity", "backup", "vacuum", "performance", "all"],
                       default="all", help="Which test to run")

    args = parser.parse_args()

    if args.test == "all":
        run_all_tests()
    elif args.test == "basic":
        test_basic_connection()
    elif args.test == "pool":
        test_connection_pool()
    elif args.test == "integrity":
        test_integrity_check()
    elif args.test == "backup":
        test_backup_system()
    elif args.test == "vacuum":
        test_vacuum()
    elif args.test == "performance":
        test_performance()