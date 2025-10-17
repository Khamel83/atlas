#!/usr/bin/env python3
"""
Update project-specific Claude Code slash commands.

Reads ops/claude/commands.template.json and merges with existing commands
in $CLAUDE_COMMANDS_FILE or ./.claude/commands.json (created if needed).
"""

import json
import os
import pathlib
import sys
import datetime

# Project-aware updater:
# - Reads ops/claude/commands.template.json
# - Writes to $CLAUDE_COMMANDS_FILE or ./.claude/commands.json (created if needed)
# - Merges by command "name" (upsert). Idempotent.

# Detect if we're running from ops/ directory or project root
ROOT = pathlib.Path.cwd()
if ROOT.name == "ops":
    # Running from ops/ directory - go up one level
    PROJECT_ROOT = ROOT.parent
    TEMPLATE = ROOT / "claude" / "commands.template.json"
else:
    # Running from project root
    PROJECT_ROOT = ROOT
    TEMPLATE = ROOT / "ops" / "claude" / "commands.template.json"

OUT_PATH = os.environ.get("CLAUDE_COMMANDS_FILE", str(PROJECT_ROOT / ".claude" / "commands.json"))

def load_json(p):
    """Load JSON file, return empty structure if not found."""
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"commands": []}
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {p}: {e}")
        sys.exit(1)

def to_index(lst):
    """Convert list of commands to dict indexed by name."""
    return {c.get("name"): c for c in lst if isinstance(c, dict) and c.get("name")}

def main():
    """Main update function."""
    if not TEMPLATE.exists():
        print("WARN: missing ops/claude/commands.template.json; nothing to update")
        return 0

    print(f"Reading template: {TEMPLATE}")
    template = load_json(TEMPLATE)

    print(f"Reading existing commands: {OUT_PATH}")
    existing = load_json(OUT_PATH)

    # Convert to indexes for easy merging
    t_idx = to_index(template.get("commands", []))
    e_idx = to_index(existing.get("commands", []))

    # Count changes
    new_commands = set(t_idx.keys()) - set(e_idx.keys())
    updated_commands = set(t_idx.keys()) & set(e_idx.keys())

    # Merge: template commands override existing ones by name
    e_idx.update(t_idx)  # upsert by name

    # Create merged structure
    merged = {
        "commands": list(e_idx.values()),
        "_updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "_source": "ops/scripts/update_slash_commands.py"
    }

    # Ensure output directory exists
    outp = pathlib.Path(OUT_PATH)
    outp.parent.mkdir(parents=True, exist_ok=True)

    # Write merged commands
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # Report changes
    print(f"UPDATED: {outp}")
    if new_commands:
        print(f"NEW: {', '.join(new_commands)}")
    if updated_commands:
        print(f"UPDATED: {', '.join(updated_commands)}")

    total_commands = len(merged["commands"])
    print(f"TOTAL: {total_commands} commands in {outp}")
    print("NOTE: New/changed commands appear in next Claude Code session")

    return 0

if __name__ == "__main__":
    sys.exit(main())