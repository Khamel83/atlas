#!/usr/bin/env python3
"""
Git-first development workflow for Atlas.
Automatically commits work every 15-30 minutes to ensure GitHub backup.
"""

import subprocess
import time
from datetime import datetime


class GitWorkflow:
    def __init__(self, max_work_minutes=20):
        self.max_work_minutes = max_work_minutes
        self.start_time = time.time()

    def check_time_limit(self):
        elapsed = (time.time() - self.start_time) / 60
        return elapsed >= self.max_work_minutes

    def auto_commit(self, message_prefix="WIP"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        commit_msg = f"{message_prefix}: Auto-commit at {timestamp}"

        try:
            subprocess.run(["git", "add", "."], check=True)
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                print("📝 No changes to commit")
                return True

            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push"], check=True)
            print(f"✅ Auto-committed and pushed: {commit_msg}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return False

    def work_with_auto_commit(self, task_function, task_name):
        """Execute work with automatic commits every 20 minutes"""
        print(f"🚀 Starting work on: {task_name}")
        print(f"⏰ Will auto-commit every {self.max_work_minutes} minutes")

        try:
            # Reset timer
            self.start_time = time.time()

            # Do the work
            result = task_function()

            # Commit at the end
            self.auto_commit(f"Complete: {task_name}")

            return result

        except Exception as e:
            # Commit even if there's an error
            self.auto_commit(f"Error during: {task_name}")
            raise e

    def start_timer_loop(self):
        """Start a timer that reminds to commit every max_work_minutes"""
        print(f"⏰ Timer started - will remind every {self.max_work_minutes} minutes")
        print("Use Ctrl+C to stop timer")

        try:
            while True:
                time.sleep(self.max_work_minutes * 60)
                print(f"\n🔔 COMMIT REMINDER: {self.max_work_minutes} minutes elapsed!")
                print("Time to commit your work:")
                print("  git add .")
                print("  git commit -m 'WIP: [describe your work]'")
                print("  git push")
                print("")
        except KeyboardInterrupt:
            print("\n⏹️  Timer stopped")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "timer":
        # Run as timer
        workflow = GitWorkflow(max_work_minutes=20)
        workflow.start_timer_loop()
    else:
        # Example usage
        workflow = GitWorkflow(max_work_minutes=20)
        workflow.auto_commit("Setup: Git workflow system")
