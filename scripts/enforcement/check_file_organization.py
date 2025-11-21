#!/usr/bin/env python3
"""
File Organization Enforcement Script
Ensures Atlas project maintains proper modular structure
"""

import os
import sys
from pathlib import Path

# STRICT ORGANIZATION RULES
ALLOWED_ROOT_FILES = {
    'README.md', 'CLAUDE.md', 'VERSION', 'LICENSE',
    'pyproject.toml', 'requirements.txt', 'requirements-dev.txt',
    '.env', '.gitignore', '.pre-commit-config.yaml',
    'atlas_content.db', 'podcast_processing.db',  # Main databases
    'atlas_content_before_reorg.db',  # Backup database
    'mypy.ini', 'pytest.ini', 'uv.lock', 'package.json', 'package-lock.json'
}

ALLOWED_ROOT_DIRS = {
    'src', 'modules', 'processors', 'integrations', 'scripts',
    'config', 'tests', 'docs', 'tools', 'data', 'logs',
    'web', 'systemd', 'mobile', 'archive', 'workspaces',
    '__pycache__', 'node_modules', '.git', 'attachments',
    'input', 'uploads', 'exports', 'temp', 'quality_reports'
}

# FILE TYPE MAPPINGS FOR CORRECT PLACEMENT
FILE_TYPE_MAPPINGS = {
    # Core Python files
    'atlas_unified.py': 'src/',
    'atlas_data_provider.py': 'src/',
    'atlas_orchestrator.py': 'src/',

    # Module files by function
    'email': 'modules/ingestion/',
    'ingestion': 'modules/ingestion/',
    'transcript': 'modules/transcript_discovery/',
    'content': 'modules/content_extraction/',
    'analytics': 'modules/analysis/',

    # Scripts
    'autostart': 'scripts/start/',
    'monitor': 'scripts/monitoring/',
    'backup': 'scripts/maintenance/',
    'diagnostic': 'scripts/maintenance/',
    'setup': 'scripts/setup/',

    # Integration files
    'relayq': 'archive/disabled_integrations/',
    'telegram': 'integrations/telegram/',
    'github': 'integrations/github/',
    'velja': 'integrations/velja/',

    # Config files
    '.toml': 'config/',
    '.json': 'config/',
    '.csv': 'data/inputs/',

    # Logs
    '.log': 'logs/',

    # Tests
    'test_': 'tests/',
}

def check_organization():
    """Check if project follows organization rules"""
    root = Path('.')
    violations = []
    suggestions = []

    # Check root directory files
    for item in root.iterdir():
        if item.name.startswith('.'):
            continue  # Skip hidden files

        if item.is_file():
            if item.name not in ALLOWED_ROOT_FILES:
                # Check if it should be moved elsewhere
                suggested_location = get_suggested_location(item.name)
                if suggested_location:
                    suggestions.append(f"Move {item.name} → {suggested_location}{item.name}")
                else:
                    violations.append(f"Unauthorized file in root: {item.name}")

        elif item.is_dir():
            if item.name not in ALLOWED_ROOT_DIRS:
                violations.append(f"Unauthorized directory in root: {item.name}")

    # Report results
    if violations:
        print("❌ CRITICAL ORGANIZATION VIOLATIONS:")
        for violation in violations:
            print(f"  - {violation}")

    if suggestions:
        print("\n🔧 SUGGESTED MOVES:")
        for suggestion in suggestions:
            print(f"  - {suggestion}")

    if violations:
        print(f"\n💥 Found {len(violations)} critical violations")
        return False
    elif suggestions:
        print(f"\n⚠️  Found {len(suggestions)} suggested improvements")
        return True
    else:
        print("✅ Perfect organization!")
        return True

def get_suggested_location(filename):
    """Suggest proper location for a file"""
    for pattern, location in FILE_TYPE_MAPPINGS.items():
        if pattern in filename.lower():
            return location
    return None

def create_directories():
    """Create required directories if they don't exist"""
    required_dirs = [
        'src', 'modules/ingestion', 'modules/transcript_discovery',
        'modules/content_extraction', 'modules/analysis', 'processors',
        'integrations/github', 'integrations/telegram', 'integrations/velja',
        'scripts/start', 'scripts/monitoring', 'scripts/maintenance',
        'scripts/setup', 'config', 'tests/unit', 'tests/integration',
        'docs/architecture', 'docs/guides', 'tools/migration',
        'data/databases', 'data/inputs', 'data/exports', 'logs/historical',
        'web/static', 'web/templates', 'systemd', 'mobile/ios',
        'mobile/bookmarklet', 'archive/disabled_integrations', 'archive/legacy'
    ]

    root = Path('.')
    for dir_path in required_dirs:
        (root / dir_path).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "create-dirs":
        create_directories()
        print("✅ Created required directories")
    else:
        success = check_organization()
        sys.exit(0 if success else 1)