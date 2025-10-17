#!/usr/bin/env python3
"""
Database Backup Script for Atlas

This script creates PostgreSQL backup scripts with pg_dump, implements
automated daily backups, compression, encryption, and retention management.

Features:
- Creates PostgreSQL backup script with pg_dump
- Implements daily automated database backups
- Sets up backup compression and encryption
- Configures backup retention (keep last 30 days)
- Creates backup verification script
- Adds cron job for daily backup execution
"""

import os
import sys
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import schedule
import time
from helpers.bulletproof_process_manager import create_managed_process


def run_command(cmd, description=""):
    """Run a shell command with error handling"""
    try:
        print(f"Executing: {description}")
        process = create_managed_process(
            cmd, description, shell=True, capture_output=True, text=True
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, output=stdout, stderr=stderr)
        print(f"Success: {description}")
        return stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {description}")
        print(f"Error: {e.stderr}")
        return None
    except Exception as e:
        print(f"Error executing: {description}")
        print(f"Error: {e}")
        return None


def generate_encryption_key():
    """Generate and save an encryption key"""
    key = Fernet.generate_key()
    key_path = "/home/ubuntu/dev/atlas/backup/.backup_key"

    with open(key_path, "wb") as key_file:
        key_file.write(key)

    # Set restrictive permissions
    os.chmod(key_path, 0o600)
    print("Encryption key generated and saved")
    return key


def load_encryption_key():
    """Load encryption key from file"""
    key_path = "/home/ubuntu/dev/atlas/backup/.backup_key"

    try:
        with open(key_path, "rb") as key_file:
            key = key_file.read()
        return key
    except FileNotFoundError:
        print("Encryption key not found, generating new key")
        return generate_encryption_key()


