"""
Automation manager for Atlas Siri shortcuts
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum


class TriggerType(Enum):
    """Supported trigger types for automation"""

    TIME = "time"
    LOCATION = "location"
    APP_USAGE = "app_usage"
    CALENDAR = "calendar"
    FOCUS_MODE = "focus_mode"
    BATTERY = "battery"
    NETWORK = "network"


class ActionType(Enum):
    """Supported action types for automation"""

    CAPTURE_CONTENT = "capture_content"
    CREATE_NOTE = "create_note"
    LOG_ENTRY = "log_entry"
    START_TIMER = "start_timer"
    SEND_NOTIFICATION = "send_notification"
    EXECUTE_SHORTCUT = "execute_shortcut"


@dataclass
class AutomationTrigger:
    """Represents an automation trigger"""

    trigger_type: TriggerType
    conditions: Dict[str, Any]  # Trigger-specific conditions
    enabled: bool = True


@dataclass
class AutomationAction:
    """Represents an automation action"""

    action_type: ActionType
    parameters: Dict[str, Any]  # Action-specific parameters
    delay: int = 0  # Delay in seconds before executing


@dataclass
class AutomationRule:
    """Represents a complete automation rule"""

    name: str
    description: str
    trigger: AutomationTrigger
    actions: List[AutomationAction]
    enabled: bool = True
    created_at: datetime = None
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class AutomationManager:
    """Manage automation workflows for Atlas"""

    def __init__(self, automations_dir: str = "automations"):
        self.automations_dir = automations_dir
        os.makedirs(automations_dir, exist_ok=True)
        self.automation_rules: Dict[str, AutomationRule] = {}
        self.analytics_data = {
            "total_triggers": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "rule_trigger_counts": {},
        }
        self.load_automations()

    def create_automation_rule(
        self,
        name: str,
        description: str,
        trigger_type: TriggerType,
        trigger_conditions: Dict[str, Any],
        actions: List[Dict[str, Any]],
        enabled: bool = True,
    ) -> str:
        """Create a new automation rule"""
        # Convert trigger_type string to enum if needed
        if isinstance(trigger_type, str):
            try:
                trigger_type = TriggerType(trigger_type)
            except ValueError:
                raise ValueError(f"Invalid trigger type: {trigger_type}")

        # Create trigger
        trigger = AutomationTrigger(
            trigger_type=trigger_type, conditions=trigger_conditions, enabled=enabled
        )

        # Create actions
        action_objects = []
        for action_data in actions:
            # Convert action_type string to enum if needed
            action_type = action_data["type"]
            if isinstance(action_type, str):
                try:
                    action_type = ActionType(action_type)
                except ValueError:
                    raise ValueError(f"Invalid action type: {action_type}")

            action_obj = AutomationAction(
                action_type=action_type,
                parameters=action_data.get("parameters", {}),
                delay=action_data.get("delay", 0),
            )
            action_objects.append(action_obj)

        # Create rule
        rule = AutomationRule(
            name=name,
            description=description,
            trigger=trigger,
            actions=action_objects,
            enabled=enabled,
        )

        # Store rule
        self.automation_rules[name] = rule

        # Save to file
        self.save_automation_rule(rule)

        return name

    def save_automation_rule(self, rule: AutomationRule) -> str:
        """Save an automation rule to a file"""
        # Convert rule to dictionary
        rule_dict = asdict(rule)
        rule_dict["trigger"]["trigger_type"] = rule.trigger.trigger_type.value
        rule_dict["actions"] = [
            {
                "action_type": action.action_type.value,
                "parameters": action.parameters,
                "delay": action.delay,
            }
            for action in rule.actions
        ]

        # Convert datetime objects to strings
        if rule_dict["created_at"]:
            rule_dict["created_at"] = rule.created_at.isoformat()
        if rule_dict["last_triggered"]:
            rule_dict["last_triggered"] = rule.last_triggered.isoformat()

        # Save to file
        # Handle special characters in filename
        safe_name = rule.name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        filename = f"{safe_name}.json"
        filepath = os.path.join(self.automations_dir, filename)

        # Ensure directory exists
        os.makedirs(
            (
                os.path.dirname(filepath)
                if os.path.dirname(filepath)
                else self.automations_dir
            ),
            exist_ok=True,
        )

        with open(filepath, "w") as f:
            json.dump(rule_dict, f, indent=2)

        return filepath

    def load_automation_rule(self, name: str) -> Optional[AutomationRule]:
        """Load an automation rule from a file"""
        # Handle special characters in filename
        safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        filename = f"{safe_name}.json"
        filepath = os.path.join(self.automations_dir, filename)

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r") as f:
                rule_dict = json.load(f)

            # Convert strings back to datetime objects
            if rule_dict.get("created_at"):
                rule_dict["created_at"] = datetime.fromisoformat(
                    rule_dict["created_at"]
                )
            if rule_dict.get("last_triggered"):
                rule_dict["last_triggered"] = datetime.fromisoformat(
                    rule_dict["last_triggered"]
                )

            # Create trigger
            trigger = AutomationTrigger(
                trigger_type=TriggerType(rule_dict["trigger"]["trigger_type"]),
                conditions=rule_dict["trigger"]["conditions"],
                enabled=rule_dict["trigger"]["enabled"],
            )

            # Create actions
            actions = []
            for action_data in rule_dict["actions"]:
                action = AutomationAction(
                    action_type=ActionType(action_data["action_type"]),
                    parameters=action_data["parameters"],
                    delay=action_data["delay"],
                )
                actions.append(action)

            # Create rule
            rule = AutomationRule(
                name=rule_dict["name"],
                description=rule_dict["description"],
                trigger=trigger,
                actions=actions,
                enabled=rule_dict["enabled"],
                created_at=rule_dict["created_at"],
                last_triggered=rule_dict["last_triggered"],
                trigger_count=rule_dict["trigger_count"],
            )

            return rule
        except Exception as e:
            print(f"Error loading automation rule {name}: {e}")
            return None

    def load_automations(self):
        """Load all automation rules from files"""
        self.automation_rules = {}

        if not os.path.exists(self.automations_dir):
            return

        for filename in os.listdir(self.automations_dir):
            if filename.endswith(".json"):
                # We can't reliably reconstruct the original name from the filename
                # So we'll load each file and get the name from the file content
                filepath = os.path.join(self.automations_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        rule_dict = json.load(f)
                    name = rule_dict["name"]
                    rule = self.load_automation_rule(name)
                    if rule:
                        self.automation_rules[name] = rule
                except Exception as e:
                    print(f"Error loading automation rule from {filename}: {e}")

    def get_automation_rule(self, name: str) -> Optional[AutomationRule]:
        """Get an automation rule by name"""
        return self.automation_rules.get(name)

    def list_automation_rules(self) -> List[str]:
        """List all automation rule names"""
        return list(self.automation_rules.keys())

    def enable_automation_rule(self, name: str) -> bool:
        """Enable an automation rule"""
        if name in self.automation_rules:
            self.automation_rules[name].enabled = True
            self.save_automation_rule(self.automation_rules[name])
            return True
        return False

    def disable_automation_rule(self, name: str) -> bool:
        """Disable an automation rule"""
        if name in self.automation_rules:
            self.automation_rules[name].enabled = False
            self.save_automation_rule(self.automation_rules[name])
            return True
        return False

    def delete_automation_rule(self, name: str) -> bool:
        """Delete an automation rule"""
        if name in self.automation_rules:
            # Remove from memory
            del self.automation_rules[name]

            # Remove file
            # Handle special characters in filename
            safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
            filename = f"{safe_name}.json"
            filepath = os.path.join(self.automations_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)

            return True
        return False

    def evaluate_trigger(
        self, trigger: AutomationTrigger, context: Dict[str, Any]
    ) -> bool:
        """Evaluate if a trigger should fire based on current context"""
        if not trigger.enabled:
            return False

        # Evaluate based on trigger type
        if trigger.trigger_type == TriggerType.TIME:
            return self._evaluate_time_trigger(trigger.conditions, context)
        elif trigger.trigger_type == TriggerType.LOCATION:
            return self._evaluate_location_trigger(trigger.conditions, context)
        elif trigger.trigger_type == TriggerType.APP_USAGE:
            return self._evaluate_app_usage_trigger(trigger.conditions, context)
        elif trigger.trigger_type == TriggerType.CALENDAR:
            return self._evaluate_calendar_trigger(trigger.conditions, context)
        elif trigger.trigger_type == TriggerType.FOCUS_MODE:
            return self._evaluate_focus_mode_trigger(trigger.conditions, context)
        elif trigger.trigger_type == TriggerType.BATTERY:
            return self._evaluate_battery_trigger(trigger.conditions, context)
        elif trigger.trigger_type == TriggerType.NETWORK:
            return self._evaluate_network_trigger(trigger.conditions, context)

        return False

    def _evaluate_time_trigger(
        self, conditions: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Evaluate time-based trigger conditions"""
        time_context = context.get("time", {})

        # Check hour
        if "hour" in conditions:
            target_hour = conditions["hour"]
            if isinstance(target_hour, list):
                if time_context.get("hour") not in target_hour:
                    return False
            else:
                if time_context.get("hour") != target_hour:
                    return False

        # Check day of week
        if "day_of_week" in conditions:
            target_day = conditions["day_of_week"]
            if isinstance(target_day, list):
                if time_context.get("day_of_week") not in target_day:
                    return False
            else:
                if time_context.get("day_of_week") != target_day:
                    return False

        # Check time of day
        if "time_of_day" in conditions:
            target_time_of_day = conditions["time_of_day"]
            if isinstance(target_time_of_day, list):
                if time_context.get("time_of_day") not in target_time_of_day:
                    return False
            else:
                if time_context.get("time_of_day") != target_time_of_day:
                    return False

        # Check weekend
        if "is_weekend" in conditions:
            if time_context.get("is_weekend") != conditions["is_weekend"]:
                return False

        return True

    def _evaluate_location_trigger(
        self, conditions: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Evaluate location-based trigger conditions"""
        location_context = context.get("location", {})

        # Check location category
        if "category" in conditions:
            target_category = conditions["category"]
            if isinstance(target_category, list):
                if location_context.get("category") not in target_category:
                    return False
            else:
                if location_context.get("category") != target_category:
                    return False

        # Check place name
        if "place_name" in conditions:
            target_place = conditions["place_name"]
            if isinstance(target_place, list):
                if location_context.get("place_name") not in target_place:
                    return False
            else:
                if location_context.get("place_name") != target_place:
                    return False

        return True

    def _evaluate_app_usage_trigger(
        self, conditions: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Evaluate app usage trigger conditions"""
        # This would integrate with iOS app usage tracking
        # For now, we'll return False as a stub
        return False

    def _evaluate_calendar_trigger(
        self, conditions: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Evaluate calendar-based trigger conditions"""
        calendar_context = context.get("calendar", {})

        # Check if in a meeting
        if "in_meeting" in conditions:
            is_in_meeting = calendar_context.get("is_ongoing", False)
            if is_in_meeting != conditions["in_meeting"]:
                return False

        # Check event title
        if "event_title" in conditions:
            target_title = conditions["event_title"]
            if isinstance(target_title, list):
                if calendar_context.get("event_title") not in target_title:
                    return False
            else:
                if calendar_context.get("event_title") != target_title:
                    return False

        return True

    def _evaluate_focus_mode_trigger(
        self, conditions: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Evaluate focus mode trigger conditions"""
        focus_context = context.get("focus_mode", {})

        # Check if focus mode is active
        if "is_active" in conditions:
            if focus_context.get("is_active") != conditions["is_active"]:
                return False

        # Check focus mode name
        if "mode_name" in conditions:
            target_mode = conditions["mode_name"]
            if isinstance(target_mode, list):
                if focus_context.get("mode_name") not in target_mode:
                    return False
            else:
                if focus_context.get("mode_name") != target_mode:
                    return False

        return True

    def _evaluate_battery_trigger(
        self, conditions: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Evaluate battery-based trigger conditions"""
        # This would integrate with iOS battery monitoring
        # For now, we'll return False as a stub
        return False

    def _evaluate_network_trigger(
        self, conditions: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Evaluate network-based trigger conditions"""
        # This would integrate with iOS network monitoring
        # For now, we'll return False as a stub
        return False

    def execute_action(
        self, action: AutomationAction, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an automation action"""
        result = {
            "status": "success",
            "action_type": action.action_type.value,
            "executed_at": datetime.now().isoformat(),
        }

        try:
            # Add delay if specified
            if action.delay > 0:
                import time

                time.sleep(action.delay)

            # Execute based on action type
            if action.action_type == ActionType.CAPTURE_CONTENT:
                result.update(self._execute_capture_content(action.parameters, context))
            elif action.action_type == ActionType.CREATE_NOTE:
                result.update(self._execute_create_note(action.parameters, context))
            elif action.action_type == ActionType.LOG_ENTRY:
                result.update(self._execute_log_entry(action.parameters, context))
            elif action.action_type == ActionType.START_TIMER:
                result.update(self._execute_start_timer(action.parameters, context))
            elif action.action_type == ActionType.SEND_NOTIFICATION:
                result.update(
                    self._execute_send_notification(action.parameters, context)
                )
            elif action.action_type == ActionType.EXECUTE_SHORTCUT:
                result.update(self._execute_shortcut(action.parameters, context))
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            self.analytics_data["failed_executions"] += 1
        else:
            self.analytics_data["successful_executions"] += 1

        return result

    def _execute_capture_content(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute content capture action"""
        # This would integrate with Atlas content capture system
        return {
            "captured": True,
            "content_type": parameters.get("type", "general"),
            "source": "automation",
        }

    def _execute_create_note(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute create note action"""
        # This would integrate with Atlas note creation system
        return {
            "note_created": True,
            "note_type": parameters.get("type", "general"),
            "title": parameters.get("title", "Automated Note"),
        }

    def _execute_log_entry(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute log entry action"""
        # This would integrate with Atlas logging system
        return {
            "logged": True,
            "entry_type": parameters.get("type", "general"),
            "value": parameters.get("value"),
        }

    def _execute_start_timer(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute start timer action"""
        # This would integrate with Atlas timer system
        return {
            "timer_started": True,
            "timer_type": parameters.get("type", "general"),
            "duration": parameters.get("duration", 0),
        }

    def _execute_send_notification(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute send notification action"""
        # This would integrate with iOS notification system
        return {
            "notification_sent": True,
            "title": parameters.get("title", "Atlas Automation"),
            "message": parameters.get("message", "Automation triggered"),
        }

    def _execute_shortcut(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute shortcut action"""
        # This would integrate with Siri Shortcuts system
        return {
            "shortcut_executed": True,
            "shortcut_name": parameters.get("name", "unknown"),
        }

    def trigger_automation_rules(self, context: Dict[str, Any]):
        """Trigger all applicable automation rules based on current context"""
        triggered_rules = []

        for name, rule in self.automation_rules.items():
            if not rule.enabled:
                continue

            # Evaluate trigger
            if self.evaluate_trigger(rule.trigger, context):
                # Update rule analytics
                rule.trigger_count += 1
                rule.last_triggered = datetime.now()
                self.analytics_data["total_triggers"] += 1
                self.analytics_data["rule_trigger_counts"][name] = rule.trigger_count

                # Save updated rule
                self.save_automation_rule(rule)

                # Execute actions
                results = []
                for action in rule.actions:
                    result = self.execute_action(action, context)
                    results.append(result)

                triggered_rules.append({"rule_name": name, "results": results})

        return triggered_rules

    def get_analytics(self) -> Dict[str, Any]:
        """Get automation analytics data"""
        return self.analytics_data

    def create_default_automations(self):
        """Create default automation rules"""
        # Time-based automations
        self.create_automation_rule(
            name="Morning Routine",
            description="Start morning routine at 8 AM on weekdays",
            trigger_type=TriggerType.TIME,
            trigger_conditions={
                "hour": 8,
                "day_of_week": [0, 1, 2, 3, 4],  # Monday to Friday
                "time_of_day": "morning",
            },
            actions=[
                {
                    "type": "start_timer",
                    "parameters": {"type": "morning_routine", "duration": 30},
                },
                {
                    "type": "send_notification",
                    "parameters": {
                        "title": "Good Morning!",
                        "message": "Time to start your morning routine",
                    },
                },
            ],
        )

        # Location-based automations
        self.create_automation_rule(
            name="Work Mode",
            description="Enable work mode when arriving at work",
            trigger_type=TriggerType.LOCATION,
            trigger_conditions={"category": "work", "place_name": "Office"},
            actions=[
                {"type": "execute_shortcut", "parameters": {"name": "work_mode"}},
                {
                    "type": "send_notification",
                    "parameters": {
                        "title": "Work Mode",
                        "message": "You've arrived at work. Time to focus!",
                    },
                },
            ],
        )

        # Calendar-based automations
        self.create_automation_rule(
            name="Meeting Notes",
            description="Create note template when entering a meeting",
            trigger_type=TriggerType.CALENDAR,
            trigger_conditions={"in_meeting": True},
            actions=[
                {
                    "type": "create_note",
                    "parameters": {"type": "meeting_notes", "title": "Meeting Notes"},
                }
            ],
        )

        # Focus mode automations
        self.create_automation_rule(
            name="Focus Time",
            description="Start focus timer when work focus mode is activated",
            trigger_type=TriggerType.FOCUS_MODE,
            trigger_conditions={"is_active": True, "mode_name": "work"},
            actions=[
                {
                    "type": "start_timer",
                    "parameters": {"type": "focus_time", "duration": 25},
                }
            ],
        )
