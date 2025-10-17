# 🚀 OOS - New Interactive Interface

**One command to rule them all: `./run.py`**

## What Changed

**Before (Complex):**
```bash
./scripts/scripts/bootstrap_enhanced.sh project-name /path/to/project --no-github --verbose --skip-secrets
```

**After (Simple):**
```bash
./run.py
# Just answer a few questions!
```

## How It Works

OOS now detects where you are and shows you relevant options:

### 📂 Empty Directory
```bash
$ mkdir my-project && cd my-project
$ ~/oos/run.py

🚀 OOS - Organized Operational Setup
📂 Empty directory - perfect for a new project!

What do you need?
1. 🔐 Just secure environment (.env from 1Password) ← RECOMMENDED
2. 🆕 Full project setup with AI tools
3. ❓ Show help

Choice [1-3]:
```

### 🛠️ Existing Git Project
```bash
$ cd my-existing-react-app
$ ~/oos/run.py

🛠️ Enhancing existing project...
Project: my-existing-react-app

What would you like to add?
1. 🔐 Add secure environment (.env from 1Password)
2. 🤖 Add AI CLI runners (Claude, Gemini, etc.)
3. 🔧 Add development tools (diagnostics, health checks)
4. 📋 All of the above

Choice [1-4]:
```

### 🔧 OOS Repository
```bash
$ cd oos
$ ./run.py

🔧 OOS Management
You're in the OOS repository

What would you like to do?
1. 🆕 Create new project elsewhere
2. 🔧 Run diagnostics
3. 📖 Show documentation
4. 🔍 Test OOS installation

Choice [1-4]:
```

## Installation

### One-Line Install
```bash
curl -fsSL https://raw.githubusercontent.com/Khamel83/oos/master/scripts/install.sh | bash
```

### Manual Install
```bash
git clone https://github.com/Khamel83/oos.git ~/oos
sudo ln -sf ~/oos/run.py /usr/local/bin/oos
```

## Quick Start

### Most Common Use Case (80%): Just Want Secure Environment

```bash
mkdir my-new-project
cd my-new-project
oos  # Global command after installation
# Choose option 1
# Enter 1Password password
# Done! .env created with secure keys
```

### Full Project Setup

```bash
oos  # From any directory
# Choose "Full project setup"
# Enter project name
# Choose project path
# OOS does everything automatically
```

### Enhance Existing Project

```bash
cd my-existing-project
oos  # Detects existing project automatically
# Choose what to add
# OOS adds only what you need
```

## Features

- 🧠 **Context-Aware**: Different options based on where you run it
- 🎯 **Smart Defaults**: Recommends the most common choices
- 🔐 **Secure by Default**: 1Password integration for environment variables
- 🤖 **AI-Ready**: Pre-configured Claude, Gemini, and Qwen runners
- 🛠️ **Non-Destructive**: Only adds what you request
- ⚡ **Fast**: Auth-only setup takes 30 seconds

## Requirements

- **1Password CLI** (`op`) - for secure environment management
- **Git** - for repository operations
- **GitHub CLI** (`gh`) - optional, for GitHub integration
- **Node.js** - optional, for JavaScript projects

## Backward Compatibility

The old interface still works:
```bash
./scripts/scripts/bootstrap_enhanced.sh project-name /path/to/project [options]
```

But the new interactive interface is recommended for all new usage.

## Help

```bash
./run.py --help
```

Shows full documentation and usage examples.

---

**The new OOS interface: Simple questions, powerful results. 🎉**