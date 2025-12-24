# Mac Mini Whisper Pipeline

## Architecture

```
Homelab                              Mac Mini
--------                             --------
data/whisper_queue/audio/            ~/atlas-whisper/audio/
        |                                   |
        | (macwhisper_pipeline.sh push)     | MacWhisper watches
        +---------------------------------->+
                                            |
                                            v
                                      MacWhisper Pro
                                            |
                                            v
                                      ~/atlas-whisper/audio/*.txt
                                            |
        +<----------------------------------+
        | (macwhisper_pipeline.sh pull)
        v
data/whisper_queue/transcripts/
        |
        v
   import_whisper_transcripts.py
```

**Key:** MacWhisper outputs `.txt` next to input files (in `audio/`), not in `transcripts/`.
The pipeline script handles this.

## Mac Mini Setup

### Critical Files
- `~/.smb_atlas_creds` - SMB password (chmod 600)
- `~/scripts/mount_atlas_whisper.sh` - Mounts SMB share without GUI prompts
- `~/scripts/health_check.sh` - Verifies everything working
- `~/atlas-whisper/audio/` - MacWhisper watches this folder

### LaunchAgents
- `com.atlas.smb-mount` - Auto-mount SMB every 5 min (for WhisperX legacy, can be disabled)

### MacWhisper Pro Configuration
MacWhisper must be configured to:
- **Watch folder:** `~/atlas-whisper/audio/`
- **Output:** Same folder as input (default behavior)
- **Format:** Plain text (.txt)

Note: WhisperX watcher is disabled. MacWhisper Pro is faster and produces good quality transcripts.

## Troubleshooting

### Check Pipeline Status
```bash
./scripts/macwhisper_pipeline.sh status
```

### Check Health
```bash
ssh mac-mini ~/scripts/health_check.sh
```

### View MacWhisper Queue
```bash
ssh mac-mini "ls ~/atlas-whisper/audio/*.mp3 2>/dev/null | wc -l"
ssh mac-mini "ls ~/atlas-whisper/audio/*.txt 2>/dev/null | wc -l"  # Ready transcripts
```

### Manual Push/Pull
```bash
./scripts/macwhisper_pipeline.sh push   # Send audio to Mac
./scripts/macwhisper_pipeline.sh pull   # Get transcripts back
```

## Past Issues & Fixes

### Kernel Panics (Dec 2024)
**Cause**: SMB mount using `open` (Finder) caused password dialogs every 5 min, blocking WindowServer until watchdog timeout.

**Fix**: Changed to `mount_smbfs` with credentials file - no GUI, no prompts.

### Daemon Crash Loop (Dec 2024)
**Cause**: `atlas_daemon.py` imported from archived script that no longer existed.

**Fix**: Removed dead import, added startup self-test to catch import errors before running.

### Health Check False Failures (Dec 2024)
**Cause**: Script used Linux `timeout` command which doesn't exist on macOS.

**Fix**: Replaced with `stat` which fails fast on stale mounts without needing timeout.

### MacWhisper Output Location (Dec 2024)
**Cause**: MacWhisper outputs `.txt` next to input files, but pipeline looked in `transcripts/` folder.

**Fix**: Updated `macwhisper_pipeline.sh` to look for `.txt` in `audio/` folder.

### WhisperX Disabled (Dec 2024)
**Reason**: MacWhisper Pro is faster and produces equivalent quality.

**Change**: Unloaded `com.atlas.whisperx.plist` LaunchAgent. Code preserved but not running.

## Homelab Side

### Pipeline Commands
```bash
./scripts/macwhisper_pipeline.sh status   # Check queue status
./scripts/macwhisper_pipeline.sh run      # Push, pull, import (full cycle)
./scripts/macwhisper_pipeline.sh push     # Just push audio
./scripts/macwhisper_pipeline.sh pull     # Just pull transcripts
```

### Import Transcripts
```bash
./venv/bin/python scripts/import_whisper_transcripts.py
```

### Check Status
```bash
./venv/bin/python scripts/atlas_status.py
```

---
Last updated: 2025-12-24
