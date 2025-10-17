# 🔒 Secure Atlas Setup Instructions

## ✅ **Security Implementation Complete**

Your Atlas repository is now secured with proper secrets management.

---

## 🚀 **How to Use Secure Setup**

### **1. Load Your Secrets**
```bash
# Load your API keys and credentials
source load_secrets.sh

# You should see:
# ✅ Secrets loaded successfully
# ✅ Using model: google/gemini-2.0-flash-001
# ✅ OpenRouter API key: sk-or-v1-5539c0d707d1...
# ✅ Firecrawl API key: fc-3b8e621cbe08...
```

### **2. Run Atlas with Secrets**
```bash
# After loading secrets, run any Atlas command
python run.py --all
python process_podcasts.py
./scripts/atlas_background_service.py start
```

### **3. Verify Model Configuration**
```bash
# Check that gemini-2.0-flash-001 is being used
source load_secrets.sh
echo "Current model: $MODEL"
```

---

## 🛡️ **Security Features Implemented**

### **✅ Secure Secrets Storage**
- **`.env.secure`** - Contains your actual API keys (never committed)
- **Permissions**: `600` (only you can read/write)
- **Protected by `.gitignore`**

### **✅ Environment Variable Pattern**
- **`.env`** - Uses `${VAR:-default}` pattern (safe to commit)
- **No hardcoded secrets** in any committed files
- **Fallback to safe defaults** if secrets not loaded

### **✅ Enhanced .gitignore**
- Blocks `.env.secure` and any files with secrets
- Prevents accidental API key commits
- Comprehensive patterns for secret detection

### **✅ Pre-commit Hooks**
- **detect-secrets** - Scans for accidentally committed secrets
- **Custom API key check** - Blocks OpenRouter/Firecrawl keys
- **Environment file check** - Prevents secrets in .env files

### **✅ Easy Secret Loading**
- **`load_secrets.sh`** - One command to load all secrets
- **Visual confirmation** - Shows what keys are loaded
- **Error handling** - Warns if secrets file missing

---

## 🔧 **Current Configuration**

### **API Keys Secured:**
- ✅ OpenRouter: `sk-or-v1-5539c0d707d1...` (in .env.secure)
- ✅ Firecrawl: `fc-3b8e621cbe08...` (in .env.secure)
- ✅ NYTimes: credentials (update when ready)
- ✅ WSJ: credentials (keeping current per your request)

### **Model Updated:**
- ✅ All API calls now use `google/gemini-2.0-flash-001`
- ✅ Environment variable pattern: `MODEL=${MODEL:-google/gemini-2.0-flash-001}`

---

## 🚨 **NEVER AGAIN! Prevention Measures**

### **1. Pre-commit Protection**
```bash
# Install pre-commit hooks (one-time setup)
pip install pre-commit
pre-commit install

# Now every commit will be scanned for secrets automatically
```

### **2. Always Use This Pattern**
```bash
# WRONG (never do this):
OPENROUTER_API_KEY=sk-or-v1-actual-key-here

# RIGHT (always use this):
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-your_openrouter_key_here}
```

### **3. Secret Workflow**
```bash
# 1. Add secrets to .env.secure (never committed)
echo 'export NEW_API_KEY="actual-key-here"' >> .env.secure

# 2. Reference in .env (committed safely)
echo 'NEW_API_KEY=${NEW_API_KEY:-your_key_here}' >> .env

# 3. Load before using
source load_secrets.sh
```

---

## 🧪 **Testing Security**

### **Test 1: Pre-commit Hook**
```bash
# This should FAIL and block the commit
echo "OPENROUTER_API_KEY=sk-or-v1-test123" >> test.txt
git add test.txt
git commit -m "test"
# Should see: ❌ FOUND API KEYS IN FILES!
```

### **Test 2: Secret Loading**
```bash
# This should work
source load_secrets.sh
echo $OPENROUTER_API_KEY
# Should show your actual key
```

### **Test 3: Environment Variables**
```bash
# This should show the model
source load_secrets.sh
echo $MODEL
# Should show: google/gemini-2.0-flash-001
```

---

## 📋 **Quick Reference**

### **Daily Workflow**
```bash
# 1. Load secrets (start of session)
source load_secrets.sh

# 2. Run Atlas normally
python run.py --all

# 3. Commit changes (pre-commit will check for secrets)
git add .
git commit -m "your changes"
```

### **Adding New Secrets**
```bash
# 1. Add to .env.secure
echo 'export NEW_SECRET="actual-value"' >> .env.secure

# 2. Add template to .env
echo 'NEW_SECRET=${NEW_SECRET:-default_value}' >> .env

# 3. Reload secrets
source load_secrets.sh
```

### **Emergency Secret Reset**
```bash
# 1. Revoke old keys at provider websites
# 2. Update .env.secure with new keys
# 3. Reload secrets
source load_secrets.sh
```

---

## ✅ **Security Checklist**

- [x] API keys moved to .env.secure (never committed)
- [x] .env uses environment variable pattern
- [x] .gitignore blocks all secret files
- [x] Pre-commit hooks prevent secret commits
- [x] Model updated to google/gemini-2.0-flash-001
- [x] Load script provides easy secret management
- [x] File permissions secured (600 on .env.secure)
- [x] Documentation created for team

**Your Atlas is now SECURE! 🔒**

No more accidental API key exposure. The pre-commit hooks will catch any secrets before they get committed, and the secure loading pattern ensures your keys are never hardcoded in git.