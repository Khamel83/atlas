# Archon Integration Guide - Project Separation & Best Practices

This guide explains how to properly integrate OOS with Archon MCP for project management while ensuring complete project separation and isolation.

## 🎯 Overview

Archon MCP provides project and task management capabilities integrated with OOS. The key principle is **complete project isolation** - each project operates independently with its own:

- Unique project ID
- Isolated task management
- Separate documentation
- Independent monitoring
- Isolated security audit trails

## 🏗️ Project Architecture

### Project Isolation Model

```
Archon Server
├── Project Alpha (ID: 550e8400-...)
│   ├── Tasks (filtered by project_id)
│   ├── Documents (scoped to project)
│   ├── Features (project-specific)
│   └── Versions (project history)
├── Project Beta (ID: 7a8b9c0d-...)
│   ├── Tasks (completely separate)
│   ├── Documents (independent)
│   ├── Features (isolated)
│   └── Versions (separate history)
└── Project Gamma (ID: 2f3e4d5c-...)
    └── (fully isolated scope)
```

### Environment Configuration

Each project maintains its own `.env` file with unique identifiers:

```bash
# Project Alpha - Authentication Service
ARCHON_PROJECT_ID=550e8400-e29b-41d4-a716-446655440000
ARCHON_URL=http://localhost:8051/mcp
PROJECT_NAME=auth-service
PROJECT_TYPE=api

# Project Beta - E-commerce Frontend
ARCHON_PROJECT_ID=7a8b9c0d-1e2f-3a4b-5c6d-7e8f90123456
ARCHON_URL=http://localhost:8051/mcp
PROJECT_NAME=ecommerce-web
PROJECT_TYPE=web-app
```

## 🚀 Step-by-Step Integration

### 1. Initial Project Setup

#### Create New Project in Archon
```javascript
// In Claude Code with Archon MCP
mcp__archon__create_project({
    title: "Authentication Service",
    description: "JWT-based authentication API with OAuth2 integration for multi-tenant SaaS platform",
    github_repo: "https://github.com/myorg/auth-service"
})

// Response includes:
// {
//   "success": true,
//   "project_id": "550e8400-e29b-41d4-a716-446655440000",
//   "message": "Project created successfully"
// }
```

#### Configure OOS Environment
```bash
# Navigate to project directory
cd /home/ubuntu/dev/auth-service

# Initialize OOS
eval "$(op signin)"
../oos/scripts/bootstrap_enhanced.sh

# Add Archon project ID to environment
echo "ARCHON_PROJECT_ID=550e8400-e29b-41d4-a716-446655440000" >> .env

# Verify Archon connectivity
./bin/diagnose.sh --check-archon

# Start monitoring
./bin/health_monitor.sh daemon
```

### 2. Task Management Integration

#### Create Project Tasks with Proper Scoping

```javascript
// Authentication Feature Tasks
mcp__archon__create_task({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    title: "Design JWT token architecture",
    description: `Design JWT token structure with:
- Access token (15 min expiry)
- Refresh token (30 day expiry)
- Token rotation strategy
- Secure token storage patterns`,
    assignee: "AI IDE Agent",
    feature: "authentication",
    task_order: 5,
    sources: [
        {
            url: "https://tools.ietf.org/rfc/rfc7519.txt",
            type: "specification",
            relevance: "JWT standard specification"
        }
    ]
})

mcp__archon__create_task({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    title: "Implement user login endpoint",
    description: `Create POST /auth/login endpoint:
- Email/password validation
- Rate limiting (5 attempts per minute)
- JWT generation on success
- Secure password hashing verification`,
    assignee: "AI IDE Agent",
    feature: "authentication",
    task_order: 10,
    code_examples: [
        {
            file: "examples/auth/login.py",
            function: "login_handler",
            purpose: "Reference implementation pattern"
        }
    ]
})

// Database Feature Tasks
mcp__archon__create_task({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    title: "Create user database schema",
    description: `PostgreSQL schema design:
- users table (id, email, password_hash, created_at, updated_at)
- user_sessions table (token_id, user_id, expires_at, created_at)
- oauth_tokens table (provider, provider_id, user_id, tokens)
- Proper indexes and constraints`,
    assignee: "AI IDE Agent",
    feature: "database",
    task_order: 3
})

// OAuth Integration Tasks
mcp__archon__create_task({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    title: "Implement Google OAuth2 provider",
    description: `OAuth2 integration with PKCE:
- Authorization URL generation
- Code exchange implementation
- User info retrieval and mapping
- Account linking logic`,
    assignee: "AI IDE Agent",
    feature: "oauth",
    task_order: 20
})
```

#### Task Workflow Management

```javascript
// Get project-specific tasks
mcp__archon__list_tasks({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    filter_by: "status",
    filter_value: "todo"
})

// Start working on a task
mcp__archon__update_task({
    task_id: "task-uuid-from-above",
    status: "doing"
})

// Complete a task
mcp__archon__update_task({
    task_id: "task-uuid",
    status: "done"
})

// Move task to review
mcp__archon__update_task({
    task_id: "task-uuid",
    status: "review"
})
```

### 3. Documentation Management

#### Create Project Documentation

```javascript
// Technical Specification
mcp__archon__create_document({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    title: "Authentication API Specification v1.0",
    document_type: "spec",
    content: {
        version: "1.0.0",
        base_url: "https://api.example.com/auth",
        authentication: "Bearer JWT tokens",
        endpoints: [
            {
                path: "/login",
                method: "POST",
                description: "User authentication",
                request: {
                    email: "string (required)",
                    password: "string (required)"
                },
                responses: {
                    200: "Login successful with tokens",
                    401: "Invalid credentials",
                    429: "Rate limit exceeded"
                }
            },
            {
                path: "/refresh",
                method: "POST",
                description: "Token refresh",
                headers: {
                    "Authorization": "Bearer <refresh_token>"
                },
                responses: {
                    200: "New access token provided",
                    401: "Invalid refresh token"
                }
            },
            {
                path: "/logout",
                method: "POST",
                description: "User logout",
                headers: {
                    "Authorization": "Bearer <access_token>"
                },
                responses: {
                    200: "Logout successful",
                    401: "Invalid token"
                }
            }
        ],
        security: {
            rate_limiting: "5 requests per minute per IP",
            cors: "Enabled for allowed origins",
            csrf: "Required for state-changing operations"
        }
    },
    tags: ["api", "authentication", "specification"],
    author: "Development Team"
})

// Architecture Design Document
mcp__archon__create_document({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    title: "Authentication System Architecture",
    document_type: "design",
    content: {
        overview: "JWT-based authentication system with OAuth2 integration",
        components: [
            {
                name: "AuthController",
                responsibility: "Handle authentication endpoints",
                dependencies: ["UserService", "TokenService", "RateLimiter"]
            },
            {
                name: "TokenService",
                responsibility: "JWT generation and validation",
                dependencies: ["SecretManager", "DatabaseService"]
            },
            {
                name: "OAuth2Service",
                responsibility: "OAuth provider integration",
                dependencies: ["HttpClient", "UserService"]
            }
        ],
        data_flow: [
            "User submits credentials",
            "AuthController validates input",
            "UserService verifies credentials",
            "TokenService generates JWT tokens",
            "Response sent with tokens"
        ],
        security_considerations: [
            "Password hashing with bcrypt",
            "JWT tokens signed with RS256",
            "Refresh token rotation",
            "Rate limiting on auth endpoints",
            "CORS configuration",
            "Input validation and sanitization"
        ]
    },
    tags: ["architecture", "design", "authentication"]
})

// Implementation Guide
mcp__archon__create_document({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    title: "Development Setup Guide",
    document_type: "guide",
    content: {
        prerequisites: [
            "Python 3.9+",
            "PostgreSQL 13+",
            "Redis 6+",
            "1Password CLI access"
        ],
        setup_steps: [
            "Clone repository",
            "Run OOS bootstrap: ./scripts/scripts/bootstrap_enhanced.sh",
            "Install dependencies: pip install -r requirements.txt",
            "Setup database: ./bin/setup_db.sh",
            "Run tests: ./bin/run_tests.sh all",
            "Start development server: ./bin/dev_server.sh"
        ],
        environment_variables: {
            "DATABASE_URL": "PostgreSQL connection string",
            "REDIS_URL": "Redis connection string",
            "JWT_SECRET": "JWT signing secret",
            "OAUTH_GOOGLE_CLIENT_ID": "Google OAuth client ID",
            "OAUTH_GOOGLE_CLIENT_SECRET": "Google OAuth client secret"
        },
        testing: {
            unit_tests: "./bin/run_tests.sh unit",
            integration_tests: "./bin/run_tests.sh integration",
            security_tests: "./bin/run_tests.sh security"
        }
    },
    tags: ["guide", "setup", "development"]
})
```

