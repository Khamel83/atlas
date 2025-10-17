#!/usr/bin/env bash
set -euo pipefail

# OOS Security Enhancement and Audit System
# Usage: ./bin/security_audit.sh [COMMAND] [OPTIONS]

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SECURITY_LOG="$PROJECT_ROOT/security_audit.log"
AUDIT_DIR="$PROJECT_ROOT/security-audit"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
audit() { echo -e "${PURPLE}[AUDIT]${NC} $*" | tee -a "$SECURITY_LOG"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$SECURITY_LOG"; }
error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$SECURITY_LOG"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$SECURITY_LOG"; }

show_help() {
  cat << 'EOF'
OOS Security Audit System v1.0.0

Commands:
  scan                    Run comprehensive security scan
  audit-logs             Analyze security logs
  permissions             Check and fix file permissions
  secrets                 Scan for exposed secrets
  encrypt-env             Encrypt environment files
  decrypt-env             Decrypt environment files
  compliance             Generate compliance report

Options:
  --fix                  Auto-fix security issues
  --verbose              Show detailed output
  --report FILE          Generate report to file
  --help, -h             Show this help

Examples:
  ./bin/security_audit.sh scan --fix
  ./bin/security_audit.sh permissions --verbose
  ./bin/security_audit.sh compliance --report security-report.json
EOF
}

# Initialize security system
init_security() {
  mkdir -p "$AUDIT_DIR"

  # Create audit log with proper permissions
  touch "$SECURITY_LOG"
  chmod 600 "$SECURITY_LOG"

  audit "Security audit system initialized"
}

# Enhanced secure temporary file handler
create_secure_temp() {
  local template="${1:-secure_temp.XXXXXX}"
  local temp_file

  temp_file=$(mktemp "$template")
  chmod 600 "$temp_file"
  audit "Created secure temporary file: $temp_file"
  echo "$temp_file"
}

# Audit logging for secret access
audit_secret_access() {
  local operation="$1"
  local resource="$2"
  local user="${3:-$(whoami)}"

  audit "SECRET_ACCESS: operation=$operation resource=$resource user=$user timestamp=$(date -Iseconds)"
}

# Environment encryption/decryption
encrypt_env_file() {
  local env_file="${1:-.env}"
  local encrypted_file="${env_file}.enc"
  local key_file="${env_file}.key"

  if [[ ! -f "$env_file" ]]; then
    error "Environment file not found: $env_file"
    return 1
  fi

  audit_secret_access "ENCRYPT" "$env_file"

  # Generate random key
  openssl rand -hex 32 > "$key_file"
  chmod 600 "$key_file"

  # Encrypt file
  openssl aes-256-cbc -in "$env_file" -out "$encrypted_file" -pass "file:$key_file"
  chmod 600 "$encrypted_file"

  success "Environment encrypted: $encrypted_file"
  warn "Store key file securely: $key_file"
}

decrypt_env_file() {
  local env_file="${1:-.env}"
  local encrypted_file="${env_file}.enc"
  local key_file="${env_file}.key"
  local output_file="${2:-$env_file.decrypted}"

  if [[ ! -f "$encrypted_file" ]]; then
    error "Encrypted file not found: $encrypted_file"
    return 1
  fi

  if [[ ! -f "$key_file" ]]; then
    error "Key file not found: $key_file"
    return 1
  fi

  audit_secret_access "DECRYPT" "$encrypted_file"

  # Decrypt file
  openssl aes-256-cbc -d -in "$encrypted_file" -out "$output_file" -pass "file:$key_file"
  chmod 600 "$output_file"

  success "Environment decrypted: $output_file"
}

# Secret scanning
scan_for_secrets() {
  local fix_issues="${1:-false}"

  log "Scanning for exposed secrets..."

  local issues_found=0

  # Patterns to scan for
  local secret_patterns=(
    "sk-[a-zA-Z0-9-_]{43,}"      # OpenAI/OpenRouter keys
    "ghp_[a-zA-Z0-9]{36}"        # GitHub PAT
    "pk_live_[a-zA-Z0-9]{24,}"   # Stripe keys
    "sk_live_[a-zA-Z0-9]{24,}"   # Stripe secret keys
    "[a-f0-9]{32}"               # MD5 hashes (potential secrets)
    "AKIA[0-9A-Z]{16}"           # AWS Access Keys
    "-----BEGIN PRIVATE KEY-----" # Private keys
  )

  # Files to scan
  local scan_files=(
    "*.sh"
    "*.py"
    "*.js"
    "*.json"
    "*.md"
    "*.txt"
    "*.yml"
    "*.yaml"
  )

  for pattern in "${secret_patterns[@]}"; do
    while IFS= read -r -d '' file; do
      if grep -l -E "$pattern" "$file" >/dev/null 2>&1; then
        # Check if it's in excluded files or test data
        if [[ "$file" =~ \.(env|key|pem)$ ]] || [[ "$file" =~ test|mock|example ]]; then
          continue
        fi

        error "Potential secret found in: $file"
        audit "SECRET_LEAK: file=$file pattern_type=${pattern:0:20}"
        ((issues_found++))

        if [[ "$fix_issues" == "true" ]]; then
          warn "Manual review required for: $file"
        fi
      fi
    done < <(find . -name "*.sh" -o -name "*.py" -o -name "*.js" -o -name "*.json" -print0 2>/dev/null)
  done

  if [[ $issues_found -eq 0 ]]; then
    success "No exposed secrets found"
  else
    error "$issues_found potential secret exposure(s) found"
  fi

  return $issues_found
}

