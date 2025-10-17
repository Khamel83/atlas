# 🚀 OOS - Open Operating System

**One command installs everything. Zero cost to run. Works with any project.**

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/Khamel83/oos/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Install](https://img.shields.io/badge/install-curl%20%7C%20bash-orange.svg)](#installation)
[![Archon Integration](https://img.shields.io/badge/Archon%20MCP-Integrated-brightgreen)](docs/ARCHON_INTEGRATION.md)
[![Persistent Assistant](https://img.shields.io/badge/AI%20Assistant-Always%20On-purple)](bin/oos-daemon)
[![Slash Commands](https://img.shields.io/badge/Slash%20Commands-14%20Available-blue)](.claude/commands/)
[![Token Optimization](https://img.shields.io/badge/Token%20Reduction-40--60%25-orange)](src/token_optimization.py)

## 🎯 What is OOS?

OOS is a universal productivity system that adds powerful search, automation, and AI capabilities to any project. Think of it as your personal operating system layer that works everywhere.

**NEW in v1.1.0**: Persistent AI assistant with Archon MCP integration for intelligent task management and wake word activation.

### ⚡ Key Features

- **🧠 Persistent AI Assistant**: Always-on background assistant with "Hey OOS" wake word activation
- **📋 Intelligent Task Management**: Archon MCP integration for AI-driven project management
- **🔍 Universal Search**: 4 free search engines + optional Perplexity Pro + knowledge base search
- **💰 Cost Optimizer**: Replace expensive APIs with free alternatives
- **🤖 Enhanced AI Integration**: 14 smart slash commands for Claude Code
- **📦 Universal Install**: One command works with any project type
- **🛡️ Built-in Safety**: Cost controls and usage monitoring
- **🎓 Self-Referential Learning**: OOS learns from usage patterns to prevent repeated inefficiencies

## 🚀 Quick Start

### One-Line Installation
```bash
curl -sSL https://raw.githubusercontent.com/Khamel83/oos/master/install.sh | bash
```

### Instant Usage
```bash
# Search anything for free
./oos search "python tutorials"
./oos search "docker best practices"

# Start persistent assistant
./bin/oos-daemon start

# Wake word activation
echo "hey oos implement user authentication" > ~/.oos/wake.txt

# Task management
./oos task list
./oos task create "Add OAuth integration" "Implement Google OAuth with PKCE"

# In Claude Code - use enhanced slash commands
/archon-status      # View project status and tasks
/archon-research    # Search knowledge base
/smart-commit       # Generate commit messages
/optimize           # Reduce context tokens
```

## 💰 Cost Benefits

| Before OOS | After OOS | Savings |
|------------|-----------|---------|
| Google Search API: $87/month | Free alternatives: $0/month | $1,044/year |
| Manual commit messages | AI-generated | Hours saved |
| Context bloat | 40% token reduction | $$$ on AI costs |

## 🎯 Works With Any Project

OOS automatically detects and integrates with:

- **Languages**: Node.js, Python, Rust, Go, PHP, Ruby, Java
- **Tools**: Git, Docker, Claude Code
- **Existing setups**: Won't break anything

### The Problem OOS Solves

- **Token waste**: Conversations hit limits with redundant context
- **Unclear requests**: You ramble, Claude asks confusing questions
- **Context loss**: Important information gets buried or forgotten
- **Repetitive work**: Same clarifications and optimizations over and over
- **Documentation debt**: Code changes without proper documentation

### The OOS Solution

- **Meta-clarification**: Get help from other AIs when Claude's questions are confusing
- **Auto-optimization**: Reduce token usage by 40-60% automatically
- **Smart workflows**: Turn rambling thoughts into structured plans
- **Self-documentation**: Automated commit messages and consistency checks
- **Learning system**: Remember lessons learned to avoid repeating mistakes

## 🚀 NEW: Persistent AI Assistant (v1.1.0)

### 🧠 Archon MCP Integration
- **Intelligent Task Management**: Full integration with Archon MCP server for AI-driven project coordination
- **Knowledge Base Search**: Access shared knowledge across all your projects
- **Natural Language Tasks**: Create and manage tasks using conversational commands
- **Cross-Project Intelligence**: Leverage learnings from one project in another

### 🎤 Wake Word Activation
```bash
# Start the persistent assistant
./bin/oos-daemon start

# Use wake word from anywhere
echo "hey oos implement user authentication with OAuth" > ~/.oos/wake.txt
```

### 🎓 Self-Referential Learning Tools

OOS now includes tools to prevent "learning the same lessons over and over":

```bash
# Review development wisdom before coding
./bin/development_guide.sh

# Capture inefficient patterns for future improvement
./bin/archon_learning.sh capture-atlas

# Smart repository updates with auto-integration
./bin/archon_learning.sh smart-update oos
```

**Key Learning Integration:**
- Pre-development learning enforcement
- Automatic pattern detection from user flows
- Integration scripts for complex project structures
- Archon-based knowledge persistence

### 📋 Enhanced Claude Code Integration
- **4 New Slash Commands**: /archon-status, /archon-task-start, /archon-research, /archon-complete
- **Task-Driven Development**: Never code without clear task context
- **Real-time Sync**: Changes in Claude Code update Archon tasks automatically
- **Research Assistant**: Instant access to relevant code examples and documentation

### 🛠️ Developer Tools
- **oos-op**: 1Password session management (7-30 day sessions or permanent service accounts)
- **oos-doctor**: Enhanced health monitoring with Archon connectivity checks
- **Enhanced Bootstrap**: Archon-first workflow setup with better error handling

## ✨ Core Features

### 🧠 Context Engineering
- **Write/Select/Compress/Isolate** principles applied automatically
- **Filesystem offloading** for large context management
- **Intelligent caching** with relevance scoring
- **Multi-strategy compression** for optimal token usage

### 🤖 Meta-Clarification System
```
Claude: "I need clarification on your authentication requirements..."
You: /meta-ai
→ Get a structured prompt for ChatGPT/Claude to get better answers
```

### ⚡ Smart Slash Commands
- `/help-me [request]` - Auto-optimized processing
- `/brain-dump [rambling]` - Turn messy thoughts into clear structure
- `/meta-ai` - Generate prompts for external AI assistance
- `/smart-commit` - AI-generated commit messages
- `/auto-fix` - Automatic code consistency fixes
- [See all 10 commands](.claude/slash_commands.json)

### 🤖 Meta-AI Prompt Enhancement
Transform brief requests into detailed, structured prompts that get better responses from Claude:

```bash
# Turn "fix auth bug" into a 300-500 word structured prompt
./bin/claude-help-me.sh "fix auth bug"

# Copy generated prompt → send to ChatGPT → use response with Claude
# Result: Much better, more targeted assistance
```

### 📊 Token Optimization
- **24.8%** average token reduction in testing
- **40-60%** reduction possible with aggressive optimization
- **Automatic budget management** with configurable limits
- **Context-aware compression** preserving important information

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude Code   │───▶│  OOS Middleware  │───▶│   Your Code     │
│   (Interface)   │    │ Context Engine   │    │  (Results)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Context Store   │
                    │ • Token Cache    │
                    │ • Learning DB    │
                    │ • Session State  │
                    └──────────────────┘
```

### Key Components

- **Clarification Workflow** ([src/clarification_workflow.py](src/clarification_workflow.py)) - Structured question/answer system
- **Token Optimization** ([src/token_optimization.py](src/token_optimization.py)) - Multi-strategy context compression
- **Auto Documentation** ([src/auto_documentation.py](src/auto_documentation.py)) - Smart git integration and consistency
- **Simple Command Handler** ([src/simple_command_handler.py](src/simple_command_handler.py)) - Clean slash command management
- **MCP Server** ([mcp_server.py](mcp_server.py)) - Claude Code integration layer
- **Archon Integration** ([docs/ARCHON_INTEGRATION.md](docs/ARCHON_INTEGRATION.md)) - Project and task management with MCP

### 📉 Code Simplification

**Recently simplified by 27.5% (1,794 lines removed):**
- Replaced overly complex 1,363-line `command_generator.py` with clean 104-line `simple_command_handler.py`
- Simplified `claude_integration.py` from 613 lines to 78 lines
- Maintained all functionality while dramatically reducing complexity

## 📚 Documentation

### Getting Started
- [QUICK_START.md](QUICK_START.md) - 30-second setup guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Detailed installation instructions
- [docs/CLAUDE_CODE_INTEGRATION.md](docs/CLAUDE_CODE_INTEGRATION.md) - How to use within Claude Code

### Architecture & Design
- [docs/context_engineering_architecture.md](docs/context_engineering_architecture.md) - Complete system design
- [docs/scaling_principles.md](docs/scaling_principles.md) - Scaling and "Bitter Lesson" principles
- [docs/retrieval_patterns.md](docs/retrieval_patterns.md) - Hybrid retrieval strategies

### Research & Implementation
- [docs/context_engineering_research.md](docs/context_engineering_research.md) - Industry research findings
- [docs/context_engineering_completion_summary.md](docs/context_engineering_completion_summary.md) - Implementation summary

## 🧪 Testing

```bash
# Run all context engineering tests
python3 -m pytest tests/test_context_engineering.py -v

# Test individual components
python3 bin/clarification_cli.py  # Interactive workflow test
./bin/oos-doctor                  # System health check
python3 -m src.token_optimization --test  # Token optimization test
```

**All tests passing**: ✅ 100% component coverage with integration validation

## 🎯 Real-World Usage

### Example: Building a Chat App
```bash
You: /brain-dump I want to build a real-time chat app but not sure about WebSocket vs Server-Sent Events vs polling, also need authentication and maybe Docker but Kubernetes might be overkill

OOS: 🧠 Processing your request with context engineering...
     📊 Context optimized: 1,847 → 1,204 tokens (35% reduction)

     ✅ I'll help you implement this with:
     • Architecture planning for real-time communication
     • Authentication strategy selection
     • Deployment approach recommendations

     🚀 Let me break this down with clarifying questions...
```

### Example: Meta-Clarification
```bash
Claude: "I need more details about your database schema requirements, performance expectations, and data consistency needs..."

You: /meta-ai

OOS: Here's a structured prompt for external AI assistance:

===COPY THIS TO CHATGPT/CLAUDE===
I'm designing a database schema and need help with these technical decisions:

Context: Building a real-time chat application with user authentication

Questions:
1. Schema design: Normalized vs denormalized for chat messages?
2. Performance: Read replicas, indexing strategy, query optimization?
3. Consistency: ACID vs eventual consistency for real-time features?

Please provide specific recommendations with trade-offs for a mid-scale application.
=============================

[You get detailed help from external AI, paste back for implementation]
```

## 🛠️ Development

### Learning Integration
OOS includes a self-referential learning system:

```bash
# Before developing, learn from past lessons
./bin/development_guide.sh

# Create Archon project for task management
./bin/create_archon_project.sh
```

This prevents repeating architecture mistakes, testing issues, and UX decisions.

### Pre-commit Hooks
```bash
# Automatic setup with oos-doctor
./bin/oos-doctor setup

# Manual setup
cp .githooks/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
```

### Portable POSIX Shell
OOS enforces portable POSIX shell scripting across macOS and Linux:

```bash
# Setup your environment (installs GNU tools on macOS)
make posix-bootstrap

# Check your POSIX environment
./bin/oos-doctor-posix-check

# Lint and format shell scripts
make lint-sh format-sh
```

- **Cross-platform compatibility** between macOS (BSD) and Linux (GNU)
- **Automatic tool installation** for GNU coreutils on macOS
- **ShellCheck + shfmt integration** for code quality
- **Portable helper functions** in `scripts/posix/portable.sh`

See [docs/PORTABLE_SHELL.md](docs/PORTABLE_SHELL.md) for details.

## 📈 Performance Metrics

- **Token Reduction**: 24.8% average, up to 60% with aggressive optimization
- **Response Time**: <1s for estimation, <5s for optimization
- **Context Accuracy**: 85%+ confidence scoring for input analysis
- **Test Coverage**: 100% component coverage with integration tests
- **Memory Efficiency**: Filesystem offloading prevents memory bloat

## 🤝 Contributing

1. **Read the philosophy**: [docs/TESTING_PHILOSOPHY.md](docs/TESTING_PHILOSOPHY.md)
2. **Understand the architecture**: [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md)
3. **Use the learning system**: `./bin/development_guide.sh`
4. **Follow the patterns**: Check existing implementations before adding new features
5. **Test thoroughly**: All changes must include tests and pass the full suite

## 🎊 Status

**✅ Context Engineering Implementation: COMPLETE**

The system is production-ready and provides:
- 10 slash commands for Claude Code integration
- Automatic context optimization with 40-60% token reduction
- Meta-clarification system for external AI assistance
- Comprehensive testing and validation
- Self-documenting workflows with git integration

Ready for immediate deployment and use! 🚀

---

*OOS truly "saves you from yourself" by making every interaction with Claude Code smarter, more efficient, and automatically optimized.* 💡

## 📝 Legacy Features

**Secure Development Environment Setup** (Original OOS functionality)

```bash
# Set up secure development environment
git clone https://github.com/Khamel83/oos.git
cd oos
./scripts/bootstrap_enhanced.sh

# Use in any project (preserves existing files!)
./scripts/bootstrap_enhanced.sh --verbose my-project /path/to/project
# → Automatic API key protection installed
# → Safe file creation (never overwrites without --force)
# → Complete development environment ready
```

**Key Features:**
- 🔒 **API Key Protection**: Pre-commit hooks prevent accidental key exposure
- 🛡️ **File Safety**: Never overwrites existing files without explicit consent
- ⚡ **One Command Setup**: Complete development environment in minutes
- 🤖 **AI-Ready**: Claude, Gemini, and Qwen integration included

---

## 🤖 Claude Code Integration

**Just say "integrate OOS" in any Claude Code project!**

Claude Code will automatically:
1. **Set up OOS development tools** (oos-dev-tools.js)
2. **Add package.json scripts** for development commands
3. **Configure token optimization** in your API routes
4. **Provide you with OOS development commands**

**Example commands after setup:**
- `npm run oos:analyze <file>` - Code complexity analysis
- `npm run oos:optimize` - Performance optimization tips
- `npm run oos:commit` - Smart commit messages

**No manual setup required!** 🚀

*See [SETUP.md](SETUP.md) for the simple 3-step process.*

---

## 📖 Full Documentation

**Quick Navigation:**
- [For Users](#for-users) | [For Contributors](#for-contributors)
- [Security Features](#-security--safety-features) | [LLM Gateway](#-llm-gateway-bifrost--zai-overflow)

### For Users

*   **🚀 Getting Started**
    *   [Installation Guide](docs/INSTALLATION.md)
    *   [Usage Guide](docs/USAGE_GUIDE.md)
    *   [1Password Setup](docs/1PASSWORD_SETUP.md)
*   **🔒 Security & Safety**
    *   [File Safety Features](docs/BOOTSTRAP_FILE_SAFETY.md) - How OOS protects your existing files
    *   [API Key Protection](bin/prevent_api_key_commits.sh) - Built-in security against credential exposure
*   **🔧 Advanced Topics**
    *   [Advanced Installation](docs/ADVANCED_INSTALLATION.md)
    *   [Advanced Usage](docs/ADVANCED_USAGE_GUIDE.md)
    *   [Troubleshooting](docs/TROUBLESHOOTING.md)

### For Contributors

*   **Core Concepts**
    *   [Contributing Guide](CONTRIBUTING.md)
    *   [System Overview](docs/SYSTEM_OVERVIEW.md)
    *   [Development Philosophy](docs/DEVELOPMENT_PHILOSOPHY.md)
    *   [Testing Philosophy](docs/TESTING_PHILOSOPHY.md)
*   **🛠️ Development Guides**
    *   [AI Collaboration Guide](docs/AI_COLLABORATION_GUIDE.md)
    *   [API Reference](docs/API_REFERENCE.md)
    *   [Archon Integration](docs/ARCHON_INTEGRATION.md)
    *   [Operations Guide](docs/OPERATIONS.md)
*   **📋 Launch & Quality**
    *   [Launch Readiness Checklist](docs/BOOTSTRAP_LAUNCH_READINESS.md) - Product launch methodology
    *   [Comprehensive Testing](tests/test_bootstrap_safe_files.sh) - Complete test suite
*   **Agent-Specific Guidelines**
    *   [Agent Guidelines](.agents/agents.md)
    *   [Claude](docs/CLAUDE.md)
    *   [Gemini](docs/GEMINI.md)
    *   [Qwen](docs/qwen.md)

---

## 🔒 Security & Safety Features

**OOS is built with security and user data protection as core principles:**

### Bulletproof API Key Protection
- **Pre-commit hooks** automatically scan every commit for API keys
- **Blocks dangerous patterns**: OpenAI, GitHub, Google, AWS, and generic long keys
- **Allows safe placeholders**: `your_api_key_here`, `sk-test-example`, etc.
- **Works everywhere**: OOS projects and all created projects get automatic protection

### Safe File Operations
- **Never overwrites existing files** without explicit `--force` flag
- **Clear user warnings** with guidance on how to proceed
- **Automatic backups** when overwriting with `--force`
- **Edge case handling**: symlinks, directories, permission errors

### Monitoring & Validation
- **Self-contained logging** with sanitized sensitive data
- **Comprehensive testing** with 10+ scenarios covering all edge cases
- **Product launch methodology** ensuring reliability and user safety

### Usage Examples

```bash
# Safe by default - preserves existing files
./scripts/bootstrap_enhanced.sh my-project

# Output: [WARN] Skipping existing file: docs/CLAUDE.md
#         [WARN]   → Use --force to overwrite (automatic backup will be created)

# Explicit overwrite with backup
./scripts/bootstrap_enhanced.sh --force my-project

# API key protection in action
git commit -m "add config"
# Output: 🚨 COMMIT BLOCKED - API keys found in staged files!
#         File: config.js:10
#         Key: sk-proj-abc123... [REDACTED]
```

---

## 🌐 LLM Gateway (Bifrost) + Z.AI Overflow

**Seamlessly switch between Anthropic Pro and cost-effective Z.AI GLM-4.5 while preserving your existing Claude Code + MCP setup.**

**Quick Navigation:**
- [How to Use (Day-to-Day)](#how-to-use-day-to-day)
- [One-Time Setup](#one-time-setup)
- [MCP (Archon + Others)](#mcp-archon--others)
- [Gateway Management](#gateway-management)
- [Keys & Safety](#keys--safety)
- [Z.AI Integration Status](#zai-integration-status)

### How to Use (Day-to-Day)

**🎯 Best UX (Recommended):** Start every session through Bifrost on Anthropic → switch to Z.AI in-session when you hit Pro limits.

```bash
# 1. Start gateway once (on your OCI VM)
bash scripts/llm_gateway_up.sh

# 2. Start Claude Code on Anthropic (via gateway)
source scripts/cc-launchers.sh
cc-sona

# 3. Work as usual. When you hit limits, don't restart—just:
/model zai/glm-4.5

# You can always switch back: /model anthropic/claude-4-sonnet
# Model switching mid-session is fully supported
```

**Alternative:** Start direct Pro, switch to gateway when needed:
```bash
cc-pro                    # Start direct Pro
# When you hit limits, exit and run:
cc-sona                   # Switch to gateway mode
claude -c                 # Resume your last conversation
# Or resume specific session: claude -r "<session-id>"
```

### One-Time Setup

```bash
# 1. Start the gateway
bash scripts/llm_gateway_up.sh

# 2. Open Bifrost UI → add providers
# Open http://127.0.0.1:8080
# Go to Providers → Add:
#   • Anthropic: paste your console API key
#   • Z.AI: paste your GLM Coding Plan API key

# 3. Load launcher functions (add to your shell profile for persistence)
source scripts/cc-launchers.sh
```

### Usage Options

**Direct Anthropic Pro (unchanged):**
```bash
cc-pro              # Use normal Claude Code with Pro/Max
# Inside Claude Code: /login once, then use /model claude-4-sonnet
```

**Via Gateway (switchable models):**
```bash
cc-sona             # Start on Anthropic Sonnet via gateway
# Inside Claude Code: /status shows base URL .../anthropic
# Switch models: /model zai/glm-4.5
# Switch back: /model anthropic/claude-4-sonnet

# Or launch directly on Z.AI
cc-zai              # Start directly on Z.AI GLM-4.5
```

### MCP (Archon + Others)

**Once you've added your MCP servers, they work the same in both modes (direct or gateway):**

```bash
# Add once, reuse everywhere
claude mcp add-json archon '{"type":"sse","url":"http://your-archon-server:8051/mcp"}'
claude mcp get archon

# Works in both cc-pro and cc-sona/cc-zai sessions
# Claude Code supports MCP; add once, reuse everywhere
```

### Gateway Management

```bash
# Start gateway
bash scripts/llm_gateway_up.sh

# Stop gateway
bash scripts/llm_gateway_down.sh

# Check if running
docker ps | grep oos-bifrost
```

### OCI Security Notes

- **Default**: Gateway binds to `127.0.0.1:8080` (localhost only)
- **For remote access**: SSH tunneling recommended
- **If you must expose**: Add NSG ingress rule for TCP/8080 and open host firewall

### Keys & Safety

**Keep keys out of git.** Put API keys into Bifrost UI or a local `.env` that's already ignored by OOS:

```bash
# LLM Gateway (optional; store keys in Bifrost UI or local .env)
ZAI_API_KEY=your_zai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
# Optional future providers:
DEEPSEEK_API_KEY=
KIMI_API_KEY=
```

**Security:** Bifrost binds to `127.0.0.1` (localhost-only). If you must expose it on OCI, open an NSG ingress + host firewall, but localhost is safer.

### Archon Integration Status

**✅ INTEGRATED BY DEFAULT**

Archon MCP is now automatically integrated with every OOS installation:

- **Automatic Setup:** Bootstrap script adds Archon configuration to all new projects
- **GitHub Integration:** Auto-detects repository URLs and links them to Archon projects
- **Project Management:** Complete task tracking and documentation system
- **MCP Integration:** Seamless Claude Code integration with your Archon server

**What You Get:**
- ✅ ARCHON_PROJECT_ID and ARCHON_URL automatically added to .env
- ✅ `bin/create_archon_project.sh` helper script created
- ✅ Archon MCP server registered with Claude Code
- ✅ GitHub repository auto-detection and linking

**Configuration:**
Update the ARCHON_URL in your .env file to point to your Archon server instance.

**Usage:**
```bash
# After OOS bootstrap, create your Archon project
./bin/create_archon_project.sh "My Project" "Project description"
# Follow the generated instructions to complete setup in Claude Code
```

---

### Other Documents

*   [Security Policy](SECURITY.md)
*   [Code Manifest](CODE_MANIFEST.md)
*   [License](LICENSE)