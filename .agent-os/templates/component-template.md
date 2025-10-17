# Atlas Component Template

## Component Name: {COMPONENT_NAME}

### Purpose
Brief description of what this component does and why it exists.

### Dependencies
- List required dependencies
- Both internal Atlas components and external libraries

### API Surface
```python
class {ComponentName}:
    def __init__(self, config: Config):
        """Initialize component with configuration."""

    def main_method(self, input_data: DataType) -> ReturnType:
        """Primary method description."""

    def _private_method(self) -> None:
        """Internal helper method."""
```

### Configuration
Environment variables or settings required:
```env
COMPONENT_SETTING=default_value
COMPONENT_TIMEOUT=30
```

### Error Handling
- Describe expected exceptions
- Fallback behaviors
- Retry logic if applicable

### Testing
```python
def test_{component_name}_basic_functionality():
    """Test basic component operation."""

def test_{component_name}_error_handling():
    """Test error scenarios."""
```

### Integration Points
- How this component integrates with other Atlas systems
- Data flow in and out
- Event triggers or scheduling

### Performance Considerations
- Memory usage patterns
- CPU intensity
- I/O requirements
- Scaling characteristics

### Monitoring
- Key metrics to track
- Health check endpoints
- Logging patterns

### Future Enhancements
- Planned improvements
- Known limitations
- Extension points