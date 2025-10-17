#!/usr/bin/env python3
"""
Apple Shortcuts Manager - Pre-built shortcuts for Atlas ingestion
Creates and manages Apple Shortcuts for seamless content capture from iOS/iPadOS/macOS.

CORE PRINCIPLE: ONE-TAP CAPTURE FROM ANY APPLE DEVICE
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from helpers.utils import log_info, log_error


class ShortcutsManager:
    """
    Manager for Apple Shortcuts integration with Atlas.

    Provides:
    - Pre-built shortcut configurations
    - Shortcut generation and export
    - Webhook endpoint management
    - Device-specific optimization
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Shortcuts Manager."""
        self.config = config or {}
        self.shortcuts_dir = Path('shortcuts')
        self.shortcuts_dir.mkdir(exist_ok=True)

        # Default webhook URL (can be configured)
        self.webhook_base = self.config.get('webhook_base_url', 'http://localhost:8081')

        # Shortcut definitions
        self.shortcuts = self._load_shortcut_definitions()

    def _load_shortcut_definitions(self) -> Dict[str, Dict]:
        """Load pre-defined shortcut configurations."""
        return {
            'atlas_capture_url': {
                'name': 'Atlas: Capture URL',
                'description': 'Send any URL to Atlas for processing',
                'icon': 'link',
                'color': 'blue',
                'inputs': ['url'],
                'actions': [
                    {'type': 'get_url_from_input'},
                    {'type': 'post_to_webhook', 'url': f'{self.webhook_base}/capture/url'},
                    {'type': 'show_notification', 'message': 'URL captured to Atlas!'}
                ]
            },

            'atlas_capture_text': {
                'name': 'Atlas: Capture Text',
                'description': 'Send selected text or typed text to Atlas',
                'icon': 'text.justify',
                'color': 'green',
                'inputs': ['text'],
                'actions': [
                    {'type': 'get_text_from_input'},
                    {'type': 'post_to_webhook', 'url': f'{self.webhook_base}/capture/text'},
                    {'type': 'show_notification', 'message': 'Text captured to Atlas!'}
                ]
            },

            'atlas_capture_page': {
                'name': 'Atlas: Capture Webpage',
                'description': 'Capture current webpage from Safari',
                'icon': 'safari',
                'color': 'orange',
                'inputs': ['safari_page'],
                'actions': [
                    {'type': 'get_current_url'},
                    {'type': 'get_page_content'},
                    {'type': 'post_to_webhook', 'url': f'{self.webhook_base}/capture/page'},
                    {'type': 'show_notification', 'message': 'Webpage captured to Atlas!'}
                ]
            },

            'atlas_capture_file': {
                'name': 'Atlas: Capture File',
                'description': 'Send any file to Atlas for processing',
                'icon': 'doc',
                'color': 'purple',
                'inputs': ['file'],
                'actions': [
                    {'type': 'get_file_from_input'},
                    {'type': 'encode_base64'},
                    {'type': 'post_to_webhook', 'url': f'{self.webhook_base}/capture/file'},
                    {'type': 'show_notification', 'message': 'File captured to Atlas!'}
                ]
            },

            'atlas_capture_photo': {
                'name': 'Atlas: Capture Photo Text',
                'description': 'Extract text from photos and send to Atlas',
                'icon': 'camera',
                'color': 'red',
                'inputs': ['photo'],
                'actions': [
                    {'type': 'get_photo_from_input'},
                    {'type': 'extract_text_from_image'},
                    {'type': 'post_to_webhook', 'url': f'{self.webhook_base}/capture/text'},
                    {'type': 'show_notification', 'message': 'Photo text captured to Atlas!'}
                ]
            },

            'atlas_capture_voice': {
                'name': 'Atlas: Voice Memo',
                'description': 'Record voice memo and send to Atlas',
                'icon': 'mic',
                'color': 'pink',
                'inputs': ['audio'],
                'actions': [
                    {'type': 'record_audio'},
                    {'type': 'encode_base64'},
                    {'type': 'post_to_webhook', 'url': f'{self.webhook_base}/capture/audio'},
                    {'type': 'show_notification', 'message': 'Voice memo captured to Atlas!'}
                ]
            },

            'atlas_reading_list': {
                'name': 'Atlas: Sync Reading List',
                'description': 'Send Safari Reading List to Atlas',
                'icon': 'list.bullet',
                'color': 'cyan',
                'inputs': [],
                'actions': [
                    {'type': 'get_reading_list_urls'},
                    {'type': 'post_to_webhook', 'url': f'{self.webhook_base}/capture/reading_list'},
                    {'type': 'show_notification', 'message': 'Reading List synced to Atlas!'}
                ]
            },

            'atlas_share_sheet': {
                'name': 'Atlas: Quick Capture',
                'description': 'Universal capture from any app via Share Sheet',
                'icon': 'square.and.arrow.up',
                'color': 'indigo',
                'inputs': ['anything'],
                'actions': [
                    {'type': 'get_input_type'},
                    {'type': 'conditional_capture'},
                    {'type': 'post_to_webhook', 'url': f'{self.webhook_base}/capture/universal'},
                    {'type': 'show_notification', 'message': 'Content captured to Atlas!'}
                ]
            }
        }

    def generate_shortcut_file(self, shortcut_name: str) -> Optional[str]:
        """
        Generate .shortcut file for iOS import.

        Returns path to generated shortcut file.
        """
        try:
            if shortcut_name not in self.shortcuts:
                log_error(f"Unknown shortcut: {shortcut_name}")
                return None

            shortcut_def = self.shortcuts[shortcut_name]

            # Generate iOS Shortcuts format (simplified)
            shortcut_data = {
                "WFWorkflowActions": self._convert_actions_to_ios_format(shortcut_def['actions']),
                "WFWorkflowClientVersion": "2170.0.4.2.1",
                "WFWorkflowHasOutputFallback": False,
                "WFWorkflowHasShortcutInputVariables": len(shortcut_def['inputs']) > 0,
                "WFWorkflowIcon": {
                    "WFWorkflowIconImageData": "",
                    "WFWorkflowIconStartColor": self._get_color_code(shortcut_def['color']),
                    "WFWorkflowIconGlyphNumber": 59511
                },
                "WFWorkflowImportQuestions": [],
                "WFWorkflowInputContentItemClasses": self._get_input_classes(shortcut_def['inputs']),
                "WFWorkflowMinimumClientVersion": 900,
                "WFWorkflowMinimumClientVersionString": "900",
                "WFWorkflowOutputContentItemClasses": [],
                "WFWorkflowTypes": ["ActionExtension", "WatchKit"],
                "WFWorkflowClientRelease": "2.0"
            }

            # Save to file
            shortcut_file = self.shortcuts_dir / f"{shortcut_name}.shortcut"
            with open(shortcut_file, 'w') as f:
                json.dump(shortcut_data, f, indent=2)

            log_info(f"Generated shortcut file: {shortcut_file}")
            return str(shortcut_file)

        except Exception as e:
            log_error(f"Error generating shortcut file: {str(e)}")
            return None

    def _convert_actions_to_ios_format(self, actions: List[Dict]) -> List[Dict]:
        """Convert action definitions to iOS Shortcuts format."""
        ios_actions = []

        for action in actions:
            action_type = action['type']

            if action_type == 'get_url_from_input':
                ios_actions.append({
                    "WFWorkflowActionIdentifier": "is.workflow.actions.url",
                    "WFWorkflowActionParameters": {
                        "WFURLActionURL": {"Value": {"string": "¤", "attachmentsByRange": {"{0, 1}": {"OutputUUID": "input"}}}}
                    }
                })

            elif action_type == 'get_text_from_input':
                ios_actions.append({
                    "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                    "WFWorkflowActionParameters": {
                        "WFTextActionText": {"Value": {"string": "¤", "attachmentsByRange": {"{0, 1}": {"OutputUUID": "input"}}}}
                    }
                })

            elif action_type == 'post_to_webhook':
                ios_actions.append({
                    "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
                    "WFWorkflowActionParameters": {
                        "WFHTTPMethod": "POST",
                        "WFURL": action['url'],
                        "WFHTTPHeaders": {
                            "Value": {
                                "WFDictionaryFieldValueItems": [
                                    {
                                        "WFItemType": 0,
                                        "WFKey": {"Value": {"string": "Content-Type"}},
                                        "WFValue": {"Value": {"string": "application/json"}}
                                    }
                                ]
                            }
                        },
                        "WFRequestVariable": {"Value": {"string": "¤", "attachmentsByRange": {"{0, 1}": {"OutputUUID": "previous"}}}}
                    }
                })

            elif action_type == 'show_notification':
                ios_actions.append({
                    "WFWorkflowActionIdentifier": "is.workflow.actions.shownotification",
                    "WFWorkflowActionParameters": {
                        "WFNotificationActionTitle": action['message']
                    }
                })

            # Add more action types as needed

        return ios_actions

    def _get_color_code(self, color_name: str) -> int:
        """Get iOS color code for shortcut icon."""
        color_codes = {
            'blue': 4282601983,
            'green': 4292093695,
            'orange': 4294961408,
            'purple': 4284861311,
            'red': 4294947584,
            'pink': 4294936832,
            'cyan': 4288931808,
            'indigo': 4279113341
        }
        return color_codes.get(color_name, 4282601983)  # Default to blue

    def _get_input_classes(self, inputs: List[str]) -> List[str]:
        """Get iOS input content classes."""
        class_mapping = {
            'url': 'WFURLContentItem',
            'text': 'WFStringContentItem',
            'file': 'WFGenericFileContentItem',
            'photo': 'WFImageContentItem',
            'audio': 'WFAudioContentItem',
            'safari_page': 'WFWebPageContentItem',
            'anything': 'WFContentItem'
        }

        classes = []
        for input_type in inputs:
            if input_type in class_mapping:
                classes.append(class_mapping[input_type])

        return classes if classes else ['WFContentItem']

    def generate_all_shortcuts(self) -> List[str]:
        """Generate all available shortcuts."""
        generated_files = []

        for shortcut_name in self.shortcuts.keys():
            file_path = self.generate_shortcut_file(shortcut_name)
            if file_path:
                generated_files.append(file_path)

        log_info(f"Generated {len(generated_files)} shortcut files")
        return generated_files

    def create_installation_guide(self) -> str:
        """Create installation guide for Apple Shortcuts."""
        guide_file = self.shortcuts_dir / 'INSTALLATION_GUIDE.md'

        guide_content = f"""# Atlas Apple Shortcuts Installation Guide

