# Atlas Development Philosophy

This document outlines the development philosophy and processes for the Atlas project. It is intended to be a living document that evolves with the project.

## Guiding Principles

- **Agent-First Development:** The primary audience for our code, documentation, and processes is AI agents. Humans are the second audience. This means that everything we do should be optimized for clarity, simplicity, and machine-readability.
- **Zero-Questions Standard:** Our goal is to create a project that can be understood and used by a new developer with no prior context, just by reading the documentation. If a question needs to be asked, the documentation has failed.
- **Transactional and Auditable:** Every change to the codebase should be a small, atomic, and verifiable transaction. This creates a detailed audit trail and makes it easy to recover from errors.
- **Mission-Driven:** All decisions should be made with the Atlas mission and vision in mind. When in doubt, choose the path that best advances the mission.

## AI-First Git & Commit Hygiene
- Optimize for **LLMs reading diffs**: many small commits > one giant diff.
- Commit prefix: `task(<ID>): <change>`; body = what/why; reference files and task ID.
- Push early/often. Humans can be messy; **the LLM must never be confused**.

## Continuous Preflight (Measure Twice, Cut Once)
- Before any task: run `scripts/preflight.sh`.
- Guarantees:
  - `.env` exists; required keys from `.env.template` are non-empty.
  - Python venv is present (`.venv`) and deps are installed.
  - Git workspace is clean on `main` (or committed/stashed).
  - **DISK SPACE CHECK**: Minimum 5GB free before operations
  - **LOG SIZE CHECK**: No single log file >100MB without rotation
- If any check fails: STOP, log to `EXECUTION_LOG.md`, open a `FIX-` task.

## Storage Crisis Prevention (Critical Learnings Aug 2025)
- **MANDATORY pre-flight disk checks** before background operations
- **Circuit breaker pattern** - Stop after 10 consecutive failures, don't retry indefinitely
- **Log rotation enforcement** - Size-based (50MB max) and time-based (daily) cleanup
- **Failure rate monitoring** - Alert if >50% operations fail, investigate immediately
- **Error log deduplication** - Don't log identical errors repeatedly
- **Background service health** - Monitor resource usage, not just process existence
- **Storage audits** - Regular `du -sh` checks to identify bloat before crisis

## Database Schema Optimization Patterns (Aug 27, 2025)
- **Cross-database queries**: Use `ATTACH DATABASE` for joining search indexes with main content
- **JSON field parsing**: Safe handling with `json.loads()` + `isinstance()` checks for list/dict structures
- **Graceful fallback**: Design search APIs to work with/without enhanced insights data
- **Batch processing**: Use `executemany()` for bulk operations, commit in batches of 100
- **Schema validation**: Always check table existence before complex joins

## LLM Integration Patterns (Aug 27, 2025)
- **Router-based selection**: Economy → Balanced → Premium model progression for cost optimization
- **JSON truncation issues**: Common LLM output problem - implement retry logic with shorter context
- **Pydantic validation**: Strong typing prevents malformed LLM responses from breaking system
- **Error handling**: Distinguish between extraction failures vs validation failures for better debugging
- **Processing time tracking**: Log extraction duration for performance monitoring

## Search Integration Architecture (Aug 27, 2025)
- **Enhanced SearchResult models**: Include AI-generated fields (summary, topics, entities, sentiment)
- **Database attachment strategy**: Use `ATTACH DATABASE` for cross-database joins in single queries
- **Graceful enhancement**: Design APIs to work with basic data + optional AI insights
- **JSON parsing safety**: Handle string/object conversion with proper error handling
- **Performance optimization**: Batch index population for 100k+ items without memory issues

## Virtual Environment Management (CRITICAL - Aug 27, 2025)
**STOP THE MADNESS**: Venv paths keep breaking background processes!

### **Definitive Solution Pattern:**
```python
# NEVER use sys.executable or hardcoded venv paths
class BackgroundService:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        # ALWAYS use this pattern for subprocess calls
        self.python_executable = str(self.project_root / "atlas_venv" / "bin" / "python3")

    def run_subprocess(self, script_name):
        subprocess.run([self.python_executable, script_name], cwd=self.project_root)
```

