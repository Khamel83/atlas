# Atlas Quick Start - Get Running in 10 Minutes

## What is Atlas?
Atlas is your personal AI knowledge system. It captures everything you read, hear, and think - then uses AI to help you discover insights and connections across all your information.

**Key Features:**
- 🎤 **Voice Capture** - "Hey Siri, save to Atlas"
- 🧠 **AI Insights** - Find patterns across all your content
- 🔍 **Semantic Search** - Find content by meaning, not just keywords
- 📱 **Mac/iOS Integration** - Capture from anywhere
- 🤖 **6 Cognitive Features** - Proactive insights, temporal analysis, Socratic questioning

## Prerequisites (5 minutes)
- **macOS**: 11.0+ (Big Sur or later)
- **Python**: 3.9+ (check with `python3 --version`)
- **Storage**: 2GB free space minimum

## Installation (3 minutes)

### Step 1: Clone and Setup
```bash
# Download Atlas
git clone https://github.com/your-org/atlas.git
cd atlas

# Quick install (handles everything)
./quick_install.sh
```

### Step 2: Verify Installation
```bash
# Check system status
python3 atlas_status.py
# Should show: ✅ Atlas is ready!
```

## First Use (2 minutes)

### Install iOS Shortcuts

**🎯 Choose Your Method:**

#### Method 1: Install from Your Phone (Easiest)
1. **Get your installation URL**:
   ```bash
   # This shows the exact URL to use on your iPhone
   ./get_mobile_url.sh
   ```
2. **Open the URL** on your iPhone (from the output above)
3. **Tap**: Each shortcut to download and install
4. **Follow**: iOS prompts to "Get Shortcut" → "Add Shortcut"

#### Method 2: Install from Computer
1. **Run**: `./install_shortcuts.sh` (on your Mac)
2. **Follow**: Terminal instructions to install

### Test Voice Capture
1. **Say**: "Hey Siri, save to Atlas"
2. **Speak**: "This is my first Atlas note"
3. **Check**: Visit `https://atlas.khamel.com/ask/html`

### Test Web Dashboard
1. **Open**: `https://atlas.khamel.com/ask/html`
2. **Try**: Click "Proactive Content Surfacer"
3. **Search**: Type "first atlas note" in search box

## What's Next?

### 📚 **Add Some Content**
- Drop a PDF in `~/Documents/Atlas/articles/`
- Save a webpage with browser bookmarklet
- Record voice memos with Siri shortcuts

### 🧠 **Explore AI Features**
Visit `https://atlas.khamel.com/ask/html` and try:
- **Proactive Content Surfacer** - Surfaces forgotten relevant content
- **Temporal Relationships** - Shows patterns over time
- **Socratic Questions** - Thought-provoking questions about your content

### 📖 **Read the Guides**
- [Mac User Guide](../docs/user-guides/MAC_USER_GUIDE.md) - Complete Mac integration
- [Mobile Guide](../docs/user-guides/MOBILE_GUIDE.md) - iPhone/iPad usage
- [Ingestion Guide](../docs/user-guides/INGESTION_GUIDE.md) - All ways to add content

## Common Issues

### "Hey Siri" Not Working
1. **Settings → Siri & Search → Listen for "Hey Siri"**
2. **Re-train Siri**: "Set Up Hey Siri Again"
3. **Check shortcuts**: Open Shortcuts app, verify Atlas shortcuts imported

### Atlas Won't Start
```bash
# Check Python environment
python3 --version  # Should be 3.9+

# Check dependencies
pip3 install -r requirements.txt

# Manual start
python3 atlas_service_manager.py start
```

### Web Dashboard Not Loading
1. **Check Atlas is running**: `python3 atlas_status.py`
2. **Try different port**: Edit `.env` and change `ATLAS_PORT=8001`
3. **Check firewall**: System Preferences → Security & Privacy

## Support
- **Documentation**: Full guides in `docs/user-guides/`
- **GitHub Issues**: Report problems and request features
- **Status Check**: Run `python3 atlas_diagnostics.py` for system info

---

**🎉 Congratulations! Atlas is now your personal AI knowledge companion.**

**Next**: Try saying "Hey Siri, save to Atlas" and speak a thought, then visit `https://atlas.khamel.com/ask/html` to see your AI insights!