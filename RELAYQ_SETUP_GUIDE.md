# RelayQ Setup Guide - Complete Installation

**Date**: 2025-11-04
**Purpose**: Step-by-step guide to set up RelayQ on your physical machines
**Time Required**: 1-2 hours per machine

---

## Overview

This guide will help you set up RelayQ to offload compute-intensive tasks (podcast transcription, video processing) from your Atlas OCI VM to your physical machines (Mac mini, Raspberry Pi 4, Raspberry Pi 3).

**Architecture**:
```
Atlas (OCI VM) → GitHub Actions (queue) → Self-hosted runners (your machines)
```

**What you'll set up**:
- ✅ GitHub Actions self-hosted runners on each machine
- ✅ Whisper for local transcription
- ✅ FFmpeg for audio/video processing
- ✅ RelayQ workflows in GitHub repository

---

## Prerequisites

### What You Need

1. **GitHub Account** with a repository for RelayQ
   - Repo: `Khamel83/relayq` (or create new)
   - Admin access to add runners

2. **GitHub Personal Access Token**
   - Scopes: `repo`, `workflow`, `admin:org` (if using org runners)
   - Create at: https://github.com/settings/tokens

3. **Physical Machines** with:
   - Mac mini: macOS 12+ (Apple Silicon preferred)
   - Raspberry Pi 4: Ubuntu 22.04 or Raspberry Pi OS
   - Raspberry Pi 3: Ubuntu 22.04 or Raspberry Pi OS (lighter tasks)

4. **Network Access**:
   - All machines can reach GitHub.com (HTTPS outbound)
   - No inbound ports needed

---

## Part 1: Create RelayQ Repository

### Step 1: Create GitHub Repository

```bash
# Option A: Create new repository
gh repo create Khamel83/relayq --public --description "RelayQ: GitHub Actions-based job queue for Atlas"

# Option B: Use existing repository
# Just navigate to https://github.com/Khamel83/relayq
```

### Step 2: Clone Repository Locally

```bash
# On your development machine (or directly on OCI VM)
cd ~
git clone https://github.com/Khamel83/relayq.git
cd relayq
```

### Step 3: Create Basic Structure

```bash
# Create directory structure
mkdir -p .github/workflows
mkdir -p bin
mkdir -p scripts
mkdir -p config

# Create README
cat > README.md << 'EOF'
# RelayQ

GitHub Actions-based job queue for offloading compute tasks to self-hosted runners.

## Runners

- **macmini**: Mac mini (Apple Silicon) - Heavy audio/video processing
- **rpi4**: Raspberry Pi 4 - Light audio processing
- **rpi3**: Raspberry Pi 3 - Background tasks, overflow

## Workflows

- `transcribe_audio.yml`: Audio transcription with Whisper
- `process_youtube.yml`: YouTube video download and transcription
- `process_bulk.yml`: Batch processing tasks

## Usage

Submit jobs via GitHub Actions dispatch:

```bash
gh workflow run transcribe_audio.yml -f url=https://example.com/audio.mp3 -f backend=local
```

## Integration

Used by Atlas (https://github.com/Khamel83/atlas) for:
- Podcast transcription
- YouTube video processing
- Bulk content downloads
EOF

git add README.md
git commit -m "docs: Initial RelayQ repository setup"
git push origin main
```

---

## Part 2: Set Up Self-Hosted Runners

### Runner Installation - Mac mini

**Connect to your Mac mini**:

```bash
# SSH into Mac mini
ssh user@macmini.local

# Or if using IP address
ssh user@192.168.1.XXX
```

**Install Dependencies**:

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install python@3.11 ffmpeg git wget

# Install Whisper
pip3 install openai-whisper

