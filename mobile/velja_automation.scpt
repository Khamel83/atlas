-- AppleScript for Velja Integration with Atlas
-- Save this script in Velja's script folder or run via Shortcuts

on process_url(url_data)
    try
        set urlText to url_data's url
        set sourceApp to url_data's source
        set titleText to url_data's title

        -- Log the URL processing
        do shell script "echo 'Processing URL: " & urlText & "' >> /tmp/velja_script.log"

        -- Call Atlas ingestion service
        set atlasScript to "/path/to/atlas/velja_integration.py"
        set shellCommand to "python3 " & atlasScript & " ingest '" & urlText & "' " & sourceApp

        do shell script shellCommand

        return {success:true, message:"URL sent to Atlas"}

    on error errMsg
        do shell script "echo 'Error: " & errMsg & "' >> /tmp/velja_script.log"
        return {success:false, error:errMsg}
    end try
end process_url

-- Main handler for Velja automation
on run argv
    if (count of argv) is 0 then
        return "Usage: osascript velja_automation.scpt <url> [source] [title]"
    end if

    set urlText to item 1 of argv
    set sourceApp to "velja"
    set titleText to ""

    if (count of argv) > 1 then
        set sourceApp to item 2 of argv
    end if

    if (count of argv) > 2 then
        set titleText to item 3 of argv
    end if

    set urlData to {url:urlText, source:sourceApp, title:titleText}
    return process_url(urlData)
end run