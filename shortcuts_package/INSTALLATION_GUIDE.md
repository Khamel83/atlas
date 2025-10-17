# Atlas Apple Shortcuts Installation Guide

## Quick Installation

1. **Download all shortcuts** from this package
2. **Open each .shortcut file** on your iPhone/iPad or Mac
3. **Tap "Add Shortcut"** when prompted
4. **Allow permissions** when asked (Network access, etc.)

## Available Shortcuts

### Basic Shortcuts

- **capture_thought.shortcut** - Quickly capture any thought or note
- **log_meal.shortcut** - Log meals with photos and descriptions
- **log_mood.shortcut** - Track mood and energy levels
- **start_focus.shortcut** - Begin focused work sessions

### Advanced Shortcuts

- **capture_evening_thought.shortcut** - End-of-day reflection capture
- **log_home_activity_context.shortcut** - Track home activities with context
- **log_work_task_context.shortcut** - Log work tasks with detailed context

## Setup Steps

### 1. Download and Install

1. Download all .shortcut files to your device
2. Open each file and tap "Add Shortcut"
3. Grant necessary permissions when prompted

### 2. Configure Atlas Server

Each shortcut needs to know your Atlas server address:

1. Open the Shortcuts app
2. Find the Atlas shortcut
3. Tap "Edit"
4. Look for the "Text" action with "http://localhost:8000"
5. Replace with your Atlas server URL if different

### 3. Test Installation

1. Run "Capture Thought" shortcut
2. Enter a test note
3. Check that it appears in your Atlas dashboard at http://localhost:8000/ask/html

## Troubleshooting

### Shortcut Won't Install
- Make sure you're opening the .shortcut file on iOS/macOS
- Try downloading the file again
- Check that Shortcuts app is up to date

### Network Errors
- Verify your Atlas server is running: `./venv/bin/python atlas_status.py`
- Check the server URL in the shortcut matches your setup
- Ensure your device can reach the Atlas server

### Permission Issues
- Go to Settings > Shortcuts > Allow Running Scripts
- Enable "Allow Untrusted Shortcuts" if needed
- Grant network and notification permissions

## Voice Commands

After installation, you can use:
- "Hey Siri, Capture Thought"
- "Hey Siri, Log Meal"
- "Hey Siri, Log Mood"
- "Hey Siri, Start Focus"

## Next Steps

1. **Customize shortcuts** for your workflow
2. **Add to Home Screen** for quick access
3. **Set up automation triggers** for routine captures
4. **Explore the Atlas dashboard** to see your captured content

For more help, see the full user guides in the docs/user-guides/ directory.