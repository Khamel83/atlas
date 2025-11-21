#!/usr/bin/env python3
"""
Simple test version of automated block executor
"""

import os
import sys
import subprocess
from helpers.bulletproof_process_manager import get_manager
from pathlib import Path


def implement_block(block_num, spec_file):
    """Test block implementation"""
    print(f"🚀 Testing Block {block_num} implementation...")

    # Call AI implementer
    cmd = f"python3 helpers/ai_block_implementer.py {block_num} {spec_file}"
    print(f"📟 Running command: {cmd}")

    try:
        manager = get_manager()
        process = manager.create_process(
            cmd,
            f"implement_block_{block_num}",
            shell=True,
            cwd="/home/ubuntu/dev/atlas"
        )
        stdout, stderr = process.communicate(timeout=30)

        print(f"📤 Return code: {process.returncode}")
        print(f"📤 STDOUT:\n{stdout.decode('utf-8')}")
        if stderr:
            print(f"📤 STDERR:\n{stderr.decode('utf-8')}")

        return process.returncode == 0
    except subprocess.TimeoutExpired:
        manager.kill_process(process.pid)
        print("❌ Command timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Block implementation failed: {e}")
        return False


def main():
    print("🧪 Testing Block Implementation")
    print("=" * 50)

    os.chdir("/home/ubuntu/dev/atlas")

    # Test Block 8 implementation
    spec_file = "docs/specs/BLOCK_8_IMPLEMENTATION.md"
    spec_path = Path(spec_file)

    if not spec_path.exists():
        print(f"📝 Creating basic spec for Block 8...")
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            """# Block 8: Personal Analytics Dashboard

## Overview
Block 8 implementation for Atlas.

# Block 8: Implementation Tasks
- [ ] Implement core functionality
- [ ] Add comprehensive testing
- [ ] Update documentation
- [ ] Integration with existing systems

This is a placeholder specification that will be enhanced during implementation.
"""
        )

    success = implement_block(8, str(spec_path))

    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
