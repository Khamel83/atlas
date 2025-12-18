# Mac Mini WhisperX Setup

Scripts for running WhisperX with speaker diarization on the Mac Mini M4.

## Quick Setup

### 1. Copy Scripts to Mac Mini

```bash
# On Mac Mini
mkdir -p ~/scripts ~/logs
# Copy whisperx_watcher.py to ~/scripts/
```

### 2. Install WhisperX

```bash
python3 -m venv ~/whisperx-env
source ~/whisperx-env/bin/activate
pip install whisperx pyannote.audio
```

### 3. HuggingFace Token

1. Create account at https://huggingface.co
2. Accept pyannote license: https://huggingface.co/pyannote/speaker-diarization-3.1
3. Create token: https://huggingface.co/settings/tokens
4. Save token:

```bash
mkdir -p ~/.huggingface
echo "YOUR_TOKEN" > ~/.huggingface/token
```

### 4. Mount SMB Share

```bash
# The share should already be mounted at /Volumes/atlas-whisper
ls /Volumes/atlas-whisper/audio/

# If not mounted, mount it:
# mount_smbfs //khamel83@homelab/atlas-whisper /Volumes/atlas-whisper
```

### 5. Test WhisperX

```bash
source ~/whisperx-env/bin/activate
TEST_FILE=$(ls /Volumes/atlas-whisper/audio/*.mp3 | head -1)
whisperx "$TEST_FILE" --model large-v3 --diarize --language en --output_dir ~/whisperx-test/
```

Check for speaker labels in output JSON:
```bash
cat ~/whisperx-test/*.json | grep speaker
```

### 6. Install LaunchAgent (Auto-Start)

```bash
# Update paths in plist if your username isn't 'khamel'
cp com.atlas.whisperx.plist ~/Library/LaunchAgents/

# Load (start now)
launchctl load ~/Library/LaunchAgents/com.atlas.whisperx.plist

# Check status
launchctl list | grep whisperx

# View logs
tail -f ~/logs/whisperx.log
```

### 7. Unload (Stop)

```bash
launchctl unload ~/Library/LaunchAgents/com.atlas.whisperx.plist
```

## Files

- `whisperx_watcher.py` - Watch folder script, transcribes new MP3s
- `com.atlas.whisperx.plist` - LaunchAgent for auto-start

## Configuration

Edit `whisperx_watcher.py` to change:
- `WATCH_DIR` - Where to watch for MP3s (default: SMB mount)
- `OUTPUT_DIR` - Where to save JSON transcripts
- `MODEL` - WhisperX model (default: large-v3)
- `BATCH_SIZE` - Reduce if running out of memory (default: 8)
- `POLL_INTERVAL` - How often to check for new files (default: 60s)

## Troubleshooting

### SMB not mounted
```bash
# Check mount
ls /Volumes/atlas-whisper/audio/

# Remount if needed (adjust user/server as needed)
mount_smbfs //khamel83@homelab/atlas-whisper /Volumes/atlas-whisper
```

### Out of memory
Reduce BATCH_SIZE in whisperx_watcher.py from 8 to 4 or 2.

### No speaker labels
Make sure you accepted the pyannote license and have a valid HF token.
