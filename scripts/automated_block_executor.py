#!/usr/bin/env python3
"""
Atlas Automated Block Executor
Executes Blocks 8-16 automatically with strategic commits and context compacting
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_progress():
    """Load execution progress from file"""
    progress_file = Path("block_execution_progress.json")
    if progress_file.exists():
        with open(progress_file, "r") as f:
            progress = json.load(f)
            # Ensure all required keys exist
            if "blocks_completed" not in progress:
                progress["blocks_completed"] = []
            return progress
    return {
        "current_block": 8,
        "blocks_completed": [],
        "started_at": None,
        "last_updated": None,
    }


def save_progress(progress):
    """Save execution progress to file"""
    progress["last_updated"] = datetime.now().isoformat()
    with open("block_execution_progress.json", "w") as f:
        json.dump(progress, f, indent=2)


def execute_git_command(cmd):
    """Execute git command safely"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd="/home/ubuntu/dev/atlas",
        )
        if result.returncode != 0:
            print(f"⚠️ Git command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ Git command exception: {e}")
        return False


def strategic_commit(message, push=True):
    """Make strategic commit with context compacting"""
    print(f"📝 Strategic commit: {message}")

    # Add all changes
    if not execute_git_command("git add -A"):
        return False

    # Commit with message
    commit_cmd = f'git commit -m "feat: {message} 🤖 Generated with [Claude Code](https://claude.ai/code)\\n\\nCo-Authored-By: Claude <noreply@anthropic.com>"'
    if not execute_git_command(commit_cmd):
        return False

    # Push to GitHub
    if push:
        branch = get_current_branch()
        if not execute_git_command(f"git push -u origin {branch}"):
            return False

    return True


def get_current_branch():
    """Get current git branch"""
    try:
        result = subprocess.run(
            "git branch --show-current", shell=True, capture_output=True, text=True
        )
        return result.stdout.strip() or "main"
    except Exception:
        return "main"


def setup_automation_branch():
    """Create and switch to automation branch"""
    print("🌿 Setting up automation branch...")

    # Commit any pending changes first
    print("📝 Adding all changes to staging...")
    execute_git_command("git add -A")
    print("💾 Committing pending changes...")
    execute_git_command(
        'git commit -m "WIP: Save changes before automated execution" || true'
    )

    # Create and checkout feature branch
    branch_name = "feat/automated-blocks"
    print(f"🌿 Switching to branch: {branch_name}")
    if not execute_git_command(
        f"git checkout -b {branch_name} 2>/dev/null || git checkout {branch_name}"
    ):
        print("⚠️ Using current branch instead")

    print("✅ Branch setup complete")
    return True


def implement_block(block_num, spec_file):
    """Implement a specific block using AI assistance"""
    print(f"🚀 Starting Block {block_num} implementation...")

    # Call AI implementer
    cmd = f"python3 helpers/ai_block_implementer.py {block_num} {spec_file}"
    try:
        result = subprocess.run(cmd, shell=True, cwd="/home/ubuntu/dev/atlas")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Block implementation failed: {e}")
        return False


def execute_blocks():
    """Execute all blocks in sequence"""
    progress = load_progress()

    if not progress.get("started_at"):
        progress["started_at"] = datetime.now().isoformat()

    # Setup branch
    setup_automation_branch()

    # Block specifications mapping
    block_specs = {
        8: "docs/specs/BLOCK_8_IMPLEMENTATION.md",
        9: "docs/specs/BLOCK_9_IMPLEMENTATION.md",
        10: "docs/specs/BLOCK_10_IMPLEMENTATION.md",
        11: "docs/specs/BLOCK_11_IMPLEMENTATION.md",
        12: "docs/specs/BLOCK_12_IMPLEMENTATION.md",
        13: "docs/specs/BLOCK_13_IMPLEMENTATION.md",
        15: "docs/specs/BLOCK_15_IMPLEMENTATION.md",
        16: "docs/specs/BLOCK_16_IMPLEMENTATION.md",
    }

    # Execute blocks starting from current
    for block_num in range(progress["current_block"], 17):
        if block_num == 14:  # Skip Block 14 (already complete)
            continue

        if block_num in progress["blocks_completed"]:
            print(f"✅ Block {block_num} already completed, skipping...")
            continue

        print(f"\n{'='*60}")
        print(f"🎯 EXECUTING BLOCK {block_num}")
        print(f"{'='*60}")

        # Strategic commit at block start
        strategic_commit(f"Block {block_num} - Starting implementation")

        # Get spec file (create basic one if missing)
        spec_file = block_specs.get(
            block_num, f"docs/specs/BLOCK_{block_num}_IMPLEMENTATION.md"
        )
        spec_path = Path(spec_file)

        if not spec_path.exists():
            print(f"📝 Creating basic spec for Block {block_num}...")
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(
                f"""# Block {block_num} Implementation

## Overview
Block {block_num} implementation for Atlas.

# Block {block_num}: Implementation Tasks
- [ ] Implement core functionality
- [ ] Add comprehensive testing
- [ ] Update documentation
- [ ] Integration with existing systems

This is a placeholder specification that will be enhanced during implementation.
"""
            )

        # Execute block implementation
        success = implement_block(block_num, str(spec_path))

        if success:
            # Mark as completed
            progress["blocks_completed"].append(block_num)
            progress["current_block"] = block_num + 1
            save_progress(progress)

            # Strategic commit at block completion
            strategic_commit(
                f"Block {block_num} implementation complete - context compacted"
            )

            print(f"✅ Block {block_num} completed successfully")
        else:
            print(f"❌ Block {block_num} implementation failed")
            save_progress(progress)
            return False

    print("\n🎉 ALL BLOCKS COMPLETED SUCCESSFULLY!")
    print("🎯 AUTOMATED EXECUTION COMPLETE!")
    print("Ready for comprehensive review.")

    return True


def main():
    """Main execution function"""
    print("🤖 Starting Automated Block Execution (YOLO Mode)")
    print("=" * 60)

    # Change to Atlas directory
    print(f"📂 Changing to Atlas directory: /home/ubuntu/dev/atlas")
    os.chdir("/home/ubuntu/dev/atlas")
    print(f"📂 Current directory: {os.getcwd()}")

    # Execute blocks
    print("🚀 Starting block execution...")
    success = execute_blocks()

    if success:
        print("🎉 Automated execution completed successfully!")
        sys.exit(0)
    else:
        print("❌ Automated execution failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
