# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-08-01-atlas-production-ready-system/spec.md

## API Architecture

### Base Configuration
- **Base URL**: `http://localhost:8000/api/v1`
- **Authentication**: API Key authentication for personal project integrations
- **Rate Limiting**: 1000 requests per hour per API key
- **Response Format**: JSON with consistent error handling

## Core API Endpoints

### Content Management
- **GET /content** - List all processed content with pagination and filtering
- **GET /content/{id}** - Retrieve specific content item with full metadata
- **POST /content** - Add new content for processing (URL or file upload)
- **DELETE /content/{id}** - Remove content and associated data

### Search Operations
- **GET /search** - Full-text search across all content with faceted filtering
- **GET /search/semantic** - Semantic search using vector embeddings
- **GET /search/suggestions** - Search suggestions and auto-complete

### Cognitive Amplification
- **GET /cognitive/proactive** - Retrieve forgotten or stale content recommendations
- **GET /cognitive/temporal** - Find time-aware relationships between content
- **POST /cognitive/socratic** - Generate Socratic questions from content
- **GET /cognitive/recall** - Spaced repetition items for review
- **GET /cognitive/patterns** - Pattern detection across tags and sources

### Analytics & Insights
- **GET /analytics/usage** - Content consumption patterns and statistics
- **GET /analytics/performance** - System performance metrics and health
- **GET /analytics/trends** - Content trends and emerging patterns

### System Management
- **GET /system/health** - System health status and diagnostics
- **GET /system/stats** - System statistics and resource usage
- **POST /system/maintenance** - Trigger maintenance operations
- **GET /system/logs** - Retrieve system logs with filtering

## Webhook System

### Event Types
- **content.processed** - Fired when new content is successfully processed
- **content.failed** - Fired when content processing fails
- **cognitive.insight** - Fired when new cognitive insights are generated
- **system.health** - Fired on system health changes

### Webhook Configuration
- **POST /webhooks** - Register new webhook endpoint
- **GET /webhooks** - List configured webhooks
- **DELETE /webhooks/{id}** - Remove webhook configuration

## Authentication & Security

### API Key Management
- **POST /auth/keys** - Generate new API key with permissions
- **GET /auth/keys** - List active API keys
- **DELETE /auth/keys/{id}** - Revoke API key

### Rate Limiting
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **429 Response**: Rate limit exceeded with retry-after header

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": ["field 'url' is required"],
    "timestamp": "2025-08-01T12:00:00Z"
  }
}
```

### Error Codes
- **400**: Bad Request - Invalid request format or parameters
- **401**: Unauthorized - Invalid or missing API key
- **403**: Forbidden - Insufficient permissions
- **404**: Not Found - Resource not found
- **429**: Too Many Requests - Rate limit exceeded
- **500**: Internal Server Error - System error with tracking ID