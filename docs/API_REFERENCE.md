# OOS API Reference - Complete Tool Documentation

This reference provides comprehensive documentation for all OOS tools, their commands, options, and integration patterns.

## 📋 Table of Contents

1. [Bootstrap System](#bootstrap-system)
2. [Diagnostics System](#diagnostics-system)
3. [Health Monitoring](#health-monitoring)
4. [Testing Framework](#testing-framework)
5. [Template Management](#template-management)
6. [Performance Monitoring](#performance-monitoring)
7. [Security Auditing](#security-auditing)
8. [MCP Management](#mcp-management)
9. [Key Rotation](#key-rotation)
10. [Web Dashboard API](#web-dashboard-api)

## 🚀 Bootstrap System

### `scripts/bootstrap_enhanced.sh`

Enhanced bootstrap script with comprehensive project setup capabilities.

#### Usage
```bash
./scripts/scripts/bootstrap_enhanced.sh [PROJECT_NAME] [PROJECT_DIR] [OPTIONS]
```

#### Options
| Option | Description | Example |
|--------|-------------|---------|
| `--dry-run` | Preview changes without executing | `--dry-run` |
| `--force` | Force overwrite existing configuration | `--force` |
| `--skip-deps` | Skip dependency checking | `--skip-deps` |
| `--existing-project` | Setup OOS in existing project | `--existing-project` |
| `--project-dir DIR` | Specify project directory | `--project-dir /path/to/project` |
| `--template TYPE` | Use specific template setup | `--template web-app` |
| `--security-hardened` | Apply enhanced security settings | `--security-hardened` |
| `--user-setup` | Individual developer setup | `--user-setup` |
| `--reset-config` | Reset to default configuration | `--reset-config` |
| `--verbose` | Show detailed output | `--verbose` |
| `--help` | Show help information | `--help` |

#### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `OP_VAULT` | 1Password vault name | `Private` |
| `OP_ITEM` | 1Password item name | `bootstrap-env` |
| `OP_FIELD` | 1Password field name | `env` |
| `ORG` | GitHub organization | Required |
| `VIS` | Repository visibility | `public` |
| `ARCHON_URL` | Archon MCP server URL | `http://localhost:8051/mcp` |

#### Return Codes
- `0`: Success
- `1`: General error
- `2`: Dependency missing
- `3`: 1Password authentication failed
- `4`: Network connectivity issues
- `5`: File permission errors

#### Examples
```bash
# Basic project setup
./scripts/scripts/bootstrap_enhanced.sh my-project /home/user/projects/my-project

# Dry run preview
./scripts/scripts/bootstrap_enhanced.sh --dry-run my-project /path/to/project

# Existing project integration
./scripts/scripts/bootstrap_enhanced.sh --existing-project --project-dir /existing/project

# Security-hardened setup
./scripts/scripts/bootstrap_enhanced.sh --security-hardened --template api-service my-api
```

---

## 🔍 Diagnostics System

### `bin/diagnose.sh`

Interactive diagnostic wizard with automated troubleshooting.

#### Usage
```bash
./bin/diagnose.sh [COMMAND] [OPTIONS]
```

#### Commands
| Command | Description | Usage |
|---------|-------------|--------|
| `check` | Run comprehensive diagnostics | `./bin/diagnose.sh check` |
| `auto` | Automated diagnostic mode | `./bin/diagnose.sh auto` |
| `collect-logs` | Collect diagnostic information | `./bin/diagnose.sh collect-logs` |
| `self-heal` | Attempt automated fixes | `./bin/diagnose.sh self-heal` |
| `interactive` | Interactive troubleshooting | `./bin/diagnose.sh interactive` |

#### Options
| Option | Description | Example |
|--------|-------------|---------|
| `--verbose` | Show detailed output | `--verbose` |
| `--output FILE` | Save results to file | `--output diagnosis.json` |
| `--check-mcp` | Check MCP connectivity only | `--check-mcp` |
| `--check-keys` | Validate API keys only | `--check-keys` |
| `--check-network` | Network connectivity only | `--check-network` |
| `--verify-archon-separation` | Verify project isolation | `--verify-archon-separation` |
| `--update-deps` | Update system dependencies | `--update-deps` |
| `--cleanup` | Clean up temporary files | `--cleanup` |
| `--test-env` | Check test environment | `--test-env` |

#### Diagnostic Categories
1. **System Dependencies**: git, python3, curl, op, gh, claude, npm, node
2. **Environment Configuration**: .env files, variable validation
3. **Network Connectivity**: External services, MCP servers
4. **API Key Validation**: OpenRouter, GitHub, Context7
5. **MCP Health**: Archon server connectivity and response
6. **File Permissions**: Security compliance checks

#### Return Codes
- `0`: All diagnostics passed
- `1`: Minor issues detected
- `2`: Major issues requiring attention
- `3`: Critical failures preventing operation

#### Examples
```bash
# Complete diagnostic check
./bin/diagnose.sh check

# Auto-fix issues
./bin/diagnose.sh self-heal --verbose

# Collect logs for support
./bin/diagnose.sh collect-logs --output support-logs.tar.gz

# Check specific subsystem
./bin/diagnose.sh --check-mcp --verbose
```

---

## 🔄 Health Monitoring

### `bin/health_monitor.sh`

Continuous health monitoring with daemon mode and alerting.

#### Usage
```bash
./bin/health_monitor.sh [COMMAND] [OPTIONS]
```

#### Commands
| Command | Description | Usage |
|---------|-------------|--------|
| `check` | Single health check | `./bin/health_monitor.sh check` |
| `daemon` | Start continuous monitoring | `./bin/health_monitor.sh daemon` |
| `status` | Show daemon status | `./bin/health_monitor.sh status` |
| `stop` | Stop daemon | `./bin/health_monitor.sh stop` |
| `logs` | Show recent logs | `./bin/health_monitor.sh logs` |

#### Options
| Option | Description | Example |
|--------|-------------|---------|
| `--interval SECONDS` | Check interval in daemon mode | `--interval 60` |
| `--profile NAME` | Use specific monitoring profile | `--profile production` |
| `--threshold COUNT` | Failure threshold for alerts | `--threshold 3` |
| `--alert-webhook URL` | Webhook for alert notifications | `--alert-webhook http://...` |
| `--verbose` | Detailed monitoring output | `--verbose` |
| `--background` | Run daemon in background | `--background` |

#### Monitoring Services
1. **Archon MCP**: Connectivity and response time
2. **OpenRouter API**: Key validity and rate limits
3. **1Password CLI**: Authentication status
4. **GitHub CLI**: API connectivity
5. **System Resources**: CPU, memory, disk usage
6. **Network Connectivity**: External service reachability

#### Alert Conditions
- Service unreachable for > threshold failures
- API key expiration or rate limiting
- High resource utilization (>80% CPU/memory)
- Network connectivity issues
- Configuration file changes

#### Log Format
```
[TIMESTAMP] SERVICE_NAME: STATUS (DETAILS)
[2025-09-02 14:30:15] ARCHON: HEALTHY (response_time=45ms)
[2025-09-02 14:30:16] OPENROUTER: RATE_LIMITED (retry_after=60s)
[2025-09-02 14:30:17] GITHUB: UNHEALTHY (HTTP 401)
```

#### Examples
```bash
# Single health check
./bin/health_monitor.sh check --verbose

# Start monitoring daemon
./bin/health_monitor.sh daemon --interval 30 --background

# Production monitoring with alerts
./bin/health_monitor.sh daemon \
  --profile production \
  --threshold 5 \
  --alert-webhook https://hooks.slack.com/...

# Check daemon status
./bin/health_monitor.sh status
```

---

## 🧪 Testing Framework

### `bin/run_tests.sh`

Comprehensive testing suite with multiple test types.

#### Usage
```bash
./bin/run_tests.sh [TEST_TYPE] [OPTIONS]
```

#### Test Types
| Type | Description | Coverage |
|------|-------------|----------|
| `unit` | Unit tests | Individual functions/modules |
| `integration` | Integration tests | Component interactions |
| `security` | Security tests | Vulnerability scanning |
| `performance` | Performance tests | Benchmarking |
| `e2e` | End-to-end tests | Full workflow testing |
| `all` | All test suites | Comprehensive testing |

#### Options
| Option | Description | Example |
|--------|-------------|---------|
| `--verbose` | Detailed test output | `--verbose` |
| `--parallel` | Run tests in parallel | `--parallel` |
| `--coverage` | Generate coverage report | `--coverage` |
| `--report FORMAT` | Output format (json/xml/html) | `--report json` |
| `--filter PATTERN` | Run specific tests | `--filter test_auth` |
| `--timeout SECONDS` | Test timeout | `--timeout 300` |
| `--retry COUNT` | Retry failed tests | `--retry 3` |
| `--reset` | Reset test environment | `--reset` |

#### Test Configuration
```bash
# tests/config.sh
TEST_TIMEOUT=120
PARALLEL_JOBS=4
COVERAGE_THRESHOLD=80
SECURITY_LEVEL="strict"
PERFORMANCE_BASELINE="baseline.json"
```

#### Test Structure
```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── security/       # Security tests
├── performance/    # Performance tests
├── e2e/           # End-to-end tests
├── fixtures/      # Test data
├── mocks/         # Mock services
└── lib/           # Test utilities
```

#### Assertion Library
```bash
# Available assertions
assert_equals "expected" "actual"
assert_contains "substring" "string"
assert_file_exists "/path/to/file"
assert_command_succeeds "command"
assert_command_fails "command"
assert_http_status 200 "http://example.com"
assert_json_key_equals "value" ".key" "json_string"
```

#### Examples
```bash
# Run all tests
./bin/run_tests.sh all --verbose --coverage

# Unit tests only
./bin/run_tests.sh unit --parallel

# Security testing
./bin/run_tests.sh security --report json > security-results.json

# Performance with baseline comparison
./bin/run_tests.sh performance --report html --baseline baseline.json

# Specific test pattern
./bin/run_tests.sh unit --filter "test_bootstrap*" --verbose
```

---

## 📁 Template Management

### `bin/template_manager.sh`

Project template system with variable substitution.

#### Usage
```bash
./bin/template_manager.sh [COMMAND] [OPTIONS]
```

#### Commands
| Command | Description | Usage |
|---------|-------------|--------|
| `list` | List available templates | `./bin/template_manager.sh list` |
| `create TEMPLATE PROJECT` | Create from template | `./bin/template_manager.sh create web-app my-app` |
| `validate TEMPLATE` | Validate template | `./bin/template_manager.sh validate my-template` |
| `add TEMPLATE_DIR` | Add custom template | `./bin/template_manager.sh add ./my-template` |
| `remove TEMPLATE` | Remove template | `./bin/template_manager.sh remove my-template` |
| `update TEMPLATE` | Update template | `./bin/template_manager.sh update web-app` |
| `init` | Initialize template system | `./bin/template_manager.sh init` |

#### Built-in Templates
| Template | Description | Features |
|----------|-------------|----------|
| `web-app` | React/Node.js web application | Frontend, backend, database |
| `api-service` | REST API service | Express, authentication, docs |
| `cli-tool` | Command-line application | Argument parsing, help system |
| `library` | Reusable library/package | Testing, documentation, CI/CD |

#### Template Structure
```
templates/web-app/
├── template.json       # Template configuration
├── src/
│   ├── main.js.tmpl   # Template files
│   └── config.json.tmpl
├── package.json.tmpl   # Package configuration
├── README.md.tmpl      # Documentation
└── hooks/
    ├── pre-create.sh   # Pre-creation hook
    └── post-create.sh  # Post-creation hook
```

#### Template Configuration
```json
{
  "name": "web-app",
  "description": "React/Node.js web application",
  "version": "1.0.0",
  "variables": {
    "project_name": "{{project_name}}",
    "author": "{{author|default:Anonymous}}",
    "license": "{{license|default:MIT}}",
    "port": "{{port|default:3000}}"
  },
  "files": [
    {"src": "src/main.js.tmpl", "dest": "src/main.js"},
    {"src": "package.json.tmpl", "dest": "package.json"}
  ],
  "hooks": {
    "pre_create": "hooks/pre-create.sh",
    "post_create": "hooks/post-create.sh"
  },
  "conditions": [
    {"if": "{{database}}", "include": ["database/"]}
  ]
}
```

#### Variable Substitution
```bash
# Supported syntax:
{{variable_name}}                    # Simple substitution
{{variable_name|default:value}}      # Default value
{{variable_name|upper}}              # Transformation
{{#if condition}}...{{/if}}          # Conditional blocks
{{#each items}}...{{/each}}          # Iteration
```

#### Examples
```bash
# List available templates
./bin/template_manager.sh list

# Create web app project
./bin/template_manager.sh create web-app my-webapp \
  --author "John Doe" \
  --license "MIT" \
  --port 8080

# Create API service with database
./bin/template_manager.sh create api-service my-api \
  --database postgresql \
  --auth jwt

# Validate custom template
./bin/template_manager.sh validate ./my-custom-template

# Add custom template to registry
./bin/template_manager.sh add ./templates/my-template
```

---

## ⚡ Performance Monitoring

### `bin/performance_monitor.sh`

Performance profiling and optimization tools.

#### Usage
```bash
./bin/performance_monitor.sh [COMMAND] [OPTIONS]
```

#### Commands
| Command | Description | Usage |
|---------|-------------|--------|
| `profile SCRIPT` | Profile script execution | `./bin/performance_monitor.sh profile ./script.sh` |
| `benchmark` | Run benchmark suite | `./bin/performance_monitor.sh benchmark` |
| `monitor` | System resource monitoring | `./bin/performance_monitor.sh monitor` |
| `optimize` | Get optimization tips | `./bin/performance_monitor.sh optimize` |
| `report` | Generate performance report | `./bin/performance_monitor.sh report` |

#### Options
| Option | Description | Example |
|--------|-------------|---------|
| `--duration SECONDS` | Monitoring duration | `--duration 300` |
| `--interval SECONDS` | Sampling interval | `--interval 5` |
| `--baseline FILE` | Baseline comparison file | `--baseline baseline.json` |
| `--threshold PERCENT` | Performance threshold | `--threshold 20` |
| `--output FORMAT` | Output format (json/csv/html) | `--output html` |
| `--project NAME` | Project-specific monitoring | `--project my-app` |
| `--update-baselines` | Update baseline data | `--update-baselines` |

#### Profiling Metrics
- **Execution Time**: Total, user, system time
- **Memory Usage**: Peak, average, allocations
- **CPU Utilization**: Percentage, cores used
- **I/O Operations**: Reads, writes, network
- **Function Calls**: Call count, time distribution

#### System Monitoring
- **CPU**: Usage per core, load average
- **Memory**: Total, used, available, swap
- **Disk**: Usage, I/O operations, throughput
- **Network**: Bandwidth, connections, errors

#### Benchmark Suite
```bash
# Available benchmarks
bootstrap_time          # Bootstrap execution time
diagnostic_runtime      # Diagnostic completion time
test_suite_performance  # Test execution speed
security_scan_time      # Security audit duration
health_check_response   # Health monitoring latency
```

#### Performance Baselines
```json
{
  "bootstrap_time": {
    "baseline": 45.2,
    "threshold": 20,
    "unit": "seconds"
  },
  "memory_usage": {
    "baseline": 256,
    "threshold": 30,
    "unit": "MB"
  },
  "test_suite_runtime": {
    "baseline": 120.5,
    "threshold": 25,
    "unit": "seconds"
  }
}
```

#### Examples
```bash
# Profile bootstrap script
./bin/performance_monitor.sh profile ./scripts/scripts/bootstrap_enhanced.sh --verbose

# Run benchmark suite
./bin/performance_monitor.sh benchmark --update-baselines

# Monitor system for 5 minutes
./bin/performance_monitor.sh monitor --duration 300 --interval 10

# Generate performance report
./bin/performance_monitor.sh report --project my-app --output html
```

---

## 🔒 Security Auditing

### `bin/security_audit.sh`

Comprehensive security scanning and compliance reporting.

#### Usage
```bash
./bin/security_audit.sh [COMMAND] [OPTIONS]
```

#### Commands
| Command | Description | Usage |
|---------|-------------|--------|
| `scan` | Comprehensive security scan | `./bin/security_audit.sh scan` |
| `secrets` | Scan for exposed secrets | `./bin/security_audit.sh secrets` |
| `permissions` | Check file permissions | `./bin/security_audit.sh permissions` |
| `encrypt-env FILE` | Encrypt environment file | `./bin/security_audit.sh encrypt-env .env` |
| `decrypt-env FILE` | Decrypt environment file | `./bin/security_audit.sh decrypt-env .env.enc` |
| `compliance` | Generate compliance report | `./bin/security_audit.sh compliance` |
| `audit-logs` | Show audit log entries | `./bin/security_audit.sh audit-logs` |

#### Options
| Option | Description | Example |
|--------|-------------|---------|
| `--fix` | Auto-fix security issues | `--fix` |
| `--report FILE` | Generate report to file | `--report security-report.json` |
| `--verbose` | Show detailed output | `--verbose` |
| `--project NAME` | Project-specific audit | `--project my-app` |

#### Security Scans
1. **Secret Exposure**: API keys, passwords, tokens
2. **File Permissions**: Sensitive file access control
3. **Dependency Vulnerabilities**: npm/pip security issues
4. **Network Security**: Open ports, service exposure
5. **Configuration Security**: Secure defaults

#### Secret Patterns
```regex
sk-[a-zA-Z0-9-_]{43,}      # OpenAI/OpenRouter keys
ghp_[a-zA-Z0-9]{36}        # GitHub Personal Access Tokens
pk_live_[a-zA-Z0-9]{24,}   # Stripe public keys
sk_live_[a-zA-Z0-9]{24,}   # Stripe secret keys
AKIA[0-9A-Z]{16}           # AWS Access Keys
-----BEGIN PRIVATE KEY----- # Private keys
[a-f0-9]{32}               # MD5 hashes (potential secrets)
```

#### Compliance Standards
- **OOS Security Standards**: Internal security requirements
- **File Permission Compliance**: Proper access controls
- **Secret Management**: Encryption and rotation policies
- **Audit Logging**: Security event tracking
- **Access Control**: User and system permissions

#### Audit Log Format
```
[TIMESTAMP] [LEVEL] ACTION: details
[2025-09-02 14:30:15] [AUDIT] SECRET_ACCESS: operation=encrypt resource=.env user=developer
[2025-09-02 14:30:16] [WARN] PERMISSION_ISSUE: file=config.json permissions=644
[2025-09-02 14:30:17] [ERROR] SECRET_LEAK: file=script.sh pattern_type=openai_key
```

#### Examples
```bash
# Complete security scan with auto-fix
./bin/security_audit.sh scan --fix --report security-scan.json

# Check for exposed secrets
./bin/security_audit.sh secrets --verbose

# Fix file permissions
./bin/security_audit.sh permissions --fix

# Encrypt environment file
./bin/security_audit.sh encrypt-env .env

# Generate compliance report
./bin/security_audit.sh compliance --report compliance-report.json
```

---

## 🔌 MCP Management

### `bin/mcp_manager.sh`

Model Context Protocol server configuration and management.

#### Usage
```bash
./bin/mcp_manager.sh [COMMAND] [OPTIONS]
```

#### Commands
| Command | Description | Usage |
|---------|-------------|--------|
| `list` | List configured MCP servers | `./bin/mcp_manager.sh list` |
| `add NAME URL` | Add new MCP server | `./bin/mcp_manager.sh add archon http://localhost:8051/mcp` |
| `remove NAME` | Remove MCP server | `./bin/mcp_manager.sh remove archon` |
| `test NAME` | Test MCP server connection | `./bin/mcp_manager.sh test archon` |
| `health` | Check all server health | `./bin/mcp_manager.sh health` |
| `backup` | Backup MCP configuration | `./bin/mcp_manager.sh backup` |
| `restore BACKUP` | Restore from backup | `./bin/mcp_manager.sh restore backup.json` |
| `discover` | Auto-discover servers | `./bin/mcp_manager.sh discover` |
| `profiles` | Manage configuration profiles | `./bin/mcp_manager.sh profiles` |

#### Options
| Option | Description | Example |
|--------|-------------|---------|
| `--profile NAME` | Use specific profile | `--profile production` |
| `--timeout SECONDS` | Connection timeout | `--timeout 10` |
| `--verbose` | Show detailed output | `--verbose` |

#### Configuration Profiles
```json
{
  "profiles": {
    "development": {
      "active_servers": ["archon-local", "context7"],
      "config": {
        "timeout": 10,
        "retry_attempts": 3
      }
    },
    "production": {
      "active_servers": ["archon-remote", "context7"],
      "config": {
        "timeout": 30,
        "retry_attempts": 5
      }
    }
  }
}
```

#### Server Registry
```json
{
  "servers": {
    "archon": {
      "url": "http://localhost:8051/mcp",
      "transport": "http",
      "description": "Local Archon MCP server",
      "health_check_interval": 60
    },
    "context7": {
      "url": "https://context7.liam.sh/mcp",
      "transport": "http",
      "description": "Context7 documentation server",
      "health_check_interval": 300
    }
  }
}
```

#### Auto-Discovery
Automatically detects common MCP servers:
- `archon`: http://localhost:8051/mcp
- `context7`: https://context7.liam.sh/mcp
- `filesystem`: npx @modelcontextprotocol/server-filesystem

#### Examples
```bash
# List all configured servers
./bin/mcp_manager.sh list

# Add new server
./bin/mcp_manager.sh add myserver http://localhost:9000/mcp

# Test server connectivity
./bin/mcp_manager.sh test archon --verbose --timeout 15

# Health check with specific profile
./bin/mcp_manager.sh health --profile production

# Auto-discover available servers
./bin/mcp_manager.sh discover

# Backup current configuration
./bin/mcp_manager.sh backup
```

---

## 🔑 Key Rotation

### `bin/key_rotator.sh`

Automated OpenRouter API key management and rotation.

#### Usage
```bash
./bin/key_rotator.sh [COMMAND] [OPTIONS]
```

#### Commands
| Command | Description | Usage |
|---------|-------------|--------|
| `validate` | Validate all API keys | `./bin/key_rotator.sh validate` |
| `rotate` | Rotate to next working key | `./bin/key_rotator.sh rotate` |
| `monitor` | Start monitoring daemon | `./bin/key_rotator.sh monitor` |
| `analytics` | Show usage analytics | `./bin/key_rotator.sh analytics` |
| `dashboard` | Interactive dashboard | `./bin/key_rotator.sh dashboard` |
| `stop` | Stop monitoring daemon | `./bin/key_rotator.sh stop` |

#### Options
| Option | Description | Example |
|--------|-------------|---------|
| `--daemon` | Run in daemon mode | `--daemon` |
| `--interval SECONDS` | Check interval | `--interval 300` |
| `--threshold COUNT` | Failure threshold | `--threshold 5` |
| `--webhook URL` | Alert webhook | `--webhook https://...` |
| `--verbose` | Detailed output | `--verbose` |

#### Key Management Features
- **Smart Rotation**: Automatically switch to working keys
- **Rate Limit Detection**: Monitor and respond to rate limits
- **Usage Analytics**: Track key usage patterns
- **Health Monitoring**: Continuous key validation
- **Failover Logic**: Intelligent key selection

#### Key Status Types
- `ACTIVE`: Currently selected key
- `VALID`: Working key available for rotation
- `RATE_LIMITED`: Temporarily unavailable
- `EXPIRED`: Invalid or expired key
- `UNKNOWN`: Status could not be determined

#### Analytics Metrics
```json
{
  "key_stats": {
    "sk-or-v1-abc123": {
      "status": "ACTIVE",
      "requests_today": 150,
      "rate_limit_hits": 2,
      "last_used": "2025-09-02T14:30:15Z",
      "avg_response_time": "245ms"
    }
  },
  "rotation_history": [
    {
      "timestamp": "2025-09-02T10:15:30Z",
      "from_key": "sk-or-v1-def456",
      "to_key": "sk-or-v1-abc123",
      "reason": "rate_limit_exceeded"
    }
  ]
}
```

#### Dashboard Interface
```
┌─ OpenRouter Key Management Dashboard ─┐
│                                        │
│ Active Key: sk-or-v1-***abc123         │
│ Status: HEALTHY                        │
│ Requests Today: 150/1000               │
│ Last Rotation: 2 hours ago             │
│                                        │
│ Available Keys:                        │
│ ✓ Key 1: ACTIVE    (150 req)          │
│ ⚠ Key 2: RATE_LIMITED (retry in 45m)  │
│ ✓ Key 3: VALID     (0 req)            │
│ ✗ Key 4: EXPIRED                      │
│                                        │
│ Commands: [r]otate [a]nalytics [q]uit  │
└────────────────────────────────────────┘
```

#### Examples
```bash
# Validate all configured keys
./bin/key_rotator.sh validate --verbose

# Start monitoring with rotation
./bin/key_rotator.sh monitor --daemon --interval 300

# View usage analytics
./bin/key_rotator.sh analytics

# Interactive dashboard
./bin/key_rotator.sh dashboard

# Manual rotation
./bin/key_rotator.sh rotate
```

---

## 🌐 Web Dashboard API

### Dashboard Server

Flask-based web dashboard with REST API and WebSocket support.

#### Starting the Server
```bash
cd dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 api/server.py
```

#### Base URL
```
http://localhost:5000
```

### REST API Endpoints

#### System Status
```http
GET /api/status
```
Response:
```json
{
  "status": "healthy",
  "uptime": "2 hours, 15 minutes",
  "services": {
    "archon": {"status": "healthy", "response_time": "45ms"},
    "openrouter": {"status": "healthy", "requests_today": 150},
    "github": {"status": "healthy", "rate_limit": "4800/5000"}
  },
  "system": {
    "cpu_usage": 15.2,
    "memory_usage": 67.8,
    "disk_usage": 42.1
  }
}
```

#### Environment Management
```http
GET /api/environment
POST /api/environment
PUT /api/environment
```

#### Project Management
```http
GET /api/projects
POST /api/projects
GET /api/projects/{id}
PUT /api/projects/{id}
DELETE /api/projects/{id}
```

#### Health Monitoring
```http
GET /api/health
POST /api/health/check
GET /api/health/logs
```

#### Security Auditing
```http
POST /api/security/scan
GET /api/security/reports
GET /api/security/compliance
```

#### Performance Metrics
```http
GET /api/performance/current
GET /api/performance/history
POST /api/performance/benchmark
```

### WebSocket Events

#### Connection
```javascript
const ws = new WebSocket('ws://localhost:5000/ws');
```

#### Event Types
- `system_status`: Real-time system metrics
- `health_update`: Service health changes
- `security_alert`: Security issue notifications
- `performance_update`: Performance metrics
- `log_entry`: New log entries

#### Example Usage
```javascript
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);

    switch(data.type) {
        case 'system_status':
            updateSystemMetrics(data.metrics);
            break;
        case 'health_update':
            updateServiceStatus(data.service, data.status);
            break;
        case 'security_alert':
            showSecurityAlert(data.alert);
            break;
    }
};
```

---

This API reference provides complete documentation for all OOS tools and their integration patterns, enabling effective use of the system for project management and operational excellence.