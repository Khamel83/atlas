#!/usr/bin/env python3
"""
Check CPU throttling status and recommendations
"""

import json
import time
import sys
from pathlib import Path

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.resource_manager import ResourceManager

def main():
    """Check throttling status"""
    rm = ResourceManager()

    print("CPU Throttling Check")
    print("=" * 30)

    # Check current throttling status
    throttle_result = rm.check_cpu_throttling()

    print(f"Current Load Average: {throttle_result['load_average']:.2f}")
    print(f"Throttle Threshold:   {throttle_result['threshold']:.2f}")
    print(f"Should Throttle:      {throttle_result['should_throttle']}")
    print(f"Throttle Level:       {throttle_result['throttle_level']}%")

    if throttle_result['should_throttle']:
        print("\n⚠️  HIGH CPU LOAD DETECTED")
        print("Recommendations:")
        print("- Reduce concurrent processes")
        print("- Check for runaway processes")
        print("- Consider scaling horizontally")
        print("- Monitor system performance")
    else:
        print("\n✅ CPU load is within normal limits")

    # Continuous monitoring if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        print("\nStarting continuous monitoring (Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(5)
                result = rm.check_cpu_throttling()
                status = "🔥" if result['should_throttle'] else "✅"
                print(f"{status} Load: {result['load_average']:.2f}, Throttle: {result['throttle_level']}%")
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()