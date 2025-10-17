# Atlas Troubleshooting Checklist

*Quick reference for common Atlas issues and solutions*

## 🚀 Quick Start Verification

Before troubleshooting, run these quick checks:

```bash
# 1. Quick setup verification
python scripts/setup_check.py

# 2. Full environment diagnosis
python scripts/diagnose_environment.py

# 3. Configuration validation
python scripts/validate_config.py
```

## 📋 Common Issues Checklist

### Installation Issues
-   [ ] **Python version is 3.9 or higher**
    -   **Check:** `python3 --version`
    -   **Fix:** Install Python 3.9+ from https://python.org

-   [ ] **All dependencies are installed**
    -   **Check:** Run `python scripts/setup_check.py`
    -   **Fix:** `pip3 install -r requirements.txt`

-   [ ] **Project files are present**
    -   **Check:** `ls run.py helpers/config.py requirements.txt`
    -   **Fix:** Ensure you're in the Atlas project directory

### Configuration Issues
-   [ ] **Configuration file exists**
    -   **Check:** `ls config/.env`
    -   **Fix:** `cp .env.example config/.env`

-   [ ] **Configuration is valid**
    -   **Check:** `python scripts/validate_config.py`
    -   **Fix:** Follow validation error guidance

-   [ ] **API keys are properly formatted**
    -   **Check:** OpenRouter keys start with `sk-or-v1-`
    -   **Fix:** Get correct keys from service providers

### Permission Issues
-   [ ] **Output directory is accessible**
    -   **Check:** `ls -la output/`
    -   **Fix:** `mkdir -p output && chmod 755 output`

-   [ ] **Can write to data directory**
    -   **Check:** `touch output/.test && rm output/.test`
    -   **Fix:** `chmod 755 output` or change DATA_DIRECTORY

### Runtime Issues
-   [ ] **Atlas CLI responds**
    -   **Check:** `python run.py --help`
    -   **Fix:** Check dependencies and configuration

-   [ ] **Network connectivity works**
    -   **Check:** `ping google.com`
    -   **Fix:** Check firewall/proxy settings

-   [ ] **External APIs are accessible**
    -   **Check:** `python scripts/diagnose_environment.py --test-apis`
    -   **Fix:** Check API keys and network settings

## 🔧 Automated Fixes

### Quick Setup
```bash
# Complete automated setup
python scripts/generate_env.py          # Create configuration
python scripts/diagnose_environment.py --fix-permissions  # Fix permissions
python scripts/validate_config.py       # Verify setup
```

### Permission Fixes
```bash
# Fix directory permissions
python scripts/diagnose_environment.py --fix-permissions

# Manual permission fix
mkdir -p output/{articles,podcasts,youtube,logs}
chmod 755 output output/*
```

### Dependency Fixes
```bash
# Reinstall all dependencies
pip3 install --force-reinstall -r requirements.txt

# Install specific missing packages
pip3 install requests beautifulsoup4 pyyaml python-dotenv
```

## 🚨 Emergency Recovery

### Complete Reset
```bash
# Backup data
cp -r output output_backup

# Clean reset
rm -rf config/.env *.db __pycache__/
pip3 install --force-reinstall -r requirements.txt
python scripts/generate_env.py
python scripts/setup_check.py
```

### Configuration Reset
```bash
# Reset configuration only
rm config/.env
cp .env.example config/.env
python scripts/generate_env.py
```

## 📞 Getting Help

### Information to Collect
```bash
# Generate diagnostic report
python scripts/diagnose_environment.py > diagnostic_report.txt
python scripts/validate_config.py >> diagnostic_report.txt
python3 --version >> diagnostic_report.txt
uname -a >> diagnostic_report.txt  # Linux/Mac
```

### Before Seeking Support
1. Run all diagnostic scripts
2. Try automated fixes
3. Check latest documentation
4. Search existing GitHub issues

## 📚 Additional Resources

- **Full Troubleshooting Guide:** `docs/environment-troubleshooting.md`
- **Configuration Guide:** `docs/configuration-validation.md`
- **Quick Start:** `QUICK_START.md`
- **Current Status:** `docs/CURRENT_STATUS.md`

---

## Legacy Issues (Archive)

-   [ ] **Configuration Error in test_module:**
    -   **Question:** Have you checked for critical failure?
    -   **Context:** Critical error occurred in test_function. Critical failure
    -   **Last Seen:** 2025-08-01T00:15:19.516798

## Post-Task Checklist: