# Using Context Engineering in Claude Code - Simple Guide

*For users who work entirely within Claude Code interface*

## 🤔 The Problem

You've got all these great context engineering tools, but you're not running terminal commands - you're working directly in Claude Code. How do you actually use this stuff?

## ✅ The Solution

The context engineering system can be triggered and used directly through Claude Code by simply **asking for it** in your messages. Here's how:

## 🎯 How to Use Each Feature

### 1. Meta-Clarification (Bidirectional AI Assistance)

**When**: Claude asks you clarification questions and you want to give much better responses

**The Problem**: You give Claude 20 words, Claude gives unclear responses. ChatGPT gives 500 structured words, Claude gives amazing responses.

**What to say**:
```
"Generate a meta-clarification prompt for these questions so I can get help crafting a better response"
```

**What happens**:
- Claude generates a prompt specifically designed to help you craft detailed responses
- You copy/paste it to ChatGPT or another Claude instance
- You get a structured 400-600 word response to paste back to Claude Code
- Claude gets the detailed context it needs for excellent assistance

**Example**:
```
You: "optimize the authentication system"
Claude: "I need clarification on OAuth vs JWT, user scale, security requirements..."
You: "Generate a meta-clarification prompt for these questions"
Claude: [Generates prompt asking external AI to help you craft detailed responses]
You: [Paste to ChatGPT, get structured 500-word response]
You: [Paste ChatGPT's detailed response back to Claude]
Claude: [Provides excellent implementation with full context]
```

### 2. Token Optimization

**When**: You're working with large codebases or complex contexts

**What to say**:
```
"Optimize the context for token efficiency before we continue"
```

**What happens**:
- Claude automatically compresses and optimizes the context
- Offloads less important information to files
- Keeps the most relevant information active
- Shows you the token savings

### 3. Smart Documentation

**When**: You want to document your work or check code quality

**What to say**:
```
"Run a documentation check on these files"
"Generate smart commit message for these changes"
"Check code consistency across the project"
```

**What happens**:
- Claude analyzes files for missing documentation
- Suggests improvements and fixes
- Generates intelligent commit messages
- Identifies consistency issues

### 4. Clarification Workflow

**When**: You have a vague or complex request

**What to say**:
```
"Use the clarification workflow to help me refine this request"
```

**What happens**:
- Claude analyzes your input for ambiguities
- Generates targeted clarification questions
- Helps you create a detailed plan
- Guides you through structured problem-solving

## 🚀 Practical Examples

### Example 1: Starting a New Feature
```
You: "I want to add user authentication"

Claude: "I'll use the clarification workflow to help refine this request..."
[Asks targeted questions about auth type, security requirements, etc.]

You: "Generate a meta-clarification prompt for these questions"

Claude: [Provides structured prompt for external AI assistance]

You: [Gets help from ChatGPT, returns with detailed answers]

Claude: "Perfect! Now I'll create an optimized implementation plan..."
```

### Example 2: Working with Large Codebase
```
You: "Analyze this entire codebase for performance issues"

Claude: "This is a large context. Let me optimize for token efficiency first..."
[Automatically compresses context, offloads less critical files]

Claude: "I've reduced context from 8000 to 3000 tokens. Here's my analysis..."
```

### Example 3: Code Quality Check
```
You: "Check if my code needs documentation or has consistency issues"

Claude: "Running documentation and consistency checks..."
[Analyzes code, finds missing docstrings and naming issues]

Claude: "Found 3 functions needing docs and 2 naming convention issues. Should I fix them?"
```

## 💡 Trigger Phrases

Just use these phrases in your Claude Code conversations:

**For Meta-Clarification** (Bidirectional AI Help):
- "Generate meta-clarification prompt"
- "Help me craft a better response to these questions"
- "Create a prompt to help me give you more detailed answers"

**For Token Optimization**:
- "Optimize context for tokens"
- "Reduce token usage"
- "Compress the context"

**For Documentation**:
- "Check documentation completeness"
- "Generate commit message"
- "Review code consistency"

**For Clarification Workflow**:
- "Use clarification workflow"
- "Help me refine this request"
- "Ask clarifying questions"

## 🔄 How It Actually Works Behind the Scenes

1. **Claude recognizes your request** for context engineering features
2. **Imports the relevant modules** (clarification_workflow.py, token_optimization.py, etc.)
3. **Runs the appropriate functions** based on what you asked for
4. **Shows you the results** in a user-friendly format
5. **Continues with optimized context** for better responses

## 🎁 The Magic

The beauty is you don't need to know Python, run commands, or understand the technical details. Just **ask Claude to use the context engineering features** and it handles everything automatically.

## 🔥 Pro Tips

1. **Start complex projects** with: "Use the clarification workflow to help me plan this"

2. **When context gets large**, say: "Optimize context before continuing"

3. **For unclear questions**, use: "Generate meta-clarification prompt so I can get help"

4. **Before committing code**, ask: "Check documentation and generate a smart commit message"

5. **Trust the system** - it's designed to make your Claude Code experience much more efficient

## 📝 Example Conversation Flow

```
You: I want to build a real-time chat application

Claude: I'll use the clarification workflow to help plan this properly.

[Analyzes input, finds ambiguities]

Claude: I need clarification on a few points to create the best plan:
1. What's your target platform? (Web, mobile, desktop)
2. How many concurrent users are you planning for?
3. What authentication method do you prefer?

You: Generate a meta-clarification prompt for these questions

Claude: Here's a structured prompt you can use with another AI:

===COPY THIS TO ANOTHER AI===
I'm planning a real-time chat application and need help answering these technical questions:

1. Platform choice: Web (React/Vue), Mobile (React Native/Flutter), Desktop (Electron/Tauri)?
   Consider: development time, performance, deployment complexity

2. User scale: Small (100s), Medium (1000s), Large (10000s+)?
   Consider: infrastructure costs, scaling complexity

3. Authentication: OAuth (Google/GitHub), Email/Password, Magic Links?
   Consider: user experience, security, implementation time

Please provide specific recommendations with brief reasoning for a solo developer.
===========================

[You get help from ChatGPT, return with detailed answers]

You: [Pastes the AI response]

Claude: Perfect! Based on those clarifications, I'll optimize the context and create a detailed implementation plan...

[Automatically optimizes token usage and creates comprehensive plan]
```

## 🎯 Bottom Line

**You don't run anything. You just ask for it.**

The context engineering system is now part of Claude's intelligence when working in your OOS codebase. Just mention what you want and Claude handles the rest automatically.

No terminals. No commands. Just better, smarter conversations with optimized token usage and structured workflows.

🎉 **It's that simple!**

## 🐚 Shell Scripting & POSIX Constraints

When generating shell scripts in this codebase, Claude automatically applies portable POSIX constraints:

**Auto-Applied Rules:**
- Uses `#!/usr/bin/env sh` (portable shebang)
- Avoids bash/zsh-specific features
- Assumes GNU tools on macOS via Homebrew setup
- Uses portable helper functions from `scripts/posix/portable.sh`
- Generates scripts that pass `shellcheck -s sh` and `shfmt -ln posix`

**Setup your environment:**
```bash
# Bootstrap POSIX tools (run once)
make posix-bootstrap
```

**Generated scripts will work on:**
- macOS (with GNU coreutils via Homebrew)
- Linux (Ubuntu/Debian/Raspberry Pi)
- BSD systems (with appropriate GNU tool packages)

See [docs/PORTABLE_SHELL.md](docs/PORTABLE_SHELL.md) for details on portable shell scripting in OOS.