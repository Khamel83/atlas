# Atlas Tutorial 7: Automation and Scheduling Script

## Introduction
Hello and welcome to the seventh tutorial in the Atlas series. In this video, I'll show you how to automate your content ingestion with RSS feeds, email forwarding, and custom schedules. By the end of this tutorial, you'll be able to set up automated workflows that keep your Atlas system constantly fed with new content.

Before we begin, make sure you have Atlas installed and configured as shown in the previous tutorials. Let's get started!

## Section 1: Setting Up RSS Feed Automation
Let's start by setting up automated RSS feed processing.

[Screen recording: Terminal and text editor showing OPML file creation]

First, we'll create an OPML file with our RSS feeds:
```bash
nano inputs/podcasts.opml
```

Add your favorite RSS feeds:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>My Atlas Feeds</title>
  </head>
  <body>
    <outline text="Technology">
      <outline
        title="Tech News"
        type="rss"
        xmlUrl="https://example.com/tech-rss" />
      <outline
        title="Programming Blog"
        type="rss"
        xmlUrl="https://example.com/programming-rss" />
    </outline>
    <outline text="Science">
      <outline
        title="Science Daily"
        type="rss"
        xmlUrl="https://example.com/science-rss" />
    </outline>
  </body>
</opml>
```

Now let's set up a cron job to process these feeds daily:

[Screen recording: Terminal showing crontab editing]
```bash
crontab -e
```

Add this line to run RSS processing every day at 8 AM:
```
0 8 * * * cd /home/ubuntu/dev/atlas && python run.py --podcasts
```

## Section 2: Configuring Email Forwarding
Let's set up email forwarding to automatically process emails sent to a dedicated address.

[Screen recording: Text editor showing .env configuration]

First, add your email credentials to the .env file:
```bash
nano .env
```

Add these lines:
```
# Email configuration for automated processing
EMAIL_PROVIDER=gmail
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_POLL_INTERVAL=300  # Check every 5 minutes
```

Now let's configure email forwarding in your email provider:
1. Open your email provider's settings
2. Navigate to forwarding settings
3. Add forwarding to your Atlas email address
4. Set up filters to automatically forward specific senders or subjects

## Section 3: Creating Custom Processing Schedules
Atlas allows you to create custom processing schedules for different content types.

[Screen recording: Terminal showing custom scheduler script]

Let's create a custom scheduler script:
```bash
nano custom_scheduler.py
```

[Screen recording: Text editor showing Python script]

```python
#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.config import load_config
from run import main as run_atlas

def should_run_daily_processing():
    """Determine if daily processing should run"""
    # Custom logic here
    return True

def should_run_weekly_processing():
    """Determine if weekly processing should run"""
    today = datetime.now()
    # Run on Sundays
    return today.weekday() == 6

def main():
    config = load_config()

    # Daily processing
    if should_run_daily_processing():
        print("Running daily processing...")
        # Simulate command line arguments
        sys.argv = ['run.py', '--all']
        run_atlas()

    # Weekly processing
    if should_run_weekly_processing():
        print("Running weekly processing...")
        # Custom weekly tasks
        run_weekly_tasks(config)

def run_weekly_tasks(config):
    """Run weekly maintenance tasks"""
    # Add your custom weekly tasks here
    print("Weekly tasks completed")

if __name__ == "__main__":
    main()
```

Make the script executable:
```bash
chmod +x custom_scheduler.py
```

Now let's set up a cron job to run this custom scheduler:

[Screen recording: Terminal showing crontab editing]
```bash
crontab -e
```

Add this line to run the custom scheduler every day at 7 AM:
```
0 7 * * * cd /home/ubuntu/dev/atlas && python custom_scheduler.py
```

## Section 4: Using systemd Timers for Advanced Scheduling
For more advanced scheduling, let's use systemd timers.

[Screen recording: Terminal and text editor showing systemd service creation]

First, create a service file:
```bash
sudo nano /etc/systemd/system/atlas-daily.service
```

Add this content:
```ini
[Unit]
Description=Atlas Daily Processing
After=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/dev/atlas
ExecStart=/home/ubuntu/dev/atlas/venv/bin/python run.py --all
```

Next, create a timer file:
```bash
sudo nano /etc/systemd/system/atlas-daily.timer
```

Add this content:
```ini
[Unit]
Description=Run Atlas Daily Processing
Requires=atlas-daily.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start the timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable atlas-daily.timer
sudo systemctl start atlas-daily.timer
```

## Section 5: Setting Up IFTTT Integration
Let's set up integration with IFTTT (If This Then That) for even more automation possibilities.

[Screen recording: Web browser showing IFTTT]

1. Go to https://ifttt.com and create an account
2. Create a new applet
3. Choose a trigger (e.g., "New feed item" from RSS)
4. Choose "Webhooks" as the action
5. Configure the webhook to send data to your Atlas server

IFTTT webhook URL format:
```
http://your-atlas-server:8000/api/v1/content/save
```

Method: POST
Content Type: application/json
Body:
```json
{
  "title": "{{EntryTitle}}",
  "url": "{{EntryUrl}}",
  "content": "{{EntryContent}}"
}
```

## Section 6: Setting Up Zapier Integration
Similarly, let's set up integration with Zapier.

[Screen recording: Web browser showing Zapier]

1. Go to https://zapier.com and create an account
2. Create a new Zap
3. Choose a trigger (e.g., "New Email" from Gmail)
4. Choose "Webhooks by Zapier" as the action
5. Configure the webhook to send data to your Atlas server

Zapier webhook URL:
```
http://your-atlas-server:8000/api/v1/email/process
```

Method: POST
Data:
```json
{
  "subject": "{{Subject}}",
  "sender": "{{FromName}}",
  "content": "{{BodyPlain}}",
  "attachments": "{{Attachments}}"
}
```

## Section 7: Monitoring Automated Processes
It's important to monitor your automated processes to ensure they're working correctly.

[Screen recording: Terminal showing log monitoring]

Monitor logs:
```bash
tail -f logs/atlas_service.log
```

Check system status:
```bash
python atlas_service_manager.py status
```

View processing statistics:
```bash
python atlas_status.py --detailed
```

## Section 8: Troubleshooting Automation Issues
When automation issues occur, here's how to troubleshoot them.

[Screen recording: Terminal showing troubleshooting]

Common issues and solutions:

1. **"Feed not found" errors**:
   - Verify RSS URLs are correct
   - Check if feeds require authentication
   - Test feeds in a browser

2. **"No new content"**:
   - Check feed update frequency
   - Verify filtering settings
   - Review last processed timestamps

3. **"Rate limit exceeded"**:
   - Implement delays between requests
   - Use caching to reduce requests
   - Contact feed providers for higher limits

4. **Email processing failures**:
   - Verify email credentials
   - Check spam folder for bounced messages
   - Review email provider security settings

5. **Cron job issues**:
   - Verify cron syntax
   - Check system timezone settings
   - Ensure Atlas service is running

## Conclusion
That's it for the automation and scheduling tutorial. You should now be able to set up automated content ingestion with RSS feeds, email forwarding, and custom schedules.

In the next tutorial, we'll cover maintenance and backup. If you found this helpful, please like and subscribe for more Atlas tutorials. Thanks for watching, and see you next time!