# OOS Troubleshooting Guide

This guide provides solutions for common issues, diagnostic procedures, and recovery methods for the OOS system.

## 🚨 Emergency Quick Fixes

### System Completely Broken
```bash
# Stop all processes
pkill -f health_monitor
pkill -f key_rotator
pkill -f performance_monitor

# Reset to clean state
./scripts/scripts/bootstrap_enhanced.sh --reset-config --force

# Verify basic functionality
./bin/diagnose.sh --self-heal
```

### Can't Access 1Password
```bash
# Sign in again
eval "$(op signin)"

# Verify access
op item get "bootstrap-env" --vault "Private" --fields env

# If still failing, check account
op account list
op account use <account>
```

### Archon MCP Unreachable
```bash
# Check local Archon
curl -I http://localhost:8051/mcp

# If fails, try remote
export ARCHON_URL=https://archon.khamel.com:8051/mcp
curl -I $ARCHON_URL

# Update environment
echo "ARCHON_URL=$ARCHON_URL" >> .env
```

## 🔍 Common Issues & Solutions

### 1. Bootstrap Failures

#### Issue: "Dependencies missing"
```bash
# Symptoms
./scripts/scripts/bootstrap_enhanced.sh
ERROR: Required dependency not found: op

# Solution
# Install 1Password CLI
curl -sSfLo op.zip https://cache.agilebits.com/dist/1P/op2/pkg/v2.21.0/op_linux_amd64_v2.21.0.zip
unzip op.zip && sudo mv op /usr/local/bin/
op --version
```

#### Issue: "1Password authentication failed"
```bash
# Symptoms
OP authentication failed (exit code: 1)

# Diagnosis
op account list
eval "$(op signin)"

# Solutions
# 1. Sign in to correct account
op signin --account <your-account>

# 2. Check item exists
op item get "bootstrap-env" --vault "Private"

# 3. Verify field name
op item get "bootstrap-env" --vault "Private" --fields env
```

#### Issue: "Network connectivity issues"
```bash
# Symptoms
Failed to connect to github.com:443

# Diagnosis
./bin/diagnose.sh --check-network

# Solutions
# 1. Check internet connection
ping -c 3 8.8.8.8

# 2. Check DNS resolution
nslookup github.com

# 3. Check firewall/proxy
curl -I https://github.com
```

#### Issue: "Permission denied errors"
```bash
# Symptoms
./scripts/scripts/bootstrap_enhanced.sh: Permission denied

# Solutions
chmod +x ./scripts/scripts/bootstrap_enhanced.sh
chmod +x bin/*.sh

# Fix all permissions
./bin/security_audit.sh permissions --fix
```

### 2. Environment Issues

#### Issue: ".env file corruption"
```bash
# Symptoms
Environment file loads unsuccessfully

# Diagnosis
cat .env | hexdump -C | head -5  # Check for BOM/CRLF

# Solutions
# 1. Re-download from 1Password
op item get "bootstrap-env" --vault "Private" --fields env > .env.new
sed -i 's/\r$//' .env.new  # Remove CRLF
mv .env.new .env

# 2. Validate environment
./bin/safe_source_env.sh
```

#### Issue: "API key validation failures"
```bash
# Symptoms
OpenRouter key invalid/expired: sk-or-v1-...

# Diagnosis
./bin/key_rotator.sh validate --verbose

# Solutions
# 1. Check key format
echo $OPENROUTER_KEYS | tr ',' '\n'

# 2. Test keys individually
curl -H "Authorization: Bearer sk-or-v1-..." https://openrouter.ai/api/v1/models

# 3. Rotate to working key
./bin/key_rotator.sh rotate
```

#### Issue: "Environment variable not found"
```bash
# Symptoms
Required variable: OPENROUTER_KEYS not found

# Diagnosis
source .env && echo $OPENROUTER_KEYS

# Solutions
# 1. Check .env file
grep OPENROUTER_KEYS .env

# 2. Re-generate environment
./bin/safe_source_env.sh
./bin/select_or_key.sh
```

