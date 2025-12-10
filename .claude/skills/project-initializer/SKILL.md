---
name: project-initializer
description: "Bootstrap new ONE_SHOT project skeletons with proper structure. Creates directory layout, required files, and initial git commit. Use when user says 'initialize', 'new project', 'scaffold', or 'set this up'."
allowed-tools: Bash, Read, Write, Glob
---

# Project Initializer

You are an expert at bootstrapping new ONE_SHOT projects with proper structure.

## When To Use

- New repo or empty directory
- User says "Initialize a new ONE_SHOT project"
- User says "Set this up with ONE_SHOT", "Scaffold the project"
- TRIAGE state = build_new + new_project

## Inputs Required

From Core Questions Q0-Q13:
- Mode: Micro / Tiny / Normal / Heavy
- Project type: Q6 (A-G)
- Naming: Q13
- Storage & scale: Q8-Q9
- Interface shape: Q11

## Outputs

- Directory skeleton:
  - `LLM-OVERVIEW.md`
  - `PRD.md` (initial version)
  - `README.md`
  - `TODO.md`
  - `scripts/` with setup.sh, start.sh, stop.sh, status.sh
  - Language-specific files (pyproject.toml or package.json)
- Git initialized with initial commit

## Workflow

### 1. Environment Detection

Detect language/runtime based on project type + user preference:
- CLI default: Python
- Web default: FastAPI + Python
- Static site: HTML/CSS/JS

### 2. Create Base Directories

```bash
mkdir -p src/ tests/ scripts/ docs/
```

### 3. Write Baseline Files

**TODO.md:**
```markdown
# TODO - [PROJECT_NAME]

> Project tasks organized by status. Updated: [DATE]

### Backlog
- [ ] Phase 1: Core Implementation
- [ ] Phase 2: Tests
- [ ] Phase 3: Scripts
- [ ] Phase 4: Deployment

### In Progress

### Done ✓
- [x] Phase 0: Repo & Skeleton [DATE]
```

**README.md:**
```markdown
# [Project Name] - [One-line description]

**Status**: In Development
**Current Tier**: [Storage/Deployment tier]
**Upgrade Trigger**: [When to upgrade]

## What This Does
[Problem → Solution in 2-3 sentences]

## Quick Start
[≤5 commands to get running]
```

**LLM-OVERVIEW.md:**
```markdown
# LLM-OVERVIEW: [Project Name]

> Complete context for any LLM to understand this project.
> **Last Updated**: [DATE]
> **ONE_SHOT Version**: 3.1

## 1. WHAT IS THIS PROJECT?
### One-Line Description
[From Q1]

### The Problem It Solves
[From Q2]

### Current State
- **Status**: In Development
- **Version**: 0.1.0

## 2. ARCHITECTURE OVERVIEW
### Tech Stack
[From Q6, Q10]

## 3. KEY FILES
- `src/main.py` - Entry point
- `scripts/` - Automation scripts
```

### 4. Language-Specific Init

**Python:**
```bash
# Create pyproject.toml or requirements.txt
touch requirements.txt
echo "# [Project dependencies]" > requirements.txt
```

**Node:**
```bash
npm init -y
```

### 5. Git Initialization

```bash
git init
# Create .gitignore
cat > .gitignore << 'EOF'
.env
.env.local
__pycache__/
*.pyc
.venv/
venv/
node_modules/
.DS_Store
*.log
EOF

git add .
git commit -m "chore(init): bootstrap ONE_SHOT project skeleton"
```

### 6. Scripts Setup

Create standard scripts:

**scripts/setup.sh:**
```bash
#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**scripts/start.sh:**
```bash
#!/bin/bash
source venv/bin/activate
python src/main.py
```

**scripts/stop.sh:**
```bash
#!/bin/bash
pkill -f "python src/main.py"
```

**scripts/status.sh:**
```bash
#!/bin/bash
pgrep -f "python src/main.py" && echo "Running" || echo "Stopped"
```

## Anti-Patterns

- Overwriting existing non-empty `src/` without explicit instruction
- Installing heavy deps (Postgres, Redis) unless demanded by PRD
- Creating Kubernetes manifests for Normal/Tiny projects
- Skipping .gitignore for secrets

## Keywords

initialize, new project, scaffold, bootstrap, setup, create project, start fresh
