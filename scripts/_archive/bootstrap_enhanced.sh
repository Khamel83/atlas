#!/usr/bin/env bash
set -euo pipefail

# Enhanced OOS Bootstrap Script
# Usage: ./scripts/bootstrap_enhanced.sh [OPTIONS] [NAME] [PATH_ABS]
# Version: 2.0.0

VERSION="2.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------- Configuration ----------
NAME="${1:-oos}"
PATH_ABS="${2:-/home/ubuntu/dev/oos}"
ORG="${ORG:-Khamel83}"         # GitHub user/org
VIS="${VIS:-public}"           # public|private

# 1Password location for the multiline .env
OP_VAULT="${OP_VAULT:-Personal}"
OP_ITEM="${OP_ITEM:-bootstrap-env}"
OP_FIELD="${OP_FIELD:-env}"    # set to 'dotenv' if that's your field name

# ---------- Script Options ----------
DRY_RUN=false
VERBOSE=false
SKIP_PREFLIGHT=false
SKIP_GIT=false
SKIP_GITHUB=false
FORCE=false
PROGRESS=true
BACKUP_EXISTING=true
CUSTOM_MCP_CONFIG=""
ROLLBACK_FILE=""

# Color support
if [[ -t 1 ]]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BLUE='\033[0;34m'
  PURPLE='\033[0;35m'
  CYAN='\033[0;36m'
  NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' BLUE='' PURPLE='' CYAN='' NC=''
fi

# ---------- Utility Functions ----------
log() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
verbose() { [[ "$VERBOSE" == "true" ]] && echo -e "${CYAN}[VERBOSE]${NC} $*"; }

# Progress indicator
progress() {
  if [[ "$PROGRESS" == "true" ]]; then
    local step="$1"
    local total="$2"
    local desc="$3"
    local percent=$((step * 100 / total))
    echo -e "${PURPLE}[${step}/${total}]${NC} (${percent}%) $desc"
  fi
}

# Self-contained monitoring function (no external dependencies)
record_bootstrap_execution() {
  local exit_code="$1"
  local flags="$2"
  local duration="$3"
  local timestamp=$(date -Iseconds)

  # SECURITY: Sanitize flags to prevent API key logging
  local safe_flags
  safe_flags=$(echo "$flags" | sed -E 's/[A-Za-z0-9_-]*[Kk][Ee][Yy][A-Za-z0-9_=-]*=[A-Za-z0-9+/=_-]+/[REDACTED]/g' | sed -E 's/sk-[A-Za-z0-9_-]+/[REDACTED]/g')

  # Only record if we can write to current directory
  if [[ -w . ]]; then
    # Simple log entry with sanitized flags
    cat >> .bootstrap_history.log 2>/dev/null <<EOF || true
$timestamp|$exit_code|$safe_flags|${duration}s
EOF

    # Update simple stats (just total runs and success rate)
    if [[ -f .bootstrap_stats.txt ]]; then
      local total=$(head -1 .bootstrap_stats.txt 2>/dev/null | cut -d'|' -f1 || echo "0")
      local success=$(head -1 .bootstrap_stats.txt 2>/dev/null | cut -d'|' -f2 || echo "0")
    else
      local total=0
      local success=0
    fi

    ((total++))
    [[ $exit_code -eq 0 ]] && ((success++))

    echo "$total|$success|$timestamp" > .bootstrap_stats.txt 2>/dev/null || true
  fi
}

# Show help
show_help() {
  cat << 'EOF'
Enhanced OOS Bootstrap Script v2.0.0

Usage: ./scripts/bootstrap_enhanced.sh [OPTIONS] [NAME] [PATH_ABS]

Arguments:
  NAME              Project name (default: oos)
  PATH_ABS          Absolute path for project (default: /home/ubuntu/dev/oos)

Options:
  --dry-run         Show what would be done without making changes
  --verbose         Show detailed output
  --force           Overwrite existing files without prompting (creates backups)
  --no-preflight    Skip dependency checks
  --no-git          Skip git initialization
  --no-github       Skip GitHub repository creation
  --no-progress     Disable progress indicators
  --no-backup       Don't backup existing files
  --mcp-config FILE Use custom MCP configuration file
  --help, -h        Show this help message

Environment Variables:
  ORG              GitHub organization/user (default: Khamel83)
  VIS              Repository visibility: public|private (default: public)
  OP_VAULT         1Password vault name (default: Personal)
  OP_ITEM          1Password item name (default: bootstrap-env)
  OP_FIELD         1Password field name (default: env)
  FORCE_COLOR      Force colored output even in non-terminal

File Safety:
  By default, existing files are preserved (not overwritten).
  Use --force to overwrite existing files. Backups are automatically created.
  Check for warnings about skipped files during normal runs.

Examples:
  ./scripts/bootstrap_enhanced.sh --dry-run myproject /path/to/project
  ./scripts/bootstrap_enhanced.sh --verbose --no-github
  ./scripts/bootstrap_enhanced.sh --force  # Overwrites existing files (with backup)
  ORG=MyOrg VIS=private ./scripts/bootstrap_enhanced.sh
EOF
}

