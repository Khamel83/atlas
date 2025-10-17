"""
Visual Progress and Feedback System for OOS
Provides rich terminal UI for monitoring background processing and user feedback
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import shutil

from renderers import Colors


class ProgressState(Enum):
    """States for visual progress tracking"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    WARNING = "warning"


@dataclass
class ProgressItem:
    """Individual progress item for tracking"""
    id: str
    title: str
    state: ProgressState
    progress: float  # 0.0 to 1.0
    details: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_time: Optional[int] = None  # seconds


class ProgressBar:
    """Visual progress bar for terminal"""

    def __init__(self, width: int = 40):
        self.width = width

    def render(self, progress: float, title: str = "", color: str = Colors.GREEN) -> str:
        """Render a progress bar"""
        filled = int(progress * self.width)
        bar = "█" * filled + "░" * (self.width - filled)
        percentage = int(progress * 100)

        return f"{color}[{bar}] {percentage:3d}%{Colors.END} {title}"

    def render_multi(self, items: List[Tuple[float, str, str]]) -> str:
        """Render multiple progress bars"""
        lines = []
        for progress, title, color in items:
            lines.append(self.render(progress, title, color))
        return "\n".join(lines)


class StatusDisplay:
    """Real-time status display for OOS operations"""

    def __init__(self):
        self.progress_bar = ProgressBar()
        self.terminal_width = self._get_terminal_width()
        self.current_items: Dict[str, ProgressItem] = {}
        self.show_completed = True
        self.max_display_items = 10

    def _get_terminal_width(self) -> int:
        """Get terminal width for responsive display"""
        try:
            return shutil.get_terminal_size().columns
        except:
            return 80

    def add_item(self, item: ProgressItem):
        """Add progress item to display"""
        item.started_at = datetime.now()
        self.current_items[item.id] = item

    def update_item(self, item_id: str, progress: float = None,
                   state: ProgressState = None, details: str = None):
        """Update progress item"""
        if item_id in self.current_items:
            item = self.current_items[item_id]

            if progress is not None:
                item.progress = min(1.0, max(0.0, progress))

            if state is not None:
                if state == ProgressState.COMPLETED and item.state != ProgressState.COMPLETED:
                    item.completed_at = datetime.now()
                item.state = state

            if details is not None:
                item.details = details

    def remove_item(self, item_id: str):
        """Remove item from display"""
        if item_id in self.current_items:
            del self.current_items[item_id]

    def render_dashboard(self) -> str:
        """Render the complete dashboard"""
        lines = []

        # Header
        lines.append(self._render_header())
        lines.append("")

        # Active items
        active_items = [item for item in self.current_items.values()
                       if item.state in [ProgressState.PENDING, ProgressState.PROCESSING]]

        if active_items:
            lines.append(f"{Colors.CYAN}🔄 Active Processing:{Colors.END}")
            for item in active_items[:self.max_display_items]:
                lines.append(self._render_item(item))
            lines.append("")

        # Completed items (if showing)
        if self.show_completed:
            completed_items = [item for item in self.current_items.values()
                             if item.state == ProgressState.COMPLETED]

            if completed_items:
                recent_completed = sorted(completed_items,
                                        key=lambda x: x.completed_at or datetime.min,
                                        reverse=True)[:3]

                lines.append(f"{Colors.GREEN}✅ Recently Completed:{Colors.END}")
                for item in recent_completed:
                    lines.append(self._render_completed_item(item))
                lines.append("")

        # Error items
        error_items = [item for item in self.current_items.values()
                      if item.state == ProgressState.ERROR]

        if error_items:
            lines.append(f"{Colors.RED}❌ Errors:{Colors.END}")
            for item in error_items:
                lines.append(self._render_error_item(item))
            lines.append("")

        # Summary
        lines.append(self._render_summary())

        return "\n".join(lines)

    def _render_header(self) -> str:
        """Render dashboard header"""
        now = datetime.now().strftime("%H:%M:%S")
        title = "OOS Background Processing Dashboard"

        # Center the title
        padding = (self.terminal_width - len(title)) // 2
        centered_title = " " * padding + title

        return f"{Colors.CYAN}{Colors.BOLD}{centered_title}{Colors.END} [{now}]"

    def _render_item(self, item: ProgressItem) -> str:
        """Render individual progress item"""
        # Choose color based on state
        color = {
            ProgressState.PENDING: Colors.YELLOW,
            ProgressState.PROCESSING: Colors.BLUE,
            ProgressState.COMPLETED: Colors.GREEN,
            ProgressState.ERROR: Colors.RED,
            ProgressState.WARNING: Colors.YELLOW
        }.get(item.state, Colors.WHITE)

        # Progress bar
        progress_bar = self.progress_bar.render(item.progress, "", color)

        # Title and details
        title_line = f"  {item.title}"
        if item.details:
            title_line += f" - {item.details}"

        # Time info
        time_info = ""
        if item.started_at:
            elapsed = datetime.now() - item.started_at
            time_info = f"({elapsed.seconds}s)"

            if item.estimated_time and item.progress > 0:
                estimated_remaining = int((item.estimated_time * (1 - item.progress)) / item.progress)
                time_info += f" ~{estimated_remaining}s remaining"

        return f"{progress_bar}\n{title_line} {Colors.WHITE}{time_info}{Colors.END}"

    def _render_completed_item(self, item: ProgressItem) -> str:
        """Render completed item"""
        duration = ""
        if item.started_at and item.completed_at:
            delta = item.completed_at - item.started_at
            duration = f"({delta.seconds}s)"

        return f"  {Colors.GREEN}✓{Colors.END} {item.title} {Colors.WHITE}{duration}{Colors.END}"

    def _render_error_item(self, item: ProgressItem) -> str:
        """Render error item"""
        return f"  {Colors.RED}✗{Colors.END} {item.title} - {item.details}"

    def _render_summary(self) -> str:
        """Render summary statistics"""
        total = len(self.current_items)
        active = len([i for i in self.current_items.values()
                     if i.state in [ProgressState.PENDING, ProgressState.PROCESSING]])
        completed = len([i for i in self.current_items.values()
                        if i.state == ProgressState.COMPLETED])
        errors = len([i for i in self.current_items.values()
                     if i.state == ProgressState.ERROR])

        summary_parts = [
            f"{Colors.WHITE}Total: {total}{Colors.END}",
            f"{Colors.BLUE}Active: {active}{Colors.END}",
            f"{Colors.GREEN}Completed: {completed}{Colors.END}"
        ]

        if errors > 0:
            summary_parts.append(f"{Colors.RED}Errors: {errors}{Colors.END}")

        return "📊 " + " | ".join(summary_parts)

    def clear_completed(self):
        """Clear completed items from display"""
        to_remove = [item_id for item_id, item in self.current_items.items()
                    if item.state == ProgressState.COMPLETED]

        for item_id in to_remove:
            del self.current_items[item_id]