### 3. Legacy Issues (Still Relevant)

#### 1) GitHub push blocked: secrets detected
**Symptom:**
```
GH013: Push cannot contain secrets … path: .env:XX
```

**Fix:**
```bash
sudo apt install -y git-filter-repo || python3 -m pip install --user git-filter-repo
git filter-repo --force --path .env --path .env.active --path .env.export --invert-paths
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin --force HEAD:master
```

Rotate any exposed tokens in providers. Keep `.env*` out of git (see `.gitignore`).

#### 2) 1Password: "not signed in" or session lost
```bash
eval "$(op signin)" && op whoami
```

#### 3) Bad env value (common)
- `GITHUB_PAT=...: No such file or directory` inside your 1Password env field.
- Remove trailing error text; keep a single line: `GITHUB_PAT=ghp_xxx` or leave empty.

#### 4) CRLF/BOM issues
**Symptom:**
```
.env: line N: $'\r': command not found
```

**Fix:**
```bash
sed -i 's/\r$//' .env
perl -i -pe 's/^\xEF\xBB\xBF//' .env
```

#### 5) Archon unreachable
- **Local:**
  ```bash
  curl -4 -I http://localhost:8051/mcp
  ```

- **Remote:**
  ```bash
  curl -4 -I https://archon.yourhost:8051/mcp
  ```

Check firewall, TLS, and that Uvicorn is running on 8051.

#### 6) MCPs missing in Claude
At project root:
```bash
claude mcp remove archon || true
claude mcp add --transport http archon $(grep '^ARCHON_URL=' .env.export | cut -d= -f2)
claude mcp list
```

#### 7) OpenRouter 401/429
- Use rotation: `OPENROUTER_KEYS=sk1,sk2,sk3`
- Rerun: `.agents/runners/run_claude.sh` (selector picks first working key).

### 4. MCP Connection Issues

#### Issue: "Archon MCP health check failed"
```bash
# Symptoms
[2025-09-02 14:20:26] Archon MCP health check failed: HTTP 000000

# Diagnosis
curl -v http://localhost:8051/mcp
./bin/mcp_manager.sh test archon --verbose

# Solutions
# 1. Check if Archon is running
ps aux | grep archon
netstat -tlnp | grep 8051

# 2. Try different URL
export ARCHON_URL=https://archon.khamel.com:8051/mcp
./bin/mcp_manager.sh test archon

# 3. Update MCP configuration
./bin/mcp_manager.sh remove archon
./bin/mcp_manager.sh add archon $ARCHON_URL
```

#### Issue: "Context7 MCP unreachable"
```bash
# Symptoms
Context7 MCP server unreachable

# Solutions
# 1. Check internet connectivity
curl -I https://context7.liam.sh/mcp

# 2. Update server configuration
./bin/mcp_manager.sh test context7 --timeout 30

# 3. Remove if consistently failing
./bin/mcp_manager.sh remove context7
```

### 5. Performance Issues

#### Issue: "Scripts running slowly"
```bash
# Symptoms
Bootstrap taking >5 minutes to complete

# Diagnosis
./bin/performance_monitor.sh profile ./scripts/scripts/bootstrap_enhanced.sh

# Solutions
# 1. Check system resources
./bin/performance_monitor.sh monitor --duration 60

# 2. Optimize environment
./bin/performance_monitor.sh optimize

# 3. Check for hanging processes
ps aux | grep -E "(curl|op|git)"
```

#### Issue: "High memory usage"
```bash
# Symptoms
System running out of memory

# Diagnosis
free -h
./bin/performance_monitor.sh monitor --interval 5 --duration 60

# Solutions
# 1. Kill memory-intensive processes
./bin/health_monitor.sh stop
pkill -f performance_monitor

# 2. Clean up temporary files
./bin/diagnose.sh --cleanup

# 3. Restart monitoring with lower frequency
./bin/health_monitor.sh daemon --interval 300
```