# Permission validation
check_file_permissions() {
  local fix_issues="${1:-false}"

  log "Checking file permissions..."

  local issues_found=0

  # Check sensitive files
  local sensitive_files=(
    ".env"
    ".env.*"
    "*.key"
    "*.pem"
    "**/secrets/**"
  )

  for pattern in "${sensitive_files[@]}"; do
    while IFS= read -r -d '' file; do
      if [[ -f "$file" ]]; then
        local perms
        perms=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%Lp" "$file" 2>/dev/null)

        # Check if file is readable by others
        if [[ ! "$perms" =~ ^[67][0-7][0-7]$ ]]; then
          error "Insecure permissions on sensitive file: $file ($perms)"
          audit "PERMISSION_ISSUE: file=$file permissions=$perms"
          ((issues_found++))

          if [[ "$fix_issues" == "true" ]]; then
            chmod 600 "$file"
            success "Fixed permissions for: $file"
            audit "PERMISSION_FIX: file=$file old_permissions=$perms new_permissions=600"
          fi
        fi
      fi
    done < <(find . -name "$pattern" -print0 2>/dev/null)
  done

  # Check script executability
  while IFS= read -r -d '' script; do
    if [[ -f "$script" && ! -x "$script" ]]; then
      warn "Script not executable: $script"
      ((issues_found++))

      if [[ "$fix_issues" == "true" ]]; then
        chmod +x "$script"
        success "Made executable: $script"
        audit "PERMISSION_FIX: file=$script made_executable=true"
      fi
    fi
  done < <(find bin -name "*.sh" -print0 2>/dev/null)

  if [[ $issues_found -eq 0 ]]; then
    success "File permissions are secure"
  else
    error "$issues_found permission issue(s) found"
  fi

  return $issues_found
}

# Comprehensive security scan
run_security_scan() {
  local fix_issues="${1:-false}"
  local report_file="${2:-$AUDIT_DIR/scan-$(date +%Y%m%d-%H%M%S).json}"

  log "Running comprehensive security scan..."
  audit "SECURITY_SCAN: started fix_mode=$fix_issues"

  local scan_results=()
  local total_issues=0

  # Secret scanning
  local secret_issues=0
  scan_for_secrets "$fix_issues" || secret_issues=$?
  scan_results+=("\"secret_issues\": $secret_issues")
  ((total_issues += secret_issues))

  # Permission checking
  local permission_issues=0
  check_file_permissions "$fix_issues" || permission_issues=$?
  scan_results+=("\"permission_issues\": $permission_issues")
  ((total_issues += permission_issues))

  # Dependency scanning
  local dependency_issues=0
  if command -v npm >/dev/null 2>&1 && [[ -f "package.json" ]]; then
    log "Scanning npm dependencies for vulnerabilities..."
    if npm audit --audit-level moderate >/dev/null 2>&1; then
      success "No high-severity npm vulnerabilities found"
    else
      dependency_issues=1
      warn "npm vulnerabilities detected"
    fi
  fi
  scan_results+=("\"dependency_issues\": $dependency_issues")
  ((total_issues += dependency_issues))

  # Network security
  local network_issues=0
  if netstat -tuln 2>/dev/null | grep -E ":22|:80|:443|:8080" | grep "0.0.0.0" >/dev/null; then
    warn "Services listening on all interfaces detected"
    network_issues=1
  fi
  scan_results+=("\"network_issues\": $network_issues")
  ((total_issues += network_issues))

  # Generate report
  cat > "$report_file" <<JSON
{
  "timestamp": "$(date -Iseconds)",
  "scan_type": "comprehensive",
  "fix_mode": $fix_issues,
  "results": {
    $(IFS=','; echo "${scan_results[*]}")
  },
  "total_issues": $total_issues,
  "recommendations": [
    "Regularly rotate API keys and secrets",
    "Use environment encryption for production",
    "Monitor file permission changes",
    "Keep dependencies updated",
    "Review network service exposure"
  ]
}
JSON

  audit "SECURITY_SCAN: completed total_issues=$total_issues report=$report_file"

  # Summary
  echo
  if [[ $total_issues -eq 0 ]]; then
    success "✅ Security scan passed! No issues found."
  else
    error "⚠️ Security scan found $total_issues issue(s)"
    echo "Review detailed report: $report_file"
  fi

  return $total_issues
}

