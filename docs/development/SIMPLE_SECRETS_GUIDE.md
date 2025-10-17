# 🔒 Simple Secrets Guide - Never Expose API Keys Again

## 🎯 The Simple Rule

**Real secrets = Home folder** (`~/.secrets/`)
**Dev work = Dev folder** (`~/dev/`)
**Never mix them!**

---

## ⚡ SUPER SIMPLE: One-Line Setup for Any Project

**Just run this single command in any new project:**

```bash
bash /home/ubuntu/setup_secrets.sh
```

**That's it!** It creates everything you need:
- ✅ `~/.secrets/PROJECT_NAME.env` (for your real keys)
- ✅ `.env` template (safe to commit)
- ✅ `load_secrets.sh` (connects them)
- ✅ `.gitignore` protection

---

## 🚀 Daily Usage (Every Time You Code)

```bash
# 1. Go to your project
cd ~/dev/any-project

# 2. Load secrets
source load_secrets.sh

# 3. Work normally
python run.py --all
```

**That's it!**

---

## 📝 What the One-Line Setup Does

When you run `bash /home/ubuntu/setup_secrets.sh PROJECT_NAME`:

1. **Creates** `~/.secrets/PROJECT_NAME.env` with template for real keys
2. **Creates** `.env` with safe `${VAR:-default}` patterns
3. **Creates** `load_secrets.sh` that connects them
4. **Updates** `.gitignore` to block secrets
5. **Ready to use** - just add your real keys and load!

### Example:
```bash
# Setup new project
cd ~/dev/my-new-app
bash /home/ubuntu/setup_secrets.sh my-new-app

# Add real keys
nano ~/.secrets/my-new-app.env

# Use it
source load_secrets.sh
# Work normally!
```

---

## 🛡️ Why This Never Fails

- ✅ **Home folder secrets** are never in any git repo
- ✅ **Dev folder templates** are safe to commit
- ✅ **Impossible to accidentally expose keys**
- ✅ **Same pattern works for all projects**

---

## 🧪 Quick Test

**This should show NO real keys:**
```bash
cat ~/dev/atlas/.env
```

**This should show your real keys:**
```bash
cat ~/.secrets/atlas.env
```

**This should work without exposing anything:**
```bash
cd ~/dev/atlas
git add .
git commit -m "test"
# No secrets exposed!
```

---

## 📝 Summary

**What to remember:**
1. Real secrets → `~/.secrets/project.env`
2. Fake templates → `~/dev/project/.env`
3. Load before work → `source load_secrets.sh`

**That's literally it.** Copy this pattern to any project and your secrets will never be exposed again! 🔒