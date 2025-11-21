#!/bin/bash
# Atlas Auto-Start Script - runs on boot
cd "/home/ubuntu/dev/atlas"
export PATH="/home/ubuntu/dev/atlas/venv/bin:/usr/local/bin:/usr/bin:/bin"
source venv/bin/activate
python3 atlas_service_manager.py start --daemon >> logs/autostart.log 2>&1
