# Atlas Production Deployment Guide

## Ubuntu Deployment (OCI VM / Raspberry Pi)

### Prerequisites
```bash
sudo apt update && sudo apt install python3 python3-pip git sqlite3
```

### 1. Clone and Setup Atlas
```bash
git clone https://github.com/Khamel83/Atlas.git
cd Atlas
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp env.template .env
nano .env
```

**Required settings:**
```bash
# Your OpenRouter API key for AI processing
OPENROUTER_API_KEY=your_actual_api_key_here

# Atlas environment
ATLAS_ENV=production
DATA_DIRECTORY=output

# Enable AI features
AI_FEATURES_ENABLED=true
AI_MODEL=google/gemini-2.0-flash-001
```

### 3. Start Atlas System

#### Option A: Quick Start (Manual)
```bash
# ONE COMMAND STARTUP - starts everything!
./start_atlas.sh

# That's it! Atlas will auto-configure and start all services
# (Won't auto-start on reboot - you'll need to run this again)
```

#### Option B: Install Auto-Start (Recommended - PiHole-like)
```bash
# Install Atlas like PiHole - runs 24/7 and survives reboots
./install_atlas_autostart.sh

# That's it! Atlas now starts automatically on boot
```

**What the installation does:**
- ✅ Auto-starts on boot (30-second delay for system stability)
- ✅ Health checks every 5 minutes with auto-restart
- ✅ Runs 24/7 with automatic failure recovery
- ✅ Survives reboots and system updates
- ✅ Simple cron-based reliability (no systemd complexity)

### 4. Monitor Status (Anytime)
```bash
python3 atlas_monitor.py         # Comprehensive system health

# If installed with auto-start:
tail -f logs/autostart.log       # Boot startup logs
tail -f logs/atlas_manager.log   # Service manager logs
crontab -l | grep atlas          # View autostart entries
```

---

## Mac Deployment (Mac Mini Worker)

### Prerequisites
```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install whisper-cpp yt-dlp python3
```

### 1. Get Atlas Worker Client
```bash
# Copy from your Ubuntu Atlas server:
scp user@your-server:/path/to/Atlas/atlas_controlled_mac_client.py ~/
scp user@your-server:/path/to/Atlas/mac_mini_setup.sh ~/

# Or download directly from GitHub:
wget https://raw.githubusercontent.com/Khamel83/Atlas/main/atlas_controlled_mac_client.py
wget https://raw.githubusercontent.com/Khamel83/Atlas/main/mac_mini_setup.sh
```

### 2. Install Python Dependencies
```bash
pip3 install requests watchdog
```

### 3. Configure Atlas Connection
```bash
export ATLAS_URL=http://your-server-ip:8000
export ATLAS_API_KEY=optional_key
export ATLAS_WORKER_ID=mac_mini_main
```

### 4. Start Worker
```bash
python3 atlas_controlled_mac_client.py
```

**Expected output:**
```
🤖 Atlas Worker Client Starting
🆔 Worker ID: mac_mini_main
🌐 Atlas URL: http://192.168.1.100:8000
✅ Worker registered: mac_mini_main
🔄 Polling Atlas for jobs... (Ctrl+C to stop)
```

### 5. Auto-Start (Optional)
Create `~/Library/LaunchAgents/com.atlas.worker.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atlas.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/yourusername/atlas_controlled_mac_client.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Then:
```bash
launchctl load ~/Library/LaunchAgents/com.atlas.worker.plist
```

---

## How It Works

### Smart Dispatching
Atlas automatically decides what to process locally vs send to Mac Mini:

```
YouTube 30min video → Mac Mini (save storage/CPU)
Article           → Atlas (immediate processing)
Podcast 5min      → Atlas (quick transcription)
Audio file upload → Mac Mini (better transcription)
```

### Job Flow
1. **Content arrives** at Atlas (articles, YouTube, podcasts)
2. **Smart dispatcher** analyzes content type, size, duration
3. **Decision made**: Process locally OR queue for Mac Mini
4. **If queued**: Mac Mini polls, downloads, transcribes, reports back
5. **Atlas processes** all results into searchable knowledge base

### Atlas Independence
- **Atlas never stops** - continues ingesting content 24/7
- **Mac Mini optional** - Atlas works fine without it
- **Jobs queue** - When Mac Mini comes online, processes backlog
- **Never loses content** - Metadata captured immediately

---

## Troubleshooting

### Ubuntu Issues
```bash
# Check Atlas status
python3 atlas_status.py

# View logs
tail -f output/logs/*.log

# Check background service
ps aux | grep atlas

# Restart everything
pkill -f atlas_background_service
python3 atlas_background_service.py
```

### Mac Issues
```bash
# Check if worker is registered
curl http://your-server:8000/api/v1/worker/status

# Test connection
curl http://your-server:8000/api/v1/health

# Check dependencies
which whisper
which yt-dlp
python3 -c "import requests; print('✅ Requests OK')"
```

### Common Issues
- **Atlas not processing**: Check OPENROUTER_API_KEY in .env
- **Mac Mini not connecting**: Verify ATLAS_URL points to server IP:8000
- **Jobs not being created**: Check API server is running on port 8000
- **Transcription failing**: Ensure whisper-cpp and yt-dlp installed on Mac

---

## Quick Start Commands

### Ubuntu Server
```bash
cd Atlas
./start_atlas.sh                           # One command - starts everything!
python3 atlas_monitor.py                   # Check comprehensive status
```

### Mac Worker
```bash
export ATLAS_URL=http://your-server:8000
python3 atlas_controlled_mac_client.py     # Start worker
```

### Test Integration
```bash
# On Ubuntu - create a job manually
curl -X POST https://atlas.khamel.com/api/v1/worker/jobs \
  -H "Content-Type: application/json" \
  -d '{"type": "transcribe_youtube", "data": {"url": "https://youtube.com/watch?v=test", "title": "Test Video"}}'

# Check job queue
curl https://atlas.khamel.com/api/v1/worker/status
```