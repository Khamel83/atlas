# Prerequisites Setup Guide

This guide ensures all necessary prerequisites are in place before beginning Atlas task execution, preventing blocking failures during development.

## Development Environment Prerequisites

### **Core Development Tools**

#### **Python Environment**
```bash
# Required: Python 3.9+
python3 --version  # Must show 3.9 or higher

# Recommended: Virtual environment
python3 -m venv atlas-venv
source atlas-venv/bin/activate  # Linux/Mac
# or
atlas-venv\Scripts\activate  # Windows

# Install development dependencies
pip install --upgrade pip
pip install pytest pytest-cov black isort mypy
```

#### **Git Configuration**
```bash
# Required: Git 2.20+
git --version

# Configure git (if not already done)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Clone Atlas repository
git clone <atlas-repository-url>
cd atlas

# Set up development branch
git checkout -b development
```

#### **Docker (Recommended)**
```bash
# Check Docker installation
docker --version  # Required for production deployment
docker-compose --version  # Required for multi-service setup

# Test Docker functionality
docker run hello-world  # Should complete successfully
```

## Atlas-Specific Prerequisites

### **Environment Configuration**

#### **Create Base .env File**
```bash
# Copy template to create working .env
cp .env.example .env

# Edit .env with your specific values
# Minimum required settings:
DATA_DIRECTORY=output
TRANSCRIBE_ENABLED=false
LOG_LEVEL=INFO
```

#### **Create Required Directories**
```bash
# Create all necessary directories
mkdir -p output/{articles,youtube,podcasts,logs}
mkdir -p output/articles/{html,markdown,metadata}
mkdir -p retries
mkdir -p config
mkdir -p logs
```

#### **Verify Current Atlas State**
```bash
# Check if basic components exist
ls -la helpers/  # Should show core modules
ls -la ask/      # Should show cognitive modules
ls -la web/      # Should show web interface
ls -la tests/    # Should show test structure

# Verify Python imports work
python -c "import helpers.config; print('Config module loads')"
python -c "import web.app; print('Web app module loads')"
```

## External Service Prerequisites

### **API Service Accounts**

#### **OpenRouter (AI Services)**
```bash
# Sign up at https://openrouter.ai/
# Generate API key
# Add to .env file:
echo "OPENROUTER_API_KEY=your_key_here" >> .env

# Test API access (optional but recommended)
curl -H "Authorization: Bearer your_key_here" \
     "https://openrouter.ai/api/v1/models" | head -20
```

#### **GitHub (Optional - for automation)**
```bash
# Generate GitHub personal access token
# Settings → Developer settings → Personal access tokens
# Required scopes: repo, workflow, read:org

# Add to .env (if using GitHub automation):
echo "GITHUB_TOKEN=your_token_here" >> .env
```

### **System Services**

#### **Redis (For Performance Phase)**
```bash
# Install Redis (required for Task 6.2)
# Ubuntu/Debian:
sudo apt-get install redis-server

# macOS:
brew install redis

# Windows:
# Download from https://redis.io/download

# Test Redis installation
redis-cli ping  # Should return "PONG"

# Start Redis service
# Linux:
sudo systemctl start redis-server
# macOS:
brew services start redis
```

#### **Meilisearch (For Search Phase)**
```bash
# Install Meilisearch (required for Task 7.2)
# Linux/macOS:
curl -L https://install.meilisearch.com | sh

# Or via Docker:
docker pull getmeili/meilisearch:latest

# Test Meilisearch installation
meilisearch --version  # Should show version number
```

## Hardware Prerequisites

### **Development Machine Requirements**

#### **Minimum Specifications**
- **RAM**: 8GB (16GB recommended for full development)
- **Storage**: 50GB free space (for content storage and development)
- **CPU**: Multi-core processor (for concurrent testing)
- **Network**: Reliable internet connection for content ingestion testing

#### **Raspberry Pi Deployment (Target Hardware)**
- **Model**: Raspberry Pi 4 (4GB+ RAM recommended)
- **Storage**: 64GB+ SD card (Class 10 or better)
- **Network**: Ethernet connection preferred for stability
- **Power**: Official Raspberry Pi power supply
- **Cooling**: Heat sinks or fan for sustained operation

### **Network Prerequisites**

#### **Firewall Configuration**
```bash
# Development: Ensure ports are available
# Port 8000: Atlas web interface
# Port 6379: Redis
# Port 7700: Meilisearch

# Check port availability
netstat -tulpn | grep :8000  # Should be empty
netstat -tulpn | grep :6379  # Should show redis if running
netstat -tulpn | grep :7700  # Should show meilisearch if running
```

#### **DNS Configuration**
```bash
# Verify external DNS works (for content ingestion)
nslookup google.com  # Should resolve successfully
nslookup youtube.com  # Should resolve successfully
nslookup archive.org  # Should resolve successfully
```

