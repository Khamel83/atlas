# RelayQ Quick Start Checklist

**Purpose**: Your step-by-step checklist to get RelayQ running
**Time**: 1-2 hours (depending on number of machines)

---

## Before You Start

**What you need**:
- [ ] GitHub account with repo access to `Khamel83/relayq`
- [ ] GitHub Personal Access Token (with `repo`, `workflow` scopes)
- [ ] SSH access to your physical machines (Mac mini, RPi4, RPi3)
- [ ] 1-2 hours of time

**What you'll get**:
- ✅ Podcast transcription running on your Mac mini
- ✅ Cost savings: $36/month → $0.17/month
- ✅ Private, local processing (no data sent to APIs)
- ✅ Faster transcription with Apple Silicon

---

## Phase 1: GitHub Setup (15 minutes)

### 1.1 Create/Verify RelayQ Repository

```bash
# Check if repo exists
gh repo view Khamel83/relayq

# If not, create it
gh repo create Khamel83/relayq --public --description "RelayQ: GitHub Actions job queue"
```

**Status**: [ ] Repository exists

### 1.2 Clone Repository

```bash
cd ~
git clone https://github.com/Khamel83/relayq.git
cd relayq
```

**Status**: [ ] Repository cloned

### 1.3 Create Directory Structure

```bash
mkdir -p .github/workflows bin scripts config
```

**Status**: [ ] Directories created

