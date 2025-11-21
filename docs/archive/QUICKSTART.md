# Atlas Quick Start Guide for Dumb Users

## What This Is

Atlas is a simple digital filing cabinet. Think of it like a box where you can save articles, web pages, and notes to read later.

## What You Need

- A computer (Mac, Windows, or Linux)
- Python 3.9 or higher
- That's it!

## Installation (The Easy Way)

1. **Open Terminal** (on Mac: press `Command + Space`, type "Terminal", press Enter)

2. **Copy and paste these commands** (one at a time):

```bash
cd ~
git clone https://github.com/Khamel83/Atlas.git
cd Atlas
pip install -r requirements.txt
```

## Starting Atlas

1. **Start the web interface**:
```bash
python3 api.py
```

2. **Open your web browser** and go to: `http://localhost:7444`

That's it! Atlas is now running.

## How to Save Stuff

### Method 1: Using the Website (Easiest)

1. Open `http://localhost:7444` in your browser
2. Click "Add Content"
3. Choose what you want to save:
   - **URL**: Paste a web address (like `https://example.com/article`)
   - **Text**: Type or paste text directly
   - **RSS Feed**: Paste a feed URL to automatically get new articles

### Method 2: From Your iPhone (Super Easy)

#### Option A: Using Shortcuts (Recommended)

1. Open the **Shortcuts** app on your iPhone
2. Tap the `+` button to create a new shortcut
3. Tap `+ Add Action`
4. Search for "URL" and select it
5. Enter: `http://YOUR_COMPUTER_IP:7444/content`
6. Tap `+ Add Action` again
7. Search for "Get Contents of URL" and select it
8. Change method to "POST"
9. Tap "Show More"
10. For "Request Body", choose "JSON"
11. Add this JSON:
```json
{
  "content": "Your text here",
  "title": "Article Title"
}
```
12. Save the shortcut as "Save to Atlas"

Now you can share any article or text to this shortcut!

#### Option B: Using Safari

1. Open Safari on your iPhone
2. Go to any article you want to save
3. Tap the **Share** button (square with arrow)
4. Scroll down and tap **"Save to Atlas"** (if you created the shortcut)

### Method 3: From Your Mac

#### Option A: Using the Bookmarklet

1. **Create a bookmark** in Safari/Chrome:
   - Name: `Save to Atlas`
   - URL: `javascript:(function(){var url=window.location.href;var title=document.title;fetch('http://localhost:8000/api/content',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,title:title})}).then(()=>alert('Saved to Atlas!'));})();`

2. **Drag this bookmark to your bookmarks bar**

Now you can click this bookmark on any page to save it to Atlas!

#### Option B: Using Terminal

```bash
# Save a URL
curl -X POST http://localhost:8000/api/content \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article", "title": "Great Article"}'

# Save text
curl -X POST http://localhost:8000/api/content \
  -H "Content-Type: application/json" \
  -d '{"content": "My note here", "title": "My Note"}'
```

## Finding Your Stuff

1. **Open Atlas**: `http://localhost:8000`
2. **Use the search box** to find anything
3. **Browse recent items** on the main page
4. **Check statistics** to see how much you've saved

## Making Atlas Run 24/7

### On Mac

1. **Open Terminal**
2. **Create a launch agent** to run Atlas automatically:
```bash
mkdir -p ~/Library/LaunchAgents
cat > ~/Library/LaunchAgents/com.atlas.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atlas</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/$USER/Atlas/start_web.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF
```

3. **Load it**:
```bash
launchctl load ~/Library/LaunchAgents/com.atlas.plist
```

Now Atlas starts automatically when you log in!

### On Linux/Raspberry Pi

1. **Create a systemd service**:
```bash
sudo nano /etc/systemd/system/atlas.service
```

2. **Paste this content** (replace `YOUR_USERNAME` with your actual username):
```ini
[Unit]
Description=Atlas Digital Filing Cabinet
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/Atlas
ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/Atlas/start_web.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. **Enable the service**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable atlas
sudo systemctl start atlas
```

## Common Problems

### "Atlas won't start"
- Make sure Python 3.9+ is installed: `python3 --version`
- Install requirements: `pip install -r requirements.txt`
- Check if port 8000 is available

### "Can't access from iPhone"
- Make sure your Mac/PC allows connections: go to System Preferences > Security & Privacy > Firewall
- Both devices need to be on the same WiFi network
- Use your computer's local IP address instead of `localhost`:
  - Find your IP: `ifconfig | grep "inet "`
  - Use `http://YOUR_IP:8000` on your iPhone

### "I forgot my Atlas URL"
- It's always `http://localhost:8000` on your computer
- From your phone: `http://YOUR_COMPUTER_IP:8000`

## Need Help?

- Check the full documentation: `README.md`
- Look at the web interface: `http://localhost:8000/docs` for API help
- Atlas keeps working even if you close the terminal - it's designed to be reliable!

---

That's it! You now have a personal digital filing cabinet that just works.