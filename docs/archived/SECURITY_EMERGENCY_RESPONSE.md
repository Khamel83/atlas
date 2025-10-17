# 🚨 SECURITY EMERGENCY: API Keys Exposed in Repository

## IMMEDIATE ACTIONS REQUIRED

### 🔥 **CONFIRMED EXPOSED SECRETS**

**File**: `.env` (committed to repository)
- **OpenRouter API Key**: `sk-or-v1-[REDACTED-OLD-KEY]`
- **Firecrawl API Key**: `fc-c9c0fa81530c4e6f82d30c8c0aa68ff2`
- **NYTimes Credentials**: `newyorktimes@khamel.com` / `4yo@X@iczgsvVF_jJYhQ`
- **WSJ Credentials**: `apllp` / `apllpny`

### 🎯 **IMMEDIATE ACTIONS (DO THESE NOW)**

#### 1. **REVOKE ALL EXPOSED API KEYS**
```bash
# OpenRouter API Key
# Go to: https://openrouter.ai/keys
# Revoke: sk-or-v1-[REDACTED-OLD-KEY]
# Generate new key

# Firecrawl API Key
# Go to: https://firecrawl.dev/account
# Revoke: fc-c9c0fa81530c4e6f82d30c8c0aa68ff2
# Generate new key
```

#### 2. **CHANGE ACCOUNT PASSWORDS**
```bash
# NYTimes Account
# Login: newyorktimes@khamel.com
# Change password: 4yo@X@iczgsvVF_jJYhQ

# WSJ Account
# Login: apllp
# Change password: apllpny
```

#### 3. **REMOVE SECRETS FROM CURRENT BRANCH**
```bash
# Replace exposed keys in .env
sed -i 's/sk-or-v1-[OLD-KEY]/YOUR_NEW_OPENROUTER_KEY/g' .env
sed -i 's/fc-c9c0fa81530c4e6f82d30c8c0aa68ff2/YOUR_NEW_FIRECRAWL_KEY/g' .env
sed -i 's/newyorktimes@khamel.com/YOUR_NYTIMES_EMAIL/g' .env
sed -i 's/4yo@X@iczgsvVF_jJYhQ/YOUR_NYTIMES_PASSWORD/g' .env
sed -i 's/apllp/YOUR_WSJ_USERNAME/g' .env
sed -i 's/apllpny/YOUR_WSJ_PASSWORD/g' .env
```

#### 4. **UPDATE .gitignore IMMEDIATELY**
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
echo ".env.production" >> .gitignore
echo "*.env" >> .gitignore
echo "secrets/" >> .gitignore
```

#### 5. **COMMIT SECURITY FIX**
```bash
git add .gitignore .env
git commit -m "security: remove exposed API keys and add proper .gitignore"
git push origin feat/podcast-transcripts
```

---

## 🔒 **GIT HISTORY CLEANUP (REQUIRED)**

The API keys are in Git history and will remain accessible even after removal. **Git history cleanup is REQUIRED**.

### **Option 1: BFG Repo-Cleaner (Recommended)**
```bash
# Install BFG
curl -O https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# Remove secrets from history
java -jar bfg-1.14.0.jar --replace-text secrets.txt .git
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push --force-with-lease origin --all
```

### **Option 2: Git Filter-Branch**
```bash
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

git push --force-with-lease origin --all
```

### **Option 3: Nuclear Option (Last Resort)**
```bash
# Delete and recreate repository if other options fail
# WARNING: This loses all git history
```

---

## 📋 **SECURE SECRETS MANAGEMENT SETUP**

### **1. Create secrets.env (NOT committed)**
```bash
# Create secure secrets file
touch secrets.env
chmod 600 secrets.env

# Add to secrets.env (with NEW keys)
cat > secrets.env << 'EOF'
OPENROUTER_API_KEY=your_new_openrouter_key_here
FIRECRAWL_API_KEY=your_new_firecrawl_key_here
NYTIMES_USERNAME=your_nytimes_email_here
NYTIMES_PASSWORD=your_new_nytimes_password_here
WSJ_USERNAME=your_wsj_username_here
WSJ_PASSWORD=your_new_wsj_password_here
EOF
```

### **2. Update .env to reference secrets**
```bash
# In .env (committed file)
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-your_openrouter_key_here}
FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY:-your_firecrawl_key_here}
NYTIMES_USERNAME=${NYTIMES_USERNAME:-your_nytimes_email_here}
NYTIMES_PASSWORD=${NYTIMES_PASSWORD:-your_nytimes_password_here}
WSJ_USERNAME=${WSJ_USERNAME:-your_wsj_username_here}
WSJ_PASSWORD=${WSJ_PASSWORD:-your_wsj_password_here}
```

### **3. Load secrets in startup script**
```bash
# In startup script
if [ -f secrets.env ]; then
    export $(cat secrets.env | xargs)
fi
```

### **4. Update .gitignore properly**
```bash
cat >> .gitignore << 'EOF'
# Secrets and environment files
.env
.env.local
.env.production
.env.development
*.env
secrets.env
secrets/
.secrets

# API keys and credentials
*api_key*
*secret*
*password*
*credentials*

# Backup files with potential secrets
*.backup
*.bak
*.old
*~
EOF
```

---

## 🎯 **GITHUB BRANCH CLEANUP STRATEGY**

### **Current Branch Structure**
- `main` - Main branch
- `feat/podcast-transcripts` - Current branch with exposed secrets

### **Cleanup Strategy**
1. **Secure current branch** (remove secrets, add .gitignore)
2. **Clean Git history** (BFG or filter-branch)
3. **Force push clean history**
4. **Verify no secrets in any branch**

### **Branch Verification Commands**
```bash
# Check all branches for secrets
git log --all --full-history -- .env
git log --all --grep="sk-or-v1"
git log --all --grep="fc-"

# Search for API keys in all branches
git rev-list --all | xargs git grep "sk-or-v1" || echo "No API keys found"
```

---

## ✅ **VERIFICATION CHECKLIST**

- [ ] OpenRouter API key revoked and regenerated
- [ ] Firecrawl API key revoked and regenerated
- [ ] NYTimes password changed
- [ ] WSJ password changed
- [ ] Secrets removed from current .env file
- [ ] Proper .gitignore added
- [ ] Git history cleaned (BFG or filter-branch)
- [ ] Force push completed
- [ ] All branches verified clean of secrets
- [ ] New secrets stored securely (not in Git)
- [ ] Team notified of security incident
- [ ] Documentation updated with secure practices

---

## 🚨 **ONGOING SECURITY MEASURES**

### **1. Pre-commit Hooks**
```bash
# Install pre-commit hooks to prevent future secret commits
pip install pre-commit
echo "repos:
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
  - id: detect-secrets" > .pre-commit-config.yaml
pre-commit install
```

### **2. Automated Secret Scanning**
```bash
# Add GitHub Action for secret scanning
# File: .github/workflows/security.yml
```

### **3. Environment Templates**
```bash
# Maintain .env.template with placeholders only
# Never commit actual .env files
# Use environment variable substitution
```

---

**PRIORITY: Complete steps 1-5 immediately. Git history cleanup can be done after securing active keys.**

This security incident demonstrates the need for proper secrets management practices going forward.