### 1.4 Get GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens/new
2. Name: `RelayQ Access Token`
3. Scopes: Check `repo` and `workflow`
4. Click "Generate token"
5. **SAVE TOKEN SECURELY** (you'll need it later)

**Status**: [ ] Token created and saved

---

## Phase 2: Mac mini Setup (30-45 minutes)

### 2.1 SSH Into Mac mini

```bash
ssh user@macmini.local
# Or: ssh user@192.168.1.XXX
```

**Status**: [ ] Connected to Mac mini

### 2.2 Install Dependencies

```bash
# Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install packages
brew install python@3.11 ffmpeg git wget

# Install Whisper
pip3 install openai-whisper

# Verify
whisper --help
ffmpeg -version
```

**Status**: [ ] Dependencies installed

### 2.3 Install GitHub Actions Runner

```bash
# Create runner directory
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download runner (Apple Silicon)
curl -o actions-runner-osx-arm64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-osx-arm64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-osx-arm64-2.311.0.tar.gz
```

**Status**: [ ] Runner downloaded and extracted

### 2.4 Get Registration Token

1. Go to: https://github.com/Khamel83/relayq/settings/actions/runners/new
2. Copy the registration token (starts with `AAAA...`)

**Status**: [ ] Registration token copied

### 2.5 Configure Runner

```bash
cd ~/actions-runner

./config.sh --url https://github.com/Khamel83/relayq --token PASTE_TOKEN_HERE

# When prompted:
# Runner name: macmini
# Labels: self-hosted,macOS,ARM64,macmini,audio,video,heavy
# Work folder: (press Enter for default)
```

**Status**: [ ] Runner configured

### 2.6 Test Runner

```bash
./run.sh
```

Leave this running in terminal. You should see:
```
√ Connected to GitHub
√ Listening for Jobs
```

Press Ctrl+C to stop after verifying.

**Status**: [ ] Runner tested successfully

### 2.7 Install as Service (Auto-start)

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
sudo ./svc.sh enable
```

**Status**: [ ] Runner service installed and running

### 2.8 Create RelayQ Config

```bash
mkdir -p ~/.config/relayq
cat > ~/.config/relayq/env << 'EOF'
ASR_BACKEND=local
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
TEMP_DIR=/tmp/relayq
MAX_CONCURRENT_JOBS=2
EOF

mkdir -p /tmp/relayq
```

**Status**: [ ] Config created

---

## Phase 3: Raspberry Pi 4 Setup (30-45 minutes)

**Note**: If you only have Mac mini, you can skip this section.

### 3.1 SSH Into RPi4

```bash
ssh pi@raspberrypi4.local
```

**Status**: [ ] Connected to RPi4

### 3.2 Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip ffmpeg git wget curl
pip3 install openai-whisper
```

**Status**: [ ] Dependencies installed

### 3.3 Install Runner

```bash
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -o actions-runner-linux-arm64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-arm64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-arm64-2.311.0.tar.gz
```

**Status**: [ ] Runner downloaded

### 3.4 Configure Runner

```bash
./config.sh --url https://github.com/Khamel83/relayq --token PASTE_TOKEN_HERE

# When prompted:
# Runner name: rpi4
# Labels: self-hosted,Linux,ARM64,rpi4,audio,light
```

**Status**: [ ] Runner configured

### 3.5 Install as Service

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh enable
```

**Status**: [ ] RPi4 runner running

---

## Phase 4: Create Workflows (15 minutes)

**Do this on your development machine or the OCI VM**

### 4.1 Create Transcription Workflow

```bash
cd ~/relayq

cat > .github/workflows/transcribe_audio.yml << 'EOF'
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

jobs:
  transcribe:
    name: Transcribe Audio File
    runs-on: self-hosted
    timeout-minutes: 60

    steps:
      - name: Download audio file
        id: download
        run: |
          mkdir -p /tmp/relayq
          cd /tmp/relayq
          FILENAME=$(basename "${{ inputs.url }}")
          wget -O "$FILENAME" "${{ inputs.url }}"
          echo "audio_file=/tmp/relayq/$FILENAME" >> $GITHUB_OUTPUT

      - name: Transcribe with Whisper
        id: transcribe
        run: |
          cd /tmp/relayq
          whisper "${{ steps.download.outputs.audio_file }}" \
            --model ${{ inputs.model }} \
            --output_format txt \
            --output_dir .
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
        run: rm -rf /tmp/relayq/*
EOF
```

**Status**: [ ] Workflow file created

### 4.2 Create Dispatch Script

```bash
cat > bin/dispatch.sh << 'EOF'
#!/bin/bash
set -e

REPO="${RELAYQ_REPO:-Khamel83/relayq}"
WORKFLOW_FILE="$1"
shift

INPUTS=()
for arg in "$@"; do
    INPUTS+=("-f" "$arg")
done

echo "Dispatching workflow: $WORKFLOW_FILE"
gh workflow run "$WORKFLOW_FILE" --repo "$REPO" "${INPUTS[@]}"
echo "✓ Workflow dispatched successfully"
EOF

chmod +x bin/dispatch.sh
```

**Status**: [ ] Dispatch script created

### 4.3 Commit and Push

```bash
git add .
git commit -m "feat: Add RelayQ workflows and dispatch script"
git push origin main
```

**Status**: [ ] Changes pushed to GitHub

---

## Phase 5: Test Everything (15 minutes)

### 5.1 Install GitHub CLI (if not already installed)

```bash
# macOS
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

**Status**: [ ] GitHub CLI installed

### 5.2 Authenticate GitHub CLI

```bash
gh auth login
# Follow prompts - use your GitHub token when asked
```

**Status**: [ ] Authenticated with GitHub

### 5.3 Verify Runners Are Online

```bash
gh api repos/Khamel83/relayq/actions/runners | jq '.runners[] | {name, status, busy}'
```

You should see:
```json
{
  "name": "macmini",
  "status": "online",
  "busy": false
}
```

**Status**: [ ] Runners showing as online

### 5.4 Run Test Transcription

```bash
# Test with a small public audio file (piano sample, ~1MB)
gh workflow run transcribe_audio.yml \
  --repo Khamel83/relayq \
  -f url=https://www.kozco.com/tech/piano2-CoolEdit.mp3 \
  -f backend=local \
  -f model=base
```

**Status**: [ ] Test job submitted

### 5.5 Watch Test Job

```bash
# Get the run ID from the latest run
RUN_ID=$(gh run list --repo Khamel83/relayq --limit 1 --json databaseId --jq '.[0].databaseId')

# Watch it
gh run watch $RUN_ID --repo Khamel83/relayq
```

You should see it complete successfully with a green checkmark.

**Status**: [ ] Test job completed successfully

### 5.6 Download Test Transcript

```bash
gh run download $RUN_ID --repo Khamel83/relayq

# View transcript
cat transcript-*/piano2-CoolEdit.mp3.txt
```

You should see transcribed text from the audio file.

**Status**: [ ] Transcript downloaded and verified

---

## Phase 6: Integrate with Atlas (Optional - Do Later)

**Note**: This step integrates RelayQ with your Atlas system. You can do this later.

### 6.1 Copy .env Template

```bash
cd ~/atlas
cp .env.template .env
nano .env
```

### 6.2 Configure RelayQ Variables

In `.env`, set:
```bash
RELAYQ_ENABLED=true
RELAYQ_REPO=Khamel83/relayq
RELAYQ_DISPATCH_SCRIPT=/home/ubuntu/relayq/bin/dispatch.sh
RELAYQ_DEFAULT_BACKEND=local
RELAYQ_DEFAULT_MODEL=base
RELAYQ_RUNNER_PREFERENCE=mac
GITHUB_TOKEN=your_github_token_here
```

**Status**: [ ] .env configured (do later)

### 6.3 Install RelayQ Client

```bash
# This will be implemented in a future update
# See RELAYQ_INTEGRATION.md for full integration details
```

**Status**: [ ] RelayQ client installed (do later)

---

## Success Criteria

You're done when:

- ✅ All runners show as "online" in GitHub
- ✅ Test transcription job completes successfully
- ✅ Transcript is downloadable from GitHub artifacts
- ✅ Transcript content is correct (recognizable text from audio)

---

## Troubleshooting

### Runner shows offline

```bash
# On the runner machine
sudo ./svc.sh status
sudo ./svc.sh start

# View logs
journalctl -u actions.runner.* -f  # Linux
tail -f ~/actions-runner/_diag/*.log  # macOS
```

### Workflow fails with "No runners available"

- Check runner labels match workflow requirements
- Verify runner is online: `gh api repos/Khamel83/relayq/actions/runners`

### Whisper command not found

```bash
# Re-install Whisper
pip3 install --upgrade openai-whisper

# Check PATH
which whisper
echo $PATH
```

### Can't download artifacts

- Check retention period (7 days default)
- Verify you have access to repository
- Try: `gh run download $RUN_ID --repo Khamel83/relayq -v`

---

## Next Steps

Once everything is working:

1. **Read RELAYQ_INTEGRATION.md** - Learn how to integrate with Atlas
2. **Optimize Whisper models** - Test different model sizes (tiny, base, small)
3. **Add more workflows** - YouTube processing, bulk operations
4. **Monitor performance** - Track transcription times and success rates
5. **Scale up** - Add more runners as needed

---

## Quick Reference

### Check runner status
```bash
gh api repos/Khamel83/relayq/actions/runners | jq '.runners[] | {name, status}'
```

### Submit transcription job
```bash
gh workflow run transcribe_audio.yml --repo Khamel83/relayq -f url=YOUR_URL -f backend=local
```

### Watch recent runs
```bash
gh run list --repo Khamel83/relayq --limit 5
```

### Download transcript
```bash
gh run download RUN_ID --repo Khamel83/relayq
```

### View runner logs
```bash
# macOS
tail -f ~/actions-runner/_diag/*.log

# Linux
journalctl -u actions.runner.* -f
```

---

**Time to complete**: 1-2 hours
**Difficulty**: Intermediate
**Cost savings**: $36/month → $0.17/month

**Good luck!** 🚀
