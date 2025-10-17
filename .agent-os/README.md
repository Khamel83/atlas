# Agent OS Integration Guide

## Overview

Agent OS is a structured AI-assisted development methodology that provides workflows for product planning, feature specification, and task execution. This directory contains all Agent OS components for this project.

## For AI Agents/LLMs: How to Use Agent OS

When working in a project with Agent OS, automatically use these workflows based on user requests:

### Automatic Workflow Triggers

**Product Planning** - When user asks to plan, initialize, or set up a new product:
- USE: `@.agent-os/instructions/plan-product.md`
- CREATES: Product documentation in `.agent-os/product/`

**Feature Specification** - When user asks to plan, spec, or design a new feature:
- USE: `@.agent-os/instructions/create-spec.md`
- CREATES: Feature specs in `.agent-os/specs/YYYY-MM-DD-feature-name/`

**Task Execution** - When user asks to implement, build, or execute tasks:
- USE: `@.agent-os/instructions/execute-tasks.md`
- FOLLOWS: Tasks defined in spec files

**Project Analysis** - When user asks to analyze existing code or add Agent OS to existing project:
- USE: `@.agent-os/instructions/analyze-product.md`
- ANALYZES: Current codebase and creates Agent OS structure

### Agent OS Directory Structure

```
.agent-os/
├── README.md                    # This file - integration guide
├── product/                     # Product-level documentation
│   ├── mission.md              # Product vision and goals
│   ├── mission-lite.md         # Condensed mission for AI context
│   ├── tech-stack.md           # Technical architecture choices
│   ├── roadmap.md              # Development phases and features
│   └── decisions.md            # Decision log and rationale
├── specs/                       # Feature specifications
│   └── YYYY-MM-DD-feature-name/
│       ├── spec.md             # Feature requirements
│       ├── spec-lite.md        # Condensed spec for AI context
│       ├── tasks.md            # Implementation task breakdown
│       └── sub-specs/          # Technical specifications
└── standards/                   # Development standards (optional)
    ├── tech-stack.md           # Technology preferences
    ├── code-style.md           # Code formatting rules
    └── best-practices.md       # Development guidelines
```

### Integration Behavior

**Proactive Usage**: Use Agent OS workflows automatically when they apply - don't wait for explicit user requests.

**Context Loading**: Always check for and load relevant Agent OS files:
- `mission-lite.md` for product context
- `spec-lite.md` for current feature context
- `roadmap.md` for development priorities

**File Creation**: Follow Agent OS file naming and structure conventions exactly as specified in the instruction files.

**Cross-References**: Always reference Agent OS files using the `@.agent-os/path/file.md` syntax.

## For Humans: Using Agent OS

### Available Commands

Agent OS provides structured workflows through these commands:

- `/plan-product` - Initialize Agent OS and create product documentation
- `/create-spec` - Plan and specify a new feature
- `/execute-tasks` - Implement tasks from a specification
- `/analyze-product` - Add Agent OS to existing project

### Getting Started

1. **New Project**: Use `/plan-product` to set up Agent OS structure
2. **Existing Project**: Use `/analyze-product` to add Agent OS to existing code
3. **New Feature**: Use `/create-spec` to plan features
4. **Implementation**: Use `/execute-tasks` to build features

### Philosophy

Agent OS treats development as a series of autonomous agents with clear contracts:
- **Product Agent**: Manages overall vision and roadmap
- **Spec Agent**: Defines feature requirements and tasks
- **Execution Agent**: Implements features following specifications

## Integration Requirements

### Global Agent OS Setup (Recommended)

For universal Agent OS access across all projects and machines:

1. **Create Global Agent OS Directory:**
   ```bash
   mkdir -p ~/.agent-os
   cp -r /path/to/any/project/.agent-os/* ~/.agent-os/
   ```

2. **Update Global Claude Configuration:**
   ```bash
   # Edit ~/.claude/CLAUDE.md to include:
   ## Automatic Agent OS Integration
   **For any project with a `/.agent-os/` directory:**
   1. **Auto-discover**: Always check for `/.agent-os/README.md` at project start
   2. **Auto-use workflows**: Apply Agent OS workflows when user requests planning, specs, or implementation
   3. **Proactive behavior**: Use Agent OS without waiting for explicit commands when appropriate
   ```

3. **Setup New Machine:**
   ```bash
   # Copy Agent OS to new machine
   scp -r ~/.agent-os new-machine:~/

   # Or clone from git repo containing Agent OS
   git clone your-agent-os-repo ~/.agent-os
   ```

### Project-Specific Integration

**Option A: Copy from Global** (Recommended)
```bash
cp -r ~/.agent-os .agent-os
# Tell AI: "Read the /.agent-os/README.md for instructions and add Agent OS integration to your project README"
```

**Option B: Fresh Setup**
1. Copy `.agent-os/` directory from any existing Agent OS project
2. Tell your AI agent: "Read the `/.agent-os/README.md` for instructions and add Agent OS integration to your project README"
3. The AI will automatically set up Agent OS integration

### For Existing Projects

Run `/analyze-product` or tell your AI agent to analyze the project and install Agent OS.

### New Machine Setup Checklist

When setting up Agent OS on a new development machine:

1. **Copy Global Agent OS:**
   ```bash
   # From existing machine
   scp -r ~/.agent-os new-machine:~/

   # Or from backup/git
   git clone your-agent-os-backup ~/.agent-os
   ```

2. **Setup Global Claude Config:**
   ```bash
   # Create ~/.claude/CLAUDE.md with Agent OS integration
   # (See example in global setup section above)
   ```

3. **Verify Setup:**
   ```bash
   ls ~/.agent-os/           # Should see: README.md, instructions/, standards/
   ls ~/.claude/CLAUDE.md    # Should exist with Agent OS config
   ```

4. **Test in Any Project:**
   - Copy `~/.agent-os` to any project as `.agent-os`
   - Tell LLM: "Read the /.agent-os/README.md for instructions"
   - Agent OS should work immediately

## Standards and Customization

### Global Standards
If global Agent OS standards exist at `~/.agent-os/standards/`, they provide defaults for:
- Technology stack preferences
- Code style guidelines
- Development best practices

### Project-Specific Standards
The `standards/` directory in this project overrides global standards:
- Customize `tech-stack.md` for project-specific technology choices
- Modify `code-style.md` for project-specific formatting rules
- Update `best-practices.md` for project-specific development patterns

## Quick Start Summary

### For New Machine Setup:
1. `scp -r ~/.agent-os new-machine:~/` (copy global Agent OS)
2. Setup `~/.claude/CLAUDE.md` with Agent OS integration
3. Ready to use in any project!

### For New Project:
1. `cp -r ~/.agent-os .agent-os` (copy to project)
2. Tell LLM: "Read /.agent-os/README.md and setup Agent OS integration"
3. Start developing with `/plan-product`, `/create-spec`, `/execute-tasks`

### For Existing Project:
1. `cp -r ~/.agent-os .agent-os` (copy to project)
2. Tell LLM: "Use /analyze-product to add Agent OS to existing code"

## Troubleshooting

**Missing workflows**: Ensure instruction files exist in `~/.agent-os/instructions/`
**File not found errors**: Use absolute paths with `@.agent-os/` prefix
**Integration issues**: Check that AI agent has read this README.md
**Global setup issues**: Verify `~/.agent-os/` and `~/.claude/CLAUDE.md` exist

---

*Agent OS provides structured, AI-assisted development workflows. Learn more at [buildermethods.com/agent-os](https://buildermethods.com/agent-os)*