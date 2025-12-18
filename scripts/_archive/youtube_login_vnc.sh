#!/bin/bash
# Start a VNC session for YouTube login
# Access via browser at http://SERVER:6080/vnc.html

set -e

cd /home/khamel83/github/atlas

# Kill any existing sessions
pkill -f "Xvfb :99" 2>/dev/null || true
pkill -f x11vnc 2>/dev/null || true
pkill -f novnc 2>/dev/null || true
sleep 1

# Start virtual display
export DISPLAY=:99
Xvfb :99 -screen 0 1280x800x24 &
sleep 2

# Start VNC server (no password for simplicity - local network only)
x11vnc -display :99 -forever -shared -nopw &
sleep 1

# Start noVNC web proxy
/usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &
sleep 2

echo ""
echo "============================================"
echo "  VNC SESSION READY"
echo "============================================"
echo ""
echo "Open in your browser:"
echo "  http://$(hostname -I | awk '{print $1}'):6080/vnc.html"
echo ""
echo "Then run this in another terminal:"
echo "  cd ~/github/atlas"
echo "  DISPLAY=:99 .venv/bin/python -m modules.ingest.youtube_history_scraper --login"
echo ""
echo "Press Ctrl+C when done to clean up"
echo "============================================"

# Wait for Ctrl+C
trap "pkill -f 'Xvfb :99'; pkill -f x11vnc; pkill -f novnc; echo 'Cleaned up'" EXIT
wait
