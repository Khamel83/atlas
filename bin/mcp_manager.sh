#!/usr/bin/env bash
set -euo pipefail

# OOS MCP Configuration Management System
# Usage: ./bin/mcp_manager.sh [COMMAND] [OPTIONS]

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MCP_REGISTRY="$HOME/.mcp/registry.json"
MCP_PROFILES_DIR="$HOME/.mcp/profiles"
MCP_BACKUP_DIR="$HOME/.mcp/backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }

show_help() {
  cat << 'EOF'
OOS MCP Configuration Manager v1.0.0

Commands:
  list                    List configured MCP servers
  add NAME URL            Add new MCP server
  remove NAME             Remove MCP server
  test NAME               Test MCP server connection
  backup                  Backup MCP configuration
  restore BACKUP          Restore from backup
  profiles                Manage configuration profiles
  sync                    Sync with remote MCP registry
  health                  Check all MCP server health

Options:
  --profile NAME          Use specific profile
  --timeout SECONDS       Connection timeout (default: 10)
  --verbose              Show detailed output
  --help, -h             Show this help

Examples:
  ./bin/mcp_manager.sh add archon http://localhost:8051/mcp
  ./bin/mcp_manager.sh test archon --verbose
  ./bin/mcp_manager.sh health --profile development
EOF
}

# Initialize MCP management
init_mcp_management() {
  mkdir -p "$(dirname "$MCP_REGISTRY")" "$MCP_PROFILES_DIR" "$MCP_BACKUP_DIR"

  if [[ ! -f "$MCP_REGISTRY" ]]; then
    cat > "$MCP_REGISTRY" <<'JSON'
{
  "version": "1.0.0",
  "servers": {},
  "profiles": {
    "default": {
      "active_servers": []
    }
  },
  "last_updated": ""
}
JSON
  fi
}

# Enhanced MCP health check with retry
test_mcp_server() {
  local name="$1"
  local timeout="${2:-10}"
  local verbose="${3:-false}"

  if [[ ! -f "$MCP_REGISTRY" ]]; then
    error "MCP registry not found"
    return 1
  fi

  local server_info
  server_info=$(python3 - "$name" <<'PY'
import json
import sys
import os

name = sys.argv[1]
registry_file = os.environ.get('MCP_REGISTRY')

with open(registry_file) as f:
    registry = json.load(f)

servers = registry.get('servers', {})
if name not in servers:
    print(f"ERROR: Server '{name}' not found")
    sys.exit(1)

print(json.dumps(servers[name]))
PY
  )

  if [[ $? -ne 0 ]]; then
    error "$server_info"
    return 1
  fi

  local url transport
  url=$(echo "$server_info" | python3 -c "import sys, json; info=json.load(sys.stdin); print(info.get('url', ''))")
  transport=$(echo "$server_info" | python3 -c "import sys, json; info=json.load(sys.stdin); print(info.get('transport', 'http'))")

  [[ "$verbose" == "true" ]] && log "Testing $name ($transport): $url"

  case "$transport" in
    "http")
      local response
      response=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout "$timeout" --max-time "$((timeout * 2))" "$url" 2>/dev/null || echo "000")

      if [[ "$response" == "200" ]] || [[ "$response" == "405" ]]; then
        success "$name is healthy (HTTP $response)"
        return 0
      else
        error "$name is unhealthy (HTTP $response)"
        return 1
      fi
      ;;
    *)
      warn "Unsupported transport type: $transport"
      return 1
      ;;
  esac
}

# Check health of all servers
check_all_health() {
  local profile="${1:-default}"
  local timeout="${2:-10}"

  log "Checking health of all MCP servers (profile: $profile)..."

  if [[ ! -f "$MCP_REGISTRY" ]]; then
    error "MCP registry not found"
    return 1
  fi

  local server_list
  server_list=$(python3 - "$profile" <<'PY'
import json
import sys
import os

profile = sys.argv[1]
registry_file = os.environ.get('MCP_REGISTRY')

with open(registry_file) as f:
    registry = json.load(f)

servers = registry.get('servers', {})
profiles = registry.get('profiles', {})

if profile in profiles:
    active_servers = profiles[profile].get('active_servers', [])
    if active_servers:
        for server in active_servers:
            if server in servers:
                print(server)
    else:
        # If no active servers specified, use all
        for server in servers.keys():
            print(server)
else:
    # Use all servers if profile not found
    for server in servers.keys():
        print(server)
PY
  )

  local healthy=0
  local total=0

  while IFS= read -r server_name; do
    if [[ -n "$server_name" ]]; then
      ((total++))
      if test_mcp_server "$server_name" "$timeout" "false"; then
        ((healthy++))
      fi
    fi
  done <<< "$server_list"

  echo
  if [[ $healthy -eq $total ]]; then
    success "All MCP servers healthy ($healthy/$total)"
    return 0
  else
    error "Some MCP servers unhealthy ($healthy/$total)"
    return 1
  fi
}

