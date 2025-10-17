#!/usr/bin/env bash
set -euo pipefail

# OOS Diagnostic Wizard - Interactive troubleshooting and system health check
# Usage: ./bin/diagnose.sh [--auto] [--verbose] [--fix] [--profile]

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/diagnostic.log"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Default options
AUTO_MODE=false
VERBOSE=false
AUTO_FIX=false
PROFILE_MODE=false
FORCE_COLOR=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --auto) AUTO_MODE=true; shift ;;
    --verbose) VERBOSE=true; shift ;;
    --fix) AUTO_FIX=true; shift ;;
    --profile) PROFILE_MODE=true; shift ;;
    --color) FORCE_COLOR=true; shift ;;
    --help|-h)
      echo "OOS Diagnostic Wizard v$VERSION"
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --auto     Run all checks without prompts"
      echo "  --verbose  Show detailed output"
      echo "  --fix      Attempt automatic fixes"
      echo "  --profile  Enable performance profiling"
      echo "  --color    Force color output"
      echo "  --help     Show this help"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Color output functions
if [[ -t 1 ]] || [[ "$FORCE_COLOR" == "true" ]]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BLUE='\033[0;34m'
  PURPLE='\033[0;35m'
  CYAN='\033[0;36m'
  NC='\033[0m' # No Color
else
  RED=''
  GREEN=''
  YELLOW=''
  BLUE=''
  PURPLE=''
  CYAN=''
  NC=''
fi

# Logging functions
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

verbose() {
  [[ "$VERBOSE" == "true" ]] && echo -e "${CYAN}[VERBOSE]${NC} $*" | tee -a "$LOG_FILE"
}

success() {
  echo -e "${GREEN}✓${NC} $*" | tee -a "$LOG_FILE"
}

warning() {
  echo -e "${YELLOW}⚠${NC} $*" | tee -a "$LOG_FILE"
}

error() {
  echo -e "${RED}✗${NC} $*" | tee -a "$LOG_FILE"
}

info() {
  echo -e "${BLUE}ℹ${NC} $*" | tee -a "$LOG_FILE"
}

# Performance profiling
profile_start() {
  [[ "$PROFILE_MODE" == "true" ]] && echo $(($(date +%s%N)/1000000))
}

profile_end() {
  if [[ "$PROFILE_MODE" == "true" ]] && [[ -n "${1:-}" ]]; then
    local end_time=$(($(date +%s%N)/1000000))
    local duration=$((end_time - $1))
    verbose "Performance: ${2:-Operation} took ${duration}ms"
  fi
}

# Interactive prompts
prompt_yes_no() {
  local question="$1"
  local default="${2:-y}"

  if [[ "$AUTO_MODE" == "true" ]]; then
    [[ "$default" == "y" ]] && return 0 || return 1
  fi

  while true; do
    if [[ "$default" == "y" ]]; then
      read -p "$question [Y/n]: " -r reply
      reply=${reply:-y}
    else
      read -p "$question [y/N]: " -r reply
      reply=${reply:-n}
    fi

    case $reply in
      [Yy]*) return 0 ;;
      [Nn]*) return 1 ;;
      *) echo "Please answer yes or no."
    esac
  done
}

# System dependency checks
check_dependencies() {
  local start_time=$(profile_start)
  info "Checking system dependencies..."

  local missing_deps=()
  local required_commands=("git" "python3" "curl" "grep" "sed" "awk" "tr")
  local optional_commands=("op" "gh" "claude" "npm" "node")

  for cmd in "${required_commands[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing_deps+=("$cmd")
      error "Required command '$cmd' is missing"
    else
      success "Found $cmd: $(command -v "$cmd")"
      verbose "$cmd version: $(eval "$cmd --version 2>/dev/null | head -1 || echo 'Version info not available'")"
    fi
  done

  for cmd in "${optional_commands[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      warning "Optional command '$cmd' is missing"
    else
      success "Found $cmd: $(command -v "$cmd")"
      verbose "$cmd version: $(eval "$cmd --version 2>/dev/null | head -1 || echo 'Version info not available'")"
    fi
  done

  if [[ ${#missing_deps[@]} -gt 0 ]]; then
    error "Missing required dependencies: ${missing_deps[*]}"
    if [[ "$AUTO_FIX" == "true" ]] || prompt_yes_no "Attempt to install missing dependencies?"; then
      install_dependencies "${missing_deps[@]}"
    fi
    return 1
  fi

  profile_end "$start_time" "Dependency check"
  return 0
}

# Install missing dependencies
install_dependencies() {
  local deps=($@)
  info "Installing missing dependencies: ${deps[*]}"

  if command -v apt-get >/dev/null 2>&1; then
    for dep in "${deps[@]}"; do
      case "$dep" in
        "python3") sudo apt-get update && sudo apt-get install -y python3 ;;
        "git") sudo apt-get update && sudo apt-get install -y git ;;
        "curl") sudo apt-get update && sudo apt-get install -y curl ;;
        *) warning "Don't know how to install $dep via apt-get"
      esac
    done
  elif command -v brew >/dev/null 2>&1; then
    for dep in "${deps[@]}"; do
      brew install "$dep" || warning "Failed to install $dep via brew"
    done
  else
    error "No package manager found. Please install manually: ${deps[*]}"
  fi
}

