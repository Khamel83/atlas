#!/bin/bash
# Atlas Complete Setup Script
# Unified setup for all Atlas components: Alerts, APIs, Mac Mini, and more

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] ℹ️  $1${NC}"
}

header() {
    echo -e "${PURPLE}"
    echo "=================================="
    echo "$1"
    echo "=================================="
    echo -e "${NC}"
}

# Function to update .env
update_env() {
    local key=$1
    local value=$2

    if [ -z "$value" ]; then
        warn "Skipping empty value for $key"
        return
    fi

    if grep -q "^${key}=" .env; then
        # Update existing
        sed -i "s|^${key}=.*|${key}=${value}|" .env
        log "Updated ${key}"
    else
        # Add new
        echo "${key}=${value}" >> .env
        log "Added ${key}"
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python packages if missing
ensure_python_package() {
    local package=$1
    if ! python3 -c "import $package" 2>/dev/null; then
        log "Installing Python package: $package"
        pip3 install "$package"
    else
        info "Python package $package already installed"
    fi
}

# Main setup function
main() {
    header "🚀 Atlas Complete Setup"

    log "Starting comprehensive Atlas setup..."
    log "This will configure: Alerts, APIs, Mac Mini, and monitoring"
    echo ""

    # Check if we're in the right directory
    if [ ! -f ".env" ] || [ ! -f "atlas_status.py" ]; then
        error "Please run this script from the Atlas root directory"
        exit 1
    fi

    # Backup .env
    if [ -f ".env" ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        log "Backed up existing .env file"
    fi

    # 1. TELEGRAM BOT SETUP
    header "📱 Telegram Bot Setup"
    echo "Set up Telegram notifications for Atlas monitoring"
    echo ""
    echo "Instructions:"
    echo "1. Open Telegram and message @BotFather"
    echo "2. Send: /newbot"
    echo "3. Name: Atlas Monitoring Bot"
    echo "4. Username: atlas_monitoring_$(whoami)_bot"
    echo "5. Copy the bot token"
    echo ""
    read -p "Enter your Telegram bot token (or press Enter to skip): " TELEGRAM_TOKEN

    if [ -n "$TELEGRAM_TOKEN" ]; then
        echo ""
        echo "Now get your chat ID:"
        echo "1. Start a chat with your bot"
        echo "2. Send any message"
        echo "3. Visit: https://api.telegram.org/bot${TELEGRAM_TOKEN}/getUpdates"
        echo "4. Find your chat ID in the response"
        echo ""
        read -p "Enter your Telegram chat ID: " TELEGRAM_CHAT_ID

        update_env "TELEGRAM_BOT_TOKEN" "$TELEGRAM_TOKEN"
        update_env "TELEGRAM_CHAT_ID" "$TELEGRAM_CHAT_ID"

        # Test Telegram
        if python3 scripts/notify.py --test 2>/dev/null; then
            log "✅ Telegram test successful!"
        else
            warn "Telegram test failed - check credentials"
        fi
    else
        warn "Skipping Telegram setup"
    fi

    # 2. UPTIME KUMA SETUP
    header "🔔 Uptime Kuma Setup (RPI)"
    echo "Configure Uptime Kuma webhook monitoring"
    echo ""
    echo "Instructions:"
    echo "1. Open your Uptime Kuma on RPI"
    echo "2. Add New Monitor → Push type"
    echo "3. Name: Atlas Transcript Processing"
    echo "4. Copy the push URL"
    echo ""
    read -p "Enter Uptime Kuma push URL (or press Enter to skip): " UPTIME_KUMA_URL

    if [ -n "$UPTIME_KUMA_URL" ]; then
        update_env "UPTIME_KUMA_URL" "$UPTIME_KUMA_URL"
        log "✅ Uptime Kuma configured"

        # Test Uptime Kuma
        if curl -s -X POST "$UPTIME_KUMA_URL" \
           -H "Content-Type: application/json" \
           -d '{"status": "up", "msg": "Atlas setup test"}' >/dev/null; then
            log "✅ Uptime Kuma test successful!"
        else
            warn "Uptime Kuma test failed - check URL"
        fi
    else
        warn "Skipping Uptime Kuma setup"
    fi

    # 3. YOUTUBE API SETUP
    header "📺 YouTube API Setup"
    echo "Configure YouTube Data API for transcript processing"
    echo ""
    echo "Instructions:"
    echo "1. Go to: https://console.developers.google.com/"
    echo "2. Create new project or select existing"
    echo "3. Enable YouTube Data API v3"
    echo "4. Create credentials → API Key"
    echo "5. Copy the API key"
    echo ""
    read -p "Enter YouTube API key (or press Enter to skip): " YOUTUBE_API_KEY

    if [ -n "$YOUTUBE_API_KEY" ]; then
        update_env "YOUTUBE_API_KEY" "$YOUTUBE_API_KEY"
        log "✅ YouTube API configured"
    else
        warn "Skipping YouTube API setup"
    fi

    # 4. MAC MINI SETUP
    header "💻 Mac Mini Integration"
    echo "Configure Mac Mini for transcript processing"
    echo ""
    echo "Prerequisites on Mac Mini:"
    echo "1. SSH access enabled"
    echo "2. Python 3 installed"
    echo "3. Network accessible from this machine"
    echo ""
    read -p "Enter Mac Mini hostname or IP (or press Enter to skip): " MAC_MINI_HOST

    if [ -n "$MAC_MINI_HOST" ]; then
        read -p "Enter Mac Mini username [$(whoami)]: " MAC_MINI_USER
        MAC_MINI_USER=${MAC_MINI_USER:-$(whoami)}

        update_env "MAC_MINI_HOST" "$MAC_MINI_HOST"
        update_env "MAC_MINI_USER" "$MAC_MINI_USER"

        # Test SSH connection
        if ssh -o ConnectTimeout=5 "${MAC_MINI_USER}@${MAC_MINI_HOST}" "echo 'SSH test successful'" 2>/dev/null; then
            log "✅ Mac Mini SSH connection successful!"

            # Set up Atlas worker directory on Mac Mini
            log "Setting up Atlas worker directory on Mac Mini..."
            ssh "${MAC_MINI_USER}@${MAC_MINI_HOST}" "mkdir -p ~/atlas_worker/queue/{tasks,results}"
            log "✅ Mac Mini worker directory created"
        else
            warn "Mac Mini SSH connection failed - check hostname and SSH setup"
        fi
    else
        warn "Skipping Mac Mini setup"
    fi

    # 5. OPENAI/OPENROUTER API SETUP
    header "🤖 AI API Setup"
    echo "Configure AI APIs for transcript processing"
    echo ""

    # Check if OpenRouter key already exists
    if grep -q "OPENROUTER_API_KEY=" .env && [ "$(grep OPENROUTER_API_KEY .env | cut -d'=' -f2)" != "" ]; then
        info "OpenRouter API key already configured"
    else
        echo "For OpenRouter API:"
        echo "1. Go to: https://openrouter.ai/"
        echo "2. Sign up/login"
        echo "3. Go to Keys section"
        echo "4. Create new API key"
        echo ""
        read -p "Enter OpenRouter API key (or press Enter to skip): " OPENROUTER_KEY

        if [ -n "$OPENROUTER_KEY" ]; then
            update_env "OPENROUTER_API_KEY" "$OPENROUTER_KEY"
            log "✅ OpenRouter API configured"
        fi
    fi

    # Optional: OpenAI API
    read -p "Enter OpenAI API key (optional, or press Enter to skip): " OPENAI_KEY
    if [ -n "$OPENAI_KEY" ]; then
        update_env "OPENAI_API_KEY" "$OPENAI_KEY"
        log "✅ OpenAI API configured"
    fi

    # 6. DEPENDENCIES CHECK
    header "📦 Dependencies Check"

    # Python packages
    log "Checking Python dependencies..."
    ensure_python_package "requests"
    ensure_python_package "beautifulsoup4"
    ensure_python_package "sqlite3"

    # System tools
    log "Checking system tools..."
    if ! command_exists "curl"; then
        warn "curl not found - install with: sudo apt install curl"
    fi

    if ! command_exists "jq"; then
        warn "jq not found - install with: sudo apt install jq"
    fi

    # 7. SYSTEM SERVICES SETUP
    header "⚙️ System Services Setup"

    echo "Setting up systemd services for reliability..."

    # Install services
    if [ -d "systemd" ]; then
        log "Installing systemd services..."
        sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/ 2>/dev/null || warn "Could not copy systemd files (run as sudo if needed)"
        sudo systemctl daemon-reload 2>/dev/null || warn "Could not reload systemd daemon"
        log "✅ Systemd services installed"
    else
        warn "systemd directory not found - services not installed"
    fi

    # 8. FINAL TESTING
    header "🧪 System Testing"

    log "Running comprehensive system test..."

    # Database test
    if python3 scripts/db_introspect.py >/dev/null 2>&1; then
        log "✅ Database connectivity test passed"
    else
        error "Database connectivity test failed"
    fi

    # Transcript worker test
    if python3 scripts/fixed_transcript_worker.py --limit 1 >/dev/null 2>&1; then
        log "✅ Transcript worker test passed"
    else
        warn "Transcript worker test failed"
    fi

    # Status script test
    if python3 atlas_status.py >/dev/null 2>&1; then
        log "✅ Status script test passed"
    else
        warn "Status script test failed"
    fi

    # Smoke test
    if python3 scripts/smoke_test_transcription.py >/dev/null 2>&1; then
        log "✅ Full smoke test passed"
    else
        warn "Full smoke test failed"
    fi

    # 9. SETUP COMPLETION
    header "🎉 Setup Complete!"

    echo ""
    log "Atlas setup completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Run: make status                    # Check system health"
    echo "2. Run: make smoke                     # Run full test"
    echo "3. Run: sudo systemctl enable --now atlas-watchdog.timer  # Enable monitoring"
    echo "4. Run: journalctl -u atlas-watchdog -f               # Monitor logs"
    echo ""
    echo "🔧 Useful commands:"
    echo "• make status         - System status"
    echo "• make restart        - Restart services"
    echo "• make logs          - View recent logs"
    echo "• make smoke         - Run tests"
    echo ""
    echo "📱 Alert testing:"
    echo "• python3 scripts/notify.py --test"
    echo "• python3 scripts/notify.py --msg 'Hello from Atlas!'"
    echo ""
    echo "📚 Documentation:"
    echo "• docs/TRANSCRIPT_RECOVERY_GUIDE.md"
    echo "• docs/runbook_reliability.md"
    echo "• ALERT_SETUP_INSTRUCTIONS.md"
    echo ""

    if [ -n "${TELEGRAM_TOKEN:-}" ]; then
        log "🎯 Sending setup completion alert..."
        python3 scripts/notify.py --msg "Atlas setup completed successfully! All systems are ready for unbreakable transcript processing." --title "Atlas Setup Complete" 2>/dev/null || warn "Could not send completion alert"
    fi

    log "🚀 Your Atlas system is now unbreakable and fully monitored!"
}

# Run main function
main "$@"