### 6. Security Issues

#### Issue: "Exposed secrets detected"
```bash
# Symptoms
Potential secret found in: script.sh

# Diagnosis
./bin/security_audit.sh secrets --verbose

# Solutions
# 1. Remove secrets from files
git filter-repo --path script.sh --invert-paths

# 2. Add to .gitignore
echo "*.env*" >> .gitignore
echo "*.key" >> .gitignore

# 3. Encrypt sensitive files
./bin/security_audit.sh encrypt-env .env
```

#### Issue: "File permission violations"
```bash
# Symptoms
Insecure permissions on sensitive file: .env (644)

# Solutions
# Auto-fix permissions
./bin/security_audit.sh permissions --fix

# Manual fix
chmod 600 .env*
chmod 600 *.key
chmod +x bin/*.sh
```

### 7. Testing Failures

#### Issue: "Test suite failures"
```bash
# Symptoms
Unit tests failing: 5/10 passed

# Diagnosis
./bin/run_tests.sh unit --verbose

# Solutions
# 1. Reset test environment
./bin/run_tests.sh reset

# 2. Run specific failing test
./bin/run_tests.sh unit --filter test_bootstrap

# 3. Update test data
./bin/run_tests.sh unit --update-fixtures
```

#### Issue: "Security tests failing"
```bash
# Symptoms
Security scan found 3 issue(s)

# Solutions
# 1. Run security scan with fixes
./bin/security_audit.sh scan --fix

# 2. Review specific issues
./bin/security_audit.sh secrets
./bin/security_audit.sh permissions

# 3. Update security baseline
./bin/run_tests.sh security --update-baseline
```

## 🔧 Advanced Troubleshooting

### Log Analysis

#### System Logs
```bash
# View recent diagnostic logs
tail -f diagnostic.log

# Health monitoring logs
tail -f health_monitor.log

# Security audit logs
tail -f security_audit.log

# Performance logs
tail -f performance.log

# All logs with timestamps
tail -f *.log | grep "$(date +%Y-%m-%d)"
```

#### Log Parsing
```bash
# Find errors in logs
grep -i error *.log

# Find specific timeframe
grep "2025-09-02 14:" *.log

# Count error types
grep -i error *.log | cut -d: -f3 | sort | uniq -c

# Performance issues
grep "SLOW" performance.log
```

#### Diagnostic Collection
```bash
# Collect comprehensive diagnostics
./bin/diagnose.sh --collect-logs

# This creates: diagnostic_logs_YYYYMMDD_HHMMSS/
# Contains:
# - All log files
# - System information
# - Configuration files (sanitized)
# - Network diagnostics
# - Process information
```

### Getting Help

#### Self-Diagnosis
```bash
# Run comprehensive diagnostics
./bin/diagnose.sh --collect-logs

# Check system health
./bin/health_monitor.sh check --verbose

# Performance analysis
./bin/performance_monitor.sh report --output html > performance-report.html

# Security audit
./bin/security_audit.sh compliance --report compliance.json
```

#### Support Information

When seeking help, collect this information:

1. **System Information**
   ```bash
   uname -a
   cat /etc/os-release
   ```

2. **OOS Version and State**
   ```bash
   git log --oneline -5
   ls -la bin/
   ```

3. **Environment Status**
   ```bash
   ./bin/diagnose.sh --output diagnosis.json
   ```

4. **Recent Logs**
   ```bash
   tail -100 *.log > recent-logs.txt
   ```

5. **Configuration (sanitized)**
   ```bash
   grep -v -E "(KEY|TOKEN|SECRET)" .env > .env.sanitized
   ```

---

This troubleshooting guide covers both legacy issues and new comprehensive diagnostic capabilities for the enhanced OOS system.