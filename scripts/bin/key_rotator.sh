#!/usr/bin/env bash
set -euo pipefail

# OOS Automated OpenRouter Key Rotation and Management
# Usage: ./bin/key_rotator.sh [COMMAND] [OPTIONS]

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KEY_LOG="$PROJECT_ROOT/key_rotation.log"
KEY_ANALYTICS_DIR="$PROJECT_ROOT/key-analytics"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$KEY_LOG"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$KEY_LOG"; }
error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$KEY_LOG"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$KEY_LOG"; }

show_help() {
  cat << 'EOF'
OOS Key Rotation Manager v1.0.0

Commands:
  status                  Show current key status and analytics
  rotate                 Rotate to next available key
  validate               Validate all configured keys
  analytics              Generate key usage analytics
  monitor                Start continuous monitoring
  alert-setup            Configure alerting for key issues
  dashboard              Show key management dashboard

Options:
  --daemon               Run as background service
  --interval SECONDS     Check interval for monitoring (default: 300)
  --threshold PERCENT    Rate limit threshold for alerts (default: 80)
  --verbose              Show detailed output
  --help, -h             Show this help

Examples:
  ./bin/key_rotator.sh status --verbose
  ./bin/key_rotator.sh monitor --daemon --interval 180
  ./bin/key_rotator.sh analytics --report key-report.json
EOF
}

# Initialize key management system
init_key_management() {
  mkdir -p "$KEY_ANALYTICS_DIR"
  touch "$KEY_LOG"
  chmod 600 "$KEY_LOG"
}

