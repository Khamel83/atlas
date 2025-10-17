#!/usr/bin/env python3
"""
Local Machine Backup Sync for Atlas

This script creates rsync scripts for syncing critical data to a personal machine,
sets up SSH key authentication, configures selective backup, implements scheduling,
and adds monitoring with email alerts.

Features:
- Creates rsync script for critical data to personal machine
- Sets up SSH key authentication for secure backup transfer
- Configures selective backup (database dumps + critical configs)
- Implements backup scheduling (weekly to personal machine)
- Creates local backup verification and cleanup
- Adds backup monitoring and email alerts
"""

import os
import sys
import subprocess
import secrets
from datetime import datetime
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


def generate_ssh_key():
    """Generate SSH key pair for backup transfers"""
    print("Generating SSH key pair for backup transfers...")

    # Create .ssh directory if it doesn't exist
    ssh_dir = os.path.expanduser("~/.ssh")
    os.makedirs(ssh_dir, exist_ok=True)

    # Generate SSH key pair
    key_path = os.path.join(ssh_dir, "atlas_backup")
    cmd = f"ssh-keygen -t rsa -b 4096 -f {key_path} -N '' -C 'atlas_backup@$(hostname)'"
    result = run_command(cmd, "Generating SSH key pair")

    if result:
        print("SSH key pair generated successfully")
        print(f"Public key: {key_path}.pub")
        print(f"Private key: {key_path}")
        print("\nPlease copy the public key to your personal machine:")
        print(f"ssh-copy-id -i {key_path}.pub user@personal-machine")
        return True
    else:
        print("Failed to generate SSH key pair")
        return False


