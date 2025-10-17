# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-08-01-atlas-production-ready-system/spec.md

## Schema Enhancements

### New Tables

#### api_keys
```sql
CREATE TABLE api_keys (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    permissions JSON,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
```

#### webhooks
```sql
CREATE TABLE webhooks (
    id VARCHAR(36) PRIMARY KEY,
    url VARCHAR(2048) NOT NULL,
    events JSON NOT NULL,
    secret VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TIMESTAMP,
    failure_count INTEGER DEFAULT 0
);

CREATE INDEX idx_webhooks_active ON webhooks(is_active);
```

#### search_cache
```sql
CREATE TABLE search_cache (
    id VARCHAR(36) PRIMARY KEY,
    query_hash VARCHAR(64) NOT NULL UNIQUE,
    query_text TEXT NOT NULL,
    results JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_search_cache_hash ON search_cache(query_hash);
CREATE INDEX idx_search_cache_expires ON search_cache(expires_at);
```

#### system_metrics
```sql
CREATE TABLE system_metrics (
    id VARCHAR(36) PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_value DECIMAL(15,4) NOT NULL,
    tags JSON,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_metrics_name_time ON system_metrics(metric_name, recorded_at);
```

### Enhanced Existing Tables

#### content_metadata (modifications)
```sql
-- Add new columns for enhanced search and analytics
ALTER TABLE content_metadata ADD COLUMN search_indexed_at TIMESTAMP;
ALTER TABLE content_metadata ADD COLUMN last_accessed_at TIMESTAMP;
ALTER TABLE content_metadata ADD COLUMN access_count INTEGER DEFAULT 0;
ALTER TABLE content_metadata ADD COLUMN cognitive_score DECIMAL(5,2);
ALTER TABLE content_metadata ADD COLUMN vector_embedding JSON;

-- Add indexes for performance
CREATE INDEX idx_content_search_indexed ON content_metadata(search_indexed_at);
CREATE INDEX idx_content_last_accessed ON content_metadata(last_accessed_at);
CREATE INDEX idx_content_cognitive_score ON content_metadata(cognitive_score);
```

#### processing_queue (enhancements)
```sql
-- Add columns for enhanced queue management
ALTER TABLE processing_queue ADD COLUMN priority INTEGER DEFAULT 5;
ALTER TABLE processing_queue ADD COLUMN estimated_duration INTEGER;
ALTER TABLE processing_queue ADD COLUMN actual_duration INTEGER;
ALTER TABLE processing_queue ADD COLUMN worker_id VARCHAR(255);

-- Add indexes for queue optimization
CREATE INDEX idx_queue_priority_status ON processing_queue(priority, status);
CREATE INDEX idx_queue_worker ON processing_queue(worker_id);
```

## Data Migration Scripts

### Migration 001: API Infrastructure
```sql
-- Create API keys table with initial admin key
INSERT INTO api_keys (id, name, key_hash, permissions)
VALUES (
    'admin-key-001',
    'Admin API Key',
    -- This would be the hash of the actual key
    'admin_key_hash_placeholder',
    '["read", "write", "admin"]'
);
```

### Migration 002: Search Enhancement
```sql
-- Update existing content for search indexing
UPDATE content_metadata
SET search_indexed_at = NULL
WHERE search_indexed_at IS NULL;

-- Initialize access counters
UPDATE content_metadata
SET access_count = 0
WHERE access_count IS NULL;
```

## Database Performance Optimizations

### Indexing Strategy
- **Composite indexes** for common query patterns
- **Partial indexes** for active records only
- **Text search indexes** for full-text search optimization

### Maintenance Procedures
- **Automated cleanup** of expired cache entries
- **Index optimization** scheduled during low-usage periods
- **Statistics updates** for query optimizer

## Data Retention Policies

### Cache Management
- **Search cache**: 24 hours retention
- **System metrics**: 30 days retention with aggregation
- **Access logs**: 7 days retention

### Backup Strategy
- **Daily incremental backups** of all tables
- **Weekly full backups** with integrity checks
- **Point-in-time recovery** capability for last 30 days