# Environment file validation
check_env_files() {
  local start_time=$(profile_start)
  info "Checking environment configuration..."

  cd "$PROJECT_ROOT"

  if [[ ! -f ".env" ]]; then
    error ".env file is missing"
    if [[ "$AUTO_FIX" == "true" ]] || prompt_yes_no "Create a template .env file?"; then
      create_env_template
    fi
    return 1
  fi

  success "Found .env file"

  # Check for common issues
  local issues=()

  # Check for CRLF line endings
  if file .env | grep -q "CRLF"; then
    issues+=("CRLF line endings detected")
    if [[ "$AUTO_FIX" == "true" ]]; then
      sed -i 's/\r$//' .env
      success "Fixed CRLF line endings"
    fi
  fi

  # Check for BOM
  if [[ "$(head -c 3 .env | xxd -p)" == "efbbbf" ]]; then
    issues+=("UTF-8 BOM detected")
    if [[ "$AUTO_FIX" == "true" ]]; then
      perl -i -pe 's/^\xEF\xBB\xBF//' .env
      success "Removed UTF-8 BOM"
    fi
  fi

  # Test safe_source_env.sh
  if [[ -f "bin/safe_source_env.sh" ]]; then
    if bash bin/safe_source_env.sh .env; then
      success "Environment file loads successfully"
      [[ -f ".env.export" ]] && success "Generated .env.export"
    else
      error "Failed to load environment file"
      issues+=("Environment loading failed")
    fi
  fi

  # Check for required variables
  local required_vars=("OPENROUTER_KEYS")
  for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env; then
      warning "Missing required variable: $var"
      issues+=("Missing $var")
    else
      success "Found required variable: $var"
    fi
  done

  if [[ ${#issues[@]} -gt 0 ]]; then
    warning "Environment issues found: ${issues[*]}"
  fi

  profile_end "$start_time" "Environment check"
  return 0
}

# Create environment template
create_env_template() {
  info "Creating .env template..."
  cat > .env <<'EOF'
# OpenRouter API Keys (comma-separated for rotation)
OPENROUTER_KEYS=sk_or_your_key_here

# GitHub Personal Access Token
GITHUB_PAT=ghp_your_token_here

# 1Password Configuration
OP_VAULT=Personal
OP_ITEM=bootstrap-env
OP_FIELD=env

# Archon MCP Configuration
ARCHON_URL=https://archon.khamel.com:8051/mcp

# Context7 API Key (optional)
CONTEXT7_API_KEY=your_context7_key_here
EOF
  success "Created .env template"
}

# Network connectivity tests
check_network() {
  local start_time=$(profile_start)
  info "Testing network connectivity..."

  local endpoints=(
    "google.com:443"
    "github.com:443"
    "openrouter.ai:443"
    "archon.khamel.com:8051"
    "context7.liam.sh:443"
  )

  for endpoint in "${endpoints[@]}"; do
    local host="${endpoint%:*}"
    local port="${endpoint#*:}"

    if timeout 5 bash -c "exec 3<>/dev/tcp/$host/$port"; then
      success "Network connectivity to $host:$port"
    else
      error "Failed to connect to $host:$port"
    fi
  done

  # Test DNS resolution
  if nslookup google.com >/dev/null 2>&1; then
    success "DNS resolution working"
  else
    error "DNS resolution failed"
  fi

  profile_end "$start_time" "Network connectivity check"
}

# API key validation
check_api_keys() {
  local start_time=$(profile_start)
  info "Validating API keys..."

  cd "$PROJECT_ROOT"

  if [[ -f ".env" ]]; then
    source bin/safe_source_env.sh .env 2>/dev/null || true

    # Test OpenRouter keys
    if [[ -n "${OPENROUTER_KEYS:-}" ]]; then
      IFS=',' read -ra KEYS <<< "$OPENROUTER_KEYS"
      local working_keys=0

      for key in "${KEYS[@]}"; do
        key=$(echo "$key" | tr -d ' "')
        if [[ -n "$key" ]]; then
          verbose "Testing OpenRouter key: ${key:0:10}..."
          local response=$(curl -sS -o /dev/null -w "%{{http_code}}" \
            -H "Authorization: Bearer $key" \
            https://openrouter.ai/api/v1/models 2>/dev/null || echo "000")

          if [[ "$response" == "200" ]]; then
            success "OpenRouter key valid: ${key:0:10}..."
            ((working_keys++))
          else
            error "OpenRouter key invalid/expired: ${key:0:10}... (HTTP $response)"
          fi
        fi
      done

      if [[ $working_keys -gt 0 ]]; then
        success "$working_keys working OpenRouter key(s)"
      else
        error "No working OpenRouter keys found"
      fi
    else
      warning "OPENROUTER_KEYS not set"
    fi

    # Test GitHub PAT
    if [[ -n "${GITHUB_PAT:-}" ]]; then
      verbose "Testing GitHub PAT..."
      local response=$(curl -sS -o /dev/null -w "%{{http_code}}" \
        -H "Authorization: token $GITHUB_PAT" \
        https://api.github.com/user 2>/dev/null || echo "000")

      if [[ "$response" == "200" ]]; then
        success "GitHub PAT is valid"
      else
        error "GitHub PAT is invalid/expired (HTTP $response)"
      fi
    else
      warning "GITHUB_PAT not set"
    fi

    # Test 1Password CLI
    if command -v op >/dev/null 2>&1; then
      if op whoami >/dev/null 2>&1; then
        success "1Password CLI is authenticated"
      else
        warning "1Password CLI not signed in"
        if [[ "$AUTO_FIX" == "true" ]] || prompt_yes_no "Sign in to 1Password?"; then
          eval "$(op signin)" && success "1Password sign-in successful"
        fi
      fi
    fi
  fi

  profile_end "$start_time" "API key validation"
}

# MCP server health checks
check_mcp_servers() {
  local start_time=$(profile_start)
  info "Checking MCP server health..."

  # Check Archon
  local archon_url="${ARCHON_URL:-https://archon.khamel.com:8051/mcp}"
  verbose "Testing Archon at: $archon_url"

  local response=$(curl -sS -o /dev/null -w "%{{http_code}}" "$archon_url" 2>/dev/null || echo "000")
  if [[ "$response" == "200" ]]; then
    success "Archon MCP server is accessible"
  else
    error "Archon MCP server unreachable (HTTP $response)"
  fi

  # Check Context7 if key is available
  if [[ -n "${CONTEXT7_API_KEY:-}" ]]; then
    verbose "Testing Context7 MCP..."
    local context7_response=$(curl -sS -o /dev/null -w "%{{http_code}}" \
      -H "CONTEXT7_API_KEY: $CONTEXT7_API_KEY" \
      https://context7.liam.sh/mcp 2>/dev/null || echo "000")

    if [[ "$context7_response" == "200" ]]; then
      success "Context7 MCP server is accessible"
    else
      error "Context7 MCP server unreachable (HTTP $context7_response)"
    fi
  fi

  # Check Claude MCP configuration
  if command -v claude >/dev/null 2>&1; then
    if claude mcp list >/dev/null 2>&1; then
      success "Claude MCP configuration accessible"
      verbose "Claude MCPs: $(claude mcp list 2>/dev/null | grep -E '^\s*\w+' || echo 'None configured')"
    else
      warning "Claude MCP configuration issues"
    fi
  fi

  profile_end "$start_time" "MCP server health check"
}

# Log collection and analysis
collect_logs() {
  local start_time=$(profile_start)
  info "Collecting system logs and diagnostics..."

  local log_dir="$PROJECT_ROOT/diagnostic_logs_$TIMESTAMP"
  mkdir -p "$log_dir"

  # System information
  {
    echo "=== System Information ==="
    uname -a
    echo
    echo "=== Disk Usage ==="
    df -h
    echo
    echo "=== Memory Usage ==="
    free -h
    echo
    echo "=== Environment Variables ==="
    env | grep -E "(PATH|HOME|USER|SHELL)" | sort
  } > "$log_dir/system_info.txt"

  # Git information
  if [[ -d ".git" ]]; then
    {
      echo "=== Git Status ==="
      git status
      echo
      echo "=== Git Remote ==="
      git remote -v
      echo
      echo "=== Recent Commits ==="
      git log --oneline -10
    } > "$log_dir/git_info.txt"
  fi

  # Process information
  {
    echo "=== Running Processes ==="
    ps aux | grep -E "(claude|archon|node|python)" | grep -v grep
  } > "$log_dir/processes.txt"

  # Network information
  {
    echo "=== Network Interfaces ==="
    ip addr show 2>/dev/null || ifconfig
    echo
    echo "=== DNS Configuration ==="
    cat /etc/resolv.conf 2>/dev/null || echo "Not accessible"
  } > "$log_dir/network_info.txt"

  # Copy important config files (sanitized)
  if [[ -f ".env" ]]; then
    grep -E "^[A-Z_]+=.*" .env | sed 's/=.*/=***REDACTED****/' > "$log_dir/env_structure.txt"
  fi

  if [[ -f "$HOME/.mcp/registry.json" ]]; then
    cp "$HOME/.mcp/registry.json" "$log_dir/mcp_registry.json"
  fi

  success "Diagnostic logs collected in: $log_dir"
  profile_end "$start_time" "Log collection"
}

# Performance profiling
run_performance_tests() {
  local start_time=$(profile_start)
  info "Running performance tests..."

  # Test bootstrap script performance
  if [[ -f "bootstrap.sh" ]]; then
    verbose "Profiling bootstrap.sh dry run..."
    local bootstrap_start=$(profile_start)

    # Create a test environment for dry run
    local test_dir=$(mktemp -d)
    (
      cd "$test_dir"
      # Simulate bootstrap without actual execution
      time bash -n "$PROJECT_ROOT/bootstrap.sh" 2>&1
    ) && success "Bootstrap script syntax check passed"
    rm -rf "$test_dir"

    profile_end "$bootstrap_start" "Bootstrap syntax check"
  fi

  # Test environment loading speed
  if [[ -f "bin/safe_source_env.sh" && -f ".env" ]]; then
    verbose "Profiling environment loading..."
    local env_start=$(profile_start)

    for i in {1..5}; do
      bash bin/safe_source_env.sh .env >/dev/null 2>&1
    done

    profile_end "$env_start" "Environment loading (5 iterations)"
  fi

  # Test API response times
  if [[ -n "${OPENROUTER_KEYS:-}" ]]; then
    verbose "Testing API response times..."
    local api_start=$(profile_start)

    IFS=',' read -ra KEYS <<< "$OPENROUTER_KEYS"
    for key in "${KEYS[@]:0:1}"; do  # Test only first key
      key=$(echo "$key" | tr -d ' "')
      if [[ -n "$key" ]]; then
        curl -sS -o /dev/null -w "OpenRouter API response time: %{time_total}s\n" \
          -H "Authorization: Bearer $key" \
          https://openrouter.ai/api/v1/models || true
        break
      fi
    done

    profile_end "$api_start" "API response time test"
  fi

  profile_end "$start_time" "Performance tests"
}

# Self-healing mechanisms
run_self_healing() {
  info "Running self-healing mechanisms..."

  # Fix common file permission issues
  if [[ -d "bin" ]]; then
    find bin -name "*.sh" -type f ! -perm -u+x -exec chmod +x {} \; && \
      success "Fixed executable permissions for shell scripts"
  fi

  # Regenerate .env.export if needed
  if [[ -f ".env" && -f "bin/safe_source_env.sh" ]]; then
    if [[ ! -f ".env.export" ]] || [[ ".env" -nt ".env.export" ]]; then
      bash bin/safe_source_env.sh .env && \
        success "Regenerated .env.export"
    fi
  fi

  # Regenerate .env.active if needed
  if [[ -f "bin/select_or_key.sh" && -f ".env" ]]; then
    if [[ ! -f ".env.active" ]] || ! grep -q "OPENAI_API_KEY=" .env.active 2>/dev/null; then
      if bash bin/select_or_key.sh .env .env.active 2>/dev/null; then
        success "Regenerated .env.active with working API key"
      fi
    fi
  fi

  # Clean up temporary files
  find . -maxdepth 1 -name "*.tmp" -o -name ".*~" -type f -delete 2>/dev/null && \
    success "Cleaned up temporary files"

  # Verify git configuration
  if [[ -d ".git" ]]; then
    if ! git config user.name >/dev/null 2>&1; then
      warning "Git user.name not configured"
    fi
    if ! git config user.email >/dev/null 2>&1; then
      warning "Git user.email not configured"
    fi
  fi
}

# Configuration validation and repair
validate_configuration() {
  info "Validating system configuration..."

  local config_issues=()

  # Check MCP registry
  if [[ -f "$HOME/.mcp/registry.json" ]]; then
    if python3 -m json.tool "$HOME/.mcp/registry.json" >/dev/null 2>&1; then
      success "MCP registry JSON is valid"
    else
      error "MCP registry JSON is invalid"
      config_issues+=("Invalid MCP registry")
    fi
  else
    warning "MCP registry not found"
    config_issues+=("Missing MCP registry")
  fi

  # Check .agents directory structure
  local required_dirs=(".agents/runners" ".claude" "bin")
  for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
      success "Directory exists: $dir"
    else
      error "Missing directory: $dir"
      config_issues+=("Missing $dir")
      if [[ "$AUTO_FIX" == "true" ]]; then
        mkdir -p "$dir"
        success "Created directory: $dir"
      fi
    fi
  done

  # Check required scripts
  local required_scripts=("bin/safe_source_env.sh" "bin/select_or_key.sh")
  for script in "${required_scripts[@]}"; do
    if [[ -f "$script" && -x "$script" ]]; then
      success "Script exists and is executable: $script"
    else
      error "Script missing or not executable: $script"
      config_issues+=("Missing/non-executable $script")
    fi
  done

  if [[ ${#config_issues[@]} -gt 0 ]]; then
    warning "Configuration issues found: ${config_issues[*]}"
    return 1
  fi

  return 0
}


# Main diagnostic menu
show_menu() {
  echo
  echo -e "${PURPLE}=== OOS Diagnostic Wizard v$VERSION ===${NC}"
  echo
  echo "Select diagnostic tests to run:"
  echo "  1) System Dependencies"
  echo "  2) Environment Configuration"
  echo "  3) Network Connectivity"
  echo "  4) API Key Validation"
  echo "  5) MCP Server Health"
  echo "  6) Configuration Validation"
  echo "  7) Performance Profiling"
  echo "  8) Collect Diagnostic Logs"
  echo "  9) Run Self-Healing"
  echo " 10) Run All Tests"
  echo "  0) Exit"
  echo
}

# Interactive menu mode
interactive_mode() {
  while true; do
    show_menu
    read -p "Enter your choice [1-10, 0 to exit]: " -r choice

    case $choice in
      1) check_dependencies ;;
      2) check_env_files ;;
      3) check_network ;;
      4) check_api_keys ;;
      5) check_mcp_servers ;;
      6) validate_configuration ;;
      7) run_performance_tests ;;
      8) collect_logs ;;
      9) run_self_healing ;;
      10) run_all_tests ;;
      0) info "Exiting diagnostic wizard."; exit 0 ;;
      *) error "Invalid choice. Please enter a number between 0-10."
    esac

    echo
    if ! prompt_yes_no "Continue with more tests?" "y"; then
      break
    fi
  done
}