# Verify installations
whisper --help
ffmpeg -version
python3 --version
```

**Download and Configure Runner**:

```bash
# Create runner directory
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download latest runner (check https://github.com/actions/runner/releases for latest version)
curl -o actions-runner-osx-arm64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-osx-arm64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-osx-arm64-2.311.0.tar.gz

# Configure runner
# Get registration token from: https://github.com/Khamel83/relayq/settings/actions/runners/new
./config.sh --url https://github.com/Khamel83/relayq --token YOUR_REGISTRATION_TOKEN

# When prompted:
# - Runner name: macmini
# - Labels: self-hosted,macOS,ARM64,macmini,audio,video,heavy
# - Work folder: _work (default)

# Test runner
./run.sh
```

**Set Up as Service (Auto-start)**:

```bash
# Install as macOS service
sudo ./svc.sh install

# Start service
sudo ./svc.sh start

# Check status
sudo ./svc.sh status

# Enable on boot
sudo ./svc.sh enable
```

**Create RelayQ Config**:

```bash
# Create config directory
mkdir -p ~/.config/relayq

# Create environment file
cat > ~/.config/relayq/env << 'EOF'
# RelayQ Runner Configuration - Mac mini
ASR_BACKEND=local
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
OPENAI_API_KEY=your_openai_key_here
FFMPEG_PATH=/opt/homebrew/bin/ffmpeg
TEMP_DIR=/tmp/relayq
MAX_CONCURRENT_JOBS=2
EOF

# Create temp directory
mkdir -p /tmp/relayq
```

### Runner Installation - Raspberry Pi 4

**Connect to your Raspberry Pi 4**:

```bash
ssh pi@raspberrypi4.local
# Or: ssh pi@192.168.1.XXX
```

**Install Dependencies**:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip ffmpeg git wget curl

# Install Whisper
pip3 install openai-whisper

# Verify
whisper --help
ffmpeg -version
```

**Download and Configure Runner**:

```bash
# Create runner directory
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download latest ARM64 runner
curl -o actions-runner-linux-arm64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-arm64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-linux-arm64-2.311.0.tar.gz

# Configure
./config.sh --url https://github.com/Khamel83/relayq --token YOUR_REGISTRATION_TOKEN

# When prompted:
# - Runner name: rpi4
# - Labels: self-hosted,Linux,ARM64,rpi4,audio,light
# - Work folder: _work (default)

# Test
./run.sh
```

**Set Up as Service**:

```bash
# Install service
sudo ./svc.sh install

# Start
sudo ./svc.sh start

# Enable on boot
sudo ./svc.sh enable
```

**Create Config**:

```bash
mkdir -p ~/.config/relayq
cat > ~/.config/relayq/env << 'EOF'
# RelayQ Runner Configuration - Raspberry Pi 4
ASR_BACKEND=local
WHISPER_MODEL=tiny
WHISPER_DEVICE=cpu
FFMPEG_PATH=/usr/bin/ffmpeg
TEMP_DIR=/tmp/relayq
MAX_CONCURRENT_JOBS=1
EOF

mkdir -p /tmp/relayq
```

### Runner Installation - Raspberry Pi 3

**Connect to RPi3**:

```bash
ssh pi@raspberrypi3.local
```

**Install Dependencies**:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install minimal packages (RPi3 is slower)
sudo apt install -y python3 python3-pip git curl

# Skip Whisper on RPi3 (too slow) - use for overflow tasks only
```

**Download and Configure Runner**:

```bash
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download ARMv7 runner (32-bit for RPi3)
curl -o actions-runner-linux-arm-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-arm-2.311.0.tar.gz

tar xzf ./actions-runner-linux-arm-2.311.0.tar.gz

./config.sh --url https://github.com/Khamel83/relayq --token YOUR_REGISTRATION_TOKEN

# When prompted:
# - Runner name: rpi3
# - Labels: self-hosted,Linux,ARM,rpi3,overflow,verylight
# - Work folder: _work (default)

# Install and start service
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh enable
```

**Create Config**:

```bash
mkdir -p ~/.config/relayq
cat > ~/.config/relayq/env << 'EOF'
# RelayQ Runner Configuration - Raspberry Pi 3
# Only lightweight tasks - no Whisper
TEMP_DIR=/tmp/relayq
MAX_CONCURRENT_JOBS=1
EOF

mkdir -p /tmp/relayq
```

---

## Part 3: Create RelayQ Workflows

### Workflow 1: Audio Transcription (Primary Use Case)

Create `.github/workflows/transcribe_audio.yml`:

```yaml
name: Transcribe Audio

on:
  workflow_dispatch:
    inputs:
      url:
        description: 'Audio file URL'
        required: true
        type: string
      backend:
        description: 'ASR backend (local, openai, router)'
        required: false
        type: string
        default: 'local'
      model:
        description: 'Whisper model (tiny, base, small, medium, large)'
        required: false
        type: string
        default: 'base'
      runner_preference:
        description: 'Runner preference (macmini, rpi4, pooled)'
        required: false
        type: string
        default: 'pooled'

jobs:
  transcribe:
    name: Transcribe Audio File
    runs-on: ${{ inputs.runner_preference == 'macmini' && 'macmini' || (inputs.runner_preference == 'rpi4' && 'rpi4' || 'self-hosted') }}
    timeout-minutes: 60

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install openai-whisper requests

      - name: Download audio file
        id: download
        run: |
          mkdir -p /tmp/relayq
          cd /tmp/relayq

          # Extract filename from URL
          FILENAME=$(basename "${{ inputs.url }}")

          # Download
          wget -O "$FILENAME" "${{ inputs.url }}"

          echo "audio_file=/tmp/relayq/$FILENAME" >> $GITHUB_OUTPUT

      - name: Transcribe with Whisper
        id: transcribe
        run: |
          cd /tmp/relayq

          # Transcribe
          whisper "${{ steps.download.outputs.audio_file }}" \
            --model ${{ inputs.model }} \
            --output_format txt \
            --output_dir .

          # Get transcript filename (Whisper adds .txt extension)
          TRANSCRIPT_FILE="${{ steps.download.outputs.audio_file }}.txt"

          echo "transcript_file=$TRANSCRIPT_FILE" >> $GITHUB_OUTPUT

      - name: Upload transcript
        uses: actions/upload-artifact@v3
        with:
          name: transcript-${{ github.run_id }}
          path: ${{ steps.transcribe.outputs.transcript_file }}
          retention-days: 7

      - name: Cleanup
        if: always()
        run: |
          rm -rf /tmp/relayq/*
```

### Workflow 2: YouTube Processing

Create `.github/workflows/process_youtube.yml`:

```yaml
name: Process YouTube Video

on:
  workflow_dispatch:
    inputs:
      url:
        description: 'YouTube video URL'
        required: true
        type: string
      extract_audio:
        description: 'Extract audio only'
        required: false
        type: boolean
        default: true
      transcribe:
        description: 'Transcribe audio'
        required: false
        type: boolean
        default: true

jobs:
  process:
    name: Process YouTube Video
    runs-on: macmini  # YouTube processing best on Mac
    timeout-minutes: 90

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install yt-dlp
        run: |
          pip3 install yt-dlp

      - name: Download video
        id: download
        run: |
          mkdir -p /tmp/relayq
          cd /tmp/relayq

          if [ "${{ inputs.extract_audio }}" == "true" ]; then
            # Audio only
            yt-dlp -x --audio-format mp3 -o "audio.%(ext)s" "${{ inputs.url }}"
            echo "audio_file=/tmp/relayq/audio.mp3" >> $GITHUB_OUTPUT
          else
            # Full video
            yt-dlp -o "video.%(ext)s" "${{ inputs.url }}"
          fi

      - name: Transcribe audio
        if: inputs.transcribe == true
        id: transcribe
        run: |
          cd /tmp/relayq
          whisper "${{ steps.download.outputs.audio_file }}" \
            --model base \
            --output_format txt \
            --output_dir .

          echo "transcript_file=/tmp/relayq/audio.mp3.txt" >> $GITHUB_OUTPUT

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: youtube-result-${{ github.run_id }}
          path: /tmp/relayq/*
          retention-days: 7

      - name: Cleanup
        if: always()
        run: rm -rf /tmp/relayq/*
```

### Workflow 3: Bulk Processing

Create `.github/workflows/process_bulk.yml`:

```yaml
name: Bulk Process Audio Files

on:
  workflow_dispatch:
    inputs:
      urls:
        description: 'Comma-separated list of audio URLs'
        required: true
        type: string
      backend:
        description: 'ASR backend'
        required: false
        type: string
        default: 'local'

jobs:
  process:
    name: Bulk Process
    runs-on: self-hosted
    timeout-minutes: 180

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Process URLs
        run: |
          mkdir -p /tmp/relayq/bulk
          cd /tmp/relayq/bulk

          # Split URLs by comma
          IFS=',' read -ra URL_ARRAY <<< "${{ inputs.urls }}"

          # Process each URL
          for url in "${URL_ARRAY[@]}"; do
            echo "Processing: $url"

            # Download
            filename=$(basename "$url")
            wget -O "$filename" "$url"

            # Transcribe
            whisper "$filename" --model base --output_format txt

            # Clean up audio file (keep transcript)
            rm "$filename"
          done

      - name: Upload all transcripts
        uses: actions/upload-artifact@v3
        with:
          name: bulk-transcripts-${{ github.run_id }}
          path: /tmp/relayq/bulk/*.txt
          retention-days: 7

      - name: Cleanup
        if: always()
        run: rm -rf /tmp/relayq/bulk
```

**Commit and push workflows**:

```bash
cd ~/relayq
git add .github/workflows/
git commit -m "feat: Add RelayQ workflows for audio transcription and video processing"
git push origin main
```

---

## Part 4: Create Dispatch Scripts

### Create Dispatch Helper

Create `bin/dispatch.sh`:

```bash
#!/bin/bash
#
# RelayQ Workflow Dispatcher
# Submits jobs to GitHub Actions workflows
#

set -e

# Configuration
REPO="${RELAYQ_REPO:-Khamel83/relayq}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Check requirements
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    echo "Install: https://cli.github.com/"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

# Parse arguments
WORKFLOW_FILE="$1"
shift

# Build inputs
INPUTS=()
for arg in "$@"; do
    INPUTS+=("-f" "$arg")
done

# Dispatch workflow
echo "Dispatching workflow: $WORKFLOW_FILE"
echo "Repository: $REPO"
echo "Inputs: ${INPUTS[*]}"

gh workflow run "$WORKFLOW_FILE" \
    --repo "$REPO" \
    "${INPUTS[@]}"

echo "✓ Workflow dispatched successfully"
echo "View runs: gh run list --repo $REPO"
```

Make it executable:

```bash
chmod +x bin/dispatch.sh
git add bin/dispatch.sh
git commit -m "feat: Add workflow dispatch script"
git push
```

---

## Part 5: Test the Setup

### Test 1: Manual Workflow Dispatch

```bash
# Test transcription workflow
gh workflow run transcribe_audio.yml \
  --repo Khamel83/relayq \
  -f url=https://www.kozco.com/tech/piano2-CoolEdit.mp3 \
  -f backend=local \
  -f model=base \
  -f runner_preference=macmini

# Check status
gh run list --repo Khamel83/relayq --limit 5
```

### Test 2: Using Dispatch Script

```bash
cd ~/relayq

# Test with dispatch script
./bin/dispatch.sh transcribe_audio.yml \
  url=https://www.kozco.com/tech/piano2-CoolEdit.mp3 \
  backend=local \
  model=base
```

### Test 3: Verify Runner Picked Up Job

```bash
# Check runner status
gh api repos/Khamel83/relayq/actions/runners

# Watch specific run
gh run watch <RUN_ID> --repo Khamel83/relayq
```

### Test 4: Download Artifacts

```bash
# List artifacts for a run
gh run view <RUN_ID> --repo Khamel83/relayq

# Download artifact
gh run download <RUN_ID> --repo Khamel83/relayq
```

---

## Part 6: Troubleshooting

### Runner Not Picking Up Jobs

**Check runner status**:
```bash
# On the runner machine
sudo ./svc.sh status

# View logs
journalctl -u actions.runner.Khamel83-relayq.macmini.service -f
```

**Common issues**:
1. Runner service not running: `sudo ./svc.sh start`
2. Runner offline: Check network connectivity to GitHub
3. Labels mismatch: Reconfigure runner with correct labels

### Whisper Installation Issues

**Mac (Apple Silicon)**:
```bash
# If Whisper fails, try:
pip3 uninstall openai-whisper
pip3 install --upgrade openai-whisper

# Or use conda:
brew install miniforge
conda create -n whisper python=3.11
conda activate whisper
pip install openai-whisper
```

**Raspberry Pi**:
```bash
# RPi may need more memory for Whisper
sudo nano /boot/config.txt
# Add: gpu_mem=16 (reduce GPU memory)

# Or use tiny model only
# In ~/.config/relayq/env: WHISPER_MODEL=tiny
```

### Workflow Fails

**Check logs**:
```bash
# View workflow run logs
gh run view <RUN_ID> --log --repo Khamel83/relayq
```

**Common issues**:
1. Missing dependencies: Re-run setup steps
2. Timeout: Increase `timeout-minutes` in workflow
3. Download failed: Check URL is accessible from runner
4. Out of disk space: Clean /tmp/relayq directory

### Artifacts Not Available

**Retention period**:
- Artifacts expire after 7 days by default
- Download within retention period
- Can configure up to 90 days (paid plans)

**Download failed**:
```bash
# Try with verbose logging
gh run download <RUN_ID> --repo Khamel83/relayq -v
```

---

## Part 7: Monitoring & Maintenance

### Check Runner Health

**Weekly health check**:
```bash
# Check all runners
gh api repos/Khamel83/relayq/actions/runners | jq '.runners[] | {name, status, busy}'

# Check specific runner
ssh user@macmini "sudo ./actions-runner/svc.sh status"
```

### Update Runners

**Update GitHub Actions runner**:
```bash
# On each runner machine
cd ~/actions-runner
sudo ./svc.sh stop
./run.sh --update
sudo ./svc.sh start
```

### Clean Up Old Artifacts

**Manual cleanup**:
```bash
# List old artifacts
gh api repos/Khamel83/relayq/actions/artifacts | jq '.artifacts[] | select(.expired == false) | {name, created_at}'

# Delete specific artifact
gh api -X DELETE repos/Khamel83/relayq/actions/artifacts/<ARTIFACT_ID>
```

### Monitor Disk Usage

**On each runner**:
```bash
# Check disk usage
df -h

# Clean temp directory
rm -rf /tmp/relayq/*

# Clean GitHub Actions cache
cd ~/actions-runner/_work/_temp
find . -type f -mtime +7 -delete
```

---

## Next Steps

Once RelayQ is set up:

1. ✅ **Test all workflows** - Verify each workflow works correctly
2. ✅ **Integrate with Atlas** - See RELAYQ_INTEGRATION.md for Atlas integration
3. ✅ **Configure monitoring** - Set up alerts for runner health
4. ✅ **Optimize performance** - Tune Whisper models based on accuracy needs
5. ✅ **Document custom workflows** - Add any custom workflows for your use cases

---

## Quick Reference

### Useful Commands

```bash
# Dispatch transcription job
gh workflow run transcribe_audio.yml --repo Khamel83/relayq -f url=<AUDIO_URL> -f backend=local

# Check recent runs
gh run list --repo Khamel83/relayq --limit 10

# Watch a run
gh run watch <RUN_ID> --repo Khamel83/relayq

# Download transcript
gh run download <RUN_ID> --repo Khamel83/relayq

# Check runner status
gh api repos/Khamel83/relayq/actions/runners

# View logs
gh run view <RUN_ID> --log --repo Khamel83/relayq
```

### Runner Service Commands

```bash
# macOS
sudo ~/actions-runner/svc.sh {start|stop|status|enable|disable}

# Linux (systemd)
sudo systemctl {start|stop|status|enable|disable} actions.runner.*
journalctl -u actions.runner.* -f
```

---

**Setup Complete!** 🎉

Your RelayQ system is now ready to process audio transcriptions, YouTube videos, and other compute-intensive tasks on your physical hardware.

For Atlas integration, proceed to RELAYQ_INTEGRATION.md Part 4: "Atlas Side Changes".
