# 🎯 OOS Usage Examples

## Real-World Scenarios

### Scenario 1: New Developer Getting Started

**Sarah just joined a team and needs to set up a development environment:**

```bash
# Install OOS once
curl -fsSL https://example.com/scripts/install.sh | bash

# Create new project
mkdir my-api-project
cd my-api-project
oos

# OOS shows:
# 📂 Empty directory - perfect for a new project!
# What do you need?
# 1. 🔐 Just secure environment (.env from 1Password) ← RECOMMENDED
# 2. 🆕 Full project setup with AI tools

# Sarah chooses 1, enters 1Password password
# ✅ Done! .env created with 50 secure variables
# ✅ Added .env to .gitignore
```

### Scenario 2: Existing Project Enhancement

**Mike has a React app and wants to add AI development tools:**

```bash
# Navigate to existing project
cd ~/projects/my-react-dashboard
oos

# OOS detects git repository and shows:
# 🛠️ Enhancing existing project...
# Project: my-react-dashboard
#
# What would you like to add?
# 1. 🔐 Add secure environment (.env from 1Password)
# 2. 🤖 Add AI CLI runners (Claude, Gemini, etc.)
# 3. 🔧 Add development tools (diagnostics, health checks)
# 4. 📋 All of the above

# Mike chooses 4 for full enhancement
# OOS adds AI tools without disrupting existing code
```

### Scenario 3: Quick Environment Setup

**Lisa needs API keys for a hackathon project:**

```bash
# Quick 30-second setup
mkdir hackathon-project
cd hackathon-project
oos

# Choose option 1 (secure environment)
# Enter 1Password password once
# ✅ Done! Ready to code with secure API keys

# Start coding immediately
echo 'console.log("API Key:", process.env.OPENAI_API_KEY)' > test.js
node test.js  # Works with secure keys!
```

### Scenario 4: Team Onboarding

**Company wants to standardize development environments:**

```bash
# IT Department creates setup guide:

# 1. Install OOS (one-time per developer)
curl -fsSL https://company.com/oos-scripts/install.sh | bash

# 2. Each project uses standardized setup
cd any-project
oos  # Context-aware setup

# 3. All developers get:
#    - Secure API keys from company 1Password
#    - Standardized AI development tools
#    - Consistent project structure
```

## Command Examples

### Basic Usage
```bash
oos              # Interactive mode - answers questions
oos --help       # Show help and documentation
```

### Context Examples
```bash
# In empty directory
mkdir new-project && cd new-project
oos  # Shows new project options

# In existing git project
cd my-existing-app
oos  # Shows enhancement options

# In OOS repository
cd ~/oos
oos  # Shows management options
```

## Integration Examples

### With IDE/Editor
```bash
# VS Code integration
cd my-project
oos  # Setup environment
code .  # Open in VS Code with secure environment

# Cursor integration
cd my-project
oos
cursor .  # AI-powered coding with secure keys
```

### With CI/CD
```bash
# GitHub Actions can use OOS-created projects
name: Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm test  # Uses .env from OOS setup
```

### With Docker
```bash
# OOS creates .env file that works with Docker
cd my-project
oos  # Creates secure .env
docker-compose up  # Uses environment variables
```

## Troubleshooting Examples

### "oos: command not found"
```bash
# Check if installed
which oos

# If not found, install:
curl -fsSL https://example.com/scripts/install.sh | bash

# Or use full path temporarily:
~/oos/run.py
```

### "1Password authentication failed"
```bash
# Sign into 1Password first:
eval $(op signin)

# Then use OOS:
oos
```

### "Permission denied"
```bash
# Fix permissions:
chmod +x ~/oos/run.py

# Try again:
oos
```

## Advanced Usage

### Custom Installation Directory
```bash
# Install to /opt instead of ~/oos
sudo git clone https://github.com/user/oos.git /opt/oos
sudo ln -sf /opt/oos/run.py /usr/local/bin/oos
```

### Multiple Environment Setup
```bash
# Development environment
cd ~/dev/my-project
oos  # Choose development options

# Production environment
cd ~/prod/my-project
oos  # Choose production-safe options
```

### Team Templates
```bash
# Create team-specific project templates
cd ~/oos/templates
# Add custom templates for your team's stack
oos  # Now shows your custom options
```

---

**The goal: One simple command (`oos`) that works everywhere and handles the complexity for you! 🎉**