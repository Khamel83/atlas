# Atlas Siri Shortcuts

This module provides comprehensive functionality for creating and managing Siri shortcuts in the Atlas system.

## Features Implemented

### ✅ SiriShortcut Dataclass with Action Definitions
- **ActionType enum** with supported actions: `LOG_ENTRY`, `START_TIMER`, `CREATE_NOTE`, `CAPTURE_URL`, `VOICE_MEMO`
- **SiriShortcut dataclass** with validation for all parameters
- **Content type support** for URL, text, voice, image, and file

### ✅ ShortcutTemplate Class for .shortcut File Generation
- **Complete .shortcut file structure** generation
- **iOS-compatible workflow actions** with proper identifiers
- **Voice capture template** for "Hey Siri, save to Atlas" functionality

### ✅ Parameter Validation and Type Checking
- **Comprehensive validation** for all shortcut parameters
- **Action-specific parameter validation** (e.g., LOG_ENTRY requires 'type' parameter)
- **Content type validation** with case-sensitive checking

### ✅ Error Handling for Malformed Shortcuts
- **JSON decode error handling** for malformed files
- **File not found handling** with clear error messages
- **Shortcut validation** with detailed error reporting

### ✅ Unit Tests for Shortcut Generation
- **9 comprehensive unit tests** covering all functionality
- **Parameter validation tests** for edge cases
- **Error handling tests** for robustness

## Usage Examples

```python
from siri_shortcuts import SiriShortcutManager, ActionType

# Initialize the shortcut manager
manager = SiriShortcutManager("my_shortcuts")

# Create a mood logging shortcut
manager.create_shortcut(
    name="log_mood",
    phrase="Log my mood",
    action=ActionType.LOG_ENTRY,
    parameters={"type": "mood", "category": "wellness"},
    content_types=["text"]
)

# Create a focus timer shortcut
manager.create_shortcut(
    name="start_focus",
    phrase="Start focus time",
    action=ActionType.START_TIMER,
    parameters={"duration": 25, "task_type": "focused_work"},
    content_types=["text"]
)

# Create a voice memo shortcut
manager.create_shortcut(
    name="capture_voice_memo",
    phrase="Capture voice memo",
    action=ActionType.VOICE_MEMO,
    parameters={"transcription": True, "category": "ideas"},
    content_types=["voice"]
)

# Create the voice capture shortcut
manager.create_voice_capture_shortcut()

# List all shortcuts
shortcuts = manager.list_shortcuts()

# Execute a shortcut
result = manager.execute_shortcut("log_mood")

# Process a voice memo
audio_data = b"your audio data here"
result = manager.process_voice_memo(audio_data, {"source": "siri"})

# Validate a shortcut file
validation = manager.validate_shortcut_file("log_mood")
```

## File Generation

The module generates two types of files for each shortcut:

1. **.json files** - Internal use for shortcut management
2. **.shortcut files** - iOS importable shortcut files

## API Reference

### SiriShortcutManager

#### `__init__(shortcuts_dir: str = "shortcuts")`
Initialize the manager with a directory for storing shortcuts.

#### `create_shortcut(name: str, phrase: str, action: ActionType, parameters: Optional[Dict[str, Any]] = None, content_types: Optional[List[str]] = None) -> str`
Create a new Siri shortcut and save it to JSON and .shortcut files.

#### `create_voice_capture_shortcut() -> str`
Create the "Hey Siri, save to Atlas" voice capture shortcut.

#### `execute_shortcut(name: str) -> Dict[str, Any]`
Execute a shortcut by name.

#### `list_shortcuts() -> Dict[str, Any]`
List all available shortcuts.

#### `validate_shortcut_file(name: str) -> Dict[str, Any]`
Validate a shortcut file for errors.

#### `process_voice_memo(audio_data: bytes, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`
Process a voice memo with transcription and analysis (stub implementation).

### ActionType Enum

Supported action types:
- `LOG_ENTRY` - Log an entry in Atlas
- `START_TIMER` - Start a timer
- `CREATE_NOTE` - Create a note
- `CAPTURE_URL` - Capture a URL
- `VOICE_MEMO` - Record a voice memo

## Testing

Run the unit tests to verify functionality:

```bash
python -m unittest test_siri_shortcuts.py
```

## Requirements

- Python 3.7+
- No external dependencies

## Implementation Status

✅ **BLOCK7.1.1 Siri Shortcuts Manager Core** - COMPLETE
- ✅ Create SiriShortcut dataclass with action definitions
- ✅ Build ShortcutTemplate class for .shortcut file generation
- ✅ Implement parameter validation and type checking
- ✅ Add error handling for malformed shortcuts
- ✅ Write unit tests for shortcut generation

✅ **BLOCK7.1.2 Voice-Activated Content Capture** - PARTIALLY COMPLETE
- ✅ Create "Hey Siri, save to Atlas" shortcut template
- ✅ Implement voice memo processing with transcription (stub)
- ✅ Add automatic categorization based on speech content (stub)
- [ ] Build retry logic for failed voice captures (stub)
- [ ] Test voice shortcuts on iOS device (stub)