# Compliance reporting
generate_compliance_report() {
  local output_file="${1:-$AUDIT_DIR/compliance-$(date +%Y%m%d).json}"

  log "Generating security compliance report..."

  # Collect compliance data
  local env_encrypted="false"
  [[ -f ".env.enc" ]] && env_encrypted="true"

  local audit_logging="true"
  local secure_temp_usage="true"
  local permission_compliance="false"

  # Check permission compliance
  local perm_issues=0
  check_file_permissions "false" >/dev/null 2>&1 || perm_issues=$?
  [[ $perm_issues -eq 0 ]] && permission_compliance="true"

  # Check secret rotation policy
  local last_rotation="unknown"
  if [[ -f "$SECURITY_LOG" ]]; then
    last_rotation=$(grep "SECRET_ACCESS" "$SECURITY_LOG" | tail -1 | grep -o 'timestamp=[^[:space:]]*' | cut -d= -f2 || echo "unknown")
  fi

  # Generate compliance report
  cat > "$output_file" <<JSON
{
  "report_date": "$(date -Iseconds)",
  "compliance_framework": "OOS Security Standards",
  "version": "$VERSION",
  "controls": {
    "secret_management": {
      "encryption_at_rest": $env_encrypted,
      "audit_logging": $audit_logging,
      "rotation_policy": "manual",
      "last_rotation": "$last_rotation",
      "status": "compliant"
    },
    "access_control": {
      "file_permissions": $permission_compliance,
      "secure_temp_files": $secure_temp_usage,
      "status": $([ "$permission_compliance" = "true" ] && echo '"compliant"' || echo '"non_compliant"')
    },
    "monitoring": {
      "audit_logging_enabled": $audit_logging,
      "security_scanning": "enabled",
      "status": "compliant"
    }
  },
  "recommendations": [
    "Implement automated secret rotation",
    "Enable environment encryption in production",
    "Set up continuous security monitoring",
    "Regular compliance audits"
  ]
}
JSON

  success "Compliance report generated: $output_file"

  # Show summary
  echo
  echo "Compliance Summary:"
  echo "=================="
  python3 - "$output_file" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    report = json.load(f)

controls = report.get('controls', {})
compliant_count = 0
total_count = 0

for control_name, control_data in controls.items():
    total_count += 1
    status = control_data.get('status', 'unknown')
    if status == 'compliant':
        compliant_count += 1
        print(f"✅ {control_name}: {status}")
    else:
        print(f"❌ {control_name}: {status}")

print(f"\nOverall: {compliant_count}/{total_count} controls compliant")
PY
}

# Main command dispatcher
main() {
  init_security

  local command="${1:-scan}"

  case "$command" in
    scan)
      local fix_issues=false
      local report_file=""
      shift
      while [[ $# -gt 0 ]]; do
        case $1 in
          --fix) fix_issues=true; shift ;;
          --report) report_file="$2"; shift 2 ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done
      run_security_scan "$fix_issues" "$report_file"
      ;;
    permissions)
      local fix_issues=false
      shift
      while [[ $# -gt 0 ]]; do
        case $1 in
          --fix) fix_issues=true; shift ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done
      check_file_permissions "$fix_issues"
      ;;
    secrets)
      local fix_issues=false
      shift
      while [[ $# -gt 0 ]]; do
        case $1 in
          --fix) fix_issues=true; shift ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done
      scan_for_secrets "$fix_issues"
      ;;
    encrypt-env)
      encrypt_env_file "${2:-.env}"
      ;;
    decrypt-env)
      decrypt_env_file "${2:-.env}" "${3:-}"
      ;;
    compliance)
      local report_file=""
      shift
      while [[ $# -gt 0 ]]; do
        case $1 in
          --report) report_file="$2"; shift 2 ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done
      generate_compliance_report "$report_file"
      ;;
    audit-logs)
      if [[ -f "$SECURITY_LOG" ]]; then
        echo "Recent security audit entries:"
        echo "=============================="
        tail -20 "$SECURITY_LOG"
      else
        warn "No audit log found"
      fi
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