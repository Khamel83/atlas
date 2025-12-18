#!/bin/bash
# Simple script to rotate large log files without command substitution

TIMESTAMP=$(date +%Y%m%d)
LOGS_DIR="/home/ubuntu/dev/atlas/logs"

if [ -d "$LOGS_DIR" ]; then
    find "$LOGS_DIR" -name "*.log" -size +100M | while read -r logfile; do
        if [ -f "$logfile" ]; then
            mv "$logfile" "${logfile}.${TIMESTAMP}.old"
            echo "Rotated large log: $logfile"
        fi
    done
else
    echo "Logs directory not found: $LOGS_DIR"
fi