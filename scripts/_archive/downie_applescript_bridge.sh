#!/bin/bash
# AppleScript-based Downie → Atlas Bridge
# Uses AppleScript to try Downie first, then Atlas

cat > ~/downie_atlas_applescript.scpt << 'EOF'
on run argv
    set targetURL to item 1 of argv
    set atlasServer to "https://atlas.khamel.com"

    tell application "System Events"
        -- Try Downie first
        try
            tell application "Downie 4"
                activate
                open location targetURL
            end tell

            -- Wait for Downie to process
            delay 5

            -- Check if Downie failed (this is approximate)
            -- In practice, you'd check Downie's status or database
            set downieSuccess to true

            -- If we detect failure, send to Atlas
            if not downieSuccess then
                set atlasURL to atlasServer & "/ingest?url=" & targetURL
                do shell script "curl -s '" & atlasURL & "'"
                display notification "URL sent to Atlas: " & targetURL
            end if

        on error errorMessage
            -- Downie failed, send to Atlas
            set atlasURL to atlasServer & "/ingest?url=" & targetURL
            do shell script "curl -s '" & atlasURL & "'"
            display notification "Downie failed, sent to Atlas: " & targetURL
        end try
    end tell
end run
EOF

# Make AppleScript executable
chmod +x ~/downie_atlas_applescript.scpt

echo "✅ AppleScript bridge created!"
echo "📋 Usage: osascript ~/downie_atlas_applescript.scpt 'https://example.com'"
echo ""
echo "💡 To use with Hyperduck, configure it to run:"
echo "   osascript ~/downie_atlas_applescript.scpt 'URL'"