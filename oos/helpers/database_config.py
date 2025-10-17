#!/usr/bin/env python3
"""
SQLite database configuration with durability and corruption prevention
"""

import sqlite3
import os
import time
import json
import shutil
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
import hashlib
from queue import Queue, Empty

class DatabasePool:
    """Connection pool for SQLite with WAL mode and durability settings"""

    def __init__(self, db_path: str, max_connections: int = 10, timeout: int = 30):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self.pool = Queue(maxsize=max_connections)
        self.active_connections = set()
        self.lock = threading.Lock()
        self.logger = logging.getLogger('database_pool')

        # Initialize database and create connections
        self._initialize_database()
        self._create_connections()

    def _initialize_database(self):
        """Initialize database with optimal settings"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Create initial connection to set up database
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            self._apply_database_settings(conn)

            # Create basic schema if needed
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_info (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_type TEXT,
                    status TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

        finally:
            conn.close()

    def _apply_database_settings(self, conn: sqlite3.Connection):
        """Apply optimal SQLite settings for durability and performance"""
        settings = [
            # WAL mode for better concurrency
            ("PRAGMA journal_mode=WAL", None),

            # Durability settings
            ("PRAGMA synchronous=NORMAL", None),  # Good balance of safety and performance

            # Performance settings
            ("PRAGMA cache_size=-64000", None),   # 64MB cache
            ("PRAGMA temp_store=MEMORY", None),   # Use memory for temporary tables
            ("PRAGMA mmap_size=134217728", None), # 128MB memory mapping

            # Timeout for locks
            ("PRAGMA busy_timeout=30000", None),  # 30 second timeout

            # Foreign key support
            ("PRAGMA foreign_keys=ON", None),

            # WAL checkpoint settings
            ("PRAGMA wal_autocheckpoint=1000", None),  # Checkpoint every 1000 pages
        ]

        for pragma, expected in settings:
            try:
                result = conn.execute(pragma).fetchone()
                if expected and result and result[0] != expected:
                    self.logger.warning(f"Setting {pragma} returned {result}, expected {expected}")
                else:
                    self.logger.debug(f"Applied setting: {pragma}")
            except Exception as e:
                self.logger.error(f"Failed to apply setting {pragma}: {e}")

    def _create_connections(self):
        """Create initial connection pool"""
        for i in range(self.max_connections):
            try:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=self.timeout,
                    check_same_thread=False,
                    isolation_level=None  # Autocommit mode
                )

                # Apply settings
                self._apply_database_settings(conn)

                # Set row factory for better usability
                conn.row_factory = sqlite3.Row

                self.pool.put(conn)

            except Exception as e:
                self.logger.error(f"Failed to create connection {i}: {e}")

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            # Get connection from pool
            conn = self.pool.get(timeout=self.timeout)

            # Track active connection
            with self.lock:
                self.active_connections.add(conn)

            # Test connection
            conn.execute("SELECT 1").fetchone()

            yield conn

        except Empty:
            raise sqlite3.OperationalError("Connection pool timeout")
        except sqlite3.Error as e:
            if conn:
                # Connection might be corrupted, create new one
                try:
                    conn.close()
                except:
                    pass

                # Create replacement connection
                try:
                    conn = sqlite3.connect(
                        self.db_path,
                        timeout=self.timeout,
                        check_same_thread=False,
                        isolation_level=None
                    )
                    self._apply_database_settings(conn)
                    conn.row_factory = sqlite3.Row
                    yield conn
                except Exception as e2:
                    self.logger.error(f"Failed to create replacement connection: {e2}")
                    raise e
            else:
                raise e
        finally:
            if conn:
                try:
                    # Remove from active connections
                    with self.lock:
                        self.active_connections.discard(conn)

                    # Return to pool
                    self.pool.put(conn, block=False)
                except:
                    # Pool might be full or connection invalid
                    try:
                        conn.close()
                    except:
                        pass

    def close_all(self):
        """Close all connections in pool"""
        with self.lock:
            # Close active connections
            for conn in list(self.active_connections):
                try:
                    conn.close()
                except:
                    pass

            # Close pooled connections
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    conn.close()
                except:
                    pass

    def get_stats(self) -> Dict:
        """Get pool statistics"""
        return {
            'db_path': self.db_path,
            'max_connections': self.max_connections,
            'available_connections': self.pool.qsize(),
            'active_connections': len(self.active_connections),
            'timeout': self.timeout
        }

class DatabaseManager:
    """High-level database management with backup and integrity checking"""

    def __init__(self, db_path: str = "data/oos.db", backup_dir: str = "data/backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.pool = DatabasePool(db_path)
        self.logger = self._setup_logging()

        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)

        # Background tasks
        self.backup_thread = None
        self.integrity_thread = None
        self.shutdown_flag = threading.Event()

        self.logger.info(f"Database manager initialized for {db_path}")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for database manager"""
        logger = logging.getLogger('database_manager')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.FileHandler('data/database.log')
            os.makedirs(os.path.dirname('data/database.log'), exist_ok=True)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def check_integrity(self) -> Dict:
        """Perform database integrity check"""
        start_time = time.time()
        result = {
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'errors': [],
            'warnings': [],
            'duration': 0
        }

        try:
            with self.pool.get_connection() as conn:
                # PRAGMA integrity_check
                self.logger.info("Running integrity check...")

                integrity_result = conn.execute("PRAGMA integrity_check").fetchall()

                if len(integrity_result) == 1 and integrity_result[0][0] == 'ok':
                    result['status'] = 'healthy'
                    self.logger.info("Database integrity check passed")
                else:
                    result['status'] = 'corrupted'
                    result['errors'] = [row[0] for row in integrity_result]
                    self.logger.error(f"Database integrity check failed: {result['errors']}")

                # Additional checks
                try:
                    # Check for WAL mode
                    journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
                    if journal_mode.upper() != 'WAL':
                        result['warnings'].append(f"Journal mode is {journal_mode}, expected WAL")

                    # Check synchronous setting
                    sync_mode = conn.execute("PRAGMA synchronous").fetchone()[0]
                    if sync_mode != 1:  # NORMAL = 1
                        result['warnings'].append(f"Synchronous mode is {sync_mode}, expected 1 (NORMAL)")

                    # Check database size and page count
                    page_count = conn.execute("PRAGMA page_count").fetchone()[0]
                    page_size = conn.execute("PRAGMA page_size").fetchone()[0]
                    db_size = page_count * page_size

                    result['database_info'] = {
                        'page_count': page_count,
                        'page_size': page_size,
                        'size_bytes': db_size,
                        'journal_mode': journal_mode,
                        'synchronous': sync_mode
                    }

                except Exception as e:
                    result['warnings'].append(f"Could not collect database info: {e}")

        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(str(e))
            self.logger.error(f"Integrity check failed: {e}")

        result['duration'] = time.time() - start_time

        # Log result to health_checks table
        self._log_health_check('integrity_check', result['status'], json.dumps(result))

        return result

    def _log_health_check(self, check_type: str, status: str, details: str):
        """Log health check result to database"""
        try:
            with self.pool.get_connection() as conn:
                conn.execute(
                    "INSERT INTO health_checks (check_type, status, details) VALUES (?, ?, ?)",
                    (check_type, status, details)
                )

                # Keep only last 100 health checks
                conn.execute("""
                    DELETE FROM health_checks
                    WHERE id NOT IN (
                        SELECT id FROM health_checks
                        ORDER BY timestamp DESC
                        LIMIT 100
                    )
                """)
        except Exception as e:
            self.logger.error(f"Failed to log health check: {e}")

    def create_backup(self, backup_name: Optional[str] = None) -> Dict:
        """Create database backup"""
        if backup_name is None:
            backup_name = f"oos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

        backup_path = os.path.join(self.backup_dir, backup_name)
        start_time = time.time()

        result = {
            'timestamp': datetime.now().isoformat(),
            'backup_name': backup_name,
            'backup_path': backup_path,
            'success': False,
            'size_bytes': 0,
            'duration': 0,
            'error': None
        }

        try:
            self.logger.info(f"Creating backup: {backup_name}")

            with self.pool.get_connection() as conn:
                # Use SQLite's backup API
                backup_conn = sqlite3.connect(backup_path)
                try:
                    conn.backup(backup_conn)

                    # Verify backup
                    backup_conn.execute("PRAGMA integrity_check").fetchone()

                    result['success'] = True
                    result['size_bytes'] = os.path.getsize(backup_path)

                    self.logger.info(f"Backup created successfully: {backup_path} ({result['size_bytes']} bytes)")

                finally:
                    backup_conn.close()

        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Backup failed: {e}")

            # Clean up failed backup
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
            except:
                pass

        result['duration'] = time.time() - start_time

        # Clean up old backups (keep last 10)
        self._cleanup_old_backups()

        return result

    def _cleanup_old_backups(self):
        """Clean up old backup files"""
        try:
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.startswith('oos_backup_') and file.endswith('.db'):
                    file_path = os.path.join(self.backup_dir, file)
                    mtime = os.path.getmtime(file_path)
                    backups.append((mtime, file_path))

            # Sort by modification time (oldest first)
            backups.sort()

            # Remove oldest backups, keep last 10
            for mtime, file_path in backups[:-10]:
                try:
                    os.remove(file_path)
                    self.logger.debug(f"Removed old backup: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove old backup {file_path}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")

    def restore_from_backup(self, backup_name: str) -> Dict:
        """Restore database from backup"""
        backup_path = os.path.join(self.backup_dir, backup_name)

        result = {
            'timestamp': datetime.now().isoformat(),
            'backup_name': backup_name,
            'success': False,
            'error': None
        }

        if not os.path.exists(backup_path):
            result['error'] = f"Backup file not found: {backup_path}"
            return result

        try:
            self.logger.info(f"Restoring from backup: {backup_name}")

            # Close all connections
            self.pool.close_all()

            # Create backup of current database
            current_backup = f"pre_restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(self.db_path, os.path.join(self.backup_dir, current_backup))

            # Restore from backup
            shutil.copy2(backup_path, self.db_path)

            # Recreate connection pool
            self.pool = DatabasePool(self.db_path)

            # Verify restored database
            integrity_result = self.check_integrity()

            if integrity_result['status'] == 'healthy':
                result['success'] = True
                self.logger.info(f"Database restored successfully from {backup_name}")
            else:
                result['error'] = f"Restored database failed integrity check: {integrity_result['errors']}"
                self.logger.error(result['error'])

        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Restore failed: {e}")

        return result

    def vacuum_database(self, check_fragmentation: bool = True) -> Dict:
        """Vacuum database if fragmentation exceeds threshold"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'vacuum_performed': False,
            'fragmentation_before': 0,
            'fragmentation_after': 0,
            'success': False,
            'error': None,
            'duration': 0
        }

        start_time = time.time()

        try:
            with self.pool.get_connection() as conn:
                if check_fragmentation:
                    # Check fragmentation
                    page_count = conn.execute("PRAGMA page_count").fetchone()[0]
                    freelist_count = conn.execute("PRAGMA freelist_count").fetchone()[0]

                    if page_count > 0:
                        fragmentation = (freelist_count / page_count) * 100
                        result['fragmentation_before'] = fragmentation

                        if fragmentation < 25.0:  # Less than 25% fragmentation
                            self.logger.info(f"Database fragmentation {fragmentation:.1f}% is below threshold, skipping vacuum")
                            result['success'] = True
                            return result

                # Perform vacuum
                self.logger.info("Starting database vacuum...")
                conn.execute("VACUUM")
                result['vacuum_performed'] = True

                # Check fragmentation after vacuum
                if check_fragmentation:
                    page_count = conn.execute("PRAGMA page_count").fetchone()[0]
                    freelist_count = conn.execute("PRAGMA freelist_count").fetchone()[0]

                    if page_count > 0:
                        fragmentation = (freelist_count / page_count) * 100
                        result['fragmentation_after'] = fragmentation

                result['success'] = True
                self.logger.info("Database vacuum completed successfully")

        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Vacuum failed: {e}")

        result['duration'] = time.time() - start_time
        return result

    def start_background_tasks(self):
        """Start background backup and integrity checking"""
        if self.backup_thread is None or not self.backup_thread.is_alive():
            self.backup_thread = threading.Thread(target=self._backup_worker, daemon=True)
            self.backup_thread.start()

        if self.integrity_thread is None or not self.integrity_thread.is_alive():
            self.integrity_thread = threading.Thread(target=self._integrity_worker, daemon=True)
            self.integrity_thread.start()

    def _backup_worker(self):
        """Background worker for periodic backups"""
        backup_interval = 6 * 3600  # 6 hours

        while not self.shutdown_flag.is_set():
            try:
                self.create_backup()

                # Wait for next backup
                if self.shutdown_flag.wait(backup_interval):
                    break

            except Exception as e:
                self.logger.error(f"Background backup failed: {e}")
                # Wait 30 minutes before retrying
                if self.shutdown_flag.wait(1800):
                    break

    def _integrity_worker(self):
        """Background worker for periodic integrity checks"""
        check_interval = 24 * 3600  # 24 hours

        while not self.shutdown_flag.is_set():
            try:
                integrity_result = self.check_integrity()

                if integrity_result['status'] != 'healthy':
                    self.logger.error("Database integrity check failed, attempting recovery...")
                    # Attempt recovery from latest backup
                    backups = self.list_backups()
                    if backups:
                        latest_backup = backups[0]['name']  # Assuming sorted by date
                        restore_result = self.restore_from_backup(latest_backup)
                        if restore_result['success']:
                            self.logger.info(f"Database recovered from backup: {latest_backup}")
                        else:
                            self.logger.error(f"Recovery failed: {restore_result['error']}")

                # Wait for next check
                if self.shutdown_flag.wait(check_interval):
                    break

            except Exception as e:
                self.logger.error(f"Background integrity check failed: {e}")
                # Wait 1 hour before retrying
                if self.shutdown_flag.wait(3600):
                    break

    def list_backups(self) -> List[Dict]:
        """List available backup files"""
        backups = []

        try:
            for file in os.listdir(self.backup_dir):
                if file.startswith('oos_backup_') and file.endswith('.db'):
                    file_path = os.path.join(self.backup_dir, file)
                    stat = os.stat(file_path)

                    backups.append({
                        'name': file,
                        'path': file_path,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })

            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created'], reverse=True)

        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")

        return backups

    def get_status(self) -> Dict:
        """Get database manager status"""
        return {
            'db_path': self.db_path,
            'backup_dir': self.backup_dir,
            'pool_stats': self.pool.get_stats(),
            'backup_count': len(self.list_backups()),
            'background_tasks': {
                'backup_thread_alive': self.backup_thread.is_alive() if self.backup_thread else False,
                'integrity_thread_alive': self.integrity_thread.is_alive() if self.integrity_thread else False
            }
        }

    def shutdown(self):
        """Shutdown database manager"""
        self.logger.info("Shutting down database manager...")

        # Signal background threads to stop
        self.shutdown_flag.set()

        # Wait for threads to finish
        if self.backup_thread and self.backup_thread.is_alive():
            self.backup_thread.join(timeout=30)

        if self.integrity_thread and self.integrity_thread.is_alive():
            self.integrity_thread.join(timeout=30)

        # Close connection pool
        self.pool.close_all()

        self.logger.info("Database manager shutdown complete")

# Global database manager instance
_db_manager = None
_db_manager_lock = threading.Lock()

def get_database_manager(db_path: str = "data/oos.db") -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager

    with _db_manager_lock:
        if _db_manager is None:
            _db_manager = DatabaseManager(db_path)
        return _db_manager

def test_database_integrity():
    """Test database integrity (for validation)"""
    db_manager = get_database_manager()
    result = db_manager.check_integrity()
    print(json.dumps(result, indent=2))
    return result['status'] == 'healthy'

if __name__ == "__main__":
    # CLI interface for testing
    import argparse

    parser = argparse.ArgumentParser(description="Database Configuration Manager")
    parser.add_argument("--db", default="data/oos.db", help="Database path")
    parser.add_argument("--backup", action="store_true", help="Create backup")
    parser.add_argument("--integrity", action="store_true", help="Check integrity")
    parser.add_argument("--vacuum", action="store_true", help="Vacuum database")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--list-backups", action="store_true", help="List backups")

    args = parser.parse_args()

    db_manager = DatabaseManager(args.db)

    try:
        if args.backup:
            result = db_manager.create_backup()
            print(json.dumps(result, indent=2))
        elif args.integrity:
            result = db_manager.check_integrity()
            print(json.dumps(result, indent=2))
        elif args.vacuum:
            result = db_manager.vacuum_database()
            print(json.dumps(result, indent=2))
        elif args.list_backups:
            backups = db_manager.list_backups()
            print(json.dumps(backups, indent=2))
        elif args.status:
            status = db_manager.get_status()
            print(json.dumps(status, indent=2))
        else:
            print("Use --help for usage information")
    finally:
        db_manager.shutdown()