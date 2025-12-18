#!/bin/bash

echo "🔍 Checking for stray config files in atlas/config..."

# Check if config dir exists
if [ -d "atlas/config" ]; then
  echo "📂 Found: atlas/config"

  # List files inside
  echo "📝 Contents:"
  ls -l atlas/config

  # Move files up if not already present
  for file in atlas/config/*; do
    base=$(basename "$file")
    if [ -f "config/$base" ]; then
      echo "⚠️  Skipping existing file: $base"
    else
      mv "$file" config/
      echo "✅ Moved: $base → config/"
    fi
  done

  # Safe delete inner atlas/
  rm -rf atlas
  echo "🧹 Cleaned up: atlas/"
else
  echo "✅ No inner atlas/config found. Nothing to clean."
fi

# Confirm final state
echo "📁 Final structure:"
find . -maxdepth 2 -type d | sort
