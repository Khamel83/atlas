#!/bin/bash
# Generate a code manifest for the project.

set -e

OUTPUT_FILE="CODE_MANIFEST.md"

# Overwrite the file with the header
echo "# Code Manifest" > "$OUTPUT_FILE"
echo "_Generated on $(date)_" >> "$OUTPUT_FILE"

# Add File Structure
echo -e "\n## File Structure" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
tree -I 'node_modules|.git|.venv|__pycache__|dist|build|site' >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"

# Add Functions and Classes
echo -e "\n## Functions and Classes (Python)" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
grep -r -E '^def |^class ' --include='*.py' . | sed 's/^..//' >> "$OUTPUT_FILE" || true
echo '```' >> "$OUTPUT_FILE"

# Add TODOs and FIXMEs
echo -e "\n## TODOs and FIXMEs" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
grep -r -E 'TODO|FIXME' --exclude-dir='{.git,node_modules,.venv,site}' . | sed 's/^..//' >> "$OUTPUT_FILE" || true
echo '```' >> "$OUTPUT_FILE"

echo "✅ Code manifest generated at $OUTPUT_FILE"