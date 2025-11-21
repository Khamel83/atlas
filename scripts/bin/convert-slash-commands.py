#!/usr/bin/env python3
"""
Convert OOS JSON slash commands to Claude Code markdown format
"""

import json
import sys
from pathlib import Path


def convert_json_to_claude_commands(json_file: str, output_dir: str = ".claude/commands"):
    """Convert JSON slash commands to Claude Code markdown files"""

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Load JSON commands
    with open(json_file, 'r') as f:
        data = json.load(f)

    commands = data.get('commands', [])

    for cmd in commands:
        name = cmd['name']
        description = cmd['description']
        script = cmd['script']

        # Create markdown file
        filename = f"{name}.md"
        filepath = Path(output_dir) / filename

        # Build content
        content = f"""---
description: "{description}"
tools: ["Bash"]
---

{description}

```bash
./{script} "$ARGUMENTS"
```"""

        # Write file
        filepath.write_text(content)
        print(f"Created: {filepath}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert-slash-commands.py <json_file> [output_dir]")
        sys.exit(1)

    json_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else ".claude/commands"

    if not Path(json_file).exists():
        print(f"Error: {json_file} not found")
        sys.exit(1)

    convert_json_to_claude_commands(json_file, output_dir)
    print(f"Conversion complete! Commands saved to {output_dir}")


if __name__ == '__main__':
    main()