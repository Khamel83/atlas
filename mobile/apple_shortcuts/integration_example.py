"""
Integration example for Siri shortcuts in Atlas
"""

import os
import sys
from typing import Dict, Any

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from apple_shortcuts import SiriShortcutManager


class AtlasSiriIntegration:
    """Integration layer for Siri shortcuts in Atlas"""

    def __init__(self, atlas_instance=None):
        self.shortcut_manager = SiriShortcutManager("atlas_shortcuts")
        self.atlas = atlas_instance

    def setup_default_shortcuts(self):
        """Set up default Siri shortcuts for Atlas"""
        shortcuts = [
            {
                "name": "log_mood",
                "phrase": "Log my mood",
                "action": "log_entry",
                "parameters": {"type": "mood"},
            },
            {
                "name": "start_focus",
                "phrase": "Start focus time",
                "action": "start_timer",
                "parameters": {"type": "focus", "duration": 25},
            },
            {
                "name": "capture_thought",
                "phrase": "Capture this thought",
                "action": "create_note",
                "parameters": {"type": "thought"},
            },
            {
                "name": "log_meal",
                "phrase": "Log my meal",
                "action": "log_entry",
                "parameters": {"type": "nutrition"},
            },
        ]

        for shortcut in shortcuts:
            self.shortcut_manager.create_shortcut(**shortcut)

        return len(shortcuts)

    def handle_shortcut_action(self, action: str, parameters: Dict[str, Any]):
        """Handle a shortcut action (placeholder for actual Atlas integration)"""
        print(f"Handling action: {action}")
        print(f"Parameters: {parameters}")

        # In a real implementation, this would integrate with the Atlas system
        # For example:
        # if action == "log_entry":
        #     return self.atlas.log_entry(parameters)
        # elif action == "start_timer":
        #     return self.atlas.start_timer(parameters)
        # elif action == "create_note":
        #     return self.atlas.create_note(parameters)

        return {
            "status": "success",
            "message": f"Action '{action}' executed with parameters {parameters}",
        }


def main():
    # Initialize the integration
    integration = AtlasSiriIntegration()

    # Set up default shortcuts
    count = integration.setup_default_shortcuts()
    print(f"Set up {count} default shortcuts")

    # List all shortcuts
    print("\nAvailable shortcuts:")
    shortcuts = integration.shortcut_manager.list_shortcuts()
    for name, data in shortcuts.items():
        print(f"  - \"{data['phrase']}\" -> {data['action']}")

    # Example of handling a shortcut action
    print("\nExample action handling:")
    result = integration.handle_shortcut_action(
        "log_entry", {"type": "mood", "value": "focused"}
    )
    print(result)


if __name__ == "__main__":
    main()
