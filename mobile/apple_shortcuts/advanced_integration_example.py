"""
Integration example for advanced Siri shortcuts in Atlas
"""

import os
import sys
from typing import Dict, Any

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from apple_shortcuts import SiriShortcutManager
from apple_shortcuts.contextual_capture import ContextualCaptureManager
from apple_shortcuts.automation_manager import AutomationManager


class AtlasAdvancedSiriIntegration:
    """Advanced integration layer for Siri shortcuts in Atlas"""

    def __init__(self, atlas_instance=None):
        self.shortcut_manager = SiriShortcutManager("atlas_advanced_shortcuts")
        self.contextual_manager = ContextualCaptureManager()
        self.automation_manager = AutomationManager()
        self.atlas = atlas_instance

    def setup_advanced_shortcuts(self):
        """Set up advanced Siri shortcuts with contextual awareness"""
        # Create context-aware shortcuts
        contextual_shortcuts = [
            {
                "name": "log_work_task_context",
                "phrase": "Log a work task with context",
                "action": "log_entry",
                "parameters": {"type": "work_task"},
                "context_aware": True,
                "priority": "high",
            },
            {
                "name": "capture_evening_thought",
                "phrase": "Capture evening thought",
                "action": "create_note",
                "parameters": {"type": "evening_reflection"},
                "context_aware": True,
                "priority": "medium",
            },
            {
                "name": "log_home_activity_context",
                "phrase": "Log what I'm doing at home",
                "action": "log_entry",
                "parameters": {"type": "home_activity"},
                "context_aware": True,
                "priority": "low",
            },
        ]

        created_files = self.shortcut_manager.create_batch_shortcuts(
            contextual_shortcuts
        )
        print(f"Created {len(created_files)} contextual shortcuts")

        # Set up default contextual shortcuts
        default_count = self.shortcut_manager.setup_default_contextual_shortcuts()
        print(f"Created {default_count} default contextual shortcuts")

        return len(created_files) + default_count

    def setup_automations(self):
        """Set up automation rules"""
        # Set up default automations
        default_count = self.shortcut_manager.setup_default_automations()
        print(f"Created {default_count} default automation rules")

        # Create custom automation rules
        custom_automations = [
            {
                "name": "Evening Review",
                "description": "Start evening review at 8 PM",
                "trigger_type": "time",
                "trigger_conditions": {"hour": 20, "time_of_day": "evening"},
                "actions": [
                    {
                        "type": "START_TIMER",
                        "parameters": {"type": "evening_review", "duration": 15},
                    },
                    {
                        "type": "SEND_NOTIFICATION",
                        "parameters": {
                            "title": "Evening Review",
                            "message": "Time for your evening review",
                        },
                    },
                ],
            },
            {
                "name": "Gym Session Log",
                "description": "Log gym session when arriving at gym",
                "trigger_type": "location",
                "trigger_conditions": {
                    "category": "gym",
                    "place_name": "Fitness Center",
                },
                "actions": [
                    {
                        "type": "LOG_ENTRY",
                        "parameters": {
                            "type": "gym_session",
                            "value": "Started gym session",
                        },
                    }
                ],
            },
        ]

        created_count = 0
        for automation in custom_automations:
            try:
                self.automation_manager.create_automation_rule(**automation)
                created_count += 1
            except Exception as e:
                print(f"Failed to create automation {automation['name']}: {e}")

        print(f"Created {created_count} custom automation rules")
        return default_count + created_count

    def handle_contextual_shortcut_action(
        self, action: str, parameters: Dict[str, Any]
    ):
        """Handle a contextual shortcut action"""
        print(f"Handling contextual action: {action}")
        print(f"Parameters: {parameters}")

        # Get current context
        context = self.contextual_manager.get_all_contexts()
        print(f"Current context: {context}")

        # Get contextual categories and priority
        categories = self.contextual_manager.get_contextual_categories()
        priority = self.contextual_manager.get_contextual_priority()

        print(f"Contextual categories: {categories}")
        print(f"Contextual priority: {priority}")

        # In a real implementation, this would integrate with the Atlas system
        # For example:
        # if action == "log_entry":
        #     return self.atlas.log_entry(parameters, context, categories, priority)
        # elif action == "start_timer":
        #     return self.atlas.start_timer(parameters, context, categories, priority)
        # elif action == "create_note":
        #     return self.atlas.create_note(parameters, context, categories, priority)

        return {
            "status": "success",
            "message": f"Contextual action '{action}' executed with parameters {parameters}",
            "context": context,
            "categories": categories,
            "priority": priority,
        }

    def trigger_automations(self):
        """Trigger automations based on current context"""
        triggered_automations = self.shortcut_manager.trigger_contextual_automations()
        print(f"Triggered {len(triggered_automations)} automation rules")

        for automation in triggered_automations:
            print(
                f"  - {automation['rule_name']}: {len(automation['results'])} actions executed"
            )

        return triggered_automations

    def get_automation_analytics(self):
        """Get automation analytics"""
        analytics = self.shortcut_manager.get_automation_analytics()
        print("Automation Analytics:")
        print(f"  Total triggers: {analytics['total_triggers']}")
        print(f"  Successful executions: {analytics['successful_executions']}")
        print(f"  Failed executions: {analytics['failed_executions']}")

        if analytics["rule_trigger_counts"]:
            print("  Rule trigger counts:")
            for rule_name, count in analytics["rule_trigger_counts"].items():
                print(f"    {rule_name}: {count}")

        return analytics


def main():
    # Initialize the advanced integration
    integration = AtlasAdvancedSiriIntegration()

    # Set up advanced shortcuts
    print("Setting up advanced shortcuts...")
    shortcut_count = integration.setup_advanced_shortcuts()
    print(f"Set up {shortcut_count} advanced shortcuts\n")

    # Set up automations
    print("Setting up automations...")
    automation_count = integration.setup_automations()
    print(f"Set up {automation_count} automations\n")

    # List all shortcuts
    print("Available shortcuts:")
    shortcuts = integration.shortcut_manager.list_shortcuts()
    for name, data in shortcuts.items():
        context_aware = data.get("context_aware", False)
        priority = data.get("priority", "medium")
        print(
            f"  - \"{data['phrase']}\" -> {data['action']} (context-aware: {context_aware}, priority: {priority})"
        )

    # Example of handling a contextual shortcut action
    print("\nExample contextual action handling:")
    result = integration.handle_contextual_shortcut_action(
        "log_entry", {"type": "work_task", "value": "Complete project proposal"}
    )
    print(result)

    # Example of triggering automations
    print("\nTriggering automations based on current context:")
    triggered = integration.trigger_automations()

    # Example of getting automation analytics
    print("\nGetting automation analytics:")
    analytics = integration.get_automation_analytics()


if __name__ == "__main__":
    main()