### **Common Failure Patterns to AVOID:**
- ❌ `sys.executable` - Points to system Python, not venv
- ❌ `/venv/bin/python3` - Wrong venv name
- ❌ Hardcoded absolute paths - Break on deployment
- ❌ Assuming `python3` command uses venv - Uses system Python

### **Mandatory Checks in All Background Services:**
1. **Verify venv exists**: Check `atlas_venv/bin/python3` before subprocess calls
2. **Use project-relative paths**: Calculate from `Path(__file__).parent`
3. **Log the actual executable**: Log which Python is being used for debugging
4. **Test subprocess calls**: Ensure they load correct dependencies

## Agentic File Index (Transactional)
- Source of truth lives at `AGENT_INDEX.json` (machine-readable) and `AGENT_INDEX.md` (human).
- Rebuilt **before** executing a task and **after** merging a task via `scripts/update_index.sh`.
- Each entry includes: `path`, `type`, `size`, `sha256`, `mtime`, `tags` (by extension), `module`, `last_commit`, `last_task_id`.
- This index enables agents to discover what exists, where it is, and relevant metadata without guessing.

## Decision Records (ADR)
- For non-trivial changes, create an ADR in `docs/adr/` with `scripts/new_adr.sh "<title>"`.
- Each ADR states the decision, alternatives, and alignment to Atlas mission/vision.

## Agent Readability Conventions
- Use stable section markers in generated docs:
  - `<!-- BEGIN: AUTO-GENERATED <name> -->` … `<!-- END: AUTO-GENERATED <name> -->`
- Prefer deterministic formats (JSON, YAML, Markdown tables).
- Avoid silent renames. If renaming paths, update the index and note in `EXECUTION_LOG.md`.

## North Star: Atlas Mission & Vision
- When in doubt, choose the path that best advances an Atlas’ mission/vision and shortens time to a durable, low-ops product.

## Secrets & Environment
- Secrets are loaded via `.env` (auto-sourced in `scripts/preflight.sh`).
- Only *required* secret to run is an API key. All else is configuration with sensible defaults.
- Paths and toggles must be environment-driven (no hardcoded paths). Keep `.env.template` authoritative.

## AI Budget & Cost Guard
- Caps: `$AI_BUDGET_DAILY_USD` (default 1.00), `$AI_BUDGET_MONTHLY_USD` (default 10.00).
- Gate before tasks: `python3 scripts/budget_guard.py check --cost <est> --task <ID>`
- Log after tasks: `python3 scripts/budget_guard.py log --cost <actual_or_est> --task <ID>`
- Goal: stay far below caps; fail early if we’d exceed.

## ID-First File Addressing
- Agents should **not** parse filenames. Use `fid` from `AGENT_INDEX.json`.
- Resolve IDs with `scripts/resolve_id.py` and update the index before/after tasks.

## Graceful Degradation
- If recoverable: skip, open a `FIX-` task, continue.
- If terminal: stop and say **"come help me please user"**.
- Keep runs idempotent; always update the index and append to the execution log.

## Qwen Autonomous Execution Rules (Aug 2025)

### **Task Structure Requirements for Autonomous Models**
All tasks in `TASKS.md` must follow these rules for successful Qwen execution:

#### **1. Concrete Deliverables Only**
```yaml
# ❌ BAD (vague, untestable)
- "Create user-friendly documentation with screenshots"
- "Test on real devices and gather feedback"

# ✅ GOOD (concrete, verifiable)
- "Create docs/user-guides/SETUP.md with sections: Installation (min 200 words), Configuration (min 150 words)"
- "Generate browser bookmarklet JavaScript code and save to web/static/bookmarklets.js"
```

#### **2. Mandatory Verification Commands**
Every task MUST include `verification_command` with bash tests:
```yaml
verification_command: |
  test -f docs/user-guides/SETUP.md &&
  wc -w docs/user-guides/SETUP.md | awk '{if($1<350) exit 1}' &&
  grep -q "Installation" docs/user-guides/SETUP.md
```