# Enhanced key validation with rate limit detection
validate_key() {
  local key="$1"
  local verbose="${2:-false}"

  [[ "$verbose" == "true" ]] && log "Validating key: ${key:0:10}..."

  local start_time=$(date +%s%N)

  # Make API call with detailed response
  local response_file
  response_file=$(mktemp)

  local http_code
  http_code=$(curl -sS -w "%{http_code}" \
    --connect-timeout 10 --max-time 30 \
    -H "Authorization: Bearer $key" \
    -H "User-Agent: OOS-KeyRotator/$VERSION" \
    -o "$response_file" \
    https://openrouter.ai/api/v1/models 2>/dev/null || echo "000")

  local end_time=$(date +%s%N)
  local response_time_ms=$(( (end_time - start_time) / 1000000 ))

  local validation_result="{\n"
  validation_result+="  \"key_prefix\": \"${key:0:10}...\",\n"
  validation_result+="  \"http_code\": \"$http_code\",\n"
  validation_result+="  \"response_time_ms\": $response_time_ms,\n"
  validation_result+="  \"timestamp\": \"$(date -Iseconds)\",\n"

  case "$http_code" in
    "200")
      validation_result+="  \"status\": \"valid\",\n"
      validation_result+="  \"message\": \"Key is working\"\n"
      local rate_limit_remaining
      rate_limit_remaining=$(grep -i 'x-ratelimit-remaining' < <(curl -sS -I -H "Authorization: Bearer $key" https://openrouter.ai/api/v1/models 2>/dev/null) | cut -d: -f2 | tr -d ' \r\n' 2>/dev/null || echo "unknown")
      if [[ "$rate_limit_remaining" != "unknown" ]]; then
        validation_result+=",\n  \"rate_limit_remaining\": \"$rate_limit_remaining\"\n"
      fi
      ;;
    "401")
      validation_result+="  \"status\": \"invalid\",\n"
      validation_result+="  \"message\": \"Invalid or expired key\"\n"
      ;;
    "429")
      validation_result+="  \"status\": \"rate_limited\",\n"
      validation_result+="  \"message\": \"Rate limit exceeded\"\n"
      local retry_after
      retry_after=$(grep -i 'retry-after' < <(curl -sS -I -H "Authorization: Bearer $key" https://openrouter.ai/api/v1/models 2>/dev/null) | cut -d: -f2 | tr -d ' \r\n' 2>/dev/null || echo "unknown")
      if [[ "$retry_after" != "unknown" ]]; then
        validation_result+=",\n  \"retry_after_seconds\": \"$retry_after\"\n"
      fi
      ;;
    *)
      validation_result+="  \"status\": \"error\",\n"
      validation_result+="  \"message\": \"HTTP $http_code or network error\"\n"
      ;;
  esac

  validation_result+="}\n"

  rm -f "$response_file"

  echo -e "$validation_result"
}

# Validate all keys and generate report
validate_all_keys() {
  local env_file="${1:-.env}"
  local report_file="$KEY_ANALYTICS_DIR/validation-$(date +%Y%m%d-%H%M%S).json"

  log "Validating all OpenRouter keys..."

  if [[ ! -f "$env_file" ]]; then
    error "Environment file not found: $env_file"
    return 1
  fi

  # Extract keys
  local keys_line
  keys_line=$(grep -E '^OPENROUTER_KEYS=' "$env_file" | head -1)

  if [[ -z "$keys_line" ]]; then
    error "No OPENROUTER_KEYS found in $env_file"
    return 1
  fi

  local keys_value="${keys_line#*=}"
  keys_value=$(echo "$keys_value" | tr -d '"')"

  IFS=',' read -ra KEYS <<< "$keys_value"

  local validation_results=()\n  local valid_count=0\n  local total_count=${#KEYS[@]}\n
  for i in "${!KEYS[@]}"; do
    local key="${KEYS[$i]}"
    key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [[ -n "$key" ]]; then
      log "Validating key $((i+1))/$total_count..."
      local result\n      result=$(validate_key "$key" "true")
      validation_results+=("$result")\n
      local status\n      status=$(echo "$result" | grep '"status"' | cut -d'"' -f4)
      [[ "$status" == "valid" ]] && ((valid_count++))
    fi
  done

  # Generate comprehensive report
  cat > "$report_file" <<JSON
{
  "timestamp": "$(date -Iseconds)",
  "total_keys": $total_count,
  "valid_keys": $valid_count,
  "invalid_keys": $((total_count - valid_count)),
  "validation_results": [
    $(IFS=','; echo "${validation_results[*]}")
  ]
}
JSON

  success "Validation report: $report_file"

  # Show summary
  echo
  echo "Key Validation Summary:"
  echo "======================"
  echo "Total Keys: $total_count"
  echo "Valid Keys: $valid_count"
  echo "Success Rate: $(( valid_count * 100 / total_count ))%"

  if [[ $valid_count -eq 0 ]]; then
    error "No working keys found!"
    return 1
  else
    success "$valid_count/$total_count keys are working"
  fi
}

# Smart key rotation with failover
smart_rotate() {
  local env_file="${1:-.env}"
  local active_file="${2:-.env.active}"

  log "Starting smart key rotation..."

  # Validate current key first
  local current_key=""
  if [[ -f "$active_file" ]]; then
    current_key=$(grep -E '^OPENAI_API_KEY=' "$active_file" | cut -d= -f2- || echo "")
  fi

  if [[ -n "$current_key" ]]; then
    log "Checking current key health..."
    local current_validation
    current_validation=$(validate_key "$current_key" "false")
    local current_status
    current_status=$(echo "$current_validation" | grep '"status"' | cut -d'"' -f4)

    if [[ "$current_status" == "valid" ]]; then
      success "Current key is still healthy, no rotation needed"
      return 0
    else
      warn "Current key is $current_status, rotating..."
    fi
  fi

  # Find next working key
  local keys_line
  keys_line=$(grep -E '^OPENROUTER_KEYS=' "$env_file" | head -1)
  local keys_value="${keys_line#*=}"
  keys_value=$(echo "$keys_value" | tr -d '"')

  IFS=',' read -ra KEYS <<< "$keys_value"

  for i in "${!KEYS[@]}"; do
    local key="${KEYS[$i]}"
    key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [[ -n "$key" && "$key" != "$current_key" ]]; then
      log "Testing key candidate $((i+1))..."
      local validation_result
      validation_result=$(validate_key "$key" "false")
      local status
      status=$(echo "$validation_result" | grep '"status"' | cut -d'"' -f4)

      if [[ "$status" == "valid" ]]; then
        # Rotate to this key
        echo "OPENAI_API_KEY=$key" > "$active_file"
        chmod 600 "$active_file"
        success "Rotated to working key: ${key:0:10}..."

        # Log rotation event
        echo "[$(date -Iseconds)] ROTATION: from=${current_key:0:10}... to=${key:0:10}... reason=failover" >> "$KEY_LOG"
        return 0
      fi
    fi
  done

  error "No working keys available for rotation!"
  return 1
}

# Generate key usage analytics
generate_analytics() {
  local report_file="${1:-$KEY_ANALYTICS_DIR/analytics-$(date +%Y%m%d).json}"

  log "Generating key usage analytics..."

  # Analyze rotation log
  local rotation_count=0
  local last_rotation="never"

  if [[ -f "$KEY_LOG" ]]; then
    rotation_count=$(grep -c "ROTATION:" "$KEY_LOG" 2>/dev/null || echo "0")
    last_rotation=$(grep "ROTATION:" "$KEY_LOG" | tail -1 | grep -o '\\[[^\\]]*\\]' | tr -d '[]' 2>/dev/null || echo "never")
  fi

  # Get current key status
  local current_key_status="unknown"
  if [[ -f ".env.active" ]]; then
    local active_key
    active_key=$(grep -E '^OPENAI_API_KEY=' ".env.active" | cut -d= -f2-)
    if [[ -n "$active_key" ]]; then
      local validation
      validation=$(validate_key "$active_key" "false")
      current_key_status=$(echo "$validation" | grep '"status"' | cut -d'"' -f4)
    fi
  fi

  # Generate report
  cat > "$report_file" <<JSON
{
  "timestamp": "$(date -Iseconds)",
  "analytics_period": "all_time",
  "key_rotation": {
    "total_rotations": $rotation_count,
    "last_rotation": "$last_rotation",
    "rotation_frequency": "$(if [[ $rotation_count -gt 0 ]]; then echo "active"; else echo "inactive"; fi)"
  },
  "current_status": {
    "active_key_status": "$current_key_status",
    "monitoring_enabled": $(if pgrep -f "key_rotator.*monitor" >/dev/null; then echo "true"; else echo "false"; fi)
  },
  "recommendations": [
    $(if [[ "$current_key_status" != "valid" ]]; then echo '"Rotate to working key",'; fi)
    $(if [[ $rotation_count -eq 0 ]]; then echo '"Set up automated rotation",'; fi)
    "Monitor key usage regularly",
    "Keep backup keys ready"
  ]
}
JSON

  success "Analytics report: $report_file"

  # Show key insights
  echo
  echo "Key Management Analytics:"
  echo "========================"
  echo "Total Rotations: $rotation_count"
  echo "Last Rotation: $last_rotation"
  echo "Current Key Status: $current_key_status"
  echo "Monitoring: $(if pgrep -f "key_rotator.*monitor" >/dev/null; then echo "Active"; else echo "Inactive"; fi)"
}

# Continuous monitoring
monitor_keys() {
  local interval="${1:-300}"
  local daemon_mode="${2:-false}"
  local rate_threshold="${3:-80}"

  if [[ "$daemon_mode" == "true" ]]; then
    log "Starting key monitoring daemon (interval: ${interval}s)"

    # Check if already running
    if pgrep -f "key_rotator.*monitor.*daemon" >/dev/null; then
      warn "Key monitoring daemon already running"
      return 1
    fi

    # Start as daemon
    nohup "$0" monitor --interval "$interval" --threshold "$rate_threshold" >"$KEY_ANALYTICS_DIR/monitor.log" 2>&1 &
    local daemon_pid=$!
    echo "$daemon_pid" > "$KEY_ANALYTICS_DIR/monitor.pid"
    success "Key monitoring daemon started (PID: $daemon_pid)"
    return 0
  fi

  log "Starting continuous key monitoring..."
  log "Check interval: ${interval}s, Rate threshold: ${rate_threshold}%"

  while true; do
    local check_time=$(date -Iseconds)

    # Validate current active key
    if [[ -f ".env.active" ]]; then
      local active_key
      active_key=$(grep -E '^OPENAI_API_KEY=' ".env.active" | cut -d= -f2- 2>/dev/null || echo "")

      if [[ -n "$active_key" ]]; then
        local validation
        validation=$(validate_key "$active_key" "false")
        local status
        status=$(echo "$validation" | grep '"status"' | cut -d'"' -f4)

        case "$status" in
          "valid")
            log "Key health check: OK"
            ;;
          "rate_limited")
            warn "Key rate limited - attempting rotation"
            smart_rotate
            ;;
          "invalid")
            error "Key invalid - attempting rotation"
            smart_rotate
            ;;
          *)
            warn "Key status: $status"
            ;;
        esac
      fi
    fi

    sleep "$interval"
  done
}

