# Atlas Setup and Configuration Guide

This comprehensive guide will help you set up Atlas on your system, from initial installation to complete configuration. Whether you're a non-technical user or an experienced developer, this guide provides step-by-step instructions to get Atlas running smoothly.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Initial Configuration](#initial-configuration)
4. [First-Time Setup Wizard](#first-time-setup-wizard)
5. [Verification Steps](#verification-steps)
6. [Platform-Specific Guides](#platform-specific-guides)
7. [Common Error Messages and Solutions](#common-error-messages-and-solutions)

## System Requirements

### Hardware Requirements

- **Minimum**: 4GB RAM, 20GB free disk space, 2 CPU cores
- **Recommended**: 8GB+ RAM, 50GB+ free disk space, 4+ CPU cores
- **Storage**: SSD recommended for better performance

### Software Requirements

- **Operating System**:
  - Ubuntu 20.04+ (recommended)
  - macOS 12+ (Intel or Apple Silicon)
  - Windows 10/11 with WSL2
- **Python**: 3.9 or higher
- **Git**: 2.20 or higher (recommended)
- **Internet Connection**: Required for initial setup and content ingestion

### Network Requirements

- **Inbound**: Port 8000 (web interface, configurable)
- **Outbound**: Access to content sources (web, YouTube, podcast feeds)
- **Optional**: Port 22 (SSH) for remote management

## Installation Steps

### One-Command Setup with Error Handling

Atlas provides a simple one-command setup process:

```bash
# Clone the repository
git clone https://github.com/your-username/atlas.git
cd atlas

# Run the setup wizard
python scripts/setup_wizard.py
```

The setup wizard will guide you through:
1. Environment validation
2. Dependency installation
3. Directory structure creation
4. Configuration setup
5. System validation

### Manual Installation Steps

If you prefer manual installation:

#### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/atlas.git
cd atlas
```

#### Step 2: Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Create Directory Structure
```bash
mkdir -p \
  output/articles/html \
  output/articles/markdown \
  output/articles/metadata \
  output/youtube/transcripts \
  output/youtube/videos \
  output/podcasts/audio \
  output/podcasts/transcripts \
  config \
  logs \
  retries
```

#### Step 5: Configure Environment
```bash
cp .env.template .env
# Edit .env with your API keys and preferences
```

## Initial Configuration

### Environment Variables

Configure Atlas behavior through the `.env` file:

#### Required Configuration

```bash
# API Keys (at least one required for AI features)
OPENROUTER_API_KEY=your_openrouter_api_key
OPENAI_API_KEY=your_openai_api_key

# Storage paths
DATA_DIRECTORY=./output
LOG_DIR=./logs
CACHE_DIR=./.cache
```

#### Optional Configuration

```bash
# YouTube API (for YouTube ingestion)
YOUTUBE_API_KEY=your_youtube_api_key

# Instapaper credentials (for Instapaper import)
INSTAPAPER_LOGIN=your_instapaper_email
INSTAPAPER_PASSWORD=your_instapaper_password

# Podcast configuration
PODCAST_EPISODE_LIMIT=10
TRANSCRIBE_ENABLED=true
WHISPER_MODEL=base

# AI Model Configuration
MODEL=google/gemini-2.0-flash-lite-001
MODEL_PREMIUM=google/gemini-2.0-flash-lite-001
MODEL_BUDGET=mistralai/mistral-7b-instruct
MODEL_FALLBACK=google/gemini-2.0-flash-lite-001
```

### Content Categories

Customize content categorization by editing `config/categories.yaml`:

```yaml
categories:
  technology:
    keywords: ["ai", "machine learning", "programming", "software"]
    priority: 1
  business:
    keywords: ["finance", "marketing", "strategy", "startup"]
    priority: 2
  science:
    keywords: ["research", "study", "experiment", "discovery"]
    priority: 3
```

## First-Time Setup Wizard

### Running the Wizard

The Atlas Setup Wizard provides a guided experience:

```bash
python scripts/setup_wizard.py
```

#### Wizard Options

- **Interactive Mode** (default): Step-by-step guidance with prompts
- **Automated Mode**: `--automated` - Uses defaults with minimal interaction
- **Skip Dependencies**: `--skip-deps` - Skip dependency validation
- **Configuration Only**: `--config-only` - Only configure environment

### Wizard Steps

1. **Environment Check**: Validates Python version and project structure
2. **Dependency Validation**: Checks and installs required packages
3. **Directory Setup**: Creates required folder structure
4. **Environment Configuration**: Generates and configures `.env` file
5. **Configuration Validation**: Tests configuration loading
6. **Initial Test**: Runs basic system tests
7. **Setup Completion**: Provides next steps and documentation

## Verification Steps

### Confirm Everything is Working

After setup, verify your installation:

#### Step 1: Check Configuration
```bash
python -c "from helpers.config import load_config; print('Configuration loads successfully')"
```

#### Step 2: Test Core Imports
```bash
python -c "from helpers.article_fetcher import ArticleFetcher; print('Article fetcher loads successfully')"
```

#### Step 3: Verify Directory Structure
```bash
ls -la output/
# Should show articles, youtube, podcasts directories
```

#### Step 4: Test Help Command
```bash
python run.py --help
# Should display available commands
```

#### Step 5: Check Web Interface
```bash
python web/app.py --help
# Should display web server options
```

### Running Your First Content Processing

#### Step 1: Add Test Content
```bash
echo "https://example.com/article1" > inputs/articles.txt
echo "https://example.com/article2" >> inputs/articles.txt
```

#### Step 2: Process Content
```bash
python run.py --articles
```

#### Step 3: Check Results
```bash
ls output/articles/markdown/
# Should show processed articles
```

## Platform-Specific Guides

### Mac Setup (Intel and Apple Silicon)

#### Prerequisites
1. Install Homebrew:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install required packages:
   ```bash
   brew install python3 git ffmpeg
   ```

#### Setup Process
```bash
# Clone repository
git clone https://github.com/your-username/atlas.git
cd atlas

# Run setup wizard
python scripts/setup_wizard.py
```

#### Notes for Apple Silicon
- Ensure you're using ARM64 Python version
- Some packages may require Rosetta 2 compatibility mode

### Linux Setup (Ubuntu/Debian)

#### Prerequisites
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git ffmpeg
```

#### Setup Process
```bash
# Clone repository
git clone https://github.com/your-username/atlas.git
cd atlas

# Run setup wizard
python scripts/setup_wizard.py
```

### Windows Setup (WSL2)

#### Prerequisites
1. Install WSL2:
   ```powershell
   wsl --install
   ```

2. Install Ubuntu from Microsoft Store

3. In Ubuntu WSL:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv git ffmpeg
   ```

#### Setup Process
```bash
# Clone repository
git clone https://github.com/your-username/atlas.git
cd atlas

# Run setup wizard
python scripts/setup_wizard.py
```

## Common Error Messages and Solutions

### "Python 3.9+ required"

**Problem**: Your system has an older Python version
**Solution**:
- Install Python 3.9+ from python.org
- Use `python3.9` or `python3.10` explicitly in commands

### "Missing required files"

**Problem**: Setup wizard can't find project files
**Solution**:
- Ensure you're running the wizard from the Atlas project root directory
- Check that all required files exist: `run.py`, `requirements.txt`, etc.

### "Dependency validation failed"

**Problem**: Required Python packages couldn't be installed
**Solution**:
- Check internet connectivity
- Try running with `--fix` option: `python scripts/validate_dependencies.py --fix`
- Manually install packages: `pip install -r requirements.txt`

### "Permission denied" when creating directories

**Problem**: Insufficient permissions in project directory
**Solution**:
- Run setup with appropriate permissions
- Change ownership of project directory: `sudo chown $USER:$USER -R .`
- Run setup wizard with sudo (not recommended)

### "API key validation failed"

**Problem**: Invalid or missing API keys
**Solution**:
- Verify API key format and validity
- Check that keys are properly set in `.env` file
- Test keys with provider's API directly

### "Port already in use"

**Problem**: Another service is using port 8000
**Solution**:
- Stop conflicting service
- Change Atlas port in configuration: `API_PORT=8001` in `.env`
- Check what's using the port: `lsof -i :8000`

### "Virtual environment not activated"

**Problem**: Running commands without activating virtual environment
**Solution**:
- Activate virtual environment: `source venv/bin/activate`
- Use full path to Python: `/path/to/venv/bin/python`
- Create alias for convenience: `alias atlaspy='/path/to/venv/bin/python'`

### "Module not found" errors

**Problem**: Python can't find required modules
**Solution**:
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python path: `echo $PYTHONPATH`
- Add project root to path: `export PYTHONPATH=/path/to/atlas:$PYTHONPATH`

## Advanced Configuration

### Customizing AI Models

Atlas supports multiple AI providers and models:

```bash
# OpenRouter (default)
LLM_PROVIDER=openrouter
MODEL=google/gemini-2.0-flash-lite-001

# OpenAI
LLM_PROVIDER=openai
MODEL=gpt-4-turbo

# Ollama (local)
LLM_PROVIDER=ollama
MODEL=llama3
```

### Mac Mini Audio Processing Setup (Optional)

Atlas can leverage a dedicated Mac Mini for high-quality Whisper transcription processing:

#### Mac Mini Requirements
- Mac Mini with macOS 12+ (Intel or Apple Silicon)
- 8GB+ RAM (16GB recommended for large models)
- 50GB+ free disk space for Whisper models
- SSH access from Atlas server

#### Mac Mini Setup Process

1. **Install Required Software on Mac Mini:**
   ```bash
   # Run this on the Mac Mini
   curl -O https://raw.githubusercontent.com/your-username/atlas/main/scripts/install_mac_mini_software.sh
   chmod +x install_mac_mini_software.sh
   ./install_mac_mini_software.sh
   ```

2. **Configure SSH Access:**
   ```bash
   # Run this on your Atlas server
   curl -O https://raw.githubusercontent.com/your-username/atlas/main/scripts/setup_mac_mini_ssh.sh
   chmod +x setup_mac_mini_ssh.sh
   ./setup_mac_mini_ssh.sh
   ```

3. **Configure Atlas to Use Mac Mini:**
   ```bash
   # Add to your .env file
   MAC_MINI_ENABLED=true
   MAC_MINI_SSH_HOST=macmini  # or IP address
   MAC_MINI_QUEUE_DIR=~/atlas_worker/queue
   MAC_MINI_WHISPER_MODEL=base  # tiny, base, small, medium, large
   MAC_MINI_TIMEOUT=300
   ```

4. **Test Mac Mini Connection:**
   ```bash
   # Test SSH connection
   python3 -c "
   from helpers.mac_mini_client import MacMiniClient
   client = MacMiniClient()
   result = client.test_connection()
   print('Mac Mini Status:', result)
   "
   ```

#### Mac Mini Processing Features

**🎙️ Whisper Model Management:**
- Automatic model downloading and caching
- Multiple model sizes for speed/quality optimization
- Graceful fallback to local processing if unavailable

**⚡ Performance Benefits:**
- Dedicated hardware for audio processing
- Faster transcription than local processing
- Parallel processing capabilities
- Reduced load on main Atlas server

**🔄 Queue-Based Processing:**
- File-based task queue over SSH
- Automatic retry logic for failed tasks
- Status monitoring and result retrieval
- Clean task cleanup after completion

#### Troubleshooting Mac Mini Integration

**Connection Issues:**
```bash
# Test SSH connectivity
ssh macmini 'echo "SSH connection successful"'

# Check Mac Mini worker status
ssh macmini 'ps aux | grep atlas_worker'

# View Mac Mini logs
ssh macmini 'tail -f ~/atlas_worker/logs/worker.log'
```

**Performance Issues:**
```bash
# Check Mac Mini resource usage
ssh macmini 'top -l 1 | head -20'

# Monitor processing queue
python3 -c "
from helpers.mac_mini_client import MacMiniClient
client = MacMiniClient()
status = client.get_queue_status()
print('Queue Status:', status)
"
```

### Performance Tuning

Adjust performance settings in `.env`:

```bash
# Limit concurrent operations
MAX_CONCURRENT_ARTICLES=5
MAX_CONCURRENT_PODCASTS=2

# Adjust timeout settings
ARTICLE_TIMEOUT=300
PODCAST_DOWNLOAD_TIMEOUT=600

# Memory optimization
CACHE_SIZE_LIMIT=1000

# Mac Mini specific settings
MAC_MINI_MAX_CONCURRENT_TASKS=3
MAC_MINI_TASK_TIMEOUT=600
MAC_MINI_RETRY_ATTEMPTS=3
```

### Security Configuration

Enhance security with these settings:

```bash
# Enable encryption
ENCRYPTION_ENABLED=true
ENCRYPTION_KEY=your_encryption_key

# Restrict web interface access
WEB_INTERFACE_BIND_ADDRESS=127.0.0.1
WEB_INTERFACE_PORT=8000

# Enable authentication
REQUIRE_AUTHENTICATION=true
```

## Troubleshooting

### System Health Monitoring

Monitor Atlas health with built-in tools:

```bash
# Check system status
python atlas_status.py

# Detailed status
python atlas_status.py --detailed

# Resource monitoring
python helpers/resource_monitor.py
```

### Log Analysis

Check logs for troubleshooting information:

```bash
# View main logs
tail -f logs/atlas_service.log

# View error logs
tail -f logs/error.log

# Search logs for specific errors
grep "ERROR" logs/*.log
```

### Reset and Recovery

If you need to reset your Atlas installation:

```bash
# Clear search index
python scripts/search_manager.py clear

# Reset configuration
rm .env
cp .env.template .env

# Clear output directories
rm -rf output/*
```

## Getting Help

### Community Support

Join the Atlas community:
- Discord: https://discord.gg/atlas
- Reddit: r/AtlasPlatform
- GitHub Discussions: https://github.com/your-username/atlas/discussions

### Professional Support

For enterprise support:
- Email: support@atlas-platform.com
- Phone: +1 (555) 123-4567
- SLA: 24-hour response time

### Reporting Issues

Report bugs and issues on GitHub:
- Repository: https://github.com/your-username/atlas
- Issue Template: Include system information, error messages, and reproduction steps

## Next Steps

After successful setup:
1. Configure your preferred AI provider
2. Set up content ingestion sources
3. Explore the web dashboard
4. Configure automated processing
5. Join the community for tips and updates

Happy content processing! 🧠✨