### 4. Version Control Integration

#### Document Versioning
```javascript
// Create version snapshots for important milestones
mcp__archon__create_version({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    field_name: "docs",
    content: [
        // Current state of all documents
    ],
    change_summary: "Initial API specification and architecture design",
    created_by: "Development Team"
})

// Version project features
mcp__archon__create_version({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    field_name: "features",
    content: {
        authentication: {
            status: "in_progress",
            completion: 60,
            components: ["login", "logout", "token_refresh"],
            tests_passing: true
        },
        oauth: {
            status: "planned",
            providers: ["google", "github"],
            completion: 0
        },
        database: {
            status: "completed",
            schema_version: "1.0",
            migrations_applied: 5
        }
    },
    change_summary: "Authentication 60% complete, database schema finalized"
})
```

## 🔒 Security & Isolation Best Practices

### Environment Isolation
```bash
# Each project has isolated environment
# Project Alpha
cat /home/ubuntu/dev/auth-service/.env
ARCHON_PROJECT_ID=550e8400-e29b-41d4-a716-446655440000
PROJECT_SECRETS_PREFIX=AUTH_SERVICE_

# Project Beta
cat /home/ubuntu/dev/ecommerce-web/.env
ARCHON_PROJECT_ID=7a8b9c0d-1e2f-3a4b-5c6d-7e8f90123456
PROJECT_SECRETS_PREFIX=ECOMMERCE_WEB_

# No cross-project access possible
```

### Access Control Validation
```bash
# Verify project isolation in each project directory

# Project Alpha - should only see its own data
cd /home/ubuntu/dev/auth-service
# In Claude Code:
# mcp__archon__list_tasks(project_id="550e8400-e29b-41d4-a716-446655440000")
# Result: Only auth-service tasks

# Project Beta - completely isolated
cd /home/ubuntu/dev/ecommerce-web
# In Claude Code:
# mcp__archon__list_tasks(project_id="7a8b9c0d-1e2f-3a4b-5c6d-7e8f90123456")
# Result: Only ecommerce-web tasks
```

### Security Monitoring Per Project
```bash
# Each project maintains separate security audit trails
./bin/security_audit.sh scan --report auth-service-security.json
./bin/security_audit.sh compliance --report auth-service-compliance.json

# Separate monitoring logs
tail -f security_audit.log | grep "PROJECT_ID=550e8400"
```

## 🔄 Workflow Integration

### Development Workflow with Archon

#### 1. Daily Standup Workflow
```bash
# Morning routine - check project status
./bin/health_monitor.sh check

# In Claude Code - review project tasks:
# mcp__archon__list_tasks(
#     project_id="550e8400-e29b-41d4-a716-446655440000",
#     filter_by="status",
#     filter_value="doing"
# )

# Start work on priority task
# mcp__archon__update_task(task_id="uuid", status="doing")
```

#### 2. Feature Development Workflow
```bash
# 1. Get task details
# mcp__archon__get_task(task_id="uuid")

# 2. Research phase - query knowledge base
# mcp__archon__perform_rag_query(
#     query="JWT authentication best practices",
#     match_count=5
# )

# 3. Code implementation
# Use task description and research findings

# 4. Testing and validation
./bin/run_tests.sh unit
./bin/security_audit.sh scan

# 5. Task completion
# mcp__archon__update_task(task_id="uuid", status="review")
```

