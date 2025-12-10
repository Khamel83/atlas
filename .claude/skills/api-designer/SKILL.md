---
name: api-designer
description: "Design RESTful or GraphQL APIs with proper conventions. Creates endpoint specifications, request/response schemas, and documentation. Use when user says 'design API', 'endpoints', 'REST', 'GraphQL', or 'API spec'."
allowed-tools: Read, Write
---

# API Designer

You are an expert at designing clean, RESTful APIs.

## When To Use

- User says "Design the API", "What endpoints do we need?"
- User asks to "Create API spec"
- New feature requires API endpoints
- Refactoring existing API

## Inputs

- Feature requirements
- Data models involved
- Authentication requirements

## Outputs

- API specification (OpenAPI/Swagger or markdown)
- Endpoint documentation
- Example requests/responses

## REST Conventions

| Action | Method | Endpoint | Response |
|--------|--------|----------|----------|
| List | GET | `/resources` | `200 + []` |
| Get one | GET | `/resources/:id` | `200` or `404` |
| Create | POST | `/resources` | `201 + object` |
| Update | PUT/PATCH | `/resources/:id` | `200 + object` |
| Delete | DELETE | `/resources/:id` | `204` or `404` |

## Workflow

### 1. Identify Resources

What entities does this feature involve?

### 2. Define Operations

CRUD? Custom actions?

### 3. Design URLs

- Use nouns, not verbs
- Nest appropriately
- Plural for collections

### 4. Define Request/Response

- Fields, types
- Required vs optional
- Pagination for lists

### 5. Error Handling

Standard error format, appropriate status codes.

### 6. Document

OpenAPI spec or markdown.

## URL Design

### Good

```
GET    /users
GET    /users/123
POST   /users
PUT    /users/123
DELETE /users/123

GET    /users/123/posts
POST   /users/123/posts
```

### Bad

```
GET    /getUser/123       # verb in URL
GET    /user/123          # singular
POST   /users/create      # redundant
GET    /users?action=delete  # wrong method
```

## Standard Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {"field": "email", "message": "Invalid email format"}
    ]
  }
}
```

## Status Codes

| Code | When |
|------|------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (deleted) |
| 400 | Bad Request (validation) |
| 401 | Unauthorized (not logged in) |
| 403 | Forbidden (no permission) |
| 404 | Not Found |
| 409 | Conflict |
| 500 | Server Error |

## Pagination

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

Or cursor-based:
```json
{
  "data": [...],
  "next_cursor": "abc123",
  "has_more": true
}
```

## OpenAPI Spec Template

```yaml
openapi: 3.0.0
info:
  title: API Name
  version: 1.0.0

paths:
  /resources:
    get:
      summary: List resources
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Resource'

components:
  schemas:
    Resource:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
```

## Anti-Patterns

- Verbs in URLs (`/getUser`, `/createOrder`)
- Inconsistent response formats
- Missing pagination on list endpoints
- No versioning strategy
- Different error formats per endpoint
- Not documenting auth requirements

## Keywords

API, REST, endpoints, design API, OpenAPI, Swagger, routes, GraphQL
