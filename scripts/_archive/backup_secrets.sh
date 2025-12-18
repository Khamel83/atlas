#!/bin/bash
# Backup encrypted secrets with rolling 1-day retention
# Run daily via cron or systemd timer

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SECRETS_FILE="$PROJECT_DIR/secrets.env.encrypted"
BACKUP_DIR="$PROJECT_DIR/.secrets-backup"
TODAY=$(date +%Y-%m-%d)

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# Check if secrets file exists and has content
if [ ! -s "$SECRETS_FILE" ]; then
    echo "ERROR: Secrets file is empty or missing: $SECRETS_FILE"
    exit 1
fi

# Create today's backup
BACKUP_FILE="$BACKUP_DIR/secrets.env.encrypted.$TODAY"
cp "$SECRETS_FILE" "$BACKUP_FILE"
echo "Created backup: $BACKUP_FILE"

# Remove backups older than 2 days (keep yesterday + today)
find "$BACKUP_DIR" -name "secrets.env.encrypted.*" -mtime +1 -delete
echo "Cleaned up old backups"

# List current backups
echo "Current backups:"
ls -la "$BACKUP_DIR/"