#### 3. Code Review Workflow
```bash
# 1. Move task to review
# mcp__archon__update_task(task_id="uuid", status="review")

# 2. Create review documentation
# mcp__archon__create_document(
#     project_id="550e8400-e29b-41d4-a716-446655440000",
#     title="JWT Implementation Review",
#     document_type="note",
#     content={
#         "implementation_summary": "...",
#         "security_review": "...",
#         "test_coverage": "...",
#         "performance_analysis": "..."
#     }
# )

# 3. Mark as completed after review
# mcp__archon__update_task(task_id="uuid", status="done")
```

### Multi-Project Coordination

#### Project Dependencies
```javascript
// Project Alpha (auth-service) creates shared authentication
// Project Beta (ecommerce-web) depends on Project Alpha

// In Project Beta - reference auth service
mcp__archon__create_task({
    project_id: "7a8b9c0d-1e2f-3a4b-5c6d-7e8f90123456",
    title: "Integrate with authentication service",
    description: "Connect frontend to auth-service API endpoints",
    sources: [
        {
            url: "http://localhost:3001/auth-service/docs",
            type: "api_documentation",
            relevance: "Authentication API endpoints from Project Alpha"
        }
    ],
    assignee: "AI IDE Agent",
    feature: "authentication_integration"
})
```

#### Cross-Project Communication
```bash
# Projects remain isolated but can reference each other's public interfaces
# Document inter-project dependencies

# Project Alpha exposes API documentation
mcp__archon__create_document({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    title: "Public API Documentation",
    document_type: "api",
    content: {
        public_endpoints: [...],
        authentication_flow: [...],
        integration_guide: [...]
    },
    tags: ["public", "api", "integration"]
})
```

## 📊 Monitoring & Analytics

### Project-Specific Monitoring
```bash
# Each project maintains independent monitoring
cd /home/ubuntu/dev/auth-service
./bin/health_monitor.sh daemon --profile auth-service

cd /home/ubuntu/dev/ecommerce-web
./bin/health_monitor.sh daemon --profile ecommerce-web

# Separate log files and monitoring data
tail -f health_monitor.log | grep "PROJECT=auth-service"
tail -f health_monitor.log | grep "PROJECT=ecommerce-web"
```

### Performance Tracking
```javascript
// Track project-specific performance metrics
mcp__archon__update_project({
    project_id: "550e8400-e29b-41d4-a716-446655440000",
    data: {
        performance_metrics: {
            api_response_time: "120ms avg",
            database_query_time: "45ms avg",
            memory_usage: "256MB",
            cpu_utilization: "15%"
        },
        last_updated: new Date().toISOString()
    }
})
```

### Analytics and Reporting
```bash
# Generate project-specific reports
./bin/performance_monitor.sh report --project auth-service
./bin/security_audit.sh compliance --project auth-service --report compliance.json
./bin/run_tests.sh report --project auth-service --format json > test-results.json
```

## 🚀 Advanced Integration Patterns

### Template Integration with Archon
```bash
# Create Archon-aware templates
./bin/template_manager.sh create archon-api-service my-service \
  --archon-integration \
  --auto-create-project \
  --project-title "My Service API" \
  --project-description "RESTful API service with authentication"

# Template automatically:
# 1. Creates Archon project
# 2. Sets ARCHON_PROJECT_ID in .env
# 3. Creates initial task structure
# 4. Sets up project documentation
```

### Automated Task Creation
```bash
# Hook into OOS bootstrap to create standard tasks
# In scripts/bootstrap_enhanced.sh integration:

create_standard_archon_tasks() {
    local project_id="$1"
    local project_type="$2"

    case "$project_type" in
        "api-service")
            # Create API-specific tasks
            ;;
        "web-app")
            # Create web app tasks
            ;;
        "cli-tool")
            # Create CLI tool tasks
            ;;
    esac
}
```

### CI/CD Integration
```yaml
# .github/workflows/archon-integration.yml
name: Archon Integration
on: [push, pull_request]

jobs:
  update-archon:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Update Archon Project
        run: |
          # Update project status in Archon
          # Mark relevant tasks as completed
          # Update project metrics
```

---

This integration guide ensures that OOS and Archon work together seamlessly while maintaining complete project isolation and providing clear operational procedures for multi-project development environments.