# Auto-discovery of MCP servers
discover_mcp_servers() {
  log "Discovering available MCP servers..."

  # Check common MCP endpoints
  local common_endpoints=(
    "archon:http://localhost:8051/mcp"
    "context7:https://context7.liam.sh/mcp"
    "filesystem:command:npx:-y:@modelcontextprotocol/server-filesystem"
  )

  local discovered=()

  for endpoint in "${common_endpoints[@]}"; do
    local name=${endpoint%%:*}
    local url=${endpoint#*:}

    if [[ "$url" =~ ^http ]]; then
      log "Testing $name at $url..."
      if curl -sS -o /dev/null --connect-timeout 5 --max-time 10 "$url" 2>/dev/null; then
        discovered+=("$name:$url")
        success "Found: $name"
      fi
    fi
  done

  if [[ ${#discovered[@]} -gt 0 ]]; then
    echo
    echo "Discovered MCP servers:"
    for server in "${discovered[@]}"; do
      echo "  ${server%:*} -> ${server#*:}"
    done
  else
    warn "No MCP servers discovered"
  fi
}

# Configuration backup and restore
backup_mcp_config() {
  local backup_name="backup-$(date +%Y%m%d-%H%M%S).json"
  local backup_file="$MCP_BACKUP_DIR/$backup_name"

  if [[ ! -f "$MCP_REGISTRY" ]]; then
    error "No MCP registry to backup"
    return 1
  fi

  cp "$MCP_REGISTRY" "$backup_file"
  success "MCP configuration backed up to: $backup_file"
  echo "$backup_file"
}

restore_mcp_config() {
  local backup_file="$1"

  if [[ ! -f "$backup_file" ]]; then
    error "Backup file not found: $backup_file"
    return 1
  fi

  # Validate backup file
  if ! python3 -m json.tool "$backup_file" >/dev/null 2>&1; then
    error "Invalid JSON in backup file"
    return 1
  fi

  # Create current backup before restore
  local current_backup
  current_backup=$(backup_mcp_config)

  # Restore
  cp "$backup_file" "$MCP_REGISTRY"
  success "MCP configuration restored from: $backup_file"
  log "Previous config backed up to: $current_backup"
}

# Profile management
manage_profiles() {
  local action="${1:-list}"
  local profile_name="${2:-}"

  case "$action" in
    "list")
      log "Available MCP profiles:"
      python3 - <<'PY'
import json
import sys
import os

registry_file = os.environ.get('MCP_REGISTRY')
with open(registry_file) as f:
    registry = json.load(f)

profiles = registry.get('profiles', {})
for name, config in profiles.items():
    active_count = len(config.get('active_servers', []))
    print(f"  📁 {name} ({active_count} servers)")
PY
      ;;
    "create")
      if [[ -z "$profile_name" ]]; then
        error "Profile name required"
        return 1
      fi

      python3 - "$profile_name" <<'PY'
import json
import sys
import os

profile_name = sys.argv[1]
registry_file = os.environ.get('MCP_REGISTRY')

with open(registry_file) as f:
    registry = json.load(f)

profiles = registry.setdefault('profiles', {})
profiles[profile_name] = {
    'active_servers': [],
    'created_at': f"{__import__('datetime').datetime.now().isoformat()}"
}

with open(registry_file, 'w') as f:
    json.dump(registry, f, indent=2)
PY

      success "Profile '$profile_name' created"
      ;;
    *)
      error "Unknown profile action: $action"
      return 1
      ;;
  esac
}

# Main command dispatcher
main() {
  init_mcp_management

  local command="${1:-list}"

  case "$command" in
    list)
      if [[ -f "$MCP_REGISTRY" ]]; then
        log "Configured MCP servers:"
        python3 - <<'PY'
import json
import sys
import os

registry_file = os.environ.get('MCP_REGISTRY')
with open(registry_file) as f:
    registry = json.load(f)

servers = registry.get('servers', {})
if not servers:
    print("  No MCP servers configured")
else:
    for name, config in servers.items():
        transport = config.get('transport', 'unknown')
        url = config.get('url', config.get('command', 'N/A'))
        print(f"  🔌 {name} ({transport}): {url}")
PY
      else
        warn "No MCP registry found"
      fi
      ;;
    test)
      if [[ $# -lt 2 ]]; then
        error "Usage: test SERVER_NAME [--timeout SECONDS]"
        exit 1
      fi

      local server_name="$2"
      local timeout=10
      local verbose=false

      shift 2
      while [[ $# -gt 0 ]]; do
        case $1 in
          --timeout) timeout="$2"; shift 2 ;;
          --verbose) verbose=true; shift ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done

      test_mcp_server "$server_name" "$timeout" "$verbose"
      ;;
    health)
      local profile="default"
      local timeout=10

      shift
      while [[ $# -gt 0 ]]; do
        case $1 in
          --profile) profile="$2"; shift 2 ;;
          --timeout) timeout="$2"; shift 2 ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done

      check_all_health "$profile" "$timeout"
      ;;
    backup)
      backup_mcp_config
      ;;
    discover)
      discover_mcp_servers
      ;;
    profiles)
      manage_profiles "${2:-list}" "${3:-}"
      ;;
    help|--help|-h)
      show_help
      ;;
    *)
      error "Unknown command: $command"
      show_help
      exit 1
      ;;
  esac
}

main "$@"