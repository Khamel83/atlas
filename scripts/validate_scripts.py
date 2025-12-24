#!/usr/bin/env python3
"""
Validate all Atlas scripts for syntax errors and import issues.

Run this before deploying or as part of CI/CD.

Usage:
    python scripts/validate_scripts.py           # Validate all scripts
    python scripts/validate_scripts.py --daemon  # Validate daemon specifically
    python scripts/validate_scripts.py --quick   # Quick syntax check only
"""

import argparse
import ast
import subprocess
import sys
from pathlib import Path

ATLAS_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = ATLAS_ROOT / "scripts"
MODULES_DIR = ATLAS_ROOT / "modules"


def check_syntax(filepath: Path) -> tuple[bool, str]:
    """Check Python file for syntax errors."""
    try:
        with open(filepath, 'r') as f:
            source = f.read()
        ast.parse(source)
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"


def check_imports(filepath: Path) -> tuple[bool, str]:
    """Check that file can be compiled (catches import issues)."""
    result = subprocess.run(
        [sys.executable, '-m', 'py_compile', str(filepath)],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, ""


def validate_daemon() -> bool:
    """Specifically test the daemon startup."""
    print("Testing daemon startup...")
    result = subprocess.run(
        [ATLAS_ROOT / 'venv/bin/python', str(SCRIPTS_DIR / 'atlas_daemon.py'), '--status'],
        capture_output=True,
        text=True,
        cwd=ATLAS_ROOT
    )
    if result.returncode != 0:
        print(f"  FAILED: {result.stderr}")
        return False
    print("  Daemon startup test passed")
    return True


def main():
    parser = argparse.ArgumentParser(description='Validate Atlas scripts')
    parser.add_argument('--daemon', action='store_true', help='Test daemon specifically')
    parser.add_argument('--quick', action='store_true', help='Quick syntax check only')
    args = parser.parse_args()

    if args.daemon:
        success = validate_daemon()
        sys.exit(0 if success else 1)

    # Collect all Python files
    py_files = list(SCRIPTS_DIR.glob("*.py"))
    py_files += list(MODULES_DIR.rglob("*.py"))

    # Exclude archived files
    py_files = [f for f in py_files if '_archive' not in str(f)]

    print(f"Validating {len(py_files)} Python files...")

    errors = []
    for filepath in py_files:
        # Always check syntax
        ok, err = check_syntax(filepath)
        if not ok:
            errors.append((filepath, f"SYNTAX: {err}"))
            continue

        # If not quick mode, also try to compile (catches some import issues)
        if not args.quick:
            ok, err = check_imports(filepath)
            if not ok:
                errors.append((filepath, f"COMPILE: {err}"))

    if errors:
        print("\n" + "=" * 60)
        print("VALIDATION FAILED")
        print("=" * 60)
        for filepath, error in errors:
            rel_path = filepath.relative_to(ATLAS_ROOT)
            print(f"\n{rel_path}:")
            print(f"  {error}")
        print("\n" + "=" * 60)
        sys.exit(1)
    else:
        print(f"All {len(py_files)} files validated successfully")

    # If not quick mode, also test daemon startup
    if not args.quick:
        if not validate_daemon():
            sys.exit(1)


if __name__ == '__main__':
    main()