# Parse command line arguments
parse_args() {
  while [[ $# -gt 0 ]]; do
    case $1 in
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      --verbose)
        VERBOSE=true
        shift
        ;;
      --force)
        FORCE=true
        shift
        ;;
      --no-preflight)
        SKIP_PREFLIGHT=true
        shift
        ;;
      --no-git)
        SKIP_GIT=true
        shift
        ;;
      --no-github)
        SKIP_GITHUB=true
        shift
        ;;
      --no-progress)
        PROGRESS=false
        shift
        ;;
      --no-backup)
        BACKUP_EXISTING=false
        shift
        ;;
      --mcp-config)
        CUSTOM_MCP_CONFIG="$2"
        shift 2
        ;;
      --help|-h)
        show_help
        exit 0
        ;;
      -*)
        error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
      *)
        # Positional arguments
        if [[ -z "${NAME_SET:-}" ]]; then
          NAME="$1"
          NAME_SET=true
        elif [[ -z "${PATH_SET:-}" ]]; then
          PATH_ABS="$1"
          PATH_SET=true
        else
          error "Too many arguments: $1"
          exit 1
        fi
        shift
        ;;
    esac
  done
}

# Dependency checker
check_dependency() {
  local cmd="$1"
  local required="${2:-true}"
  local install_hint="${3:-}"

  if command -v "$cmd" >/dev/null 2>&1; then
    verbose "✓ $cmd found: $(command -v "$cmd")"
    if [[ "$cmd" == "op" ]]; then
      # Special check for 1Password authentication
      if ! op whoami >/dev/null 2>&1; then
        warn "1Password CLI found but not signed in"
        if [[ "$DRY_RUN" == "false" ]]; then
          log "Please sign in to 1Password..."
          eval "$(op signin)" || {
            error "Failed to sign in to 1Password"
            return 1
          }
        fi
      else
        verbose "✓ 1Password CLI is authenticated"
      fi
    fi
    return 0
  else
    if [[ "$required" == "true" ]]; then
      error "Missing required dependency: $cmd"
      [[ -n "$install_hint" ]] && echo "  Install with: $install_hint"
      return 1
    else
      warn "Optional dependency not found: $cmd"
      [[ -n "$install_hint" ]] && echo "  Install with: $install_hint"
      return 0
    fi
  fi
}

# Pre-flight checks
run_preflight_checks() {
  if [[ "$SKIP_PREFLIGHT" == "true" ]]; then
    warn "Skipping pre-flight checks (--no-preflight)"
    return 0
  fi

  progress 1 12 "Running pre-flight checks..."

  local failed=0

  # Required dependencies
  check_dependency "git" true "apt install git" || ((failed++))
  check_dependency "python3" true "apt install python3" || ((failed++))
  check_dependency "curl" true "apt install curl" || ((failed++))
  check_dependency "rsync" true "apt install rsync" || ((failed++))
  check_dependency "op" true "https://1password.com/downloads/command-line/" || ((failed++))

  # Check for node/npm
  if ! command -v npm >/dev/null 2>&1 && ! command -v node >/dev/null 2>&1; then
    error "Missing node/npm"
    echo "  Install with: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
    ((failed++))
  else
    verbose "✓ node/npm available"
  fi

  # Optional dependencies
  check_dependency "gh" false "https://cli.github.com/"

  # Check Claude CLI and attempt installation if missing
  if ! command -v claude >/dev/null 2>&1; then
    warn "Claude CLI not found, attempting installation..."
    if [[ "$DRY_RUN" == "false" ]]; then
      npm install -g @anthropic-ai/claude-code >/dev/null 2>&1 || warn "Failed to install Claude CLI"
    fi
  else
    verbose "✓ Claude CLI found"
  fi

  if [[ $failed -gt 0 ]]; then
    error "Pre-flight checks failed ($failed issues)"
    echo "Fix the above issues and try again, or use --no-preflight to skip"
    return 1
  fi

  success "Pre-flight checks passed"
  return 0
}

# Install Python dependencies
install_python_dependencies() {
  progress 1 1 "Installing Python dependencies..."

  if [[ -f "requirements.txt" ]]; then
    verbose "Installing dependencies from requirements.txt..."
    if [[ "$DRY_RUN" == "false" ]]; then
      python3 -m pip install -r requirements.txt || warn "Failed to install from requirements.txt"
    else
      log "Would install dependencies from requirements.txt"
    fi
  fi

  if [[ -f "requirements-dev.txt" ]]; then
    verbose "Installing development dependencies from requirements-dev.txt..."
    if [[ "$DRY_RUN" == "false" ]]; then
      python3 -m pip install -r requirements-dev.txt || warn "Failed to install from requirements-dev.txt"
    else
      log "Would install development dependencies from requirements-dev.txt"
    fi
  fi

  success "Python dependencies installed."
}

