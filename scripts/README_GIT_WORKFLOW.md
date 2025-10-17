# Atlas Git-First Development Workflow

## Overview

This workflow ensures **NO MORE than 20-30 minutes** between GitHub commits to prevent work loss and maintain continuous backup.

## Core Principle

**NEVER work more than 30 minutes without pushing to GitHub**

## Quick Start

```bash
# 1. Safety check before starting work
python scripts/git_safety.py

# 2. Start timer for commit reminders (in separate terminal)
python scripts/git_workflow.py timer

# 3. Execute individual tasks with auto-commit
python scripts/execute_task.py 011

# 4. Manual commit when needed
git add . && git commit -m "WIP: describe work" && git push
```

## Scripts

### `git_safety.py`
**Run before starting any work**
- Checks for uncommitted changes
- Verifies remote connectivity
- Warns if last commit was >30 minutes ago

```bash
python scripts/git_safety.py
```

### `git_workflow.py`
**Auto-commit and timer system**
- Auto-commits every 20 minutes during active work
- Timer mode reminds you to commit

```bash
# Auto-commit now
python scripts/git_workflow.py

# Start 20-minute reminder timer
python scripts/git_workflow.py timer
```

### `execute_task.py`
**Execute Atlas tasks with auto-commit**
- Implements specific Atlas tasks
- Auto-commits during long tasks
- Commits completion when done

```bash
# Execute specific task
python scripts/execute_task.py 011

# Execute with description
python scripts/execute_task.py 023 "Implement Wallabag-style article extraction"
```

## Workflow Rules

### 🔴 MANDATORY
1. **Safety check before work**: `python scripts/git_safety.py`
2. **Commit every 15-20 minutes maximum**
3. **Push to GitHub immediately after commit**
4. **Never lose more than 20 minutes of work**

### 🟡 RECOMMENDED
1. **Use timer**: `python scripts/git_workflow.py timer`
2. **Descriptive commit messages**
3. **Commit at logical breakpoints**
4. **Test before committing**

### 🟢 BEST PRACTICES
1. **Commit at task boundaries**
2. **Include validation results in commits**
3. **Update documentation with code changes**
4. **Use conventional commit format**

## Commit Message Format

```
Type: Brief description

- Bullet point for major change
- Another bullet for important detail
- Validation status or test results

🤖 Generated with Claude Code
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `WIP:` Work in progress
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring

## Emergency Procedures

### If Git Push Fails
```bash
# 1. Check what's wrong
git status
git log --oneline -5

# 2. Try to resolve
git pull --rebase origin main

# 3. If still failing, save work locally
git stash
git fetch origin
git reset --hard origin/main
git stash pop

# 4. Commit and push immediately
git add .
git commit -m "Emergency: Recover work after push failure"
git push
```

### Large File Issues
```bash
# 1. Remove large files
git rm --cached large_file_name
echo "large_file_pattern" >> .gitignore

# 2. Commit the removal
git add .gitignore
git commit -m "Remove large files and update gitignore"
git push
```

### Lost Connection
```bash
# 1. Save work locally first
git add .
git commit -m "WIP: Save before connection issue"

# 2. Try to reconnect later
git push origin main
```

## Integration with Atlas Tasks

Each Atlas task should:

1. **Start with safety check**
2. **Implement in 15-20 minute chunks**
3. **Auto-commit during long tasks**
4. **Final commit when complete**
5. **Update task tracking**

Example task flow:
```bash
# Start
python scripts/git_safety.py

# Work (with auto-commit every 20 min)
python scripts/execute_task.py 011

# Verify completion
git log --oneline -3
git status
```

## Monitoring

Track your commit frequency:
- Last commit should be <30 minutes ago
- Aim for commits every 15-20 minutes
- Use timer for consistent reminders

**Remember: Better to over-commit than lose work!**