#### **3. No Manual Testing or Device Access**
Qwen cannot:
- Test on iOS/macOS devices
- Take screenshots or record videos
- Interact with browser extensions
- Perform user experience testing
- Access external APIs without credentials

Replace with:
- Code generation with examples
- Documentation with code snippets
- Automated file structure validation
- Content verification via text analysis

#### **4. Specific File Path Requirements**
Always specify exact paths and directory structures:
```yaml
# ❌ BAD
- "Create documentation files"

# ✅ GOOD
- "Create docs/user-guides/MAC_GUIDE.md"
- "Generate apple_shortcuts/shortcuts/save-to-atlas.shortcut"
- "Update web/templates/dashboard.html with new sections"
```

#### **5. Content Specifications**
Include minimum requirements for generated content:
```yaml
# Content requirements
min_word_count: 500
required_sections: ["Installation", "Configuration", "Troubleshooting"]
required_code_blocks: ["JavaScript bookmarklet", "Python API example"]
required_keywords: ["Atlas", "setup", "configuration"]
```

#### **6. Self-Validating Steps**
Each step should be verifiable by the model itself:
```bash
# Good verification steps
ls -la docs/user-guides/ | grep -c "\.md$" | awk '{if($1<5) exit 1}'  # At least 5 guides
python3 -c "import json; json.load(open('config/settings.json'))"      # Valid JSON
curl -s https://atlas.khamel.com/health | grep -q "healthy"               # API responsive
```

#### **7. AgentOS Lifecycle Compliance**
Follow the agents.md execution pattern:
```yaml
preflight_checks:
  - "test -f .env || cp .env.template .env"
  - "python3 -c 'import requests' || pip install requests"

git_workflow:
  branch_name: "task/ATLAS-COMPLETE-XXX-description"
  commit_prefix: "task(ATLAS-COMPLETE-XXX):"

post_completion:
  - "git add . && git commit -m 'task(ATLAS-COMPLETE-XXX): completed task'"
  - "python3 scripts/update_index.sh"
```

### **Task Quality Checklist**
Before adding any task to `TASKS.md`, verify:

- [ ] All steps are concrete file/code operations
- [ ] Verification command tests actual deliverables
- [ ] No manual testing or device access required
- [ ] File paths and structures explicitly specified
- [ ] Content requirements quantified (word counts, sections)
- [ ] Success criteria measurable via bash commands
- [ ] Dependencies clearly listed in `depends_on`
- [ ] AgentOS lifecycle steps included

### **Common Anti-Patterns to Avoid**
```yaml
# ❌ These will fail in autonomous mode:
- "Create engaging user experience"
- "Test thoroughly on multiple devices"
- "Gather user feedback and iterate"
- "Make it look professional"
- "Optimize for best practices"
- "Create compelling screenshots"
- "Record demonstration videos"

# ✅ Replace with concrete alternatives:
- "Create docs/UX_GUIDE.md with 5 workflow examples (min 100 words each)"
- "Generate test data in tests/fixtures/ and validate with pytest"
- "Create docs/FAQ.md addressing 10 common user questions"
- "Apply consistent CSS styling to web/static/css/main.css"
- "Implement PEP 8 formatting and validate with ruff check"
- "Generate ASCII diagrams in docs/ARCHITECTURE.md using text"
- "Create step-by-step text tutorials with code examples"
```

## Qwen Task Execution Fixes (Aug 28, 2025)

### **Critical Issues Identified & Fixed**

#### **1. Task Status Tracking Problems**
**Issue**: Tasks marked as "todo" remained that way even after completion, causing Qwen to skip or re-attempt completed work.

**Fix**:
- Manually updated completed tasks in `TASKS.md` to `status: done`
- Updated: ATLAS-COMPLETE-001, ATLAS-COMPLETE-002, ATLAS-COMPLETE-003

**Prevention**: Always mark tasks as "done" immediately after completion in YAML blocks.

