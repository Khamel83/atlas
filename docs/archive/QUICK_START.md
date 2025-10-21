# OOS Context Engineering - Quick Start Guide

## 🚀 What You Get

OOS transforms Claude Code into an intelligent middleware that:
- **Saves you from yourself** with automated context optimization
- **Meta-clarification** - get help from other AIs when Claude asks confusing questions
- **Smart slash commands** - trigger powerful workflows with simple commands
- **Automatic token optimization** - reduce context usage by 40-60%
- **Rambling support** - dump messy thoughts and get organized results

## ⚡ 30-Second Setup

### Step 1: Install as MCP Server
Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "oos-context": {
      "command": "python3",
      "args": ["/home/ubuntu/dev/oos/mcp_server.py"],
      "cwd": "/home/ubuntu/dev/oos"
    }
  }
}
```

### Step 2: Restart Claude Code
The slash commands are now available!

## 🎯 How to Use (User Stories)

### Story 1: "I have a messy idea and need help"
```
You: /brain-dump I want to add authentication but not sure OAuth vs JWT vs sessions, also need database migrations and maybe Redis for caching, also the frontend needs updating
```
**What happens**:
- Auto-analyzes your rambling input
- Optimizes context for token efficiency
- Asks clarifying questions with multiple choice options
- Generates a structured plan with priorities

### Story 2: "Claude's questions are confusing"
```
Claude: "I need clarification on your authentication requirements..."
You: /meta-ai
```
**What happens**:
- Generates a structured prompt optimized for external AI
- You copy/paste to ChatGPT or another Claude instance
- Get better, more detailed answers
- Paste back for optimized implementation

### Story 3: "I want everything auto-optimized"
```
You: /help-me optimize the database performance
```
**What happens**:
- Automatically optimizes context before processing
- Analyzes your codebase for bottlenecks
- Provides specific recommendations
- All within optimized token budget

### Story 4: "I need better documentation"
```
You: /smart-commit
```
**What happens**:
- Analyzes your git changes
- Generates intelligent commit message with context
- Includes proper attribution and change summary

## 📋 Available Slash Commands

### Core Workflow Commands
- `/help-me [request]` - Smart processing with auto-optimization
- `/brain-dump [rambling]` - Process messy input into clear structure
- `/clarify [vague request]` - Get clarification questions
- `/workflow [complex task]` - Start structured workflow

### AI Assistance Commands
- `/meta-ai` - Generate prompt for external AI help
- `/optimize` - Optimize context for token efficiency

### Code Quality Commands
- `/smart-commit` - Generate intelligent commit message
- `/doc-check` - Check documentation completeness
- `/auto-fix` - Fix code issues automatically

### System Commands
- `/context-stats` - Show token usage and optimization stats

## 🎁 The Magic Behind the Scenes

When you use any command, OOS automatically:

1. **Analyzes your input** for clarity and intent
2. **Optimizes token usage** through compression and filesystem offloading
3. **Applies context engineering** using Write/Select/Compress/Isolate principles
4. **Enhances responses** with structured workflows and AI assistance
5. **Tracks everything** for consistency and learning

## 💡 Pro Tips

### Start Complex Projects
```
/workflow build a real-time chat app with WebSocket support
```

### When Context Gets Large
```
/optimize
```
*Automatically reduces token usage while preserving important information*

### For Unclear Responses
```
/meta-ai
```
*Get a structured prompt to use with ChatGPT/Claude for better answers*

### Before Committing Code
```
/doc-check
/smart-commit
```

### When You're Rambling
```
/brain-dump I'm thinking about microservices but also monolith might be easier but then scaling becomes an issue and Docker is complex but Kubernetes might be overkill...
```

## 🔥 Automatic Features

### Always-On Optimization
- Every interaction is automatically token-optimized
- Context is compressed using multiple strategies
- Less important information is offloaded to files
- You get better responses with lower token costs

### Smart Clarification
- Detects when your input is ambiguous (confidence scoring)
- Asks targeted questions instead of generic ones
- Supports meta-clarification for external AI assistance
- Remembers context across clarification sessions

### Self-Documentation
- Automatically generates commit messages
- Tracks code changes and suggests documentation updates
- Maintains consistency across your codebase
- Integrates with Git for seamless workflow

## 🎯 Real Example Workflow

```
You: /brain-dump I need user auth but not sure what approach

OOS: 🧠 Processing your request with context engineering...
     📊 Analyzing input...
        Intent detected: implementation
        Confidence: 85%
        Context tokens: 1,240

     ✅ Your request is clear! Here's how I can help:
     🏗️ I'll help you implement this with:
        • Architecture planning
        • Step-by-step implementation
        • Testing and validation

     🚀 Ready to proceed! What would you like me to focus on first?

You: Actually the questions are complex, can you help me get better answers?

OOS: /meta-ai

     Here's a structured prompt for external AI assistance:

     ===COPY THIS TO ANOTHER AI===
     I'm implementing user authentication and need help choosing the right approach.

     Context: Building a web application that needs secure user management

     Questions:
     1. Authentication method: OAuth2 (Google/GitHub), JWT tokens, or session-based?
        Consider: security, user experience, implementation complexity

     2. Storage: Database sessions, Redis cache, or stateless tokens?
        Consider: scalability, performance, infrastructure requirements

     Please provide specific recommendations with trade-offs for a mid-scale application.
     ===========================

[You get help from ChatGPT, return with better answers]

You: [Pastes detailed AI response about OAuth2 + JWT recommendations]

OOS: Perfect! Based on those clarifications, I'll optimize the context and create a detailed implementation plan...

     [Automatically optimizes token usage and creates comprehensive plan]

     📋 Implementation Plan:
     1. Set up OAuth2 provider integration (Google)
     2. Implement JWT token handling with refresh logic
     3. Create user session management
     4. Add security middleware and validation
     5. Set up testing framework for auth flows

     Let's start with OAuth2 provider setup. Should I begin implementation?
```

## 🎊 Bottom Line

**You don't think about token optimization, context management, or clarification workflows.**

Just use the slash commands and OOS handles everything automatically:
- Smarter responses through context engineering
- Lower token costs through automatic optimization
- Better clarification through AI assistance
- Improved code quality through automated checks

**It's that simple!** 🎉

Your Claude Code experience just got significantly more powerful and efficient.