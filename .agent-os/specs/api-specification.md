# Atlas API Specification

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently uses basic authentication. Production deployment should implement JWT tokens.

## Core Endpoints

### Health Check
```http
GET /api/v1/health
```
**Response**: System health status

### Content Search
```http
GET /api/v1/search/?query={query}&limit={limit}
```
**Parameters**:
- `query`: Search terms
- `limit`: Number of results (default: 10)

**Response**: Array of content items with relevance scoring

### Dashboard
```http
GET /api/v1/dashboard/
```
**Response**: HTML dashboard interface

### Analytics
```http
GET /api/v1/dashboard/analytics
```
**Response**: JSON analytics data including:
- Total items processed
- Content type distribution
- Processing statistics
- System metrics

## Data Models

### ContentMetadata
```python
{
    "id": str,
    "title": str,
    "content_type": ContentType,
    "source_url": str,
    "created_at": datetime,
    "metadata": dict,
    "evaluation": dict,
    "status": ProcessingStatus
}
```

### SearchResult
```python
{
    "content_id": str,
    "title": str,
    "content_type": str,
    "url": str,
    "relevance_score": float,
    "snippet": str
}
```

## Error Handling
All endpoints return standard HTTP status codes:
- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

## Rate Limiting
No rate limiting currently implemented. Consider adding for production.

## CORS
CORS is enabled for development. Configure appropriately for production deployment.