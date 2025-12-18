#!/bin/bash
# Atlas Database Path Resolver
# Prints the resolved database path for the current environment

set -euo pipefail

# Load environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Use Python to resolve the path via database_config.py
python3 -c "
import sys
sys.path.insert(0, '.')
from helpers.database_config import get_database_path
print(get_database_path())
"