## Development Data Prerequisites

### **Test Content**

#### **Sample URLs for Testing**
Create `test_urls.txt` with sample content:
```
# Articles
https://blog.python.org/2023/10/python-3122-is-now-available.html
https://docs.python.org/3/tutorial/introduction.html

# YouTube
https://www.youtube.com/watch?v=HN1UjzRSdBk

# Podcasts
https://feeds.simplecast.com/54nAGcIl
```

#### **Test Configuration Files**
```bash
# Create minimal test configuration
cat > config/test_categories.yaml << EOF
categories:
  technology:
    keywords: ["python", "software", "programming"]
  education:
    keywords: ["tutorial", "guide", "learn"]
EOF
```

### **Database Prerequisites**

#### **SQLite Setup**
```bash
# Verify SQLite is available
sqlite3 --version  # Should show SQLite version

# Create test database (if needed)
sqlite3 atlas_test.db ".schema"  # Should create empty database
rm atlas_test.db  # Clean up test
```

## Quality Assurance Prerequisites

### **Code Quality Tools**

#### **Linting and Formatting**
```bash
# Install and configure code quality tools
pip install black isort mypy flake8

# Test tools work correctly
black --version
isort --version
mypy --version

# Create basic mypy configuration
cat > mypy.ini << EOF
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
EOF
```

#### **Testing Infrastructure**
```bash
# Install testing dependencies
pip install pytest pytest-cov pytest-mock responses

# Test pytest configuration
pytest --version
pytest --collect-only  # Should discover existing tests

# Run existing tests to verify setup
pytest -v  # Should run existing tests (may have failures - that's expected)
```

## Security Prerequisites

### **Basic Security Setup**

#### **File Permissions**
```bash
# Set secure permissions on sensitive files
chmod 600 .env  # Only user can read/write
chmod 700 atlas-venv/  # Only user can access virtual environment
chmod 755 output/  # User full access, others read/execute
```

#### **SSH Keys (for Raspberry Pi deployment)**
```bash
# Generate SSH key pair for Pi deployment (if needed)
ssh-keygen -t ed25519 -C "atlas-deployment-key"

# Test SSH access to Pi (replace with your Pi's IP)
ssh pi@raspberry-pi-ip "echo 'SSH connection works'"
```

## Validation Checklist

### **Pre-Development Validation**
Run this checklist before starting Task 1.1:

- [ ] **Python 3.9+** installed and accessible
- [ ] **Virtual environment** created and activated
- [ ] **Git repository** cloned and configured
- [ ] **Base .env file** created from template
- [ ] **Required directories** created with proper permissions
- [ ] **Core Atlas modules** import successfully
- [ ] **Development dependencies** installed (pytest, black, isort, mypy)
- [ ] **Code quality tools** working correctly
- [ ] **Docker** installed and functional (if using)

### **External Services Validation**
- [ ] **OpenRouter API key** configured and tested (if using AI features)
- [ ] **Redis** installed and responding to ping
- [ ] **Meilisearch** installed and accessible
- [ ] **GitHub token** configured (if using automation)
- [ ] **Network connectivity** verified for content ingestion
- [ ] **SSH access** to Raspberry Pi configured (if deploying)

### **Development Environment Validation**
- [ ] **Existing tests** run without import errors
- [ ] **Code formatting** tools work on existing codebase
- [ ] **Type checking** runs on existing codebase
- [ ] **Basic functionality** verified (imports work, no obvious breakage)
- [ ] **Test data** prepared for development testing
- [ ] **Documentation** accessible and readable

## Troubleshooting Common Prerequisites Issues

### **Import Errors**
```bash
# Problem: "ModuleNotFoundError" when importing Atlas modules
# Solution: Ensure you're in the correct directory and virtual environment
pwd  # Should show Atlas project directory
which python  # Should show virtual environment path
pip list | grep -E "(fastapi|beautifulsoup|requests)"  # Should show Atlas dependencies
```

### **Permission Errors**
```bash
# Problem: Permission denied errors when accessing files
# Solution: Fix file permissions
sudo chown -R $USER:$USER .  # Take ownership of all project files
chmod -R u+rw .  # Ensure user can read/write all files
chmod +x scripts/*.py  # Make scripts executable
```

### **Port Conflicts**
```bash
# Problem: "Address already in use" errors
# Solution: Find and kill conflicting processes
sudo lsof -i :8000  # Find process using port 8000
sudo kill -9 <PID>  # Kill the conflicting process
```

### **Network Issues**
```bash
# Problem: Cannot connect to external services
# Solution: Verify network connectivity and DNS
ping 8.8.8.8  # Test basic connectivity
nslookup google.com  # Test DNS resolution
curl -I https://httpbin.org/get  # Test HTTPS connectivity
```

This prerequisites guide ensures a smooth start to Atlas development by addressing all potential blocking issues before they can halt task execution.