# Backup existing files
backup_existing_files() {
  if [[ "$BACKUP_EXISTING" == "false" ]]; then
    return 0
  fi

  local backup_dir="${PATH_ABS}.backup.$(date +%Y%m%d_%H%M%S)"
  local files_to_backup=(
    ".env"
    ".env.active"
    ".env.export"
    "bin"
    ".agents"
    ".claude"
    "docs/CLAUDE.md"
    "docs/GEMINI.md"
    "docs/qwen.md"
  )

  local backed_up=0

  for file in "${files_to_backup[@]}"; do
    local full_path="$PATH_ABS/$file"
    if [[ -e "$full_path" ]]; then
      if [[ $backed_up -eq 0 ]]; then
        log "Creating backup: $backup_dir"
        [[ "$DRY_RUN" == "false" ]] && mkdir -p "$backup_dir"
      fi
      verbose "Backing up: $file"
      [[ "$DRY_RUN" == "false" ]] && cp -r "$full_path" "$backup_dir/"
      ((backed_up++))
    fi
  done

  if [[ $backed_up -gt 0 ]]; then
    success "Backed up $backed_up items to $backup_dir"
    ROLLBACK_FILE="$backup_dir"
  fi
}

# Validate 1Password connection
validate_onepassword() {
  progress 2 12 "Validating 1Password connection..."

  verbose "Checking 1Password authentication..."
  if [[ "$DRY_RUN" == "false" ]]; then
    if ! op whoami >/dev/null 2>&1; then
      error "1Password CLI not authenticated. Please run 'op signin'"
      return 1
    fi

    verbose "Testing access to vault '$OP_VAULT' item '$OP_ITEM'..."
    if ! op item get "$OP_ITEM" --vault "$OP_VAULT" --fields "$OP_FIELD" >/dev/null 2>&1; then
      error "Cannot access 1Password item: $OP_VAULT/$OP_ITEM/$OP_FIELD"
      echo "Please check your 1Password configuration and try again"
      return 1
    fi
  fi

  success "1Password connection validated"
  return 0
}

# Pull environment from 1Password
setup_environment() {
  progress 3 12 "Setting up environment configuration..."

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Would pull .env from 1Password: $OP_VAULT/$OP_ITEM/$OP_FIELD"
    return 0
  fi

  local tmp_env
  tmp_env="$(mktemp)"

  verbose "Pulling environment from 1Password..."
  if ! op item get "$OP_ITEM" --vault "$OP_VAULT" --fields "$OP_FIELD" > "$tmp_env"; then
    error "Failed to retrieve environment from 1Password"
    rm -f "$tmp_env"
    return 1
  fi

  # Validate env file content
  if [[ ! -s "$tmp_env" ]]; then
    error "Retrieved environment file is empty"
    rm -f "$tmp_env"
    return 1
  fi

  verbose "Environment file retrieved successfully ($(wc -l < "$tmp_env") lines)"

  # Create project directory structure
  mkdir -p "$(dirname "$PATH_ABS")"
  cd "$(dirname "$PATH_ABS")"
  mkdir -p "$PATH_ABS"
  cd "$PATH_ABS"

  # Install environment file
  cp "$tmp_env" .env
  chmod 600 .env  # Secure permissions
  rm -f "$tmp_env"

  success "Environment configuration installed"
  return 0
}

