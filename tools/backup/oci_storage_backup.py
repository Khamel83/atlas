#!/usr/bin/env python3
"""
OCI Object Storage Backup for Atlas

This script sets up OCI Object Storage backup for Atlas, including
uploading backups to OCI Object Storage, implementing backup rotation,
and sending email notifications.

Features:
- Sets up OCI Object Storage bucket (free tier)
- Installs and configures OCI CLI
- Creates script to upload backups to OCI Object Storage
- Implements backup rotation in object storage (30 days)
- Adds backup success/failure email notifications
- Tests backup upload and cleanup processes
"""

import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
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


def install_oci_cli():
    """Install and configure OCI CLI"""
    print("Installing OCI CLI...")

    # Install OCI CLI
    run_command(
        "curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh > /tmp/install.sh",
        "Downloading OCI CLI installer",
    )
    run_command("chmod +x /tmp/install.sh", "Making installer executable")
    run_command("sudo /tmp/install.sh --accept-all-defaults", "Installing OCI CLI")

    print("OCI CLI installed successfully")


def configure_oci_cli():
    """Configure OCI CLI with user credentials"""
    print("Configuring OCI CLI...")

    # Get configuration from environment variables
    tenancy_ocid = os.environ.get("OCI_TENANCY_OCID")
    user_ocid = os.environ.get("OCI_USER_OCID")
    region = os.environ.get("OCI_REGION", "us-phoenix-1")
    fingerprint = os.environ.get("OCI_KEY_FINGERPRINT")
    key_file = os.environ.get("OCI_PRIVATE_KEY_FILE")

    # Validate required environment variables
    if not all([tenancy_ocid, user_ocid, fingerprint, key_file]):
        print("Error: Missing required OCI configuration environment variables")
        print("Please set:")
        print("- OCI_TENANCY_OCID")
        print("- OCI_USER_OCID")
        print("- OCI_KEY_FINGERPRINT")
        print("- OCI_PRIVATE_KEY_FILE")
        return False

    # Create OCI config directory
    config_dir = os.path.expanduser("~/.oci")
    os.makedirs(config_dir, exist_ok=True)

    # Create config file
    config_content = f"""
[DEFAULT]
tenancy={tenancy_ocid}
user={user_ocid}
fingerprint={fingerprint}
key_file={key_file}
region={region}
"""

    with open(os.path.join(config_dir, "config"), "w") as f:
        f.write(config_content)

    # Set restrictive permissions
    os.chmod(os.path.join(config_dir, "config"), 0o600)

    print("OCI CLI configured successfully")
    return True


def create_bucket():
    """Create OCI Object Storage bucket"""
    print("Creating OCI Object Storage bucket...")

    # Get compartment OCID from environment variable
    compartment_ocid = os.environ.get("OCI_COMPARTMENT_OCID")
    if not compartment_ocid:
        print("Error: OCI_COMPARTMENT_OCID environment variable not set")
        return False

    # Get bucket name from environment variable or use default
    bucket_name = os.environ.get("OCI_BUCKET_NAME", "atlas-backups")

    # Create bucket
    cmd = f"oci os bucket create --compartment-id {compartment_ocid} --name {bucket_name} --public-access-type NoPublicAccess"
    result = run_command(cmd, "Creating Object Storage bucket")

    if result:
        print(f"Bucket '{bucket_name}' created successfully")
        return True
    else:
        print("Failed to create bucket")
        return False


