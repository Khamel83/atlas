-- Downie → Atlas AppleScript Bridge
-- This script can be triggered when Downie fails to process a URL

on sendURLToAtlas(url)
    set atlasServer to "http://atlas.khamel.com:35555"
    set atlasURL to atlasServer & "/ingest?url=" & url

    try
        -- Use curl to send URL to Atlas
        do shell script "curl -s '" & atlasURL & "'"
        log "Sent to Atlas: " & url
    on error errMsg
        log "Failed to send to Atlas: " & errMsg
    end try
end sendURLToAtlas

-- This could be triggered by Downie's failure handling
-- or run periodically to check for failed URLs

-- Example: Check Downie's recent failures
on checkDownieFailures()
    set downieLog to (path to home folder as text) & "Library:Logs:Downie.log"

    try
        set logContent to do shell script "tail -n 50 '" & POSIX path of downieLog & "' | grep -i 'failed\\|error\\|unsupported'"

        if logContent is not "" then
            -- Extract URLs and send to Atlas
            repeat
                try
                    set urlToExtract to do shell script "echo '" & logContent & "' | grep -o 'https\\?://[^ ]*' | head -1"
                    if urlToExtract is not "" then
                        my sendURLToAtlas(urlToExtract)
                    end if
                exit repeat
                on error
                    exit repeat
                end try
            end repeat
        end if
    on error
        log "Could not read Downie log"
    end try
end checkDownieFailures

-- Run the check
checkDownieFailures()