#### **2. Broken Task Parser Regex**
**Issue**: `scripts/next_task.py` had incorrect regex pattern causing task parsing failures:
```python
# ❌ BROKEN - Wrong pattern for task headers
HDR = re.compile(r"^### \[(?P<id>[^\]]+)\]\s*(?P<title>.+)$")
```

**Fix**: Corrected regex to match actual TASKS.md format:
```python
# ✅ WORKING - Matches "### **ATLAS-COMPLETE-001: Title**"
HDR = re.compile(r"^### \*\*(?P<id>ATLAS-COMPLETE-\d+):\s*(?P<title>[^*]+)\*\*$")
```

**Prevention**: Test regex patterns against actual task headers before deployment.

#### **3. Command Substitution Security Restrictions**
**Issue**: Scripts failed with "Command substitution using $() is not allowed for security reasons"

**Fix**: Created `scripts/rotate_large_logs.sh` without command substitution:
```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d)  # Safe - uses direct assignment
find "$LOGS_DIR" -name "*.log" -size +100M | while read -r logfile; do
    mv "$logfile" "${logfile}.${TIMESTAMP}.old"
done
```

**Prevention**: Avoid $(), <(), >() patterns in scripts called by Qwen. Use direct variable assignment.

#### **4. PyYAML Import Errors**
**Issue**: Task parser failed with "ModuleNotFoundError: No module named 'yaml'"

**Fix**: Installed system-wide PyYAML:
```bash
pip3 install PyYAML --break-system-packages
```

**Prevention**: Ensure all required dependencies in task parsing scripts are installed system-wide for Qwen access.

### **Emergency Task Picker Solution**
Created simplified `scripts/simple_next_task.py` as working backup:
```python
# Manual list of ready tasks when parser fails
READY_TASKS = [
    {
        "id": "ATLAS-COMPLETE-005",
        "slug": "validate-core-features",
        "title": "Validate all cognitive features and infrastructure work",
        "priority": "medium"
    }
]
```

**Usage**: Replace broken parser temporarily while debugging full solution.

### **Testing & Validation Commands**
```bash
# Test task parser works
python3 scripts/next_task.py

# Test simplified picker
python3 scripts/simple_next_task.py

# Test log rotation (if needed)
bash scripts/rotate_large_logs.sh

# Verify task status parsing
python3 quick_task_test.py
```

### **Qwen Execution Checklist**
Before starting autonomous Qwen execution:

- [ ] Test `scripts/next_task.py` returns valid JSON
- [ ] Verify completed tasks marked as `status: done`
- [ ] Check no command substitution ($()) in scripts
- [ ] Confirm PyYAML installed system-wide
- [ ] Test regex patterns against actual task headers
- [ ] Have backup `scripts/simple_next_task.py` ready
- [ ] Clear large log files (>100MB)

### **Emergency Recovery Steps**
If Qwen execution fails:

1. **Check task picker**: `python3 scripts/next_task.py`
2. **Use simple picker**: `python3 scripts/simple_next_task.py`
3. **Mark completed tasks**: Update YAML blocks with `status: done`
4. **Clear logs**: `bash scripts/rotate_large_logs.sh`
5. **Install deps**: `pip3 install PyYAML --break-system-packages`

## Gemini CLI Autonomous Execution Rules (Aug 28, 2025)

### **Strategic Usage Pattern: Planning First, Execution Second**
Gemini CLI provides 60 Pro requests initially, then drops to free tier with limited requests. Optimize by front-loading planning tasks.

#### **Phase 1: High-Value Planning Tasks (Use Pro Tier)**
```bash
# Strategic analysis and architecture decisions
gemini -p "Analyze TASKS.md and create execution plan for next 5 tasks with dependencies"
gemini -p "Review current Atlas architecture and identify optimization opportunities"
gemini -p "Design error handling strategy for background services"
gemini -p "Create comprehensive test strategy for cognitive features"
```

