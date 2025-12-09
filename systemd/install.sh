#!/bin/bash
# Install Atlas systemd units
#
# Usage: sudo ./install.sh [--all]
#
# Services:
#   Core (always installed):
#     - atlas-gmail: Process Gmail inbox
#     - atlas-inbox: Process content inbox
#     - atlas-content-retry: Retry failed content
#
#   Podcasts (--all or --podcasts):
#     - atlas-podcast-discovery: Discover new episodes from RSS
#     - atlas-transcripts: Fetch transcripts (Podscripts, NPR, YouTube via proxy)
#     - atlas-youtube-retry: Weekly retry of YouTube-blocked episodes
#
# Prerequisites:
#   - NordVPN proxy at 100.112.130.100:8118 for YouTube

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"
ATLAS_DIR="/home/khamel83/github/atlas"
ATLAS_LOG_DIR="/var/log/atlas"

echo "Installing Atlas systemd units..."

# Ensure log directory exists
if [ ! -d "$ATLAS_LOG_DIR" ]; then
    mkdir -p "$ATLAS_LOG_DIR"
    chown khamel83:khamel83 "$ATLAS_LOG_DIR"
    echo "Created log directory: $ATLAS_LOG_DIR"
fi

# Core services - always install
CORE_SERVICES="atlas-gmail atlas-inbox atlas-content-retry"
for service in $CORE_SERVICES; do
    if [ -f "$SCRIPT_DIR/${service}.service" ]; then
        cp "$SCRIPT_DIR/${service}.service" "$SYSTEMD_DIR/"
        echo "Installed ${service}.service"
    fi
    if [ -f "$SCRIPT_DIR/${service}.timer" ]; then
        cp "$SCRIPT_DIR/${service}.timer" "$SYSTEMD_DIR/"
        echo "Installed ${service}.timer"
    fi
done

# Podcast services - install with --all or --podcasts
if [ "$1" = "--all" ] || [ "$1" = "--podcasts" ]; then
    echo ""
    echo "Installing podcast services..."

    # Environment file is already in place
    echo "Using atlas-podcasts.env"

    PODCAST_SERVICES="atlas-podcast-discovery atlas-transcripts atlas-youtube-retry"
    for service in $PODCAST_SERVICES; do
        if [ -f "$SCRIPT_DIR/${service}.service" ]; then
            cp "$SCRIPT_DIR/${service}.service" "$SYSTEMD_DIR/"
            echo "Installed ${service}.service"
        fi
        if [ -f "$SCRIPT_DIR/${service}.timer" ]; then
            cp "$SCRIPT_DIR/${service}.timer" "$SYSTEMD_DIR/"
            echo "Installed ${service}.timer"
        fi
    done
fi

# Reload systemd
systemctl daemon-reload
echo ""
echo "Reloaded systemd daemon"

# Enable and start core timers
echo ""
echo "Enabling core timers..."
for timer in $CORE_SERVICES; do
    if [ -f "$SYSTEMD_DIR/${timer}.timer" ]; then
        systemctl enable "${timer}.timer" 2>/dev/null || true
        systemctl start "${timer}.timer" 2>/dev/null || true
        echo "  Enabled ${timer}.timer"
    fi
done

# Enable podcast timers if installed
if [ "$1" = "--all" ] || [ "$1" = "--podcasts" ]; then
    echo ""
    echo "Enabling podcast timers..."
    for timer in atlas-podcast-discovery atlas-transcripts atlas-youtube-retry; do
        if [ -f "$SYSTEMD_DIR/${timer}.timer" ]; then
            systemctl enable "${timer}.timer" 2>/dev/null || true
            systemctl start "${timer}.timer" 2>/dev/null || true
            echo "  Enabled ${timer}.timer"
        fi
    done
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "Installation complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Check timers:"
echo "  systemctl list-timers --all | grep atlas"
echo ""
echo "Manual run:"
echo "  systemctl start atlas-transcripts"
echo ""
echo "View logs:"
echo "  journalctl -u atlas-transcripts -f"
echo "  tail -f $ATLAS_LOG_DIR/transcripts.log"
echo ""
echo "Check podcast coverage:"
echo "  cd $ATLAS_DIR && ./venv/bin/python -m modules.podcasts.cli status"
echo ""
