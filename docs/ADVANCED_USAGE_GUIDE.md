# OOS Usage Guide - Complete Workflows

This guide provides step-by-step instructions for using OOS in different scenarios, ensuring proper project separation in Archon and clear operational procedures.

## 📋 Table of Contents

1. [Quick Start Scenarios](#quick-start-scenarios)
2. [Project Setup Workflows](#project-setup-workflows)
3. [Archon Integration & Project Separation](#archon-integration--project-separation)
4. [Daily Operations](#daily-operations)
5. [Maintenance & Monitoring](#maintenance--monitoring)
6. [Troubleshooting](#troubleshooting)

## 🚀 Quick Start Scenarios

### Scenario 1: Brand New Project
```bash
# 1. Create project directory
mkdir -p /home/ubuntu/dev/my-new-project
cd /home/ubuntu/dev/my-new-project

# 2. Sign into 1Password
eval "$(op signin)"

# 3. Bootstrap with enhanced setup
OP_VAULT="Private" OP_ITEM="bootstrap-env" OP_FIELD="env" \
ORG="YourOrg" VIS="public" \
/home/ubuntu/dev/oos/scripts/bootstrap_enhanced.sh

# 4. Verify setup
./bin/diagnose.sh

# 5. Start monitoring
./bin/health_monitor.sh daemon
```

### Scenario 2: Add OOS to Existing Project
```bash
# 1. Navigate to existing project
cd /path/to/existing-project

# 2. Add OOS as submodule
git submodule add https://github.com/your-org/oos .oos

# 3. Setup OOS in existing project
cd .oos
eval "$(op signin)"
./scripts/scripts/bootstrap_enhanced.sh --project-dir .. --existing-project

# 4. Return to project root and verify
cd ..
./.oos/bin/diagnose.sh
```

### Scenario 3: Team Setup (Multiple Developers)
```bash
# Each developer runs:
git clone https://github.com/your-org/your-project
cd your-project
git submodule update --init --recursive

# Setup individual environment
eval "$(op signin)"  # Each dev uses their own 1Password
cd .oos
./scripts/scripts/bootstrap_enhanced.sh --project-dir .. --user-setup

# Verify team setup
./bin/diagnose.sh --team-mode
```

## 🏗️ Project Setup Workflows

### Creating Different Project Types

#### Web Application Project
```bash
# 1. Create from template
./bin/template_manager.sh create web-app my-web-app
cd my-web-app

# 2. Initialize with enhanced features
../oos/scripts/bootstrap_enhanced.sh --template web-app

# 3. Setup Archon project
# In Claude Code:
# mcp__archon__create_project(title="My Web App", description="React/Node.js web application")

# 4. Configure environment
echo "ARCHON_PROJECT_ID=your-project-id-from-step-3" >> .env

# 5. Run comprehensive setup
./bin/diagnose.sh --self-heal
./bin/run_tests.sh all
./bin/security_audit.sh scan --fix
```

#### CLI Tool Project
```bash
# 1. Create CLI tool template
./bin/template_manager.sh create cli-tool my-cli-tool
cd my-cli-tool

# 2. Bootstrap with CLI-specific settings
../oos/scripts/bootstrap_enhanced.sh --template cli-tool

# 3. Setup development environment
./bin/run_tests.sh unit
./bin/performance_monitor.sh profile ./bin/my-cli-tool
```

#### API Service Project
```bash
# 1. Create API service template
./bin/template_manager.sh create api-service my-api
cd my-api

# 2. Enhanced bootstrap with security focus
../oos/scripts/bootstrap_enhanced.sh --template api-service --security-hardened

# 3. Setup API-specific monitoring
./bin/health_monitor.sh daemon --profile api-service
./bin/security_audit.sh compliance --report api-compliance.json
```

### Custom Template Creation
```bash
# 1. Create custom template structure
mkdir templates/my-custom-template
cd templates/my-custom-template

# 2. Create template files with variable substitution
cat > template.json <<'EOF'
{
  "name": "my-custom-template",
  "description": "My custom project template",
  "variables": {
    "PROJECT_NAME": "{{project_name}}",
    "AUTHOR": "{{author|default:Anonymous}}",
    "LICENSE": "{{license|default:MIT}}"
  },
  "files": [
    {"src": "src/main.py.tmpl", "dest": "src/main.py"},
    {"src": "README.md.tmpl", "dest": "README.md"}
  ]
}
EOF

# 3. Create template files
mkdir src
cat > src/main.py.tmpl <<'EOF'
#!/usr/bin/env python3
"""
{{PROJECT_NAME}} - Main application
Author: {{AUTHOR}}
License: {{LICENSE}}
"""

def main():
    print("Hello from {{PROJECT_NAME}}!")

if __name__ == "__main__":
    main()
EOF

# 4. Register template
cd ../..
./bin/template_manager.sh add templates/my-custom-template
```

## 🎯 Archon Integration & Project Separation

### Ensuring Proper Project Separation

#### 1. Project Creation in Archon
```bash
# In Claude Code with Archon MCP access:

# Create unique project
mcp__archon__create_project(
    title="Project Alpha - Authentication Service",
    description="JWT-based authentication service with OAuth2 providers",
    github_repo="https://github.com/myorg/project-alpha"
)

# Result: project_id = "550e8400-e29b-41d4-a716-446655440000"
```

#### 2. Configure Project Environment
```bash
# Add project ID to environment (ensures separation)
echo "ARCHON_PROJECT_ID=550e8400-e29b-41d4-a716-446655440000" >> .env
echo "ARCHON_URL=http://localhost:8051/mcp" >> .env

# Verify environment isolation
./bin/diagnose.sh --verify-archon-separation
```

#### 3. Task Management with Separation
```bash
# In Claude Code - Create project-specific tasks:

# Feature: Authentication
mcp__archon__create_task(
    project_id="550e8400-e29b-41d4-a716-446655440000",
    title="Implement JWT authentication",
    description="Create JWT token generation and validation with refresh tokens",
    assignee="AI IDE Agent",
    feature="authentication",
    task_order=10
)

# Feature: OAuth Integration
mcp__archon__create_task(
    project_id="550e8400-e29b-41d4-a716-446655440000",
    title="Add Google OAuth2 provider",
    description="Integrate Google OAuth2 with PKCE security",
    assignee="AI IDE Agent",
    feature="oauth",
    task_order=20
)

# Feature: Database
mcp__archon__create_task(
    project_id="550e8400-e29b-41d4-a716-446655440000",
    title="Setup user database schema",
    description="PostgreSQL schema for users, sessions, and oauth tokens",
    assignee="AI IDE Agent",
    feature="database",
    task_order=5
)
```

#### 4. Document Management with Isolation
```bash
# In Claude Code - Create project-specific documents:

# Technical specification
mcp__archon__create_document(
    project_id="550e8400-e29b-41d4-a716-446655440000",
    title="Authentication API Specification",
    document_type="spec",
    content={
        "endpoints": [
            {"path": "/auth/login", "method": "POST", "description": "User login"},
            {"path": "/auth/refresh", "method": "POST", "description": "Refresh token"},
            {"path": "/auth/logout", "method": "POST", "description": "User logout"}
        ],
        "authentication": "Bearer JWT tokens",
        "security": {"rate_limiting": true, "cors": true}
    },
    tags=["api", "authentication", "security"]
)

# Design document
mcp__archon__create_document(
    project_id="550e8400-e29b-41d4-a716-446655440000",
    title="OAuth2 Integration Design",
    document_type="design",
    content={
        "overview": "OAuth2 PKCE implementation for Google provider",
        "flow": ["authorization_request", "code_exchange", "token_validation"],
        "security_considerations": ["PKCE", "state_parameter", "nonce_validation"]
    },
    tags=["oauth", "design", "security"]
)
```

#### 5. Verification of Project Separation
```bash
# Verify project isolation in Claude Code:

# List tasks (should only show current project)
mcp__archon__list_tasks(project_id="550e8400-e29b-41d4-a716-446655440000")

# List documents (should only show current project)
mcp__archon__list_documents(project_id="550e8400-e29b-41d4-a716-446655440000")

# Get project features (isolated to this project)
mcp__archon__get_project_features(project_id="550e8400-e29b-41d4-a716-446655440000")
```

### Multiple Project Management

#### Project Alpha (Authentication Service)
```bash
# Project directory: /home/ubuntu/dev/project-alpha
cd /home/ubuntu/dev/project-alpha
cat .env | grep ARCHON_PROJECT_ID
# ARCHON_PROJECT_ID=550e8400-e29b-41d4-a716-446655440000

# Check project-specific tasks
# (In Claude Code - tasks will be filtered to this project ID)
```

#### Project Beta (E-commerce API)
```bash
# Project directory: /home/ubuntu/dev/project-beta
cd /home/ubuntu/dev/project-beta
cat .env | grep ARCHON_PROJECT_ID
# ARCHON_PROJECT_ID=7a8b9c0d-1e2f-3a4b-5c6d-7e8f90123456

# Completely isolated from Project Alpha
# Different tasks, documents, and project scope
```

## 📅 Daily Operations

### Morning Startup Routine
```bash
# 1. Check system health
./bin/health_monitor.sh check

# 2. Validate API keys
./bin/key_rotator.sh validate

# 3. Review overnight logs
./bin/health_monitor.sh status
tail -20 health_monitor.log

# 4. Check security status
./bin/security_audit.sh scan

# 5. Start development environment
./bin/health_monitor.sh daemon &
.agents/runners/run_claude.sh
```

### Development Session Workflow
```bash
# 1. Start working on a task (in Claude Code)
# mcp__archon__get_task(task_id="task-uuid")
# mcp__archon__update_task(task_id="task-uuid", status="doing")

# 2. Monitor performance during development
./bin/performance_monitor.sh monitor &

# 3. Run tests frequently
./bin/run_tests.sh unit

# 4. Check security as you code
./bin/security_audit.sh secrets

# 5. Complete task (in Claude Code)
# mcp__archon__update_task(task_id="task-uuid", status="done")
```

### End-of-Day Routine
```bash
# 1. Run comprehensive test suite
./bin/run_tests.sh all

# 2. Security audit
./bin/security_audit.sh scan --fix

# 3. Performance check
./bin/performance_monitor.sh benchmark

# 4. Commit and push (if tests pass)
git add -A
git commit -m "feat: implement user authentication

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 5. Stop monitoring
./bin/health_monitor.sh stop
```

## 🔧 Maintenance & Monitoring

### Weekly Maintenance
```bash
# 1. Update dependencies
./bin/diagnose.sh --update-deps

# 2. Rotate API keys if needed
./bin/key_rotator.sh analytics
./bin/key_rotator.sh rotate

# 3. Comprehensive security audit
./bin/security_audit.sh compliance --report weekly-compliance.json

# 4. Performance baseline update
./bin/performance_monitor.sh benchmark --update-baselines

# 5. Backup MCP configurations
./bin/mcp_manager.sh backup
```

### Monthly Operations
```bash
# 1. System optimization
./bin/performance_monitor.sh optimize

# 2. Template updates
./bin/template_manager.sh update-all

# 3. Security policy review
./bin/security_audit.sh audit-logs
./bin/security_audit.sh compliance

# 4. Environment cleanup
./bin/diagnose.sh --cleanup

# 5. Documentation updates
# Review and update project documentation in Archon
```

### Monitoring Dashboard
```bash
# Start web dashboard for visual monitoring
cd dashboard
source venv/bin/activate
python3 api/server.py

# Access at http://localhost:5000
# Features:
# - Real-time system status
# - Project management
# - Environment variable management
# - Live health monitoring
# - Performance metrics
```

## 🔍 Troubleshooting

### Common Issues & Solutions

#### 1. Archon Connection Issues
```bash
# Symptom: HTTP 000 errors in health monitor log
./bin/diagnose.sh --self-heal

# Manual check
curl -I http://localhost:8051/mcp

# Fix: Restart Archon service
# Or switch to remote: ARCHON_URL=https://archon.khamel.com:8051/mcp
```

#### 2. API Key Problems
```bash
# Symptom: Authentication failures
./bin/key_rotator.sh validate

# Check key status
./bin/key_rotator.sh analytics

# Force rotation
./bin/key_rotator.sh rotate
```

#### 3. Permission Errors
```bash
# Symptom: Script execution failures
./bin/security_audit.sh permissions --fix

# Manual fix
chmod +x bin/*.sh
chmod 600 .env*
```

#### 4. Performance Issues
```bash
# Diagnose slow operations
./bin/performance_monitor.sh profile ./slow-script.sh

# Get optimization recommendations
./bin/performance_monitor.sh optimize

# Check resource usage
./bin/performance_monitor.sh monitor
```

#### 5. Test Failures
```bash
# Run specific test suite
./bin/run_tests.sh unit --verbose

# Check test environment
./bin/diagnose.sh --test-env

# Reset test data
./bin/run_tests.sh reset
```

### Emergency Procedures

#### System Recovery
```bash
# 1. Stop all background processes
./bin/health_monitor.sh stop
pkill -f "performance_monitor"
pkill -f "key_rotator"

# 2. Run full diagnostics
./bin/diagnose.sh --collect-logs

# 3. Reset to known good state
./scripts/scripts/bootstrap_enhanced.sh --reset-config

# 4. Verify recovery
./bin/run_tests.sh all
```

#### Data Recovery
```bash
# 1. Restore MCP configuration
./bin/mcp_manager.sh restore backup-20231201-120000.json

# 2. Decrypt environment if needed
./bin/security_audit.sh decrypt-env .env

# 3. Restore from git if necessary
git reset --hard HEAD~1
./scripts/scripts/bootstrap_enhanced.sh --force
```

### Getting Help

#### Log Analysis
```bash
# System logs
tail -f diagnostic.log

# Health monitoring logs
tail -f health_monitor.log

# Security audit logs
tail -f security_audit.log

# Performance logs
tail -f performance.log
```

#### Diagnostic Information
```bash
# Comprehensive system info
./bin/diagnose.sh --collect-logs

# Specific subsystem check
./bin/diagnose.sh --check-mcp
./bin/diagnose.sh --check-keys
./bin/diagnose.sh --check-network
```

#### Dashboard Monitoring
```bash
# Real-time monitoring
cd dashboard && source venv/bin/activate
python3 api/server.py

# Visit http://localhost:5000 for:
# - System status overview
# - Live performance metrics
# - Error tracking
# - Resource utilization
```

---

This usage guide provides complete workflows for using OOS effectively while ensuring proper project separation in Archon and maintaining operational excellence.
