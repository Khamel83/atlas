# OOS Capability Layer - Service Integration Guide

This document explains how to set up and integrate external services with the OOS Capability Layer.

## Overview

The OOS Capability Layer provides a unified interface for understanding service capabilities and executing actions across multiple domains. It integrates with various documentation sources and tool aggregators through MCP (Model Context Protocol) servers.

## Architecture

```
Natural Language Request
         ↓
  Capability Router
         ↓
   ┌─────────────────┐
   │ Knowledge       │ ← Context7, Docs MCP, Deep-Research
   │ Resolver        │
   └─────────────────┘
         ↓
   ┌─────────────────┐
   │ Actions         │ ← MetaMCP, Remote MCP Servers
   │ Gateway         │
   └─────────────────┘
         ↓
  Rendered Output
```

## Quick Start

### 1. Environment Configuration

Set up the required environment variables:

```bash
# Knowledge Adapters
export CONTEXT7_URL=http://localhost:8080
export CONTEXT7_API_KEY=your-api-key
export DOCS_MCP_URL=http://localhost:8001
export DEEP_RESEARCH_MCP_URL=http://localhost:8002

# Action Aggregators
export META_MCP_URL=http://localhost:9000
export REMOTE_MCP_URLS=http://mcp1:8001,http://mcp2:8001

# Timeouts
export KNOWLEDGE_TIMEOUT=30
export ACTIONS_TIMEOUT=30
```

### 2. Start Required Services

#### Context7 (Official Documentation)

```bash
# Using Docker
docker run -d -p 8080:8080 context7/context7:latest

# Or using the Context7 MCP server
python -m context7_mcp.server --port 8080
```

#### Docs MCP (Indexed Documentation)

```bash
# Clone and start Docs MCP
git clone https://github.com/example/docs-mcp
cd docs-mcp
pip install -r requirements.txt
python server.py --port 8001
```

#### MetaMCP (Tool Aggregator)

```bash
# Using Docker
docker run -d -p 9000:9000 metamcp/metamcp:latest

# Or local setup
git clone https://github.com/example/metamcp
cd metamcp
docker-compose up -d
```

## Service Integration Details

### Knowledge Adapters

#### Context7 Adapter
- **Purpose**: Fetch up-to-date official documentation
- **Endpoint**: `http://localhost:8080`
- **Required**: Context7 server with library resolution
- **Features**:
  - Automatic library URI resolution
  - Current documentation retrieval
  - Source attribution with dates

#### Docs MCP Adapter
- **Purpose**: Query indexed documentation spaces
- **Endpoint**: `http://localhost:8001`
- **Required**: MCP server with indexed docs
- **Features**:
  - Fast search over pre-indexed content
  - Domain-specific filtering
  - Relevance scoring

#### Deep-Research Adapter
- **Purpose**: Web research when docs are insufficient
- **Endpoint**: `http://localhost:8002`
- **Required**: MCP server with web research capabilities
- **Features**:
  - Autonomous web research
  - Source citation
  - Fact verification

### Action Aggregators

#### MetaMCP
- **Purpose**: Unified tool discovery and execution
- **Endpoint**: `http://localhost:9000`
- **Features**:
  - Dynamic tool discovery
  - Tool execution proxy
  - Authentication brokering
  - Audit logging

#### Remote MCP Servers
- **Purpose**: Direct tool server connections
- **Format**: Comma-separated URLs
- **Features**:
  - Fallback when MetaMCP unavailable
  - Specialized tool domains
  - Direct server communication

## Domain Support

### Supported Domains

The capability layer supports the following domains:

| Domain | Description | Example Services |
|--------|-------------|------------------|
| `account/plan` | Service plans, pricing, quotas | ChatGPT Plus, AWS tiers, API limits |
| `search/web` | Web search and research | Google Search, Bing, research tools |
| `docs/api` | API documentation | REST APIs, SDKs, technical docs |
| `files/cloud` | Cloud storage and file operations | Google Drive, Dropbox, AWS S3 |
| `calendar` | Calendar and scheduling | Google Calendar, Outlook, iCal |
| `messaging` | Chat and communication | Slack, Teams, Discord |
| `payments` | Payment processing | Stripe, PayPal, Square |
| `transport` | Transportation and delivery | Uber, Lyft, delivery services |
| `maps` | Maps and location services | Google Maps, Mapbox, geocoding |
| `devops` | Development and operations | CI/CD, deployment, monitoring |
| `email` | Email services | Gmail, Outlook, SendGrid |

### Adding New Domains

To add a new domain:

1. **Update Ontology** (`config/ontology.yaml`):

```yaml
domains:
  new/domain:
    aliases: ["new", "domain", "related terms"]
```

2. **Configure Knowledge Sources**:
   - Add documentation to Docs MCP
   - Ensure Context7 has library coverage
   - Configure domain-specific research rules

3. **Add Tool Support**:
   - Create MCP tools for the domain
   - Register tools with MetaMCP
   - Update tool schemas and documentation

## Authentication Setup

### API Keys and Credentials

Store sensitive credentials securely:

```bash
# Context7
export CONTEXT7_API_KEY=sk-context7-...

# Service-specific credentials
export GOOGLE_API_KEY=your-google-key
export OPENAI_API_KEY=sk-openai-...
export STRIPE_SECRET_KEY=sk_test-...
```

### Auth Broker Configuration

The system includes an authentication broker in `auth.py`:

```python
from src.auth import get_auth_token

# Get scoped token for a service
token = get_auth_token("stripe", ["read", "write"])
```

## Testing the Integration

### 1. Test Knowledge Resolution

