#!/usr/bin/env python3
"""
Import Path Updater
Updates all import statements when files are moved to new locations
"""

import os
import re
import sys
from pathlib import Path

# Import path mappings for moved files
IMPORT_MAPPINGS = {
    # Core files moved to src/
    'from atlas_data_provider import': 'from src.atlas_data_provider import',
    'from atlas_orchestrator import': 'from src.atlas_orchestrator import',
    'from atlas_unified import': 'from src.atlas_unified import',
    'import atlas_data_provider': 'import src.atlas_data_provider',
    'import atlas_orchestrator': 'import src.atlas_orchestrator',
    'import atlas_unified': 'import src.atlas_unified',

    # Module files
    'from simple_email_ingester import': 'from modules.ingestion.simple_email_ingester import',
    'from transcript_scrapers import': 'from modules.transcript_discovery.transcript_scrapers import',
    'from transcript_fetchers import': 'from modules.transcript_discovery.transcript_fetchers import',

    # Integrations
    'from relayq_integration import': 'from archive.disabled_integrations.relayq_integration import',

    # Tools
    'from diagnostic_analysis import': 'from scripts.maintenance.diagnostic_analysis import',
    'from fix_system import': 'from scripts.maintenance.fix_system import',
}

def update_imports_in_file(file_path):
    """Update import statements in a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Update imports
        for old_import, new_import in IMPORT_MAPPINGS.items():
            content = content.replace(old_import, new_import)

        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def update_all_imports(root_dir='.'):
    """Update imports in all Python files"""
    root = Path(root_dir)
    updated_files = []

    # Find all Python files
    for py_file in root.rglob('*.py'):
        # Skip our own scripts
        if 'scripts/enforcement' in str(py_file):
            continue

        if update_imports_in_file(py_file):
            updated_files.append(str(py_file))
            print(f"✅ Updated imports in {py_file}")

    return updated_files

def update_script_paths():
    """Update paths in shell scripts"""
    root = Path('.')
    updated_scripts = []

    # Common path updates
    path_updates = {
        'python3 atlas_unified.py': 'python3 src/atlas_unified.py',
        './atlas_unified.py': './src/atlas_unified.py',
        'atlas_data_provider.py': 'src/atlas_data_provider.py',
        'atlas_orchestrator.py': 'src/atlas_orchestrator.py',
        'simple_email_ingester.py': 'modules/ingestion/simple_email_ingester.py',
        'diagnostic_analysis.py': 'scripts/maintenance/diagnostic_analysis.py',
        'fix_system.py': 'scripts/maintenance/fix_system.py',
    }

    for script_file in root.rglob('*.sh'):
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Update paths
            for old_path, new_path in path_updates.items():
                content = content.replace(old_path, new_path)

            if content != original_content:
                with open(script_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                updated_scripts.append(str(script_file))
                print(f"✅ Updated paths in {script_file}")

        except Exception as e:
            print(f"Error updating {script_file}: {e}")

    return updated_scripts

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "update-imports":
            updated = update_all_imports()
            print(f"\n📝 Updated imports in {len(updated)} files")
        elif sys.argv[1] == "update-scripts":
            updated = update_script_paths()
            print(f"\n📝 Updated paths in {len(updated)} scripts")
        elif sys.argv[1] == "update-all":
            py_files = update_all_imports()
            sh_files = update_script_paths()
            print(f"\n📝 Updated imports in {len(py_files)} Python files")
            print(f"📝 Updated paths in {len(sh_files)} shell scripts")
    else:
        print("Usage: python update_imports.py [update-imports|update-scripts|update-all]")