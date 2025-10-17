# Atlas Configuration Guide

This guide provides comprehensive information about configuring Atlas for different environments and use cases.

## Table of Contents

- [Configuration Overview](#configuration-overview)
- [Environment Setup](#environment-setup)
- [Configuration Files](#configuration-files)
- [Environment Variables](#environment-variables)
- [Secret Management](#secret-management)
- [Configuration Validation](#configuration-validation)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)

## Configuration Overview

Atlas uses a hierarchical configuration system that supports:

- **Environment-specific settings** (development, staging, production)
- **Encrypted secrets** for sensitive data
- **Schema validation** to ensure configuration correctness
- **Runtime configuration updates** without service restarts
- **Configuration export/import** for backup and migration

### Configuration Loading Order

1. **Default values** (built into the application)
2. **Environment files** (`.env` files)
3. **Environment variables** (system-level overrides)
4. **Runtime modifications** (via CLI or API)

## Environment Setup

### Supported Environments

Atlas supports four main environments:

- **development**: Local development with debug features enabled
- **staging**: Pre-production testing with production-like settings
- **production**: Live deployment with security and performance optimizations
- **testing**: Automated testing environment

### Environment Selection

Set the environment using the `ATLAS_ENVIRONMENT` variable:

```bash
# Set environment
export ATLAS_ENVIRONMENT=production

# Or use environment file
echo "ATLAS_ENVIRONMENT=production" >> config/.env
```

## Configuration Files

### File Structure

```
config/
├── .env                     # Main configuration file
├── development.env          # Development-specific overrides
├── staging.env             # Staging-specific overrides
├── production.env          # Production-specific overrides
├── testing.env             # Testing-specific overrides
├── schemas.yaml            # Configuration validation schemas
└── secrets/                # Secret files directory
    ├── development.secrets
    ├── staging.secrets
    └── production.secrets
```

### Main Configuration File (.env)

The primary configuration file contains system-wide settings:

```ini
# Environment
ATLAS_ENVIRONMENT=development

# Database
ATLAS_DATABASE_PATH=data/dev/atlas.db
DATABASE_WAL_MODE=true
DATABASE_TIMEOUT=30

# API Settings
API_HOST=0.0.0.0
API_PORT=7444
API_DEBUG=false
API_CORS_ORIGINS=*
API_RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Security
JWT_SECRET_KEY=your-secret-key-here
SESSION_SECRET=your-session-secret-here
API_TOKEN_REQUIRED=false

# Processing
MAX_CONCURRENT_ARTICLES=5
ARTICLE_PROCESSING_TIMEOUT=300
BACKLOG_PROCESSING_BATCH_SIZE=10

# External Services
OPENROUTER_API_KEY=your-openrouter-api-key
YOUTUBE_API_KEY=your-youtube-api-key
GOOGLE_SEARCH_API_KEY=your-google-search-api-key
GOOGLE_SEARCH_CX=your-google-search-cx

# Monitoring
MONITORING_ENABLED=true
MONITORING_PORT=7445
OBSERVABILITY_ENABLED=true
OBSERVABILITY_PORT=7446
METRICS_EXPORT_ENABLED=true
ALERTING_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/atlas.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Cache
CACHE_ENABLED=true
CACHE_TTL=300
CACHE_MAX_SIZE=1000

# Content Processing
CONTENT_PROCESSING_WORKERS=3
CONTENT_PROCESSING_QUEUE_SIZE=100
CONTENT_PROCESSING_RETRY_COUNT=3
CONTENT_PROCESSING_RETRY_DELAY=60

# Ingestors
YOUTUBE_INGESTOR_ENABLED=true
YOUTUBE_MAX_VIDEOS_PER_DAY=50
GOOGLE_SEARCH_INGESTOR_ENABLED=true
GOOGLE_SEARCH_MAX_RESULTS_PER_DAY=100
INSTAPAPER_INGESTOR_ENABLED=false
INSTAPAPER_LOGIN=your-instapaper-email
INSTAPAPER_PASSWORD=your-instapaper-password
FIRECRAWL_INGESTOR_ENABLED=false
FIRECRAWL_API_KEY=your-firecrawl-api-key

# Notifications
EMAIL_ENABLED=false
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Backup and Maintenance
AUTO_BACKUP_ENABLED=true
BACKUP_INTERVAL_HOURS=24
BACKUP_RETENTION_DAYS=30
LOG_ROTATION_ENABLED=true
LOG_RETENTION_DAYS=7
CLEANUP_ENABLED=true
CLEANUP_INTERVAL_HOURS=6
```

### Environment-Specific Files

#### development.env

```ini
# Development-specific settings
API_DEBUG=true
LOG_LEVEL=DEBUG
API_CORS_ORIGINS=http://localhost:3000,http://localhost:8080
DATABASE_PATH=data/dev/atlas_dev.db
```

#### staging.env

```ini
# Staging-specific settings
API_DEBUG=false
LOG_LEVEL=INFO
API_CORS_ORIGINS=https://staging.example.com
DATABASE_PATH=data/staging/atlas_staging.db
MONITORING_ENABLED=true
ALERTING_ENABLED=true
```

#### production.env

```ini
# Production-specific settings
API_DEBUG=false
LOG_LEVEL=WARNING
API_CORS_ORIGINS=https://example.com
DATABASE_PATH=data/prod/atlas_prod.db
MONITORING_ENABLED=true
ALERTING_ENABLED=true
METRICS_EXPORT_ENABLED=true
```

### Validation Schema (schemas.yaml)

The `schemas.yaml` file defines validation rules for all configuration parameters:

```yaml
ATLAS_ENVIRONMENT:
  type: str
  required: false
  default: "development"
  allowed_values: ["development", "staging", "production", "testing"]
  description: "Deployment environment"

API_PORT:
  type: int
  required: false
  default: 7444
  min_value: 1024
  max_value: 65535
  description: "API server port"

MAX_CONCURRENT_ARTICLES:
  type: int
  required: false
  default: 5
  min_value: 1
  max_value: 20
  description: "Maximum concurrent article processing"

LOG_LEVEL:
  type: str
  required: false
  default: "INFO"
  allowed_values: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
  description: "Logging level"

# ... more schema definitions
```

## Environment Variables

### Core Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ATLAS_ENVIRONMENT` | str | `development` | Deployment environment |
| `ATLAS_DATABASE_PATH` | str | `data/dev/atlas.db` | Database file path |
| `DATABASE_WAL_MODE` | bool | `true` | Enable WAL mode for better performance |
| `DATABASE_TIMEOUT` | int | `30` | Database timeout in seconds |

### API Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `API_HOST` | str | `0.0.0.0` | API server host |
| `API_PORT` | int | `7444` | API server port |
| `API_DEBUG` | bool | `false` | Enable debug mode |
| `API_CORS_ORIGINS` | str | `*` | CORS allowed origins |
| `API_RATE_LIMIT_REQUESTS_PER_MINUTE` | int | `60` | Rate limit requests per minute |

### Security Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `JWT_SECRET_KEY` | str | - | JWT signing secret |
| `SESSION_SECRET` | str | - | Session encryption secret |
| `API_TOKEN_REQUIRED` | bool | `false` | Require API token for access |

### Processing Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MAX_CONCURRENT_ARTICLES` | int | `5` | Maximum concurrent articles |
| `ARTICLE_PROCESSING_TIMEOUT` | int | `300` | Article processing timeout |
| `BACKLOG_PROCESSING_BATCH_SIZE` | int | `10` | Backlog processing batch size |

### External Services

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENROUTER_API_KEY` | str | - | OpenRouter API key |
| `YOUTUBE_API_KEY` | str | - | YouTube Data API v3 key |
| `GOOGLE_SEARCH_API_KEY` | str | - | Google Search API key |
| `GOOGLE_SEARCH_CX` | str | - | Google Search CX ID |

### Monitoring and Observability

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MONITORING_ENABLED` | bool | `true` | Enable monitoring dashboard |
| `MONITORING_PORT` | int | `7445` | Monitoring dashboard port |
| `OBSERVABILITY_ENABLED` | bool | `true` | Enable observability service |
| `OBSERVABILITY_PORT` | int | `7446` | Observability service port |
| `METRICS_EXPORT_ENABLED` | bool | `true` | Enable metrics export |
| `ALERTING_ENABLED` | bool | `true` | Enable alerting |

### Logging Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | str | `INFO` | Logging level |
| `LOG_FORMAT` | str | `json` | Log format |
| `LOG_FILE` | str | `logs/atlas.log` | Log file path |
| `LOG_MAX_SIZE` | int | `10485760` | Maximum log file size |
| `LOG_BACKUP_COUNT` | int | `5` | Number of log backups |

## Secret Management

### Secret Files

Secrets are stored in encrypted files within the `config/secrets/` directory:

```
config/secrets/
├── development.secrets
├── staging.secrets
└── production.secrets
```

### Secret Format

Secret files use the same format as configuration files but are encrypted:

```ini
# Database secrets
DATABASE_PASSWORD=encrypted:encrypted_password_here
DATABASE_USER=encrypted:encrypted_user_here

# API keys
OPENROUTER_API_KEY=encrypted:encrypted_api_key_here
YOUTUBE_API_KEY=encrypted:youtube_api_key_here

# Email credentials
EMAIL_USERNAME=encrypted:email_username_here
EMAIL_PASSWORD=encrypted:email_password_here
```

### Managing Secrets

#### Setting Secrets

```bash
# Set a secret
python3 tools/config_cli.py secret set DATABASE_PASSWORD my_password

# Set an encrypted secret
python3 tools/config_cli.py secret set API_KEY my_api_key --encrypt

# Set multiple secrets
python3 tools/config_cli.py secret set DATABASE_PASSWORD my_password DATABASE_USER my_user
```

#### Viewing Secrets

```bash
# List all secrets
python3 tools/config_cli.py secret list

# View a specific secret
python3 tools/config_cli.py secret show DATABASE_PASSWORD

# Show secret with default value
python3 tools/config_cli.py secret show NON_EXISTENT_SECRET --default "not_found"
```

#### Deleting Secrets

```bash
# Delete a secret
python3 tools/config_cli.py secret delete OLD_SECRET
```

#### Exporting Secrets

```bash
# Export secrets to environment file
python3 tools/config_cli.py secret export --format env > secrets.env

# Export secrets to JSON
python3 tools/config_cli.py secret export --format json > secrets.json

# Export with encryption
python3 tools/config_cli.py secret export --format env --encrypt > encrypted-secrets.env
```

#### Importing Secrets

```bash
# Import secrets from environment file
python3 tools/config_cli.py secret import --file secrets.env

# Import with encryption
python3 tools/config_cli.py secret import --file secrets.env --encrypt
```

#### Rotating Secrets

```bash
# Rotate a secret
python3 tools/config_cli.py secret rotate DATABASE_PASSWORD
```

### Encryption Configuration

Atlas uses Fernet encryption for secret management:

```bash
# Generate new encryption key
python3 tools/config_cli.py generate-key

# Set custom encryption key
export ATLAS_ENCRYPTION_KEY=your-fernet-key-here
```

## Configuration Validation

### Validation Rules

Configuration is validated against schemas defined in `schemas.yaml`:

- **Type validation**: Ensures correct data types
- **Range validation**: Checks numeric ranges
- **Enum validation**: Validates allowed values
- **Required validation**: Ensures required values are present
- **Pattern validation**: Validates string patterns

### Running Validation

```bash
# Validate all configuration
python3 tools/config_cli.py validate

# Validate specific key
python3 tools/config_cli.py validate --key API_PORT

# Validate with detailed output
python3 tools/config_cli.py validate --verbose

# Fix validation errors automatically
python3 tools/config_cli.py validate --fix
```

### Validation Output

```bash
🔧 Configuration Validation Report
========================================

✅ SUCCESS: All configuration values are valid

Configuration Summary:
- Total values: 45
- Environment: development
- Database: SQLite (WAL enabled)
- API: Port 7444, Debug mode disabled
- Processing: 5 concurrent workers
- Monitoring: Enabled
- Security: Token authentication disabled
```

## Advanced Configuration

### Configuration Profiles

Create custom configuration profiles for different use cases:

```bash
# Create profile for high-performance mode
python3 tools/config_cli.py profile create high-performance

# Apply profile
python3 tools/config_cli.py profile apply high-performance

# List profiles
python3 tools/config_cli.py profile list
```

### Dynamic Configuration

Update configuration without restarting services:

```bash
# Update configuration at runtime
python3 tools/config_cli.py set MAX_CONCURRENT_ARTICLES 10 --runtime

# Reload configuration
python3 tools/config_cli.py reload
```

### Configuration Templates

Create configuration templates for different environments:

```yaml
# templates/production.yaml
environment: production
database:
  path: /data/atlas/prod/atlas.db
  wal_mode: true
  timeout: 30
api:
  host: 0.0.0.0
  port: 7444
  debug: false
  cors_origins:
    - https://example.com
monitoring:
  enabled: true
  port: 7445
```

### Environment Overrides

Override specific settings for different environments:

```bash
# Override for staging
export ATLAS_ENVIRONMENT=staging
export API_PORT=7445
export LOG_LEVEL=DEBUG

# Override for production
export ATLAS_ENVIRONMENT=production
export API_PORT=80
export LOG_LEVEL=WARNING
```

## Troubleshooting

### Common Configuration Issues

#### Missing Required Configuration

**Error**: `Required configuration 'DATABASE_PATH' not found`

**Solution**:
```bash
# Set the required configuration
python3 tools/config_cli.py set DATABASE_PATH data/atlas.db

# Or set environment variable
export ATLAS_DATABASE_PATH=data/atlas.db
```

#### Invalid Configuration Values

**Error**: `Configuration validation failed for 'API_PORT': value must be between 1024 and 65535`

**Solution**:
```bash
# Set valid value
python3 tools/config_cli.py set API_PORT 7444
```

#### Secret Decryption Failure

**Error**: `Failed to decrypt secret 'API_KEY'`

**Solution**:
```bash
# Check encryption key
echo $ATLAS_ENCRYPTION_KEY

# Generate new key if needed
python3 tools/config_cli.py generate-key

# Reset secret
python3 tools/config_cli.py secret set API_KEY new_api_key
```

#### Database Connection Issues

**Error**: `Unable to connect to database`

**Solution**:
```bash
# Check database path
python3 tools/config_cli.py show ATLAS_DATABASE_PATH

# Verify directory exists
mkdir -p $(dirname $(python3 tools/config_cli.py show ATLAS_DATABASE_PATH))

# Check file permissions
ls -la $(python3 tools/config_cli.py show ATLAS_DATABASE_PATH)
```

### Debug Configuration

```bash
# Show current configuration
python3 tools/config_cli.py show

# Show configuration with values
python3 tools/config_cli.py show --values

# Show configuration source
python3 tools/config_cli.py show --source

# Export configuration for debugging
python3 tools/config_cli.py export --format json > debug-config.json
```

### Configuration Backup and Restore

#### Backup Configuration

```bash
# Backup configuration
python3 tools/config_cli.py export --format yaml > config-backup-$(date +%Y%m%d).yaml

# Backup secrets
python3 tools/config_cli.py secret export --format env > secrets-backup-$(date +%Y%m%d).env
```

#### Restore Configuration

```bash
# Restore configuration
python3 tools/config_cli.py import --file config-backup-YYYYMMDD.yaml

# Restore secrets
python3 tools/config_cli.py secret import --file secrets-backup-YYYYMMDD.env
```

### Configuration Security

#### Secure Configuration Practices

1. **Use Environment Variables** for sensitive data
2. **Encrypt Secrets** using the secret management system
3. **Restrict File Permissions** on configuration files
4. **Use Different Secrets** for different environments
5. **Rotate Secrets** regularly
6. **Audit Configuration** changes

#### File Permissions

```bash
# Set secure permissions
chmod 600 config/.env
chmod 600 config/secrets/*.secrets
chmod 644 config/schemas.yaml
```

#### Environment Variables Security

```bash
# Set secure environment variables
export ATLAS_ENCRYPTION_KEY=$(openssl rand -hex 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export SESSION_SECRET=$(openssl rand -hex 32)
```

### Performance Optimization

#### Database Configuration

```bash
# Enable WAL mode for better performance
python3 tools/config_cli.py set DATABASE_WAL_MODE true

# Optimize database timeout
python3 tools/config_cli.py set DATABASE_TIMEOUT 60

# Set appropriate journal mode
python3 tools/config_cli.py set DATABASE_JOURNAL_MODE WAL
```

#### Processing Configuration

```bash
# Optimize concurrent processing
python3 tools/config_cli.py set MAX_CONCURRENT_ARTICLES $(nproc)

# Set appropriate timeouts
python3 tools/config_cli.py set ARTICLE_PROCESSING_TIMEOUT 600

# Configure retry settings
python3 tools/config_cli.py set CONTENT_PROCESSING_RETRY_COUNT 5
python3 tools/config_cli.py set CONTENT_PROCESSING_RETRY_DELAY 120
```

#### Cache Configuration

```bash
# Enable caching
python3 tools/config_cli.py set CACHE_ENABLED true

# Set appropriate cache TTL
python3 tools/config_cli.py set CACHE_TTL 600

# Configure cache size
python3 tools/config_cli.py set CACHE_MAX_SIZE 2000
```

---

*This guide is part of the Atlas documentation. For additional information, see other files in the `docs/` directory.*