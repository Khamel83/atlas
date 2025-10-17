# Hyperduck + Atlas Setup Instructions

## 🎯 What You Need to Do

**Step 1: Open Hyperduck Preferences**
1. Open Hyperduck on your Mac Mini
2. Click **Hyperduck** in the menu bar (top left)
3. Select **Preferences...** or **Settings...**

**Step 2: Find External Editor Settings**
1. In Preferences, look for tabs like:
   - **External Editor**
   - **Actions**
   - **Integration**
   - **Advanced**

**Step 3: Locate Downie Connection**
You should see something like:
- **Default external editor**: Downie
- **Open with**: Downie.app
- **Application**: Downie

**Step 4: Add Atlas Alongside Downie**

**Option A: If Hyperduck supports multiple external editors**
1. Add **Atlas** as a second external editor
2. Configure it to use: `http://atlas.khamel.com:35555/ingest?url={url}`

**Option B: If Hyperduck only supports one external editor**
1. Create a simple script that calls both Downie and Atlas
2. Set the script as your external editor

## 🧪 Option B Script (if needed)

Create this script on your Mac Mini:

```bash
#!/bin/bash
# Save as: /usr/local/bin/both-downie-atlas.sh

URL="$1"

# Send to Downie (existing behavior)
open -a Downie "$URL"

# Send to Atlas (new)
curl "http://atlas.khamel.com:35555/ingest?url=$(echo "$URL" | sed 's/+/%2B/g' | sed 's/&/%26/g')"
```

Make it executable:
```bash
chmod +x /usr/local/bin/both-downie-atlas.sh
```

Then in Hyperduck, set the external editor to: `/usr/local/bin/both-downie-atlas.sh`

## 🧪 Test the Connection

1. **Test Atlas is working**:
   ```bash
   curl "http://atlas.khamel.com:35555/ingest?url=https://example.com"
   ```

2. **Configure Hyperduck** using the steps above

3. **Test by sending a URL through Hyperduck**

## 🎮 If You Get Stuck

**Can't find the Downie setting?**
1. Look in **Hyperduck → Preferences → External Editor**
2. Check for **Actions** or **Integration** settings
3. Look for any setting that mentions "Downie" or "external editor"

**Still can't find it?**
- Send me a screenshot of Hyperduck's Preferences window
- Or tell me what tabs/options you see in Preferences

## 📊 Expected Result

Once configured:
- Hyperduck sends URLs to both Downie and Atlas
- Downie downloads videos it can handle
- Atlas stores everything with smart content detection
- Nothing gets lost!

**Bottom Line**: You just need to tell Hyperduck to also send URLs to Atlas alongside Downie.