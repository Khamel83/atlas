#!/usr/bin/env python3
"""
Git safety checks to prevent work loss
"""

import os
import subprocess
import sys


def check_git_status():
    """Ensure Git is ready and no work will be lost"""
    try:
        # Check if we're in a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print("❌ Not in a Git repository!")
            return False

        print("✅ In Git repository")

        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        )

        if result.stdout.strip():
            print("⚠️  WARNING: Uncommitted changes detected!")
            print("Uncommitted files:")
            print(result.stdout)

            # In automated mode, just warn but continue
            if len(sys.argv) > 1 and sys.argv[1] == "--auto":
                print("🤖 Auto mode: Continuing with uncommitted changes")
                return True

            response = input("Commit these changes before proceeding? (y/n/skip): ")
            if response.lower() == "y":
                try:
                    subprocess.run(["git", "add", "."], check=True)
                    commit_msg = input(
                        "Commit message (or press Enter for auto message): "
                    )
                    if not commit_msg.strip():
                        commit_msg = f"WIP: Auto-commit before safety check - {os.path.basename(os.getcwd())}"

                    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                    print("✅ Changes committed")

                    # Try to push
                    try:
                        subprocess.run(["git", "push"], check=True, timeout=10)
                        print("✅ Changes pushed to remote")
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                        print("⚠️ Could not push to remote (continuing anyway)")

                except subprocess.CalledProcessError as e:
                    print(f"❌ Git commit failed: {e}")
                    return False

            elif response.lower() == "skip":
                print("⏭️ Skipping commit, continuing...")
            else:
                print("❌ Stopping to prevent work loss")
                return False
        else:
            print("✅ No uncommitted changes")

        # Check if remote is accessible (with timeout)
        try:
            subprocess.run(
                ["git", "ls-remote", "--heads", "origin"],
                check=True,
                capture_output=True,
                timeout=10,
            )
            print("✅ Remote repository accessible")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("⚠️ Remote repository not accessible (continuing anyway)")

        # Check current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()
        print(f"📍 Current branch: {current_branch}")

        # Check if branch is up to date
        try:
            subprocess.run(
                ["git", "fetch"], check=True, capture_output=True, timeout=10
            )

            result = subprocess.run(
                ["git", "status", "-uno"], capture_output=True, text=True, check=True
            )
            if "behind" in result.stdout:
                print("⚠️ Local branch is behind remote")
            elif "ahead" in result.stdout:
                print("📤 Local branch is ahead of remote")
            else:
                print("✅ Branch is up to date with remote")

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("⚠️ Could not check remote status")

        print("✅ Git safety check completed")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Git safety check failed: {e}")
        return False


def enforce_commit_frequency():
    """Check when last commit was made and warn if too long ago"""
    try:
        # Get timestamp of last commit
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            capture_output=True,
            text=True,
            check=True,
        )
        last_commit_timestamp = int(result.stdout.strip())

        import time

        current_timestamp = int(time.time())
        minutes_since_commit = (current_timestamp - last_commit_timestamp) / 60

        if minutes_since_commit > 30:
            print(
                f"⚠️  WARNING: Last commit was {minutes_since_commit:.0f} minutes ago!"
            )
            print(
                "🔔 Consider committing your work more frequently (every 15-20 minutes)"
            )
            return False
        elif minutes_since_commit > 15:
            print(f"⏰ Last commit was {minutes_since_commit:.0f} minutes ago")
            print("💡 Consider committing soon")
        else:
            print(f"✅ Recent commit ({minutes_since_commit:.0f} minutes ago)")

        return True

    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"⚠️ Could not check commit frequency: {e}")
        return True


def main():
    print("🔍 Running Git safety checks...")

    safety_ok = check_git_status()
    frequency_ok = enforce_commit_frequency()

    if safety_ok and frequency_ok:
        print("\n✅ All Git safety checks passed - ready to work!")
        return 0
    else:
        print("\n⚠️ Some checks failed - please review before continuing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