## Quick Setup

1. **Start Atlas Webhook Server**
   ```bash
   python -c "from helpers.apple_integrations import setup_apple_shortcuts_webhook; setup_apple_shortcuts_webhook()"
   ```

2. **Install Shortcuts on iOS/iPadOS**
   - Open each `.shortcut` file on your device
   - Tap "Add Shortcut" in the Shortcuts app
   - Grant necessary permissions when prompted

3. **Test Integration**
   - Try "Atlas: Capture URL" with any webpage
   - Check Atlas for captured content

## Available Shortcuts

### 📱 Core Capture Shortcuts

"""

        for name, shortcut in self.shortcuts.items():
            guide_content += f"**{shortcut['name']}**\n"
            guide_content += f"- {shortcut['description']}\n"
            guide_content += f"- File: `{name}.shortcut`\n\n"

        guide_content += """
## Device-Specific Instructions

### iPhone/iPad
1. Download shortcut files to Files app
2. Open each file - it will open in Shortcuts app
3. Tap "Add Shortcut" and configure permissions
4. Add shortcuts to Home Screen for quick access

### Mac
1. Open Shortcuts app (macOS Monterey+)
2. Import shortcut files
3. Configure network permissions for webhook access

### Apple Watch
- Voice shortcuts will sync automatically
- Use "Atlas: Voice Memo" for quick capture

