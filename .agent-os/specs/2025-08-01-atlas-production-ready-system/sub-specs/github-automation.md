# GitHub Automation Specification

This specification details the automated GitHub workflow for continuous integration, documentation updates, and project synchronization to support intermittent development cycles.

## Automation Goals

### Primary Objectives
- **Continuous Integration**: Automated testing and quality checks on every commit
- **Documentation Sync**: Automatic updates to documentation when code changes
- **Progress Tracking**: Automated task completion tracking and project status updates
- **Release Management**: Automated versioning and release creation
- **Backup & Recovery**: Regular backup of project state and configuration

### Development Workflow Support
- **Intermittent Development**: Support for starting/stopping development cycles
- **Context Preservation**: Maintain project state and progress tracking
- **AI Agent Handoff**: Clear task status and next steps for future AI agents
- **Quality Assurance**: Automated code quality and test coverage validation

## GitHub Actions Workflows

### 1. Continuous Integration (.github/workflows/ci.yml)
```yaml
name: Continuous Integration
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov black isort mypy
      - name: Run code quality checks
        run: |
          black --check .
          isort --check-only .
          mypy .
      - name: Run tests with coverage
        run: |
          pytest --cov=. --cov-report=xml --cov-report=term-missing
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
```

### 2. Documentation Update (.github/workflows/docs.yml)
```yaml
name: Documentation Update
on:
  push:
    branches: [ main ]
    paths:
      - '**.py'
      - '.agent-os/**'
      - 'docs/**'

jobs:
  update-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - name: Generate API documentation
        run: |
          pip install -r requirements.txt
          python scripts/generate_api_docs.py
      - name: Update README status
        run: |
          python scripts/update_readme_status.py
      - name: Commit documentation updates
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add docs/ README.md
          git diff --staged --quiet || git commit -m "docs: Auto-update documentation"
          git push
```

### 3. Task Progress Tracking (.github/workflows/task-tracker.yml)
```yaml
name: Task Progress Tracking
on:
  push:
    branches: [ main ]

jobs:
  track-progress:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Update task completion status
        run: |
          python scripts/track_task_progress.py
      - name: Update project roadmap
        run: |
          python scripts/update_roadmap_progress.py
      - name: Create progress report
        run: |
          python scripts/generate_progress_report.py
      - name: Commit progress updates
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .agent-os/ docs/progress/
          git diff --staged --quiet || git commit -m "track: Update task progress and roadmap"
          git push
```

### 4. Release Management (.github/workflows/release.yml)
```yaml
name: Release Management
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Atlas ${{ github.ref }}
          body: |
            Automated release created from completed task milestone.
            See CHANGELOG.md for detailed information.
          draft: false
          prerelease: false
```

## Automation Scripts

### Task Progress Tracker (scripts/track_task_progress.py)
```python
#!/usr/bin/env python3
"""
Automated task progress tracking based on git commits and test results.
Updates .agent-os/specs/ files with completion status.
"""

import re
import subprocess
from pathlib import Path
import json
from datetime import datetime

def get_recent_commits():
    """Get recent commits since last progress update."""
    result = subprocess.run(
        ['git', 'log', '--since="1 day ago"', '--oneline'],
        capture_output=True, text=True
    )
    return result.stdout.strip().split('\n') if result.stdout.strip() else []

def extract_task_references(commit_message):
    """Extract task references from commit messages."""
    # Pattern: "task X.Y: description" or "fix: task X.Y"
    pattern = r'task\s+(\d+)\.(\d+)'
    matches = re.findall(pattern, commit_message.lower())
    return [(int(major), int(minor)) for major, minor in matches]

# Implementation continues...
```

### Documentation Generator (scripts/generate_api_docs.py)
```python
#!/usr/bin/env python3
"""
Automated API documentation generation from FastAPI application.
"""

from fastapi.openapi.utils import get_openapi
import json
import yaml
from pathlib import Path

def generate_api_docs():
    """Generate API documentation from FastAPI app."""
    # Import the FastAPI app
    from web.app import app

    # Generate OpenAPI schema
    openapi_schema = get_openapi(
        title="Atlas API",
        version="1.0.0",
        description="Personal Cognitive Amplification Platform API",
        routes=app.routes,
    )

    # Save as JSON and YAML
    docs_dir = Path("docs/api")
    docs_dir.mkdir(exist_ok=True)

    with open(docs_dir / "openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)

    with open(docs_dir / "openapi.yaml", "w") as f:
        yaml.dump(openapi_schema, f, default_flow_style=False)

# Implementation continues...
```

## Project State Management

### Development Session Tracking
- **Session Start**: Automatic detection of development activity
- **Progress Logging**: Track completed tasks and time invested
- **State Persistence**: Save current focus area and next steps
- **Handoff Documentation**: Generate context for future sessions

### AI Agent Handoff Protocol
```markdown
## Development Session Handoff

**Last Active**: 2025-08-01 23:30 PST
**Current Phase**: Phase 1 - Infrastructure Stabilization
**Active Task**: Task 1.3 - Implement dependency validation
**Progress**: 3/8 subtasks completed
**Next Steps**: Complete dependency validation error messages
**Blockers**: None
**Notes**: Environment setup automation 60% complete

**Context for Next Session**:
- Focus on completing Task 1 before moving to Task 2
- Test coverage currently at 75%, target is 90%
- All changes committed and pushed to main branch
- No merge conflicts or outstanding issues
```

## Automated Quality Gates

### Code Quality Checks
- **Black formatting**: Enforce consistent code style
- **Import sorting**: Maintain clean import organization
- **Type checking**: Validate type annotations with mypy
- **Test coverage**: Maintain 90%+ coverage requirement

### Documentation Quality
- **API docs sync**: Ensure API documentation matches implementation
- **README accuracy**: Validate claims match actual functionality
- **Link validation**: Check all documentation links are working
- **Spelling/grammar**: Basic documentation quality checks

### Deployment Readiness
- **Environment validation**: Ensure all required dependencies are available
- **Configuration testing**: Validate all configuration options work
- **Database migration**: Ensure schema changes are properly migrated
- **Service health**: Validate all services start and respond correctly

## Monitoring & Alerting

### GitHub Integration
- **Issue creation**: Automatically create issues for failed builds or tests
- **Status badges**: Update README with current build and coverage status
- **Progress tracking**: Update project boards with task completion
- **Release notes**: Generate release notes from completed tasks

### External Notifications
- **Email alerts**: Notify on build failures or critical issues
- **Slack integration**: Optional team notifications for major milestones
- **Dashboard updates**: Update external dashboards with project status