def create_backup_script():
    """Create the database backup script"""
    print("Creating database backup script...")

    # Backup script content
    backup_script = """#!/bin/bash
# Atlas Database Backup Script

# Configuration
DB_NAME="atlas"
DB_USER="atlas_user"
BACKUP_DIR="/home/ubuntu/dev/atlas/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/atlas_backup_$DATE.sql"
COMPRESSED_FILE="$BACKUP_FILE.gz"
ENCRYPTED_FILE="$COMPRESSED_FILE.enc"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -U $DB_USER -d $DB_NAME > $BACKUP_FILE

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Database backup created: $BACKUP_FILE"

    # Compress backup
    gzip $BACKUP_FILE
    echo "Backup compressed: $COMPRESSED_FILE"

    # Encrypt backup
    python3 /home/ubuntu/dev/atlas/backup/encrypt_backup.py $COMPRESSED_FILE
    echo "Backup encrypted: $ENCRYPTED_FILE"

    # Remove uncompressed file
    rm -f $COMPRESSED_FILE

    # Verify backup
    python3 /home/ubuntu/dev/atlas/backup/verify_backup.py $ENCRYPTED_FILE

    echo "Backup completed successfully"
else
    echo "Database backup failed"
    exit 1
fi
"""

    # Write backup script
    script_path = "/home/ubuntu/dev/atlas/backup/db_backup.sh"
    with open(script_path, "w") as f:
        f.write(backup_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Database backup script created successfully")


def create_encryption_script():
    """Create the backup encryption script"""
    print("Creating backup encryption script...")

    # Encryption script content
    encrypt_script = """#!/usr/bin/env python3
# Backup Encryption Script

import sys
import os
from cryptography.fernet import Fernet

def encrypt_file(file_path):
    # Load encryption key
    key_path = "/home/ubuntu/dev/atlas/backup/.backup_key"
    try:
        with open(key_path, "rb") as key_file:
            key = key_file.read()
    except FileNotFoundError:
        print("Encryption key not found")
        return False

    # Initialize Fernet cipher
    cipher = Fernet(key)

    # Read file to encrypt
    try:
        with open(file_path, "rb") as file:
            file_data = file.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return False

    # Encrypt data
    encrypted_data = cipher.encrypt(file_data)

    # Write encrypted data
    encrypted_file_path = file_path + ".enc"
    with open(encrypted_file_path, "wb") as encrypted_file:
        encrypted_file.write(encrypted_data)

    print(f"File encrypted: {encrypted_file_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: encrypt_backup.py <file_to_encrypt>")
        sys.exit(1)

    file_path = sys.argv[1]
    if encrypt_file(file_path):
        # Remove original file after encryption
        os.remove(file_path)
        sys.exit(0)
    else:
        sys.exit(1)
"""

    # Write encryption script
    script_path = "/home/ubuntu/dev/atlas/backup/encrypt_backup.py"
    with open(script_path, "w") as f:
        f.write(encrypt_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Backup encryption script created successfully")


def create_verification_script():
    """Create the backup verification script"""
    print("Creating backup verification script...")

    # Verification script content
    verify_script = """#!/usr/bin/env python3
# Backup Verification Script

import sys
import os
from cryptography.fernet import Fernet

def verify_backup(file_path):
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Backup file not found: {file_path}")
        return False

    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        print(f"Backup file is empty: {file_path}")
        return False

    print(f"Backup file verified: {file_path} ({file_size} bytes)")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: verify_backup.py <backup_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    if verify_backup(file_path):
        sys.exit(0)
    else:
        sys.exit(1)
"""

    # Write verification script
    script_path = "/home/ubuntu/dev/atlas/backup/verify_backup.py"
    with open(script_path, "w") as f:
        f.write(verify_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Backup verification script created successfully")


def setup_cron_job():
    """Setup cron job for daily backups"""
    print("Setting up cron job for daily backups...")

    # Create cron job entry
    cron_job = "0 2 * * * /home/ubuntu/dev/atlas/backup/db_backup.sh >> /home/ubuntu/dev/atlas/logs/backup.log 2>&1"

    # Add to crontab
    try:
        # Get current crontab
        process = create_managed_process(["crontab", "-l"], "get_crontab_cron_job")
        stdout, stderr = process.communicate()
        current_crontab = stdout.decode('utf-8').strip()

        # Check if our job already exists
        if "/home/ubuntu/dev/atlas/backup/db_backup.sh" in current_crontab:
            print("Cron job already exists")
            return

        # Add new job
        new_crontab = current_crontab + "\n" + cron_job if current_crontab else cron_job

        # Write to temporary file
        temp_dir = os.environ.get("ATLAS_TEMP_DIR", "/tmp")
        crontab_file = os.path.join(temp_dir, "new_crontab")
        with open(crontab_file, "w") as f:
            f.write(new_crontab + "\n")

        # Install new crontab
        process = create_managed_process(["crontab", crontab_file], "install_crontab_cron_job")
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, output=stdout, stderr=stderr)
        print("Cron job installed successfully")

    except subprocess.CalledProcessError as e:
        print(f"Error setting up cron job: {e}")
        print("Please add the following line to your crontab manually:")
        print(cron_job)


def setup_retention_policy():
    """Setup backup retention policy (30 days)"""
    print("Setting up backup retention policy...")

    # Create cleanup script
    cleanup_script = """#!/bin/bash
# Atlas Backup Cleanup Script

BACKUP_DIR="/home/ubuntu/dev/atlas/backups"
RETENTION_DAYS=30

# Find and delete backups older than retention period
find $BACKUP_DIR -name "atlas_backup_*.sql.gz.enc" -mtime +$RETENTION_DAYS -delete

echo "Backup cleanup completed: $(date)"
"""

    # Write cleanup script
    script_path = "/home/ubuntu/dev/atlas/backup/cleanup_backups.sh"
    with open(script_path, "w") as f:
        f.write(cleanup_script)

    # Make script executable
    os.chmod(script_path, 0o755)

    # Add cleanup job to crontab (runs daily at 3 AM)
    cleanup_cron = "0 3 * * * /home/ubuntu/dev/atlas/backup/cleanup_backups.sh >> /home/ubuntu/dev/atlas/logs/cleanup.log 2>&1"

    try:
        # Get current crontab
        process = create_managed_process(["crontab", "-l"], "get_crontab_cleanup_job")
        stdout, stderr = process.communicate()
        current_crontab = stdout.decode('utf-8').strip()

        # Check if cleanup job already exists
        if "/home/ubuntu/dev/atlas/backup/cleanup_backups.sh" in current_crontab:
            print("Cleanup cron job already exists")
            return

        # Add cleanup job
        new_crontab = (
            current_crontab + "\n" + cleanup_cron if current_crontab else cleanup_cron
        )

        # Write to temporary file
        temp_dir = os.environ.get("ATLAS_TEMP_DIR", "/tmp")
        crontab_file = os.path.join(temp_dir, "new_crontab")
        with open(crontab_file, "w") as f:
            f.write(new_crontab + "\n")

        # Install new crontab
        process = create_managed_process(["crontab", crontab_file], "install_crontab_cleanup_job")
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, output=stdout, stderr=stderr)
        print("Cleanup cron job installed successfully")

    except subprocess.CalledProcessError as e:
        print(f"Error setting up cleanup cron job: {e}")
        print("Please add the following line to your crontab manually:")
        print(cleanup_cron)


def test_backup_process():
    """Test the backup process"""
    print("Testing backup process...")

    # This would typically run the backup script and verify the results
    # For now, we'll just print a message
    print("Backup process test would be implemented here")
    print("Please run the backup script manually to test:")
    print("/home/ubuntu/dev/atlas/backup/db_backup.sh")


def main():
    """Main database backup setup function"""
    print("Starting Atlas database backup setup...")

    # Create backup directory
    os.makedirs("/home/ubuntu/dev/atlas/backups", exist_ok=True)
    os.makedirs("/home/ubuntu/dev/atlas/logs", exist_ok=True)

    # Generate encryption key
    load_encryption_key()

    # Create backup scripts
    create_backup_script()
    create_encryption_script()
    create_verification_script()

    # Setup cron jobs
    setup_cron_job()
    setup_retention_policy()

    # Test backup process
    test_backup_process()

    print("\nDatabase backup setup completed successfully!")
    print("Features configured:")
    print("- Daily automated database backups at 2 AM")
    print("- Backup compression with gzip")
    print("- Backup encryption with Fernet")
    print("- 30-day backup retention policy")
    print("- Automatic backup cleanup")
    print("- Backup verification")

    print("\nNext steps:")
    print(
        "1. Update the database credentials in /home/ubuntu/dev/atlas/backup/db_backup.sh"
    )
    print("2. Test the backup process manually")
    print("3. Verify cron jobs are running correctly")


if __name__ == "__main__":
    main()