class NotificationManager:
    """Manages various types of user notifications"""

    def __init__(self):
        self.notification_history: List[Dict[str, Any]] = []
        self.max_history = 100

    async def show_notification(self, title: str, message: str,
                              notification_type: str = "info",
                              duration: int = 5):
        """Show a notification to the user"""
        # Choose icon and color based on type
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "idea": "💡",
            "completion": "🎉"
        }

        colors = {
            "info": Colors.BLUE,
            "success": Colors.GREEN,
            "warning": Colors.YELLOW,
            "error": Colors.RED,
            "idea": Colors.CYAN,
            "completion": Colors.GREEN
        }

        icon = icons.get(notification_type, "📢")
        color = colors.get(notification_type, Colors.WHITE)

        # Format notification
        notification = f"{color}{icon} {title}{Colors.END}"
        if message:
            notification += f"\n{message}"

        # Show notification
        print(f"\n{notification}\n")

        # Store in history
        self.notification_history.append({
            "timestamp": datetime.now(),
            "title": title,
            "message": message,
            "type": notification_type
        })

        # Cleanup old notifications
        if len(self.notification_history) > self.max_history:
            self.notification_history = self.notification_history[-self.max_history:]

    async def show_idea_received(self, idea_content: str):
        """Show notification for received idea"""
        await self.show_notification(
            "Idea Received",
            f"Processing: {idea_content[:50]}{'...' if len(idea_content) > 50 else ''}",
            "idea"
        )

    async def show_idea_completed(self, idea_content: str, project_name: str):
        """Show notification for completed idea"""
        await self.show_notification(
            "Project Ready!",
            f"'{project_name}' created from: {idea_content[:30]}...",
            "completion"
        )

    async def show_safety_warning(self, issue: str):
        """Show safety warning notification"""
        await self.show_notification(
            "Safety Warning",
            issue,
            "warning"
        )

    async def show_error(self, error_message: str):
        """Show error notification"""
        await self.show_notification(
            "Error",
            error_message,
            "error"
        )