def create_rsync_script():
    """Create rsync script for backup sync"""
    print("Creating rsync backup script...")

    # Get configuration from environment variables
    remote_user = os.environ.get("BACKUP_REMOTE_USER", "backup")
    remote_host = os.environ.get("BACKUP_REMOTE_HOST", "personal-machine")
    remote_path = os.environ.get("BACKUP_REMOTE_PATH", "/backup/atlas")

    # Rsync script content
    rsync_script = f"""#!/bin/bash
# Atlas Local Machine Backup Sync

# Configuration
REMOTE_USER="{remote_user}"
REMOTE_HOST="{remote_host}"
REMOTE_PATH="{remote_path}"
LOCAL_BACKUP_DIR="/home/ubuntu/dev/atlas/backups"
LOCAL_CONFIG_DIR="/home/ubuntu/dev/atlas/config"
LOG_FILE="/home/ubuntu/dev/atlas/logs/local_sync.log"

# Function to log messages
log_message() {{
    echo "$(date): $1" >> $LOG_FILE
}}

# Create log directory if it doesn't exist
mkdir -p "$(dirname $LOG_FILE)"

log_message "Starting local backup sync"

# Create temporary directory for sync
TEMP_DIR="/tmp/atlas_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEMP_DIR"

# Copy database backups
if [ -d "$LOCAL_BACKUP_DIR" ]; then
    cp -r "$LOCAL_BACKUP_DIR" "$TEMP_DIR/" 2>/dev/null
    log_message "Copied database backups"
else
    log_message "WARNING: Local backup directory not found: $LOCAL_BACKUP_DIR"
fi

# Copy critical configuration files
if [ -d "$LOCAL_CONFIG_DIR" ]; then
    cp -r "$LOCAL_CONFIG_DIR" "$TEMP_DIR/" 2>/dev/null
    log_message "Copied configuration files"
else
    log_message "WARNING: Local config directory not found: $LOCAL_CONFIG_DIR"
fi

# Create a backup info file
BACKUP_INFO="$TEMP_DIR/backup_info.txt"
cat > "$BACKUP_INFO" << EOF
Atlas Backup Information
========================

Backup Date: $(date)
Hostname: $(hostname)
Backup Contents:
- Database backups from: $LOCAL_BACKUP_DIR
- Configuration files from: $LOCAL_CONFIG_DIR

This backup was created for sync to personal machine.
EOF

log_message "Created backup info file"

# Sync to remote machine using rsync
log_message "Syncing to remote machine: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"
rsync -avz -e "ssh -i ~/.ssh/atlas_backup" "$TEMP_DIR/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/latest/" >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    log_message "Backup sync completed successfully"

    # Create timestamped backup directory
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ssh -i ~/.ssh/atlas_backup "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_PATH/$TIMESTAMP && cp -r $REMOTE_PATH/latest/* $REMOTE_PATH/$TIMESTAMP/" >> $LOG_FILE 2>&1

    if [ $? -eq 0 ]; then
        log_message "Timestamped backup created: $TIMESTAMP"
    else
        log_message "WARNING: Failed to create timestamped backup"
    fi

    # Send success email notification
    python3 /home/ubuntu/dev/atlas/backup/send_local_notification.py "SUCCESS" "Local backup sync completed successfully"
else
    log_message "ERROR: Backup sync failed"

    # Send failure email notification
    python3 /home/ubuntu/dev/atlas/backup/send_local_notification.py "FAILURE" "Local backup sync failed"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Clean up temporary directory
rm -rf "$TEMP_DIR"
log_message "Cleaned up temporary directory"

# Verify remote backup
ssh -i ~/.ssh/atlas_backup "$REMOTE_USER@$REMOTE_HOST" "test -d $REMOTE_PATH/latest && echo 'Remote backup verified'" >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    log_message "Remote backup verified"
else
    log_message "WARNING: Failed to verify remote backup"
fi

log_message "Local backup sync completed"
"""

    # Write rsync script
    script_path = "/home/ubuntu/dev/atlas/backup/local_sync.sh"
    with open(script_path, "w") as f:
        f.write(rsync_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Rsync backup script created successfully")


def create_notification_script():
    """Create script to send local backup email notifications"""
    print("Creating local backup email notification script...")

    # Notification script content
    notification_script = '''#!/usr/bin/env python3
# Local Backup Email Notification Script

import sys
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_email(status, message):
    # Get email configuration from environment variables
    smtp_server = os.environ.get('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
    port = int(os.environ.get('EMAIL_SMTP_PORT', 587))
    sender_email = os.environ.get('EMAIL_SENDER')
    sender_password = os.environ.get('EMAIL_PASSWORD')
    recipient_email = os.environ.get('EMAIL_RECIPIENT')

    # Validate required environment variables
    if not all([sender_email, sender_password, recipient_email]):
        print("Error: Missing email configuration environment variables")
        return False

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Atlas Local Backup {status}"
    msg["From"] = sender_email
    msg["To"] = recipient_email

    # Create text part
    text = f"""
Atlas Local Backup Notification

Status: {status}
Message: {message}

This is an automated message from your Atlas local backup system.
"""

    text_part = MIMEText(text, "plain")
    msg.attach(text_part)

    # Send email
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())

        print(f"Local backup email notification sent: {status}")
        return True
    except Exception as e:
        print(f"Error sending local backup email: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: send_local_notification.py <status> <message>")
        sys.exit(1)

    status = sys.argv[1]
    message = sys.argv[2]

    if send_email(status, message):
        sys.exit(0)
    else:
        sys.exit(1)
'''

    # Write notification script
    script_path = "/home/ubuntu/dev/atlas/backup/send_local_notification.py"
    with open(script_path, "w") as f:
        f.write(notification_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Local backup email notification script created successfully")


def setup_selective_backup():
    """Configure selective backup of critical data"""
    print("Setting up selective backup configuration...")

    # Create backup configuration file
    config_content = """
# Atlas Selective Backup Configuration

# Directories to include in backup
INCLUDE_DIRS=(
    "/home/ubuntu/dev/atlas/backups"
    "/home/ubuntu/dev/atlas/config"
    "/home/ubuntu/dev/atlas/.env"
)

# File patterns to include
INCLUDE_PATTERNS=(
    "*.sql.gz.enc"
    "*.conf"
    "*.cfg"
    ".env"
)

# File patterns to exclude
EXCLUDE_PATTERNS=(
    "*.log"
    "*.tmp"
    "*.cache"
    "__pycache__"
)
"""

    config_path = "/home/ubuntu/dev/atlas/backup/selective_backup.conf"
    with open(config_path, "w") as f:
        f.write(config_content)

    print("Selective backup configuration created")


def setup_scheduling():
    """Setup backup scheduling (weekly)"""
    print("Setting up weekly backup scheduling...")

    # Add weekly cron job (runs every Sunday at 5 AM)
    weekly_cron = "0 5 * * 0 /home/ubuntu/dev/atlas/backup/local_sync.sh >> /home/ubuntu/dev/atlas/logs/local_sync.log 2>&1"

    try:
        # Get current crontab
        process = create_managed_process(["crontab", "-l"], "get_crontab_scheduling")
        stdout, stderr = process.communicate()
        current_crontab = stdout.decode('utf-8').strip()

        # Check if weekly job already exists
        if "/home/ubuntu/dev/atlas/backup/local_sync.sh" in current_crontab:
            print("Weekly backup cron job already exists")
            return

        # Add weekly job
        new_crontab = (
            current_crontab + "\n" + weekly_cron if current_crontab else weekly_cron
        )

        # Write to temporary file
        temp_dir = os.environ.get("ATLAS_TEMP_DIR", "/tmp")
        crontab_file = os.path.join(temp_dir, "new_crontab")
        with open(crontab_file, "w") as f:
            f.write(new_crontab + "\n")

        # Install new crontab
        process = create_managed_process(["crontab", crontab_file], "install_crontab_scheduling")
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, output=stdout, stderr=stderr)
        print("Weekly backup cron job installed successfully")

    except subprocess.CalledProcessError as e:
        print(f"Error setting up weekly cron job: {e}")
        print("Please add the following line to your crontab manually:")
        print(weekly_cron)


def create_verification_script():
    """Create backup verification script"""
    print("Creating backup verification script...")

    # Get configuration from environment variables
    remote_user = os.environ.get("BACKUP_REMOTE_USER", "backup")
    remote_host = os.environ.get("BACKUP_REMOTE_HOST", "personal-machine")
    remote_path = os.environ.get("BACKUP_REMOTE_PATH", "/backup/atlas")

    # Verification script content
    verify_script = f"""#!/bin/bash
# Atlas Local Backup Verification

# Configuration
REMOTE_USER="{remote_user}"
REMOTE_HOST="{remote_host}"
REMOTE_PATH="{remote_path}"
LOG_FILE="/home/ubuntu/dev/atlas/logs/backup_verify.log"

# Function to log messages
log_message() {{
    echo "$(date): $1" >> $LOG_FILE
}}

# Create log directory if it doesn't exist
mkdir -p "$(dirname $LOG_FILE)"

log_message "Starting backup verification"

# Verify local backup directory
if [ -d "/home/ubuntu/dev/atlas/backups" ]; then
    local_count=$(ls -1 /home/ubuntu/dev/atlas/backups/*.sql.gz.enc 2>/dev/null | wc -l)
    log_message "Local backups found: $local_count"
else
    log_message "ERROR: Local backup directory not found"
    exit 1
fi

# Verify remote backup directory
remote_count=$(ssh -i ~/.ssh/atlas_backup "$REMOTE_USER@$REMOTE_HOST" "ls -1 $REMOTE_PATH/latest/atlas_backup_*.sql.gz.enc 2>/dev/null | wc -l" 2>/dev/null)

if [ $? -eq 0 ]; then
    log_message "Remote backups found: $remote_count"

    if [ "$local_count" -eq "$remote_count" ]; then
        log_message "Backup verification successful: counts match"
        exit 0
    else
        log_message "WARNING: Backup count mismatch - local: $local_count, remote: $remote_count"
        exit 1
    fi
else
    log_message "ERROR: Failed to access remote backup directory"
    exit 1
fi
"""

    # Write verification script
    script_path = "/home/ubuntu/dev/atlas/backup/verify_local_backup.sh"
    with open(script_path, "w") as f:
        f.write(verify_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Backup verification script created successfully")


def create_cleanup_script():
    """Create local backup cleanup script"""
    print("Creating local backup cleanup script...")

    # Cleanup script content
    cleanup_script = """#!/bin/bash
# Atlas Local Backup Cleanup

# Configuration
BACKUP_DIR="/home/ubuntu/dev/atlas/backups"
RETENTION_DAYS=30
LOG_FILE="/home/ubuntu/dev/atlas/logs/local_cleanup.log"

# Function to log messages
log_message() {
    echo "$(date): $1" >> $LOG_FILE
}

# Create log directory if it doesn't exist
mkdir -p "$(dirname $LOG_FILE)"

log_message "Starting local backup cleanup"

# Find and delete backups older than retention period
find "$BACKUP_DIR" -name "atlas_backup_*.sql.gz.enc" -mtime +$RETENTION_DAYS -delete

if [ $? -eq 0 ]; then
    log_message "Local backup cleanup completed successfully"
else
    log_message "ERROR: Local backup cleanup failed"
    exit 1
fi

# Clean up log files older than 30 days
find "/home/ubuntu/dev/atlas/logs" -name "*.log" -mtime +30 -delete

log_message "Log cleanup completed"
log_message "Local backup cleanup completed"
"""

    # Write cleanup script
    script_path = "/home/ubuntu/dev/atlas/backup/cleanup_local_backups.sh"
    with open(script_path, "w") as f:
        f.write(cleanup_script)

    # Make script executable
    os.chmod(script_path, 0o755)

    # Add cleanup job to crontab (runs daily at 6 AM)
    cleanup_cron = "0 6 * * * /home/ubuntu/dev/atlas/backup/cleanup_local_backups.sh >> /home/ubuntu/dev/atlas/logs/local_cleanup.log 2>&1"

    try:
        # Get current crontab
        process = create_managed_process(["crontab", "-l"], "get_crontab_cleanup")
        stdout, stderr = process.communicate()
        current_crontab = stdout.decode('utf-8').strip()

        # Check if cleanup job already exists
        if "/home/ubuntu/dev/atlas/backup/cleanup_local_backups.sh" in current_crontab:
            print("Local cleanup cron job already exists")
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
        process = create_managed_process(["crontab", crontab_file], "install_crontab_cleanup")
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, output=stdout, stderr=stderr)
        print("Local cleanup cron job installed successfully")

    except subprocess.CalledProcessError as e:
        print(f"Error setting up cleanup cron job: {e}")
        print("Please add the following line to your crontab manually:")
        print(cleanup_cron)


def test_backup_sync():
    """Test backup sync to personal machine"""
    print("Testing backup sync to personal machine...")

    # This would typically run the sync script and verify the results
    # For now, we'll just print a message
    print("Backup sync test would be implemented here")
    print("Please run the sync script manually to test:")
    print("/home/ubuntu/dev/atlas/backup/local_sync.sh")


def main():
    """Main local machine backup sync setup function"""
    print("Starting local machine backup sync setup for Atlas...")

    # Generate SSH key pair
    if not generate_ssh_key():
        print("Failed to generate SSH key pair")
        sys.exit(1)

    # Create rsync script
    create_rsync_script()

    # Create notification script
    create_notification_script()

    # Setup selective backup
    setup_selective_backup()

    # Setup scheduling
    setup_scheduling()

    # Create verification script
    create_verification_script()

    # Create cleanup script
    create_cleanup_script()

    # Test backup sync
    test_backup_sync()

    print("\nLocal machine backup sync setup completed successfully!")
    print("Features configured:")
    print("- SSH key authentication for secure transfers")
    print("- Rsync script for backup synchronization")
    print("- Selective backup of critical data")
    print("- Weekly backup scheduling")
    print("- Backup verification script")
    print("- Local backup cleanup")
    print("- Email notifications for success/failure")

    print("\nNext steps:")
    print("1. Set the required environment variables:")
    print("   - BACKUP_REMOTE_USER")
    print("   - BACKUP_REMOTE_HOST")
    print("   - BACKUP_REMOTE_PATH")
    print("   - EMAIL_SENDER")
    print("   - EMAIL_PASSWORD")
    print("   - EMAIL_RECIPIENT")
    print("2. Copy the public SSH key to your personal machine")
    print("3. Test the backup sync process manually")
    print("4. Verify cron jobs are running correctly")


if __name__ == "__main__":
    main()