# Run all tests
run_all_tests() {
  local start_time=$(profile_start)
  local total_issues=0

  info "Running complete diagnostic suite..."
  echo

  check_dependencies || ((total_issues++))
  echo
  check_env_files || ((total_issues++))
  echo
  check_network || ((total_issues++))
  echo
  check_api_keys || ((total_issues++))
  echo
  check_mcp_servers || ((total_issues++))
  echo
  validate_configuration || ((total_issues++))
  echo
  run_self_healing
  echo

  if [[ "$PROFILE_MODE" == "true" ]]; then
    run_performance_tests
    echo
  fi

  collect_logs
  echo

  if [[ $total_issues -eq 0 ]]; then
    success "All diagnostic tests passed! System appears healthy."
  else
    warning "$total_issues test(s) found issues. Check the output above for details."
  fi

  profile_end "$start_time" "Complete diagnostic suite"
}

# Initialize diagnostic session
init_diagnostics() {
  cd "$PROJECT_ROOT"

  # Create log file
  : > "$LOG_FILE"
  log "=== OOS Diagnostic Session Started ==="
  log "Version: $VERSION"
  log "Timestamp: $TIMESTAMP"
  log "Working Directory: $PROJECT_ROOT"
  log "Command: $0 $*"

  success "Diagnostic wizard initialized"
  info "Log file: $LOG_FILE"

  if [[ "$VERBOSE" == "true" ]]; then
    info "Verbose mode enabled"
  fi

  if [[ "$AUTO_FIX" == "true" ]]; then
    info "Auto-fix mode enabled"
  fi

  if [[ "$PROFILE_MODE" == "true" ]]; then
    info "Performance profiling enabled"
  fi
}

# Main execution
main() {
  init_diagnostics

  if [[ "$AUTO_MODE" == "true" ]]; then
    run_all_tests
  else
    interactive_mode
  fi

  log "=== Diagnostic session completed ==="
}

# Error handling
trap 'error "Script interrupted"; exit 1' INT TERM

# Run main function
main "$@"