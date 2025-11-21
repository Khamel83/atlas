#!/bin/bash
set -e

echo "🔍 Running Black (formatter)..."
black .

echo "🧹 Running Ruff (auto-fix)..."
ruff check . --fix

echo "✅ Running pre-commit (final check)..."
pre-commit run --all-files

# Check if there are changes to commit
if [[ -n $(git status --porcelain) ]]; then
  git add .
  git commit -m "Auto-format and lint cleanup"
  git push
  echo "🚀 Changes pushed to GitHub."
else
  echo "✅ No changes to commit. Already clean."
fi
