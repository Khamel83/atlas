#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/ubuntu/dev/atlas')

from helpers.bulletproof_process_manager import get_manager, create_managed_process
import time
import os

def test_basic_functionality():
    print("🧪 Testing BulletproofProcessManager...")

    # Test process creation
    process = create_managed_process(['sleep', '5'], 'test_process')
    print(f"✅ Created process PID: {process.pid}")

    # Test status
    manager = get_manager()
    status = manager.get_status()
    print(f"✅ Manager status: {status['total_processes']} processes")

    # Test cleanup
    success = manager.kill_process(process.pid)
    print(f"✅ Process cleanup: {'SUCCESS' if success else 'FAILED'}")

    print("🎉 BulletproofProcessManager test completed!")
    return True

if __name__ == "__main__":
    test_basic_functionality()