# Show key dashboard
show_dashboard() {
  clear
  echo -e "${PURPLE}OOS Key Management Dashboard${NC}"
  echo -e "${PURPLE}==============================${NC}"
  echo

  # Current status
  local active_key_status="No active key"
  if [[ -f ".env.active" ]]; then
    local active_key
    active_key=$(grep -E '^OPENAI_API_KEY=' ".env.active" | cut -d= -f2- 2>/dev/null || echo "")
    if [[ -n "$active_key" ]]; then
      local validation
      validation=$(validate_key "$active_key" "false")
      local status
      status=$(echo "$validation" | grep '"status"' | cut -d'"' -f4)
      active_key_status="${active_key:0:10}... ($status)"
    fi
  fi

  echo -e "${BLUE}Active Key:${NC} $active_key_status"

  # Key count
  local total_keys=0
  if [[ -f ".env" ]]; then
    local keys_line\n    keys_line=$(grep -E '^OPENROUTER_KEYS=' ".env" | head -1)
    if [[ -n "$keys_line" ]]; then
      local keys_value="${keys_line#*=}"
      keys_value=$(echo "$keys_value" | tr -d '"')
      IFS=',' read -ra KEYS <<< "$keys_value"
      total_keys=${#KEYS[@]}
    fi
  fi

  echo -e "${BLUE}Total Keys:${NC} $total_keys"

  # Monitoring status
  local monitoring_status="Inactive"
  if pgrep -f "key_rotator.*monitor" >/dev/null; then
    monitoring_status="Active"
  fi
  echo -e "${BLUE}Monitoring:${NC} $monitoring_status"

  # Recent rotations
  local last_rotation="Never"
  if [[ -f "$KEY_LOG" ]]; then
    last_rotation=$(grep "ROTATION:" "$KEY_LOG" | tail -1 | grep -o '\\[[^\\]]*\\]' | tr -d '[]' 2>/dev/null || echo "Never")
  fi
  echo -e "${BLUE}Last Rotation:${NC} $last_rotation"

  echo
  echo -e "${CYAN}Quick Actions:${NC}"
  echo "  r) Rotate keys"
  echo "  v) Validate all keys"
  echo "  m) Start monitoring"
  echo "  q) Quit"
}

# Main command dispatcher
main() {
  init_key_management

  local command="${1:-status}"

  case "$command" in
    status)\n      show_dashboard
      ;;\n    validate)\n      validate_all_keys "${2:-.env}"
      ;;\n    rotate)\n      smart_rotate "${2:-.env}" "${3:-.env.active}"
      ;;\n    analytics)\n      local report_file=""
      shift
      while [[ $# -gt 0 ]]; do
        case $1 in
          --report) report_file="$2"; shift 2 ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done
      generate_analytics "$report_file"
      ;;\n    monitor)\n      local interval=300
      local daemon_mode=false
      local threshold=80

      shift
      while [[ $# -gt 0 ]]; do
        case $1 in
          --daemon) daemon_mode=true; shift ;;
          --interval) interval="$2"; shift 2 ;;
          --threshold) threshold="$2"; shift 2 ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done

      monitor_keys "$interval" "$daemon_mode" "$threshold"
      ;;\n    dashboard)\n      while true; do\n        show_dashboard\n        read -n 1 -s choice\n        case "$choice" in\n          r) smart_rotate; sleep 2 ;;\n          v) validate_all_keys; sleep 3 ;;\n          m) monitor_keys 60 true; sleep 2 ;;\n          q) break ;;\n        esac\n      done\n      ;;\n    help|--help|-h)\n      show_help
      ;;\n    *)\n      error "Unknown command: $command"
      show_help
      exit 1
      ;;\n  esac\n}

main "$@"