class LiveDashboard:
    """Live updating dashboard for OOS operations"""

    def __init__(self, update_interval: float = 1.0):
        self.status_display = StatusDisplay()
        self.notification_manager = NotificationManager()
        self.update_interval = update_interval
        self.running = False
        self.last_render = ""

    async def start(self):
        """Start the live dashboard"""
        self.running = True

        while self.running:
            try:
                # Clear screen and render dashboard
                current_render = self.status_display.render_dashboard()

                # Only update if content changed
                if current_render != self.last_render:
                    self._clear_screen()
                    print(current_render)
                    self.last_render = current_render

                await asyncio.sleep(self.update_interval)

            except Exception as e:
                print(f"{Colors.RED}Dashboard error: {e}{Colors.END}")
                await asyncio.sleep(5)

    def stop(self):
        """Stop the dashboard"""
        self.running = False

    def _clear_screen(self):
        """Clear terminal screen"""
        print("\033[2J\033[H", end="")

    def add_idea_processing(self, idea_id: str, idea_content: str):
        """Add idea to processing display"""
        item = ProgressItem(
            id=idea_id,
            title=f"Processing: {idea_content[:40]}...",
            state=ProgressState.PROCESSING,
            progress=0.0,
            estimated_time=120  # 2 minutes estimate
        )
        self.status_display.add_item(item)

    def update_idea_progress(self, idea_id: str, phase: str, progress: float):
        """Update idea processing progress"""
        self.status_display.update_item(
            idea_id,
            progress=progress,
            details=f"Phase: {phase}"
        )

    def complete_idea_processing(self, idea_id: str, project_name: str):
        """Mark idea processing as completed"""
        self.status_display.update_item(
            idea_id,
            progress=1.0,
            state=ProgressState.COMPLETED,
            details=f"Created: {project_name}"
        )

    def error_idea_processing(self, idea_id: str, error_message: str):
        """Mark idea processing as error"""
        self.status_display.update_item(
            idea_id,
            state=ProgressState.ERROR,
            details=error_message
        )


# Global instances
_status_display = None
_notification_manager = None
_live_dashboard = None


def get_status_display() -> StatusDisplay:
    """Get or create status display instance"""
    global _status_display
    if _status_display is None:
        _status_display = StatusDisplay()
    return _status_display


def get_notification_manager() -> NotificationManager:
    """Get or create notification manager instance"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def get_live_dashboard() -> LiveDashboard:
    """Get or create live dashboard instance"""
    global _live_dashboard
    if _live_dashboard is None:
        _live_dashboard = LiveDashboard()
    return _live_dashboard


async def start_live_dashboard():
    """Start the live dashboard"""
    dashboard = get_live_dashboard()
    await dashboard.start()


def stop_live_dashboard():
    """Stop the live dashboard"""
    dashboard = get_live_dashboard()
    dashboard.stop()


if __name__ == "__main__":
    # Test the visual feedback system
    async def test():
        print(f"{Colors.CYAN}Testing Visual Feedback System{Colors.END}")

        # Test progress bar
        progress_bar = ProgressBar()
        for i in range(11):
            progress = i / 10
            bar = progress_bar.render(progress, f"Test Progress {i}")
            print(f"\r{bar}", end="", flush=True)
            await asyncio.sleep(0.2)
        print()

        # Test status display
        status = StatusDisplay()

        # Add some test items
        item1 = ProgressItem("1", "Processing idea: Discord bot", ProgressState.PROCESSING, 0.3)
        item2 = ProgressItem("2", "Creating project structure", ProgressState.PROCESSING, 0.7)
        item3 = ProgressItem("3", "Completed project: Weather app", ProgressState.COMPLETED, 1.0)

        status.add_item(item1)
        status.add_item(item2)
        status.add_item(item3)

        print("\n" + status.render_dashboard())

        # Test notifications
        notifications = NotificationManager()
        await notifications.show_idea_received("Create a Discord bot for my gaming server")
        await notifications.show_safety_warning("Code contains potentially risky operations")
        await notifications.show_idea_completed("Discord bot project", "gaming-discord-bot")

        print(f"\n{Colors.GREEN}✅ Visual feedback system test completed{Colors.END}")

    asyncio.run(test())