```bash
# Test routing
python -c "
from src.capability_router import route_request
result = route_request('What does ChatGPT Plus offer?')
print(f'Domain: {result.domain}, Mode: {result.mode}')
"

# Test knowledge resolution (requires running adapters)
python -c "
import asyncio
from src.knowledge_resolver import resolve_knowledge

async def test():
    result = await resolve_knowledge('ChatGPT Plus capabilities', 'account/plan')
    print(f'Capabilities: {result.capabilities}')
    print(f'API Access: {result.api_access}')

asyncio.run(test())
"
```

### 2. Test Action Execution

```bash
# Test tool listing
python -c "
import asyncio
from src.actions_gateway import list_available_tools

async def test():
    tools = await list_available_tools('files/cloud')
    for tool in tools:
        print(f'{tool.name}: {tool.description}')

asyncio.run(test())
"

# Test action execution
python -c "
import asyncio
from src.actions_gateway import execute_action

async def test():
    result = await execute_action('cloud-upload', {
        'file_path': '/tmp/test.txt',
        'destination': 'documents'
    })
    print(f'Success: {result.success}')
    print(f'Duration: {result.duration_ms}ms')

asyncio.run(test())
"
```

### 3. Test Slash Commands

```bash
# Test capabilities command
python src/commands/capabilities_command.py "What does ChatGPT Plus offer?"

# Test actions command
python src/commands/actions_command.py actions files/cloud

# Test act command (simulation)
python src/commands/actions_command.py act upload file=test.txt
```

### 4. Test MCP Integration

```bash
# Start MCP server
python mcp_server.py

# Test MCP tools (requires MCP client)
# Example using curl (simplified):
curl -X POST http://localhost:8000/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool_id": "oos_capabilities", "params": {"text": "ChatGPT Plus"}}'
```

## Troubleshooting

### Common Issues

#### Service Not Available
```bash
# Check service health
curl http://localhost:8080/health  # Context7
curl http://localhost:8001/health  # Docs MCP
curl http://localhost:9000/health  # MetaMCP
```

#### Authentication Failures
```bash
# Verify environment variables
env | grep -E '(API_KEY|SECRET|AUTH)'

# Test credentials
python -c "
from src.auth import validate_credentials
print(validate_credentials())
"
```

#### Domain Routing Issues
```bash
# Test ontology loading
python -c "
from src.capability_router import router
print('Available domains:', list(router.domains.keys()))
print('Info keywords:', router.mode_patterns.get('info_keywords', []))
"
```

#### Tool Execution Failures
```bash
# Check audit log
python -c "
import asyncio
from src.actions_gateway import ActionsGateway

async def test():
    gateway = ActionsGateway()
    audit = await gateway.get_audit_log()
    for entry in audit[-5:]:  # Last 5 entries
        print(f'{entry[\"timestamp\"]}: {entry[\"status\"]}')

asyncio.run(test())
"
```

### Performance Optimization

#### Caching
- Enable Redis for knowledge caching
- Configure cache TTL based on documentation update frequency
- Use CDN for static documentation

#### Connection Pooling
```bash
# Configure connection pooling
export MAX_CONNECTIONS=100
export CONNECTION_TIMEOUT=30
export KEEP_ALIVE=300
```

#### Rate Limiting
```bash
# Set rate limits for external APIs
export CONTEXT7_RATE_LIMIT=100
export DOCS_MCP_RATE_LIMIT=200
export META_MCP_RATE_LIMIT=50
```

## Security Considerations

### Credential Management
- Never commit API keys to version control
- Use environment variables or secret management
- Rotate keys regularly
- Implement key scoping and permissions

### Input Validation
- All user inputs are sanitized
- Tool parameters are validated against schemas
- File paths are restricted to allowed directories
- URLs are validated and filtered

### Audit Logging
- All actions are logged with timestamps
- Sensitive parameters are redacted
- Logs are retained for security analysis
- Access logs are monitored for anomalies

## Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  oos-capability:
    build: .
    environment:
      - CONTEXT7_URL=http://context7:8080
      - DOCS_MCP_URL=http://docs-mcp:8001
      - META_MCP_URL=http://metamcp:9000
    depends_on:
      - context7
      - docs-mcp
      - metamcp

  context7:
    image: context7/context7:latest
    ports:
      - "8080:8080"

  docs-mcp:
    image: docs-mcp:latest
    ports:
      - "8001:8001"

  metamcp:
    image: metamcp:latest
    ports:
      - "9000:9000"
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oos-capability-layer
spec:
  template:
    spec:
      containers:
      - name: oos
        image: oos/capability-layer:latest
        env:
        - name: CONTEXT7_URL
          value: "http://context7-service:8080"
        - name: DOCS_MCP_URL
          value: "http://docs-mcp-service:8001"
        - name: META_MCP_URL
          value: "http://metamcp-service:9000"
```

## Contributing

### Adding New Knowledge Sources

1. Implement adapter in `src/knowledge_resolver.py`
2. Add configuration options
3. Write tests in `tests/test_knowledge_resolver.py`
4. Update documentation

### Adding New Tool Aggregators

1. Implement client in `src/actions_gateway.py`
2. Add environment variables
3. Write tests in `tests/test_actions_gateway.py`
4. Update integration docs

### Extending Domains

1. Update `config/ontology.yaml`
2. Add test cases to `tests/test_capability_router.py`
3. Update documentation
4. Test with real-world queries

## Support

For issues and questions:
- Check existing tests for usage examples
- Review integration test cases
- Monitor audit logs for debugging
- Use health check endpoints for service status

---

*This documentation covers the OOS Capability Layer service integration. For general OOS documentation, see the main README.*