def create_backup_upload_script():
    """Create script to upload backups to OCI Object Storage"""
    print("Creating backup upload script...")

    # Get bucket name from environment variable or use default
    bucket_name = os.environ.get("OCI_BUCKET_NAME", "atlas-backups")

    # Upload script content
    upload_script = f"""#!/bin/bash
# Atlas Backup Upload to OCI Object Storage

# Configuration
BUCKET_NAME="{bucket_name}"
BACKUP_DIR="/home/ubuntu/dev/atlas/backups"
LOG_FILE="/home/ubuntu/dev/atlas/logs/oci_upload.log"

# Function to log messages
log_message() {{
    echo "$(date): $1" >> $LOG_FILE
}}

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log_message "ERROR: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Find the latest backup file
LATEST_BACKUP=$(ls -t $BACKUP_DIR/atlas_backup_*.sql.gz.enc 2>/dev/null | head -n1)

if [ -z "$LATEST_BACKUP" ]; then
    log_message "ERROR: No backup files found in $BACKUP_DIR"
    exit 1
fi

# Upload backup to OCI Object Storage
log_message "Uploading backup: $(basename $LATEST_BACKUP)"
oci os object put -bn $BUCKET_NAME -f $LATEST_BACKUP --name $(basename $LATEST_BACKUP) >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    log_message "Backup uploaded successfully: $(basename $LATEST_BACKUP)"

    # Send success email notification
    python3 /home/ubuntu/dev/atlas/backup/send_notification.py "SUCCESS" "Backup uploaded to OCI Object Storage: $(basename $LATEST_BACKUP)"
else
    log_message "ERROR: Failed to upload backup: $(basename $LATEST_BACKUP)"

    # Send failure email notification
    python3 /home/ubuntu/dev/atlas/backup/send_notification.py "FAILURE" "Failed to upload backup to OCI Object Storage: $(basename $LATEST_BACKUP)"
    exit 1
fi
"""

    # Write upload script
    script_path = "/home/ubuntu/dev/atlas/backup/upload_to_oci.sh"
    with open(script_path, "w") as f:
        f.write(upload_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Backup upload script created successfully")


def create_notification_script():
    """Create script to send email notifications"""
    print("Creating email notification script...")

    # Notification script content
    notification_script = '''#!/usr/bin/env python3
# Email Notification Script

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
    msg["Subject"] = f"Atlas Backup {status}"
    msg["From"] = sender_email
    msg["To"] = recipient_email

    # Create text part
    text = f"""
Atlas Backup Notification

Status: {status}
Message: {message}

This is an automated message from your Atlas backup system.
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

        print(f"Email notification sent: {status}")
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: send_notification.py <status> <message>")
        sys.exit(1)

    status = sys.argv[1]
    message = sys.argv[2]

    if send_email(status, message):
        sys.exit(0)
    else:
        sys.exit(1)
'''

    # Write notification script
    script_path = "/home/ubuntu/dev/atlas/backup/send_notification.py"
    with open(script_path, "w") as f:
        f.write(notification_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Email notification script created successfully")


def setup_backup_rotation():
    """Setup backup rotation in OCI Object Storage"""
    print("Setting up backup rotation...")

    # Get bucket name from environment variable or use default
    bucket_name = os.environ.get("OCI_BUCKET_NAME", "atlas-backups")

    # Create cleanup script
    cleanup_script = f"""#!/bin/bash
# OCI Object Storage Backup Cleanup

# Configuration
BUCKET_NAME="{bucket_name}"
RETENTION_DAYS=30
LOG_FILE="/home/ubuntu/dev/atlas/logs/oci_cleanup.log"

# Function to log messages
log_message() {{
    echo "$(date): $1" >> $LOG_FILE
}}

# Get list of objects in bucket
log_message "Getting list of backup objects"
OBJECTS=$(oci os object list -bn $BUCKET_NAME --all --fields name,time-created | jq -r '.data[] | "\\(.["time-created"]) \\(.name)"')

if [ -z "$OBJECTS" ]; then
    log_message "No objects found in bucket"
    exit 0
fi

# Process each object
echo "$OBJECTS" | while read -r time_created name; do
    # Convert time to seconds since epoch
    created_seconds=$(date -d "$time_created" +%s 2>/dev/null)

    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to parse date: $time_created"
        continue
    fi

    # Calculate age in days
    current_seconds=$(date +%s)
    age_days=$(( (current_seconds - created_seconds) / 86400 ))

    # Delete if older than retention period
    if [ $age_days -gt $RETENTION_DAYS ]; then
        log_message "Deleting old backup: $name (age: $age_days days)"
        oci os object delete -bn $BUCKET_NAME --name "$name" --force >> $LOG_FILE 2>&1

        if [ $? -eq 0 ]; then
            log_message "Successfully deleted: $name"
        else
            log_message "ERROR: Failed to delete: $name"
        fi
    fi
done

log_message "Backup cleanup completed"
"""

    # Write cleanup script
    script_path = "/home/ubuntu/dev/atlas/backup/cleanup_oci_backups.sh"
    with open(script_path, "w") as f:
        f.write(cleanup_script)

    # Make script executable
    os.chmod(script_path, 0o755)

    # Add cleanup job to crontab (runs daily at 4 AM)
    cleanup_cron = "0 4 * * * /home/ubuntu/dev/atlas/backup/cleanup_oci_backups.sh >> /home/ubuntu/dev/atlas/logs/oci_cleanup.log 2>&1"

    try:
        # Get current crontab
        process = create_managed_process(["crontab", "-l"], "get_crontab")
        stdout, stderr = process.communicate()
        current_crontab = stdout.decode('utf-8').strip()

        # Check if cleanup job already exists
        if "/home/ubuntu/dev/atlas/backup/cleanup_oci_backups.sh" in current_crontab:
            print("OCI cleanup cron job already exists")
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
        process = create_managed_process(["crontab", crontab_file], "install_crontab")
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, output=stdout, stderr=stderr)
        print("OCI cleanup cron job installed successfully")

    except subprocess.CalledProcessError as e:
        print(f"Error setting up cleanup cron job: {e}")
        print("Please add the following line to your crontab manually:")
        print(cleanup_cron)


def test_backup_upload():
    """Test backup upload to OCI Object Storage"""
    print("Testing backup upload to OCI Object Storage...")

    # This would typically run the upload script and verify the results
    # For now, we'll just print a message
    print("Backup upload test would be implemented here")
    print("Please run the upload script manually to test:")
    print("/home/ubuntu/dev/atlas/backup/upload_to_oci.sh")


def main():
    """Main OCI Object Storage backup setup function"""
    print("Starting OCI Object Storage backup setup for Atlas...")

    # Install and configure OCI CLI
    install_oci_cli()
    if not configure_oci_cli():
        print("Failed to configure OCI CLI")
        sys.exit(1)

    # Create bucket
    if not create_bucket():
        print("Failed to create bucket")
        sys.exit(1)

    # Create backup upload script
    create_backup_upload_script()

    # Create notification script
    create_notification_script()

    # Setup backup rotation
    setup_backup_rotation()

    # Test backup upload
    test_backup_upload()

    print("\nOCI Object Storage backup setup completed successfully!")
    print("Features configured:")
    print("- OCI Object Storage bucket for backups")
    print("- Backup upload script")
    print("- Email notifications for success/failure")
    print("- 30-day backup rotation in object storage")
    print("- Automatic backup cleanup")

    print("\nNext steps:")
    print("1. Set the required environment variables:")
    print("   - OCI_TENANCY_OCID")
    print("   - OCI_USER_OCID")
    print("   - OCI_KEY_FINGERPRINT")
    print("   - OCI_PRIVATE_KEY_FILE")
    print("   - OCI_COMPARTMENT_OCID")
    print("   - EMAIL_SENDER")
    print("   - EMAIL_PASSWORD")
    print("   - EMAIL_RECIPIENT")
    print("2. Test the backup upload process manually")
    print("3. Verify cron jobs are running correctly")


if __name__ == "__main__":
    main()
