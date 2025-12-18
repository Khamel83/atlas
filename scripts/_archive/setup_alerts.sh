#!/bin/bash
# Atlas Alert Setup Script
# Run this after getting your Telegram and Uptime Kuma credentials

set -euo pipefail

echo "🔔 Atlas Alert System Setup"
echo "=========================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Function to update .env
update_env() {
    local key=$1
    local value=$2

    if grep -q "^${key}=" .env; then
        # Update existing
        sed -i "s|^${key}=.*|${key}=${value}|" .env
        echo "✅ Updated ${key}"
    else
        # Add new
        echo "${key}=${value}" >> .env
        echo "✅ Added ${key}"
    fi
}

echo ""
echo "📱 TELEGRAM BOT SETUP"
echo "Instructions:"
echo "1. Message @BotFather on Telegram"
echo "2. Send: /newbot"
echo "3. Name: Atlas Monitoring Bot"
echo "4. Username: atlas_monitoring_YOUR_NAME_bot"
echo ""
read -p "Enter your bot token: " BOT_TOKEN

echo ""
echo "💬 TELEGRAM CHAT ID SETUP"
echo "Instructions:"
echo "1. Start chat with your bot"
echo "2. Send any message"
echo "3. Visit: https://api.telegram.org/bot${BOT_TOKEN}/getUpdates"
echo "4. Find your chat ID in the response"
echo ""
read -p "Enter your chat ID: " CHAT_ID

echo ""
echo "🔔 UPTIME KUMA SETUP (Optional)"
echo "Instructions:"
echo "1. Open Uptime Kuma on your RPI"
echo "2. Add New Monitor > Push type"
echo "3. Name: Atlas Transcript Processing"
echo "4. Copy the push URL"
echo ""
read -p "Enter Uptime Kuma push URL (or press Enter to skip): " KUMA_URL

# Update .env file
echo ""
echo "📝 Updating .env file..."

update_env "TELEGRAM_BOT_TOKEN" "$BOT_TOKEN"
update_env "TELEGRAM_CHAT_ID" "$CHAT_ID"

if [ -n "$KUMA_URL" ]; then
    update_env "UPTIME_KUMA_URL" "$KUMA_URL"
else
    echo "⏭️  Skipped Uptime Kuma setup"
fi

echo ""
echo "🧪 Testing alert system..."

# Test the notification system
if python3 scripts/notify.py --test; then
    echo "✅ Alert system working!"
else
    echo "❌ Alert system test failed - check your credentials"
    exit 1
fi

echo ""
echo "🎉 Alert setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Test manual alert: python3 scripts/notify.py --msg 'Hello from Atlas!'"
echo "2. Install systemd services: make install"
echo "3. Enable watchdog: sudo systemctl enable --now atlas-watchdog.timer"
echo ""
echo "🔍 Monitor logs with: journalctl -u atlas-watchdog -f"