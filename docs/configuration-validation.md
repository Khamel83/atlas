# Configuration Validation System

Atlas includes a comprehensive configuration validation system that provides detailed error messages and specific guidance for resolving configuration issues.

## Features

### ✅ Enhanced Error Messages
- Detailed explanations of what's wrong
- Specific guidance on how to fix issues
- Ready-to-run fix commands
- Links to relevant documentation

### ✅ Multiple Validation Levels
- **Errors**: Issues that prevent Atlas from working
- **Warnings**: Suggestions for better performance, security, or cost optimization
- **Info**: Additional recommendations

### ✅ Smart Detection
- Invalid API key formats
- Placeholder credentials
- Expensive model configurations
- Security and privacy concerns
- Performance optimization opportunities

## Usage

### Command Line Validation

```bash
# Basic validation report
python scripts/validate_config.py

# JSON output for automation
python scripts/validate_config.py --json

# Show only fix commands
python scripts/validate_config.py --fix

# Show only errors (no warnings)
python scripts/validate_config.py --errors-only

# Quiet mode (only output if issues found)
python scripts/validate_config.py --quiet
```

### Programmatic Usage

```python
from helpers.validate import ConfigValidator, validate_config_enhanced

# Load your config
from helpers.config import load_config
config = load_config()

# Enhanced validation with detailed guidance
validator = ConfigValidator()
errors, warnings = validator.validate_config(config)

# Print formatted report
if errors or warnings:
    report = validator.format_validation_report(errors, warnings)
    print(report)

# Or use the convenience function
errors, warnings = validate_config_enhanced(config)
```

## Common Issues and Solutions

### Missing API Keys

**Error**: `OPENROUTER_API_KEY is required when llm_provider is 'openrouter'`

**Solution**:
1. Get your API key from https://openrouter.ai/keys
2. Add it to your `.env` file:
   ```bash
   echo 'OPENROUTER_API_KEY=your_key_here' >> config/.env
   ```

### Invalid API Key Format

**Error**: `OpenRouter API key format appears invalid`

**Guidance**: OpenRouter API keys should start with `sk-or-v1-`. Verify your key at https://openrouter.ai/keys

### Expensive Model Configuration

**Warning**: `Using expensive model without budget tier configured`

**Suggestion**: Configure a budget model for simple tasks:
```bash
echo 'MODEL_BUDGET=mistralai/mistral-7b-instruct:free' >> config/.env
```

### High Resource Usage

**Warning**: `High podcast episode limit (200) may impact performance`

**Suggestion**: Consider a lower limit for better performance:
```bash
sed -i 's/PODCAST_EPISODE_LIMIT=200/PODCAST_EPISODE_LIMIT=20/' config/.env
```

### Privacy Concerns

**Warning**: `12ft.io fallback is enabled - potential privacy concern`

**Guidance**: The 12ft.io service sends URLs to a third-party service. Disable if privacy is important:
```bash
sed -i 's/USE_12FT_IO_FALLBACK=true/USE_12FT_IO_FALLBACK=false/' config/.env
```

## Validation Categories

### 1. LLM Configuration
- Provider validation (openrouter, deepseek, ollama)
- Model configuration
- API key requirements and format validation
- Cost optimization suggestions

### 2. API Keys and Credentials
- Required API keys for enabled features
- Credential format validation
- Placeholder detection
- Security best practices

### 3. Ingestor Configuration
- YouTube API requirements
- Instapaper credentials
- NYT subscription validation
- Feature-specific requirements

### 4. Paths and Storage
- Data directory accessibility
- Write permissions
- Subdirectory creation
- Storage space considerations

### 5. Performance Settings
- Resource usage optimization
- Episode limits and batch sizes
- Memory management
- Processing efficiency

### 6. Security and Privacy
- Credential security
- Third-party service usage
- Data transmission policies
- Access control validation

## Validation Error Structure

Each validation error includes:

```python
ValidationError(
    field="field_name",              # The configuration field
    message="Brief description",     # What's wrong
    severity="error|warning|info",   # How critical it is
    guidance="Detailed explanation", # How to fix it
    fix_command="command",          # Ready-to-run fix
    documentation_url="https://..."  # More information
)
```

## Integration with Atlas

The validation system is automatically integrated into Atlas:

1. **Startup Validation**: Atlas validates configuration on startup
2. **Enhanced Error Messages**: All configuration errors include guidance
3. **Development Workflow**: Validation runs during development and testing
4. **CI/CD Integration**: Validation can be automated in deployment pipelines

## Example Output

```
🔧 Configuration Validation Report
========================================

❌ ERRORS (1 found) - These must be fixed:

1. OPENROUTER_API_KEY: OpenRouter API key is required but not configured
   💡 How to fix: Get your API key from https://openrouter.ai/keys and add it to your .env file. OpenRouter provides access to multiple AI models with pay-per-use pricing.
   🔨 Quick fix: echo 'OPENROUTER_API_KEY=your_key_here' >> config/.env
   📖 Docs: https://openrouter.ai/docs/quick-start

⚠️  WARNINGS (2 found) - Consider addressing:

1. llm_model_budget: No budget model configured for cost optimization
   💡 Suggestion: Configure a budget model to reduce costs for simple tasks. Recommended budget models:
- OpenRouter: 'mistralai/mistral-7b-instruct:free' or 'google/gemma-2-9b-it:free'
- DeepSeek: Use the same model as default for simplicity
   🔨 Optional fix: echo 'MODEL_BUDGET=mistralai/mistral-7b-instruct:free' >> config/.env

========================================

❗ Application may not work correctly until errors are resolved.
```

## Testing

The validation system includes comprehensive tests:

```bash
# Run validation tests
python -m pytest tests/test_enhanced_validation.py -v

# Run demo
python demo_validation.py
```

This enhanced validation system ensures users can quickly identify and resolve configuration issues, making Atlas more reliable and user-friendly.