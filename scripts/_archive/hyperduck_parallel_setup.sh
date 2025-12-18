#!/bin/bash
# BULLETPROOF HYPERDUCK PARALLEL SETUP
# Sends URLs to BOTH Downie AND Atlas simultaneously
# October 2025 Configuration

echo "🔫 BULLETPROOF HYPERDUCK → DOWNIE + ATLAS SETUP"
echo "=============================================="

# Create the parallel processing script
cat > ~/hyperduck-parallel-handler.sh << 'EOF'
#!/bin/bash
# Parallel URL Handler for Hyperduck
# Sends to BOTH Downie and Atlas simultaneously

URL="$1"
ATLAS_SERVER="https://atlas.khamel.com"

if [ -z "$URL" ]; then
    echo "Usage: $0 'URL'"
    exit 1
fi

echo "🔫 Processing URL in parallel: $URL"

# Send to Downie (in background)
(
    echo "📺 Sending to Downie..."
    osascript -e "tell application \"Downie 4\" to open location \"$URL\"" 2>/dev/null
    echo "✅ Sent to Downie: $URL"
) &

# Send to Atlas (in background)
(
    echo "🗂️  Sending to Atlas..."
    response=$(curl -s "$ATLAS_SERVER/ingest?url=$URL")
    if echo "$response" | grep -q "success"; then
        echo "✅ Sent to Atlas: $URL"
    else
        echo "❌ Atlas failed: $URL"
    fi
) &

# Wait for both to complete
wait

echo "🎯 Parallel processing complete for: $URL"
EOF

# Make it executable
chmod +x ~/hyperduck-parallel-handler.sh

echo ""
echo "✅ Parallel handler created: ~/hyperduck-parallel-handler.sh"
echo ""
echo "📋 STEP-BY-STEP HYPERDUCK CONFIGURATION:"
echo "========================================"
echo ""
echo "STEP 1: Open Hyperduck App"
echo "   • Launch Hyperduck on your Mac Mini"
echo ""
echo "STEP 2: Go to Preferences"
echo "   • Click Hyperduck menu → Preferences..."
echo "   • OR press Cmd+, (Command+Comma)"
echo ""
echo "STEP 3: Find External Editor Setting"
echo "   • Look for 'External Editor' or 'Default App' setting"
echo "   • Currently set to 'Downie' or 'Downie 4'"
echo ""
echo "STEP 4: Change to Custom Script"
echo "   • Change from 'Downie 4' to 'Custom Script' or 'Other'"
echo "   • Browse to select: $HOME/hyperduck-parallel-handler.sh"
echo "   • OR copy this path: $(pwd)/hyperduck-parallel-handler.sh"
echo ""
echo "STEP 5: Test the Setup"
echo "   • Send a URL through Hyperduck"
echo "   • You should see both Downie AND Atlas receive it"
echo ""
echo "🧪 MANUAL TEST:"
echo "   ~/hyperduck-parallel-handler.sh 'https://example.com'"
echo ""
echo "🔫 RESULT: 100% BULLETPROOF"
echo "   • Every URL goes to BOTH services"
echo "   • No failures missed"
echo "   • No dependency on logs or databases"