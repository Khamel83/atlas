# 🚀 OOS Advanced Installation Guide

This guide covers more advanced installation methods for OOS.

## Manual Installation

### Option 1: Global Command (Recommended)
```bash
# Clone OOS anywhere you want
git clone https://github.com/Khamel83/oos.git
cd oos

# Make it globally accessible (recommended)
sudo ln -sf $(pwd)/run.py /usr/local/bin/oos

# Now you can use it anywhere
cd /path/to/another/project
oos
```

### Option 2: Add to your PATH
```bash
# Clone the repository
git clone https://github.com/Khamel83/oos.git ~/oos

# Add to your shell configuration (e.g., .bashrc, .zshrc)
echo 'export PATH="$PATH:$HOME/oos"' >> ~/.bashrc
source ~/.bashrc

# Now you can run it
cd /path/to/another/project
run.py
```

## Installation Examples

### Example 1: System-wide Installation
```bash
# Install for all users
cd /opt
sudo git clone https://github.com/Khamel83/oos.git
sudo ln -sf /opt/oos/run.py /usr/local/bin/oos

# Now anyone can use:
oos
```

### Example 2: Personal Installation
```bash
# Install in your home directory
cd ~
git clone https://github.com/Khamel83/oos.git

# Use with full path:
~/oos/run.py

# OR create personal alias
echo 'alias oos="~/oos/run.py"' >> ~/.bashrc
source ~/.bashrc

# Now you can use:
oos
```

## Requirements Check

```bash
# Check if you have requirements
oos --help  # Should show help if installed correctly

# Requirements:
# ✅ Python 3 (usually pre-installed)
# ✅ Git (for project management)
# ⚠️  1Password CLI (optional, for secure environments)
# ⚠️  GitHub CLI (optional, for GitHub integration)
```

## Troubleshooting

### "oos: command not found"
```bash
# Check if symlink exists
ls -la /usr/local/bin/oos

# If not, create it:
sudo ln -sf ~/oos/run.py /usr/local/bin/oos

# Or use full path:
~/oos/run.py
```

### "Permission denied"
```bash
# Make sure it's executable
chmod +x ~/oos/run.py
```