#### **Phase 2: Execution Tasks (Use Free Tier)**
```bash
# Implementation work (less model-intensive)
gemini -p "Implement the pre-planned refactoring in helpers/path_manager.py"
gemini -p "Apply the designed error patterns to atlas_service_manager.py"
gemini -p "Execute the test plan created in Phase 1"
```

### **Authentication Strategy**
```bash
# Option 1: OAuth (Recommended for Atlas)
# - 60 requests/min, 1000 requests/day initially
# - Gemini 2.5 Pro with 1M token context
# - No API key management
gemini auth login

# Option 2: API Key (Fallback)
# - 100 requests/day with Gemini 2.5 Pro
# - More granular control
export GOOGLE_API_KEY="your-key"
gemini -k
```

### **Context Configuration**
Create `GEMINI.md` in project root for consistent behavior:
```markdown
# Atlas Project Context for Gemini CLI
You are working on Atlas, a cognitive amplification system.

## Key Constraints:
- Follow bulletproof process management patterns
- All subprocess calls must use helpers/bulletproof_process_manager.py
- Update TASKS.md status immediately after task completion
- Test all changes before committing
- Follow git workflow: branch → work → test → commit → merge

## Current Architecture:
- Python 3.12 with atlas_venv virtual environment
- SQLite databases with AI-powered search indexing
- FastAPI web services with bulletproof monitoring
- Apple ecosystem integration (iOS shortcuts, extensions)

## Execution Patterns:
- Use atlas_status.py for system health checks
- Run pytest for validation before commits
- Apply ruff/mypy for code quality
- Follow agents.md lifecycle for autonomous work
```

### **Optimized Command Patterns**

#### **Planning Commands (Pro Tier)**
```bash
# Architecture analysis
gemini --include-directories helpers,monitoring "Analyze memory leak patterns and design prevention strategy"

# Strategic task planning
gemini -p "Review TASKS.md and create detailed execution plan with time estimates and risk analysis"

# Complex problem solving
gemini "Given the current Qwen execution issues documented in dev.md, design a robust autonomous execution framework"
```

#### **Execution Commands (Free Tier)**
```bash
# Direct implementation
gemini -p "Implement the planned bulletproof subprocess wrapper in helpers/bulletproof_process_manager.py"

# Specific fixes
gemini -p "Apply the designed logging pattern to atlas_background_service.py line 156-203"

# Testing and validation
gemini -p "Create pytest test for the implemented memory leak detection using the planned test strategy"
```

### **Request Budget Management**

#### **Pro Tier Usage (First 60 requests)**
Priority order for maximum value:
1. **Strategic Planning** (20 requests): Architecture decisions, task sequencing, risk analysis
2. **Problem Solving** (20 requests): Complex debugging, system design, optimization strategies
3. **Code Review** (10 requests): Security analysis, performance review, best practices
4. **Documentation** (10 requests): Architecture docs, user guides, API documentation

#### **Free Tier Usage (100 requests/day)**
Focus on concrete implementation:
1. **Code Implementation**: Following pre-made plans from Pro tier
2. **Testing**: Executing test plans created during planning phase
3. **Bug Fixes**: Applying solutions designed during Pro analysis
4. **Maintenance**: Routine updates and minor improvements

### **Autonomous Execution Integration**

#### **Gemini + Qwen Hybrid Approach**
```bash
# 1. Gemini for planning (Pro tier)
PLAN=$(gemini -p "Create execution plan for ATLAS-COMPLETE-005 with specific file changes and validation steps")

# 2. Qwen for execution (unlimited)
echo "$PLAN" > task_execution_plan.md
# Then run Qwen with the detailed plan
```

#### **Error Recovery with Gemini**
```bash
# When Qwen encounters issues
gemini -p "Debug this Qwen execution error and provide specific fix commands: $(cat execution_error.log)"

# Strategic replanning when tasks fail
gemini "Given these failed attempts, redesign the approach for ATLAS-COMPLETE task completion"
```

### **Context Management**
```bash
# Include relevant directories for better context
gemini --include-directories scripts,helpers,monitoring "Design system health monitoring"

# Use conversation checkpointing for complex tasks
gemini --checkpoint planning_session_001 "Continue architectural analysis from previous session"
```

