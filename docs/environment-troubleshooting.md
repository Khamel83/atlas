# Atlas Environment Troubleshooting Guide

This comprehensive guide helps you diagnose and resolve common environment setup issues with Atlas. Use this when Atlas doesn't start, configuration fails, or you encounter setup problems.

## 🚨 Quick Diagnosis

If Atlas isn't working, run this diagnostic command first:

```bash
python3 scripts/validate_config.py
```

This will identify most configuration issues with specific fix instructions.

## 📋 Systematic Troubleshooting Checklist

### 1. System Requirements Check

#### Python Version
```bash
python3 --version
```
**Requirement**: Python 3.9 or higher
**Issue**: `ImportError` or syntax errors
**Fix**: Install Python 3.9+ from https://python.org

#### System Dependencies
```bash
# Check if pip is available
pip3 --version

# Check if git is available (for cloning)
git --version
```

### 2. Installation Issues

#### Missing Dependencies
**Symptoms**: `ModuleNotFoundError` when running Atlas
```bash
# Install all required packages
pip3 install -r requirements.txt

# If requirements.txt is missing, install core dependencies
pip3 install requests beautifulsoup4 lxml readability pyyaml python-dotenv schedule
```

#### Permission Issues
**Symptoms**: `Permission denied` errors during installation
```bash
# Option 1: Use user installation (recommended)
pip3 install --user -r requirements.txt

# Option 2: Use virtual environment
python3 -m venv atlas_env
source atlas_env/bin/activate  # On Windows: atlas_env\Scripts\activate
pip3 install -r requirements.txt
```

#### Network/Proxy Issues
**Symptoms**: `Connection timeout` or `SSL errors` during installation
```bash
# For corporate networks, configure pip proxy
pip3 install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### 3. Configuration Problems

#### Missing .env File
**Symptoms**: Atlas runs but can't access external services
```bash
# Create .env file from template
cp .env.example .env

# Or use the automated setup script
python3 scripts/generate_env.py
```

#### Invalid Configuration Values
**Symptoms**: Configuration errors on startup
```bash
# Run detailed validation
python3 scripts/validate_config.py

# Check for placeholder values
grep -E "(your_|test_|example)" config/.env
```

#### Directory Permission Issues
**Symptoms**: `PermissionError` when creating output directories
```bash
# Create output directory with proper permissions
mkdir -p output/{articles,podcasts,youtube,logs}
chmod 755 output
chmod 755 output/*

# Or change DATA_DIRECTORY to a writable location
echo "DATA_DIRECTORY=$HOME/atlas_data" >> config/.env
```

### 4. API Key Issues

#### OpenRouter API Key Problems

**Invalid Key Format**
```bash
# Check key format (should start with sk-or-v1-)
grep OPENROUTER_API_KEY config/.env
```
**Fix**: Get correct key from https://openrouter.ai/keys

**Key Not Working**
```bash
# Test API key directly
curl -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  https://openrouter.ai/api/v1/models
```

#### DeepSeek API Key Problems
```bash
# Test DeepSeek key
curl -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  https://api.deepseek.com/v1/models
```

#### YouTube API Key Issues
```bash
# Test YouTube API key
curl "https://www.googleapis.com/youtube/v3/search?part=snippet&q=test&key=YOUR_KEY"
```

### 5. Runtime Errors

#### Import Errors
**Symptoms**: `ModuleNotFoundError` or `ImportError`

**Missing modules**:
```bash
# Install specific missing modules
pip3 install module_name

# Reinstall all requirements
pip3 install --force-reinstall -r requirements.txt
```

**Path issues**:
```bash
# Check Python path
python3 -c "import sys; print('\\n'.join(sys.path))"

# Run from correct directory
cd /path/to/Atlas
python3 run.py --help
```

#### Database/Storage Issues
**Symptoms**: `sqlite3.OperationalError` or file access errors

```bash
# Check database file permissions
ls -la *.db

# Create new database if corrupted
rm atlas.db  # This will recreate on next run

# Check disk space
df -h .
```

#### Memory Issues
**Symptoms**: `MemoryError` or system freezing

```bash
# Check available memory
free -h  # Linux
vm_stat  # macOS

# Reduce podcast episode limit
echo "PODCAST_EPISODE_LIMIT=10" >> config/.env

# Use lighter AI models
echo "MODEL_BUDGET=mistralai/mistral-7b-instruct:free" >> config/.env
```

### 6. Network and Connectivity

#### Firewall/Proxy Issues
```bash
# Test basic connectivity
curl -I https://openrouter.ai
curl -I https://www.youtube.com

# Configure proxy if needed
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
```

#### DNS Issues
```bash
# Test DNS resolution
nslookup openrouter.ai
nslookup api.deepseek.com

# Use alternative DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

## 🔍 Diagnostic Commands

### Configuration Diagnosis
```bash
# Full configuration report
python3 scripts/validate_config.py

# Check specific issues
python3 scripts/validate_config.py --errors-only

# Get fix commands only
python3 scripts/validate_config.py --fix > fix_config.sh
chmod +x fix_config.sh
./fix_config.sh
```

### System Information
```bash
# Python environment info
python3 -c "
import sys
import platform
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'Architecture: {platform.architecture()}')
"

# Installed packages
pip3 list | grep -E "(requests|beautifulsoup|yaml|dotenv)"
```

### Permissions Check
```bash
# Check directory permissions
ls -la output/
ls -la config/

# Test write permissions
touch output/.write_test && rm output/.write_test && echo "✅ Output directory writable" || echo "❌ Output directory not writable"
```

## 🚫 Common Error Messages and Solutions

### "ModuleNotFoundError: No module named 'requests'"
```bash
pip3 install requests beautifulsoup4 lxml
```

### "FileNotFoundError: [Errno 2] No such file or directory: 'config/.env'"
```bash
cp .env.example config/.env
# Or create minimal .env:
mkdir -p config
echo "DATA_DIRECTORY=output" > config/.env
```

### "PermissionError: [Errno 13] Permission denied: 'output'"
```bash
mkdir -p output
chmod 755 output
# Or change to home directory:
echo "DATA_DIRECTORY=$HOME/atlas_data" >> config/.env
```

### "ConnectionError: HTTPSConnectionPool(host='openrouter.ai')"
```bash
# Check internet connection
ping openrouter.ai

# Check firewall/proxy settings
curl -v https://openrouter.ai

# Try with proxy if needed
export HTTPS_PROXY=http://your-proxy:port
```

### "Invalid API key format"
```bash
# Check key in .env file
grep OPENROUTER_API_KEY config/.env

# Key should start with sk-or-v1-
# Get new key from https://openrouter.ai/keys
```

## 🏥 Recovery Procedures

### Complete Reset
If Atlas is completely broken:
```bash
# 1. Back up any important data
cp -r output output_backup

# 2. Clean installation
rm -rf config/.env *.db __pycache__/ */__pycache__/