## Webhook Configuration

Default webhook: `{self.webhook_base}`

To change webhook URL, edit config and regenerate shortcuts:
```python
config = {{'webhook_base_url': 'https://your-atlas-server.com'}}
manager = ShortcutsManager(config)
manager.generate_all_shortcuts()
```

## Troubleshooting

### "Can't Connect to Server"
- Ensure Atlas webhook server is running
- Check network connectivity
- Verify webhook URL in shortcut settings

### "Permission Denied"
- Grant Shortcuts app access to required resources
- Enable "Allow Untrusted Shortcuts" in Settings > Shortcuts

### "Capture Failed"
- Check Atlas logs for error details
- Verify webhook endpoint is responding
- Test with simple URL capture first

## Advanced Usage

### Custom Shortcuts
You can create custom shortcuts using the webhook endpoints:

- `POST {self.webhook_base}/capture/url` - Capture URL
- `POST {self.webhook_base}/capture/text` - Capture text
- `POST {self.webhook_base}/capture/file` - Capture file
- `POST {self.webhook_base}/capture/universal` - Universal capture

### Automation
Set up iOS Automations to trigger Atlas capture:
- Auto-capture from specific apps
- Time-based reading list sync
- Location-based content capture

"""

        with open(guide_file, 'w') as f:
            f.write(guide_content)

        log_info(f"Installation guide created: {guide_file}")
        return str(guide_file)

    def create_webhook_test_page(self) -> str:
        """Create test page for webhook endpoints."""
        test_file = self.shortcuts_dir / 'test_webhook.html'

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Atlas Webhook Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .test-section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        button {{ background: #007AFF; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #005CBB; }}
        textarea {{ width: 100%; height: 100px; margin: 10px 0; }}
        .result {{ margin: 10px 0; padding: 10px; background: #f0f0f0; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>Atlas Webhook Test Page</h1>
    <p>Test your Atlas webhook endpoints before using with Apple Shortcuts.</p>

    <div class="test-section">
        <h3>Test URL Capture</h3>
        <input type="url" id="test-url" placeholder="https://example.com" style="width: 100%; padding: 8px;">
        <br><br>
        <button onclick="testUrlCapture()">Test URL Capture</button>
        <div id="url-result" class="result" style="display: none;"></div>
    </div>

    <div class="test-section">
        <h3>Test Text Capture</h3>
        <textarea id="test-text" placeholder="Enter text to capture..."></textarea>
        <button onclick="testTextCapture()">Test Text Capture</button>
        <div id="text-result" class="result" style="display: none;"></div>
    </div>

    <div class="test-section">
        <h3>Webhook Status</h3>
        <button onclick="checkWebhookStatus()">Check Webhook Status</button>
        <div id="status-result" class="result" style="display: none;"></div>
    </div>

    <script>
        const webhookBase = '{self.webhook_base}';

        async function testUrlCapture() {{
            const url = document.getElementById('test-url').value;
            const resultDiv = document.getElementById('url-result');

            try {{
                const response = await fetch(`${{webhookBase}}/capture/url`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ url: url, source: 'test' }})
                }});

                const result = await response.json();
                resultDiv.innerHTML = `<strong>Success:</strong> ${{JSON.stringify(result)}}`;
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#d4edda';
            }} catch (error) {{
                resultDiv.innerHTML = `<strong>Error:</strong> ${{error.message}}`;
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#f8d7da';
            }}
        }}

        async function testTextCapture() {{
            const text = document.getElementById('test-text').value;
            const resultDiv = document.getElementById('text-result');

            try {{
                const response = await fetch(`${{webhookBase}}/capture/text`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ text: text, source: 'test' }})
                }});

                const result = await response.json();
                resultDiv.innerHTML = `<strong>Success:</strong> ${{JSON.stringify(result)}}`;
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#d4edda';
            }} catch (error) {{
                resultDiv.innerHTML = `<strong>Error:</strong> ${{error.message}}`;
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#f8d7da';
            }}
        }}

        async function checkWebhookStatus() {{
            const resultDiv = document.getElementById('status-result');

            try {{
                const response = await fetch(`${{webhookBase}}/status`);
                const result = await response.json();
                resultDiv.innerHTML = `<strong>Webhook Status:</strong> ${{JSON.stringify(result)}}`;
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#d1ecf1';
            }} catch (error) {{
                resultDiv.innerHTML = `<strong>Error:</strong> Webhook server not running or unreachable`;
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#f8d7da';
            }}
        }}
    </script>
</body>
</html>"""

        with open(test_file, 'w') as f:
            f.write(html_content)

        log_info(f"Webhook test page created: {test_file}")
        return str(test_file)

    def update_webhook_url(self, new_webhook_url: str):
        """Update webhook URL in all shortcuts."""
        self.webhook_base = new_webhook_url

        # Update shortcut definitions
        for shortcut_name, shortcut_def in self.shortcuts.items():
            for action in shortcut_def['actions']:
                if action['type'] == 'post_to_webhook':
                    old_url = action['url']
                    # Replace the base URL part
                    action['url'] = old_url.replace(old_url.split('/capture')[0], new_webhook_url)

        log_info(f"Updated webhook URL to: {new_webhook_url}")
        log_info("Regenerate shortcuts to apply changes")


def setup_apple_shortcuts(webhook_url: str = None) -> Dict[str, str]:
    """
    Complete Apple Shortcuts setup for Atlas.

    Returns:
        Dict with file paths for shortcuts and guides
    """
    config = {}
    if webhook_url:
        config['webhook_base_url'] = webhook_url

    manager = ShortcutsManager(config)

    # Generate all shortcuts
    shortcut_files = manager.generate_all_shortcuts()

    # Create installation guide
    guide_file = manager.create_installation_guide()

    # Create test page
    test_file = manager.create_webhook_test_page()

    return {
        'shortcuts': shortcut_files,
        'installation_guide': guide_file,
        'test_page': test_file,
        'webhook_url': manager.webhook_base
    }