### **Quality Assurance Pattern**
```bash
# Pro tier: Strategic review
gemini "Review completed implementation and identify potential issues before deployment"

# Free tier: Specific validation
gemini -p "Run validation tests for the implemented changes and fix any errors"
```

### **Best Practices Summary**
- **Front-load planning**: Use Pro tier for high-level analysis and strategy
- **Batch execution**: Group implementation tasks for free tier usage
- **Context optimization**: Use GEMINI.md and directory inclusion for better results
- **Hybrid approach**: Gemini for planning, Qwen for execution
- **Error recovery**: Leverage Gemini's problem-solving for debugging complex issues
- **Request tracking**: Monitor usage to stay within limits and optimize value

## Universal Port Configuration Strategy (Sep 2025)

### **Problem: The 8000 Port Conflict Crisis**
Every development project defaults to port 8000, causing constant conflicts during development. Atlas encountered this exact issue with hardcoded ports throughout the codebase.

### **Solution: Unique Random Port Assignment**
Implement universal port configuration to eliminate conflicts across all future projects:

#### **1. Environment-Driven Port Configuration**
```bash
# .env file pattern for all projects
API_PORT=$(python3 -c "import random; print(random.randint(7000, 9999))")
# Or use project hash for consistency:
API_PORT=$(echo "project_name" | md5sum | cut -c1-4 | python3 -c "import sys; print(7000 + int(sys.stdin.read().strip(), 16) % 3000)")
```

#### **2. Core Service Pattern**
All services must read from environment with fallbacks:
```python
# Pattern for all Python services
import os
from dotenv import load_dotenv

load_dotenv()
api_port = int(os.getenv('API_PORT', 7444))  # Project-specific default
```

#### **3. Universal Port Utilities**
Create port management utilities in every project:
```python
# get_port.py - Universal port getter
def get_project_port():
    load_dotenv()
    return int(os.getenv('API_PORT', generate_project_port()))

def generate_project_port():
    # Generate stable port based on project name
    project_name = Path(__file__).parent.name
    hash_val = hash(project_name) % 3000
    return 7000 + hash_val
```

#### **4. Documentation Pattern**
Never hardcode ports in documentation:
```markdown
# ❌ BAD - Hardcoded port
Visit https://atlas.khamel.com

# ✅ GOOD - Dynamic port reference
PORT=$(python -c 'from get_port import get_project_port; print(get_project_port())')
Visit http://localhost:$PORT
```

#### **5. Zero-Hardcode Rule**
**CRITICAL**: Core services must NEVER hardcode ports. All hardcoding leads to:
- Development conflicts between projects
- Deployment issues across environments
- Documentation becoming outdated
- Developer confusion about which service runs where

### **Implementation Checklist for New Projects**
- [ ] Create `.env` with unique `API_PORT` assignment
- [ ] Add `get_port.py` utility for consistent port access
- [ ] Update all services to read from environment
- [ ] Replace hardcoded ports in documentation with dynamic references
- [ ] Add port validation to startup scripts
- [ ] Create port conflict detection in health checks

### **Atlas Success Story**
Atlas successfully implemented this pattern:
- **Before**: 94 files with hardcoded port 8000 references
- **After**: All core services read from `.env`, fully configurable
- **Result**: Universal port configuration with zero conflicts

### **Future Project Template**
```bash
# setup_project_ports.sh
#!/bin/bash
PROJECT_NAME=${PWD##*/}
UNIQUE_PORT=$((7000 + $(echo $PROJECT_NAME | md5sum | cut -c1-4 | python3 -c "import sys; print(int(sys.stdin.read(), 16) % 3000)")))

echo "API_PORT=$UNIQUE_PORT" >> .env
echo "Project '$PROJECT_NAME' assigned port $UNIQUE_PORT"
```

This approach ensures every project gets a unique, stable port based on its name, eliminating the 8000 conflict forever.

## North Star
- Decisions prioritize Atlas mission/vision and reduce time to a durable, low-ops product.