# 3. Reinstall dependencies
pip3 install --force-reinstall -r requirements.txt

# 4. Recreate configuration
python3 scripts/generate_env.py

# 5. Validate setup
python3 scripts/validate_config.py
```

### Partial Reset (Keep Data)
If configuration is corrupted but data is good:
```bash
# Reset configuration only
rm config/.env
cp .env.example config/.env

# Reconfigure
python3 scripts/generate_env.py

# Validate
python3 scripts/validate_config.py
```

### Database Recovery
If database is corrupted:
```bash
# Backup current database
cp atlas.db atlas.db.backup

# Remove corrupted database (will recreate)
rm atlas.db

# Run Atlas to recreate database
python3 run.py --help
```

## 🔧 Advanced Troubleshooting

### Debug Mode
```bash
# Run with maximum logging
python3 run.py --all --verbose

# Check log files
tail -f output/logs/atlas.log
```

### Environment Variables Debug
```bash
# Show all Atlas-related environment variables
env | grep -E "(ATLAS|LLM|API|DATA_)"

# Test configuration loading
python3 -c "
from helpers.config import load_config
config = load_config()
print('Config loaded successfully')
for key in sorted(config.keys()):
    if 'password' not in key.lower() and 'key' not in key.lower():
        print(f'{key}: {config[key]}')
"
```

### Network Debug
```bash
# Test all external services
services=("https://openrouter.ai" "https://api.deepseek.com" "https://www.googleapis.com")
for service in "${services[@]}"; do
    echo "Testing $service..."
    curl -I --connect-timeout 10 "$service" && echo "✅ OK" || echo "❌ Failed"
done
```

## 📞 Getting Help

### Before Seeking Help
1. Run `python3 scripts/validate_config.py` and include output
2. Include your Python version: `python3 --version`
3. Include your operating system: `uname -a` (Linux/Mac) or `systeminfo` (Windows)
4. Include the specific error message (full traceback if possible)

### Information to Provide
```bash
# Generate diagnostic report
echo "=== Atlas Diagnostic Report ===" > diagnostic_report.txt
echo "Date: $(date)" >> diagnostic_report.txt
echo "Python Version: $(python3 --version)" >> diagnostic_report.txt
echo "Platform: $(uname -a)" >> diagnostic_report.txt
echo "" >> diagnostic_report.txt
echo "=== Configuration Validation ===" >> diagnostic_report.txt
python3 scripts/validate_config.py >> diagnostic_report.txt 2>&1
echo "" >> diagnostic_report.txt
echo "=== Directory Structure ===" >> diagnostic_report.txt
ls -la >> diagnostic_report.txt
echo "" >> diagnostic_report.txt
echo "=== Installed Packages ===" >> diagnostic_report.txt
pip3 list >> diagnostic_report.txt
```

### Community Resources
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check `docs/` directory for specific guides
- **Configuration Reference**: See `.env.example` for all options

## ✅ Verification Checklist

After troubleshooting, verify Atlas is working:

- [ ] Configuration validates without errors: `python3 scripts/validate_config.py`
- [ ] Atlas starts without errors: `python3 run.py --help`
- [ ] Output directory is writable: `ls -la output/`
- [ ] API keys work (if configured): Test with validation script
- [ ] Basic functionality works: `python3 run.py --articles` (with a test URL)

---

*This troubleshooting guide covers the most common Atlas environment issues. If you encounter problems not covered here, please check the latest documentation or report the issue.*