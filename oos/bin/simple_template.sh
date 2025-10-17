#!/bin/bash
# Simple Template Manager - 5 lines instead of 809

PROJECT_NAME="$1"
[ -z "$PROJECT_NAME" ] && echo "Usage: $0 project_name" && exit 1
mkdir -p "$PROJECT_NAME"
cp -r templates/basic/* "$PROJECT_NAME/" 2>/dev/null || echo "No basic template found"
echo "✅ Created $PROJECT_NAME"