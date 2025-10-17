#!/bin/bash

# Navigate to the project root directory
cd /home/ubuntu/dev/atlas || { echo "Error: Could not navigate to project directory."; exit 1; }

# Activate the virtual environment
source .venv/bin/activate || { echo "Error: Could not activate virtual environment."; exit 1; }

# Install/update Python dependencies
echo "Installing/updating Python dependencies..."
pip install -r requirements.txt || { echo "Error: Failed to install dependencies."; exit 1; }

# Clear the search index (non-interactively)
echo "Attempting to clear the search index..."
echo "y" | .venv/bin/python scripts/search_manager.py clear || { echo "Error: Failed to clear search index."; exit 1; }

echo "Script finished. Please check the output for any errors."