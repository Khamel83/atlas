#!/bin/bash
# Encrypt atlas secrets with SOPS

set -e

AGE_KEY_FILE="$HOME/.age/key.txt"
ENV_FILE="/tmp/atlas.env"
OUTPUT_FILE="secrets.env.encrypted"

# Check if age key exists
if [ ! -f "$AGE_KEY_FILE" ]; then
    echo "Error: Age key not found at $AGE_KEY_FILE"
    exit 1
fi

# Get public key
AGE_PUBLIC_KEY=$(grep -oP 'public key: \K.*' "$AGE_KEY_FILE")

if [ -z "$AGE_PUBLIC_KEY" ]; then
    echo "Error: Could not extract public key from $AGE_KEY_FILE"
    exit 1
fi

echo "Using age public key: $AGE_PUBLIC_KEY"

# Create template if not exists
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << 'ENVEOF'
# Atlas Environment Configuration
# Encrypted with SOPS + Age

# Gmail IMAP Access
GMAIL_EMAIL_ADDRESS=zoheri+atlas@gmail.com
GMAIL_APP_PASSWORD=PLACEHOLDER_SET_REAL_PASSWORD

# Telegram Notifications (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# OpenRouter API for LLM features (optional)
OPENROUTER_API_KEY=

# MacWhisper NFS mount for transcription fallback
MACWHISPER_INBOX=/mnt/macwhisper/inbox
MACWHISPER_OUTBOX=/mnt/macwhisper/outbox

# YouTube OAuth (deferred - set up later)
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=

# Rate limiting
RATE_LIMIT_DELAY_MIN=2.0
RATE_LIMIT_DELAY_MAX=3.0
ENVEOF
fi

# Encrypt
sops --encrypt --age "$AGE_PUBLIC_KEY" --input-type dotenv --output-type dotenv "$ENV_FILE" > "$OUTPUT_FILE"

# Clean up
rm -f "$ENV_FILE"

echo "Created encrypted $OUTPUT_FILE"
echo "Edit with: sops --input-type dotenv --output-type dotenv $OUTPUT_FILE"
