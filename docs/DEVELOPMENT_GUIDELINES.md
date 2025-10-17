# Atlas Development Guidelines

## Configuration Management

### The .env Rule: NO HARDCODED VALUES

**RULE**: All user-configurable values MUST be in `.env` with environment variable support.

**✅ GOOD**:
```python
import os
from helpers.config import load_config

# Use config system
config = load_config()
api_key = config.get('API_KEY')

# Or direct environment access with defaults
timeout = int(os.environ.get('PROCESSING_TIMEOUT', '30'))
base_url = os.environ.get('API_BASE_URL', 'https://api.example.com')

# Atlas secrets pattern: .env has variable definitions, ~/.secrets/ has values
# .env file contains:
# API_KEY=${API_KEY:-default_value}  # pragma: allowlist secret
# ~/.secrets/atlas.env contains:
# export API_KEY=actual_secret_value  # pragma: allowlist secret
```

**❌ BAD**:
```python
# Never hardcode these values
API_KEY = "sk-1234567890"
TIMEOUT = 30
BASE_URL = "https://api.example.com"
SAVE_FOLDER = "/Users/username/Documents/atlas"
```

### What Must Be Configurable

**Always use .env for**:
- **Credentials**: API keys, passwords, tokens
- **Paths**: File/directory paths, URLs, endpoints
- **Limits**: Timeouts, retry counts, batch sizes
- **Features**: Enable/disable flags, mode switches
- **Services**: Port numbers, host addresses

### Configuration Best Practices

1. **Update env.template**: Add new variables with descriptions
2. **Add to .env**: Use Atlas secrets pattern `VAR=${VAR:-default}`
3. **Add to ~/.secrets/atlas.env**: Set actual secret values with `export VAR=value`
4. **Provide defaults**: Use sensible fallback values
5. **Document requirements**: Mark required vs optional in comments
6. **Type conversion**: Cast strings to appropriate types
7. **Validation**: Check for required variables at startup

### Example Implementation

```python
import os
from typing import Optional

class EmailConfig:
    def __init__(self):
        # Required - will fail if not set
        self.enabled = os.environ.get('GMAIL_ENABLED', 'false').lower() == 'true'

        # Optional with sensible defaults
        self.sync_frequency = int(os.environ.get('GMAIL_SYNC_FREQUENCY', '30'))
        self.max_emails = int(os.environ.get('GMAIL_MAX_EMAILS_PER_SYNC', '100'))

        # Paths with defaults
        self.credentials_path = os.environ.get(
            'GMAIL_CREDENTIALS_PATH',
            'email_download_historical/credentials.json'
        )

        # Validate required settings
        if self.enabled and not os.path.exists(self.credentials_path):
            raise ValueError(f"Gmail enabled but credentials not found: {self.credentials_path}")
```

---

## Code Quality Standards

### Error Handling
- Always handle API failures gracefully
- Log errors with context for debugging
- Provide fallback behavior when possible
- Never expose credentials in error messages

### Logging
- Use structured logging with appropriate levels
- Include context (file, function, operation)
- Log configuration values at startup (mask secrets)
- Use logger from `helpers.config`

### Documentation
- Update CLAUDE.md for major features
- Document .env variables in env.template
- Create setup guides for manual steps
- Use clear commit messages

### Testing
- Test with different .env configurations
- Mock external services in tests
- Test error conditions and edge cases
- Include configuration validation tests

---

## File Organization

### Configuration Files
- `env.template`: All possible configuration options with defaults
- `.env`: Variable definitions using Atlas secrets pattern (safe to commit)
- `~/.secrets/atlas.env`: Actual secret values (never commit, secure permissions)
- `helpers/config.py`: Configuration loading and validation
- `docs/SETUP_GUIDES/`: Manual configuration instructions

### Code Structure
- Keep configuration at top of files
- Group related .env variables together
- Use descriptive variable names
- Include type hints for configuration classes

---

This ensures Atlas remains configurable, maintainable, and deployable across different environments without code changes.