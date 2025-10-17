#!/bin/bash

# Atlas Management System Startup Script
# Runs continuously without manual intervention

echo "🚀 STARTING ATLAS MANAGEMENT SYSTEM"
echo "=================================="
echo "This will run continuously in the background"
echo "Log files will be written to logs/atlas_manager.log"
echo "=================================="

# Create logs directory
mkdir -p logs

# Kill any existing atlas manager processes
pkill -f "python3 atlas_manager.py" 2>/dev/null || true

# Start the Atlas Manager in background
nohup python3 atlas_manager.py > logs/atlas_manager.log 2>&1 &

# Get the process ID
ATLAS_PID=$!

echo "Atlas Manager started with PID: $ATLAS_PID"
echo "To check status: tail -f logs/atlas_manager.log"
echo "To stop: pkill -f 'python3 atlas_manager.py'"
echo "=================================="

# Wait a moment and check if it's running
sleep 3

if ps -p $ATLAS_PID > /dev/null; then
    echo "✅ Atlas Manager is running successfully"
    echo "Last few log entries:"
    echo "----------------------------------"
    tail -n 5 logs/atlas_manager.log
else
    echo "❌ Atlas Manager failed to start"
    echo "Check logs/atlas_manager.log for errors"
fi
