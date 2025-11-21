# 🔒 Universal Secrets System - NEVER Expose API Keys Again

## 🎯 The Solution: Secrets Outside Dev Folder

**Problem**: API keys in dev folders can be accidentally committed
**Solution**: Store ALL secrets in `~/.secrets/` (outside any dev work)

---

## 📋 Manual Setup Instructions (Do This Once)

### Step 1: Create Universal Secrets Directory
```bash
# Create secrets directory in your home folder (NOT in dev/)
mkdir -p ~/.secrets
chmod 700 ~/.secrets
```

### Step 2: Create Atlas Secrets File
```bash
# Create the secrets file
touch ~/.secrets/atlas.env
chmod 600 ~/.secrets/atlas.env
```

### Step 3: Add Your API Keys
```bash
# Edit the secrets file with your REAL keys
nano ~/.secrets/atlas.env
```

**Add this content with YOUR actual keys:**
```bash
# Atlas API Keys - NEVER commit this file
export OPENROUTER_API_KEY="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"
export FIRECRAWL_API_KEY="fc-3b8e621cbe084db69f235ec3ff631a00"
export MODEL="google/gemini-2.0-flash-001"

# Optional: Site credentials (update when ready)
export NYTIMES_USERNAME="your_nytimes_email_here"
export NYTIMES_PASSWORD="your_nytimes_password_here"
export WSJ_USERNAME="your_wsj_username_here"
export WSJ_PASSWORD="your_wsj_password_here"
```

### Step 4: Test the System
```bash
# Go to your Atlas project
cd ~/dev/atlas

# Load secrets (should work now)
source load_secrets.sh

# You should see:
# ✅ Secrets loaded successfully
# ✅ Using model: google/gemini-2.0-flash-001
# ✅ OpenRouter API key: sk-or-v1-5539c0d707d1...
```

---

## 🚀 How to Use (Daily Workflow)

### For Atlas Project:
```bash
cd ~/dev/atlas
source load_secrets.sh    # Load secrets
python run.py --all        # Run normally
```

### For Future Projects:
```bash
cd ~/dev/new-project
source load_secrets.sh    # Same command, same secrets
# OR create project-specific: ~/.secrets/project-name.env
```

---

## 🛡️ Why This is Bulletproof

### ✅ **Location Safety**
- Secrets in `~/.secrets/` (home folder)
- Dev work in `~/dev/` (separate folder)
- **Impossible** to accidentally commit secrets

### ✅ **Universal Pattern**
- Same secrets work for ALL projects
- One setup, use everywhere
- No secrets ever in any dev folder

### ✅ **File Permissions**
- `chmod 600` = only YOU can read/write
- `chmod 700` = only YOU can access directory
- System-level protection

### ✅ **Git-Proof**
- No `.env` files with real secrets in ANY repo
- All `.env` files only have `${VAR:-default}` patterns
- Pre-commit hooks catch any accidents

---

## 🔄 For Future Projects (Copy This Pattern)

### 1. Create `.env` (safe to commit):
```bash
# Project Configuration - Safe to commit
API_KEY=${API_KEY:-your_api_key_here}
DATABASE_URL=${DATABASE_URL:-your_db_url_here}
```

### 2. Create `load_secrets.sh` (safe to commit):
```bash
#!/bin/bash
SECRETS_FILE="$HOME/.secrets/project-name.env"
if [ -f "$SECRETS_FILE" ]; then
    source "$SECRETS_FILE"
    echo "✅ Secrets loaded"
else
    echo "❌ Create $SECRETS_FILE first"
fi
```

### 3. Add secrets to `~/.secrets/project-name.env`:
```bash
export API_KEY="real-key-here"
export DATABASE_URL="real-url-here"
```

### 4. Use anywhere:
```bash
cd ~/dev/any-project
source load_secrets.sh
```

---

## 🧪 Test Commands

### Test Atlas:
```bash
cd ~/dev/atlas
source load_secrets.sh
echo "Model: $MODEL"
echo "Key: ${OPENROUTER_API_KEY:0:20}..."
```

### Test Security:
```bash
# This should show NO real keys
cat ~/dev/atlas/.env

# This should show real keys (only you can see)
cat ~/.secrets/atlas.env
```

### Test Git Safety:
```bash
cd ~/dev/atlas
git add .
git commit -m "test commit"
# Should work fine - no secrets in repo
```

---

## 📝 Summary in Simplest Language

**The Rule**:
- **Real secrets** = `~/.secrets/` (home folder, safe)
- **Fake templates** = `~/dev/project/.env` (dev folder, gets committed)
- **Load script** = `source load_secrets.sh` (connects them)

**Why it works**:
- Home folder (`~/.secrets/`) is NEVER part of any git repo
- Dev folders (`~/dev/project/`) only have template files
- Impossible to commit real secrets accidentally

**Daily use**:
1. `cd ~/dev/project`
2. `source load_secrets.sh`
3. Work normally

**For new projects**:
1. Copy the pattern (`.env` + `load_secrets.sh`)
2. Add real secrets to `~/.secrets/project-name.env`
3. Use same workflow

**Result**: API keys NEVER get exposed, no matter what you commit or push!