# Create utility scripts
create_utility_scripts() {
  progress 4 12 "Creating utility scripts..."

  mkdir -p bin .agents/runners .claude

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Would create utility scripts in bin/"
    return 0
  fi

  verbose "Creating OpenRouter key management scripts..."

  # Enhanced key selector with better error handling
  cat > bin/select_or_key.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

# OpenRouter Key Selector with Enhanced Error Handling
ENV_FILE="${1:-.env}"
ACTIVE_FILE="${2:-.env.active}"
VERBOSE="${VERBOSE:-false}"

log() { [[ "$VERBOSE" == "true" ]] && echo "[select_or_key] $*" >&2; }
error() { echo "[select_or_key] ERROR: $*" >&2; }

# Check if env file exists
[[ -f "$ENV_FILE" ]] || { error "Environment file not found: $ENV_FILE"; exit 1; }

# Extract keys
mapfile -t KEYS < <(grep -E '^OPENROUTER_KEYS=' "$ENV_FILE" | sed 's/^OPENROUTER_KEYS=//' | tr -d '"'"'" | tr ',' '\n' | sed '/^\s*$/d')

if [[ ${#KEYS[@]} -eq 0 ]]; then
  error "No OPENROUTER_KEYS found in $ENV_FILE"
  exit 1
fi

log "Testing ${#KEYS[@]} OpenRouter key(s)..."

# Test each key
for i in "${!KEYS[@]}"; do
  key="${KEYS[$i]}"
  key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')  # trim whitespace

  if [[ -z "$key" ]]; then
    log "Skipping empty key at index $i"
    continue
  fi

  log "Testing key $((i+1))/${#KEYS[@]}..."

  code=$(curl -sS -o /dev/null -w "%{http_code}" \
    --connect-timeout 10 --max-time 30 \
    -H "Authorization: Bearer $key" \
    https://openrouter.ai/api/v1/models 2>/dev/null || echo "000")

  if [[ "$code" == "200" ]]; then
    log "Key $((i+1)) is working (HTTP $code)"
    printf "OPENAI_API_KEY=%s\n" "$key" > "$ACTIVE_FILE"
    exit 0
  else
    log "Key $((i+1)) failed (HTTP $code)"
  fi
done

error "No working OpenRouter keys found"
exit 2
SH

  # Enhanced key rotator
  cat > bin/rotate_or_key.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

# OpenRouter Key Rotator with Enhanced Logic
ENV_FILE="${1:-.env}"
ACTIVE_FILE="${2:-.env.active}"
VERBOSE="${VERBOSE:-false}"

log() { [[ "$VERBOSE" == "true" ]] && echo "[rotate_or_key] $*" >&2; }
error() { echo "[rotate_or_key] ERROR: $*" >&2; }

# Check files exist
[[ -f "$ENV_FILE" ]] || { error "Environment file not found: $ENV_FILE"; exit 1; }
[[ -f "$ACTIVE_FILE" ]] || { error "Active file not found: $ACTIVE_FILE"; exit 1; }

# Get current key
current="$(grep -E '^OPENAI_API_KEY=' "$ACTIVE_FILE" 2>/dev/null | cut -d= -f2- || true)"
[[ -n "$current" ]] || { error "No current key found in $ACTIVE_FILE"; exit 1; }

# Get all keys
keys=$(grep -E '^OPENROUTER_KEYS=' "$ENV_FILE" | sed 's/^OPENROUTER_KEYS=//' | tr -d '"'"'" | tr ',' '\n' | sed '/^\s*$/d')
[[ -n "$keys" ]] || { error "No OPENROUTER_KEYS found in $ENV_FILE"; exit 1; }

mapfile -t arr <<< "$keys"
idx=-1

log "Current key: [REDACTED]"
log "Available keys: ${#arr[@]}"

# Find current key index
for i in "${!arr[@]}"; do
  key=$(echo "${arr[$i]}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  if [[ "$key" == "$current" ]]; then
    idx=$i
    break
  fi
done

if [[ $idx -eq -1 ]]; then
  log "Current key not found in available keys, using first key"
  idx=0
else
  log "Current key found at index $idx"
fi

# Calculate next index
next_index=$(( (idx + 1) % ${#arr[@]} ))
next_key=$(echo "${arr[$next_index]}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

log "Rotating to key $((next_index+1))/${#arr[@]}..."
printf "OPENAI_API_KEY=%s\n" "$next_key" > "$ACTIVE_FILE"
SH

  # Safe environment sourcer
  cat > bin/safe_source_env.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

# Safe Environment Variable Sourcer
ENV_FILE="${1:-.env}"
EXPORT_FILE="${2:-.env.export}"
VERBOSE="${VERBOSE:-false}"

log() { [[ "$VERBOSE" == "true" ]] && echo "[safe_source_env] $*" >&2; }
error() { echo "[safe_source_env] ERROR: $*" >&2; }

[[ -f "$ENV_FILE" ]] || { error "Environment file not found: $ENV_FILE"; exit 1; }

# Validate and clean environment file
temp_file=$(mktemp)
trap "rm -f $temp_file" EXIT

# Process each line safely
while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip empty lines and comments
  [[ -n "$line" ]] || continue
  [[ "$line" =~ ^[[:space:]]*# ]] && continue

  # Validate format: KEY=VALUE
  if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
    echo "$line" >> "$temp_file"
  else
    log "Skipping invalid line: $line"
  fi
done < "$ENV_FILE"

# Source the cleaned file
set -a
source "$temp_file"
set +a

# Export to file for other scripts
if [[ -n "${EXPORT_FILE:-}" ]]; then
  env | grep -E '^[A-Za-z_][A-Za-z0-9_]*=' | sort > "$EXPORT_FILE"
fi

log "Environment loaded successfully"
SH


  # Copy API key prevention script
  verbose "Creating API key prevention script..."
  cp "$SCRIPT_DIR/../bin/prevent_api_key_commits.sh" bin/prevent_api_key_commits.sh 2>/dev/null || {
    # If source doesn't exist, create a minimal version
    cat > bin/prevent_api_key_commits.sh <<'PREVENT_SH'
#!/usr/bin/env bash
# Minimal API Key Prevention Script
echo "API key prevention not available in this installation"
exit 0
PREVENT_SH
  }

  chmod +x bin/*.sh
  success "Utility scripts created"
}

# Create runner scripts
create_runners() {
  progress 5 12 "Creating AI runner scripts..."

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Would create runner scripts in .agents/runners/"
    return 0
  fi

  verbose "Creating Claude runner..."
  cat > .agents/runners/run_claude.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

# Enhanced Claude Runner with Error Handling
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Source environment safely
if [[ -f "bin/safe_source_env.sh" ]]; then
  source bin/safe_source_env.sh .env
else
  set -a; source .env 2>/dev/null || { echo "Failed to load .env"; exit 1; }; set +a
fi

# Ensure active key is available
if [[ ! -f .env.active ]] || ! grep -q "OPENAI_API_KEY=" .env.active 2>/dev/null; then
  echo "Setting up OpenRouter key..."
  if ! bin/select_or_key.sh .env .env.active; then
    echo "Failed to set up working API key"
    exit 1
  fi
fi

# Source active key
source .env.active

echo "Starting Claude with MCP debugging..."
echo "Project: $PROJECT_ROOT"
echo "API Key: [CONFIGURED]"

exec claude --mcp-debug
SH

  verbose "Creating Gemini runner..."
  cat > .agents/runners/run_gemini.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

set -a
source bin/safe_source_env.sh .env 2>/dev/null || source .env
[[ -f .env.active ]] || bin/select_or_key.sh .env .env.active
source .env.active
set +a

echo "Starting Gemini chat..."
exec gemini chat
SH

  verbose "Creating Qwen runner..."
  cat > .agents/runners/run_qwen.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

set -a
source bin/safe_source_env.sh .env 2>/dev/null || source .env
[[ -f .env.active ]] || bin/select_or_key.sh .env .env.active
source .env.active
set +a

echo "Starting Qwen chat..."
exec qwen chat
SH

  chmod +x .agents/runners/*.sh
  success "AI runner scripts created"
}

# Safe file creation function with edge case handling
create_file_safely() {
  local file_path="$1"
  local content="$2"
  local description="${3:-file}"

  # Handle existing files/directories/symlinks
  if [[ -e "$file_path" || -L "$file_path" ]]; then
    if [[ -d "$file_path" ]]; then
      error "Cannot create $description: $file_path is a directory"
      return 1
    elif [[ -L "$file_path" ]]; then
      if [[ "$FORCE" == "true" ]]; then
        warn "Overwriting existing symlink $description: $file_path"
        rm "$file_path"
        mkdir -p "$(dirname "$file_path")"
        printf "%s" "$content" > "$file_path"
      else
        warn "Skipping existing symlink $description: $file_path"
        warn "  → Use --force to overwrite (will replace symlink with regular file)"
      fi
    elif [[ -f "$file_path" ]]; then
      if [[ "$FORCE" == "true" ]]; then
        warn "Overwriting existing $description: $file_path (backup created)"
        printf "%s" "$content" > "$file_path"
      else
        warn "Skipping existing $description: $file_path"
        warn "  → Use --force to overwrite (automatic backup will be created)"
        warn "  → Or manually backup/rename the file before running"
      fi
    else
      warn "Skipping $description: $file_path (unknown file type)"
    fi
  else
    verbose "Creating $description: $file_path"
    if ! mkdir -p "$(dirname "$file_path")" 2>/dev/null; then
      error "Cannot create directory for $description: $(dirname "$file_path")"
      return 1
    fi
    if ! printf "%s" "$content" > "$file_path" 2>/dev/null; then
      error "Cannot write $description: $file_path (permission denied?)"
      return 1
    fi
  fi
}

# Create project documentation
create_documentation() {
  progress 6 12 "Creating project documentation..."

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Would create documentation files"
    return 0
  fi

  mkdir -p .claude/commands .agents/prompts

  verbose "Creating dev log..."
  local dev_content
  dev_content=$(printf "# Development Log\n\nProject: %s\nCreated: %s\nPath: %s\n\n## Bootstrap Log\n- Enhanced bootstrap completed successfully\n" \
    "$NAME" "$(date)" "$PATH_ABS")
  create_file_safely "dev.md" "$dev_content" "development log"

  verbose "Creating agent instructions..."
  local agents_content='# Agent Instructions

## Core Principles
- Use Archon + MCPs for context and task management
- Keep code diffs small and focused
- Log all significant decisions in dev.md
- Never print or expose secrets in output
- Reference sensitive data by name/description only

## Planning Process
- Create short, test-first implementation plans
- Break complex tasks into manageable steps
- Consider rollback scenarios for critical changes
- Document assumptions and constraints

## Development Workflow
- Test changes incrementally
- Use diagnostic tools to verify system health
- Maintain clean git history with descriptive commits
- Follow established patterns and conventions'
  create_file_safely ".agents/agents.md" "$agents_content" "agent instructions"

  verbose "Creating Claude commands..."
  create_file_safely ".claude/commands/plan.md" "- Plan: Goal / Constraints / Steps (3–7) / Risks" "Claude plan command"

  # Generate OOS-specific slash commands if JSON file exists
  if [[ -f ".claude/slash_commands.json" ]]; then
    verbose "Converting OOS slash commands to Claude Code format..."
    python3 bin/convert-slash-commands.py .claude/slash_commands.json .claude/commands
  fi

  verbose "Creating overlay files..."
  local claude_content
  claude_content=$(printf "# Claude Code Overlay\n- Read .agents/agents.md\n\n# important-instruction-reminders\nDo what has been asked; nothing more, nothing less.\nNEVER create files unless they're absolutely necessary for achieving your goal.\nALWAYS prefer editing an existing file to creating a new one.\nNEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.\n")
  create_file_safely "docs/CLAUDE.md" "$claude_content" "Claude overlay"

  create_file_safely "docs/GEMINI.md" "# Gemini CLI Overlay\n- Read .agents/agents.md\n" "Gemini overlay"
  create_file_safely "docs/qwen.md" "# Qwen Code Overlay\n- Read .agents/agents.md\n" "Qwen overlay"

  success "Project documentation created"
}

# Setup MCP configuration
setup_mcp_configuration() {
  progress 7 12 "Setting up MCP configuration..."

  local mcp_registry="$HOME/.mcp/registry.json"
  local mcp_config

  if [[ -n "$CUSTOM_MCP_CONFIG" ]]; then
    if [[ ! -f "$CUSTOM_MCP_CONFIG" ]]; then
      error "Custom MCP config file not found: $CUSTOM_MCP_CONFIG"
      return 1
    fi
    verbose "Using custom MCP configuration: $CUSTOM_MCP_CONFIG"
    mcp_config="$CUSTOM_MCP_CONFIG"
  else
    verbose "Using default MCP configuration"
    mcp_config=""
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Would setup MCP registry at: $mcp_registry"
    return 0
  fi

  mkdir -p "$HOME/.mcp"

  if [[ -n "$mcp_config" ]]; then
    cp "$mcp_config" "$mcp_registry"
  else
    # Default MCP configuration
    cat > "$mcp_registry" <<'JSON'
{
  "servers": {
    "archon": {
      "transport": "http",
      "url": "http://localhost:8051/mcp",
      "description": "Archon project management and task coordination"
    },
    "context7": {
      "transport": "http",
      "url": "https://context7.liam.sh/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"
      },
      "description": "Context7 code analysis and documentation"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/ubuntu"],
      "description": "Filesystem access for file operations"
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PAT}"
      },
      "description": "GitHub integration for repository operations"
    },
    "sequential": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
      "description": "Sequential thinking support for complex reasoning"
    }
  }
}
JSON
  fi

  success "MCP configuration installed"
}

# Sync MCP to other AI tools
sync_mcp_to_other_tools() {
  progress 8 12 "Syncing MCP configuration to other AI tools..."

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Would sync MCP config to Gemini/Qwen"
    return 0
  fi

  verbose "Syncing MCP configuration to Gemini and Qwen..."

  python3 - "$HOME/.mcp/registry.json" "$HOME/.gemini/settings.json" "$HOME/.qwen/settings.json" <<'PY'
import json, os, sys

try:
    with open(sys.argv[1], 'r') as f:
        registry = json.load(f)

    servers = registry.get("servers", {})

    for settings_file in sys.argv[2:]:
        try:
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)

            # Load existing settings
            current_settings = {}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r') as f:
                        current_settings = json.load(f)
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON in {settings_file}, creating new")
                    current_settings = {}

            # Update MCP servers
            current_settings["mcpServers"] = servers

            # Write back
            with open(settings_file, 'w') as f:
                json.dump(current_settings, f, indent=2)

            print(f"Synced MCP config to {settings_file}")

        except Exception as e:
            print(f"Failed to sync to {settings_file}: {e}")

except Exception as e:
    print(f"Failed to process MCP registry: {e}")
    sys.exit(1)

print("MCP sync completed.")
PY

  success "MCP configuration synced to other AI tools"
}

# Register Claude MCP servers
register_claude_mcps() {
  progress 9 12 "Registering MCP servers with Claude..."

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Would register MCP servers with Claude CLI"
    return 0
  fi

  if ! command -v claude >/dev/null 2>&1; then
    warn "Claude CLI not found, skipping MCP registration"
    return 0
  fi

  verbose "Registering Archon MCP server..."
  claude mcp add --transport http archon "http://localhost:8051/mcp" || {
    warn "Failed to register Archon MCP server"
  }

  # Register Context7 if key is available
  if grep -q '^CONTEXT7_API_KEY=' .env 2>/dev/null; then
    KEY=$(grep '^CONTEXT7_API_KEY=' .env | cut -d= -f2-)
    if [[ -n "$KEY" && "$KEY" != "your_context7_key_here" ]]; then
      verbose "Registering Context7 MCP server..."
      # Use environment variable to avoid key exposure in command line
      CONTEXT7_API_KEY="$KEY" claude mcp add --transport http context7 "https://context7.liam.sh/mcp" --header "CONTEXT7_API_KEY: \${CONTEXT7_API_KEY}" || {
        warn "Failed to register Context7 MCP server"
      }
    else
      verbose "Context7 API key not set, skipping registration"
    fi
  fi

  success "MCP servers registered with Claude"
}

# Git initialization
init_git_repository() {
  if [[ "$SKIP_GIT" == "true" ]]; then
    warn "Skipping git initialization (--no-git)"
    return 0
  fi

  progress 10 12 "Initializing git repository..."

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Would initialize git repository and make initial commit"
    return 0
  fi

  # Initialize git if not already initialized
  if [[ ! -d .git ]]; then
    verbose "Initializing git repository..."
    git init -q
  else
    verbose "Git repository already exists"
  fi

  # Create .gitignore if it doesn't exist
  if [[ ! -f .gitignore ]]; then
    verbose "Creating .gitignore..."
    cat > .gitignore <<'IGNORE'
# Environment files
.env
.env.*
!.env.example

# Dependencies
node_modules/
.venv/
__pycache__/

# Logs
*.log
diagnostic_logs_*/
.bootstrap_history.log
.bootstrap_stats.txt

# Temporary files
*.tmp
.DS_Store
Thumbs.db

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Build artifacts
dist/
build/
*.egg-info/

# Database files
*.db
*.sqlite
*.sqlite3
IGNORE
  fi

  verbose "Adding files to git..."
  git add -A

  verbose "Installing API key prevention hook..."
  if [[ -f "bin/prevent_api_key_commits.sh" ]]; then
    ./bin/prevent_api_key_commits.sh --install >/dev/null 2>&1 || {
      warn "Failed to install API key prevention hook"
    }
  fi

  verbose "Creating initial commit..."
  git commit -m "feat: enhanced bootstrap for ${NAME}

- Added comprehensive pre-flight checks
- Enhanced error handling and rollback capabilities
- Improved MCP configuration management
- Added progress indicators and verbose logging
- Created utility scripts for key management
- Set up documentation and development workflow

Generated by scripts/bootstrap_enhanced.sh v${VERSION}" >/dev/null 2>&1 || {
    verbose "Initial commit already exists or no changes to commit"
  }

  success "Git repository initialized"
}

# Create GitHub repository
create_github_repository() {
  if [[ "$SKIP_GITHUB" == "true" ]]; then
    warn "Skipping GitHub repository creation (--no-github)"
    return 0
  fi

  progress 11 12 "Creating GitHub repository..."

  if ! command -v gh >/dev/null 2>&1; then
    warn "GitHub CLI not found, skipping repository creation"
    echo "  Install with: https://cli.github.com/"
    return 0
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    log "Would create GitHub repository: ${ORG}/${NAME} (${VIS})"
    return 0
  fi

  # Check if remote already exists
  if git remote get-url origin >/dev/null 2>&1; then
    verbose "Remote origin already exists, pushing changes..."
    git push -u origin HEAD || warn "Failed to push to existing remote"
  else
    verbose "Creating GitHub repository: ${ORG}/${NAME} (${VIS})"
    if gh repo create "${ORG}/${NAME}" --${VIS} --source "." --remote origin --push; then
      success "GitHub repository created and pushed"
    else
      warn "Failed to create GitHub repository"
      return 1
    fi
  fi
}

# Final validation and summary
final_validation() {
  progress 12 12 "Running final validation..."

  local issues=0

  # Check essential files exist
  local essential_files=(
    ".env"
    "bin/select_or_key.sh"
    "bin/rotate_or_key.sh"
    "bin/safe_source_env.sh"
    ".agents/runners/run_claude.sh"
    "docs/CLAUDE.md"
    "dev.md"
  )

  for file in "${essential_files[@]}"; do
    if [[ ! -f "$file" ]]; then
      error "Essential file missing: $file"
      ((issues++))
    fi
  done

  # Test key selection if not dry run
  if [[ "$DRY_RUN" == "false" ]]; then
    verbose "Testing OpenRouter key selection..."
    if ! bin/select_or_key.sh .env .env.active 2>/dev/null; then
      warn "OpenRouter key selection test failed (this may be expected if keys are not valid)"
    else
      verbose "✓ OpenRouter key selection working"
    fi
  fi

  # Generate code manifest
  if [ -f bin/generate_code_manifest.sh ]; then
      verbose "Generating code manifest..."
      if [[ "$DRY_RUN" == "false" ]]; then
          ./bin/generate_code_manifest.sh
      fi
  fi

  if [[ $issues -eq 0 ]]; then
    success "Final validation passed"
    return 0
  else
    error "Final validation failed ($issues issues)"
    return 1
  fi
}

# Rollback function
perform_rollback() {
  if [[ -z "$ROLLBACK_FILE" ]] || [[ ! -d "$ROLLBACK_FILE" ]]; then
    error "No backup available for rollback"
    return 1
  fi

  warn "Performing rollback from: $ROLLBACK_FILE"

  # Remove current files
  rm -rf bin .agents .claude .env .env.active .env.export docs/CLAUDE.md docs/GEMINI.md docs/qwen.md dev.md

  # Restore from backup
  cp -r "$ROLLBACK_FILE"/* ./ 2>/dev/null || true

  success "Rollback completed"
}

# Cleanup function
cleanup() {
  local exit_code=$?

  # Record execution for monitoring (including failures)
  if [[ -n "${start_time:-}" && -n "${execution_flags:-}" ]]; then
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    record_bootstrap_execution "$exit_code" "$execution_flags" "$duration"
  fi

  if [[ $exit_code -ne 0 ]] && [[ "$DRY_RUN" == "false" ]]; then
    error "Bootstrap failed with exit code $exit_code"

    # Error already recorded in record_bootstrap_execution above

    if [[ -n "$ROLLBACK_FILE" ]]; then
      echo
      warn "Backup available at: $ROLLBACK_FILE"
      read -p "Perform rollback? (y/N): " -n 1 -r
      echo
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        perform_rollback
      fi
    fi
  fi
}

# Main execution function
main() {
  # Parse command line arguments
  parse_args "$@"

  # Track execution for monitoring (product launch principle)
  local start_time=$(date +%s)
  local execution_flags="$*"

  # Set up cleanup trap
  trap cleanup EXIT

  echo -e "${PURPLE}Enhanced OOS Bootstrap v${VERSION}${NC}"
  echo "Project: $NAME"
  echo "Path: $PATH_ABS"
  echo "Mode: $([ "$DRY_RUN" == "true" ] && echo "DRY RUN" || echo "LIVE")"
  echo

  # Create directory and backup existing files
  mkdir -p "$(dirname "$PATH_ABS")"
  cd "$(dirname "$PATH_ABS")"
  mkdir -p "$PATH_ABS"
  cd "$PATH_ABS"

  backup_existing_files

  # Run all bootstrap steps
  run_preflight_checks
  install_python_dependencies
  validate_onepassword
  setup_environment
  create_utility_scripts
  create_runners
  create_documentation
  setup_mcp_configuration
  sync_mcp_to_other_tools
  register_claude_mcps
  init_git_repository
  create_github_repository
  final_validation

  # Success summary
  echo
  success "✅ Enhanced bootstrap completed successfully!"

  # Record successful execution for monitoring (self-contained)
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  record_bootstrap_execution 0 "$execution_flags" "$duration"

  echo
  echo "Project: $NAME"
  echo "Location: $PATH_ABS"
  [[ -n "$ROLLBACK_FILE" ]] && echo "Backup: $ROLLBACK_FILE"
  echo
  echo -e "${CYAN}Next Steps:${NC}"
  echo "  cd $PATH_ABS"
  echo "  .agents/runners/run_claude.sh   # Start Claude with MCP support"
  echo "  .agents/runners/run_gemini.sh   # Start Gemini"
  echo "  .agents/runners/run_qwen.sh     # Start Qwen"
  echo
  echo -e "${CYAN}Useful Commands:${NC}"
  echo "  bin/select_or_key.sh            # Select working API key"
  echo "  bin/rotate_or_key.sh            # Rotate to next API key"
  echo
  echo -e "${PURPLE}💡 Quick Learning Capture:${NC}"
  echo "  echo 'insight' | bin/development_guide.sh update  # Add learnings instantly"
  echo "  bin/development_guide.sh quick                    # Show current wisdom"
  echo "  ./bin/diagnose.sh --auto        # Run system diagnostics"
  echo "  ./bin/health_monitor.sh --daemon # Start health monitoring"

  if [[ -n "$ROLLBACK_FILE" ]]; then
    echo
    echo -e "${YELLOW}Cleanup:${NC}"
    echo "  rm -rf $ROLLBACK_FILE           # Remove backup after verification"
  fi

  echo
}

# Run main function with all arguments
main "$@"