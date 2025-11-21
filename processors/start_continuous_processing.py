#!/usr/bin/env python3
"""
Start Atlas Continuous Processing
Launch the full non-stop processing pipeline
"""

import subprocess
import sys
import os
from datetime import datetime

def main():
    print("🚀 Starting Atlas Continuous Processing Pipeline")
    print("=" * 60)
    print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Objective: Process ALL 2,373 episodes non-stop")
    print("📊 Success Threshold: 50% (self-correcting if below)")
    print("⚡ Strategy: Continuous processing with auto-optimization")
    print()
    print("🔧 Features:")
    print("   ✅ Non-stop batch processing")
    print("   ✅ Self-correcting failure patterns")
    print("   ✅ Auto-blacklist 100% failure sources")
    print("   ✅ Adaptive batch sizing")
    print("   ✅ Real-time progress tracking")
    print("   ✅ Automatic status reporting")
    print()
    print("📊 Processing Plan:")
    print("   Phase 1: Validate with first 10 episodes (already running)")
    print("   Phase 2: Scale to 50 episodes per batch")
    print("   Phase 3: Full speed until complete")
    print()
    print("🎯 Expected Timeline:")
    print("   - Phase 1 results: 24-48 hours")
    print("   - Full processing: 2-5 days")
    print("   - Total completion: ~1 week")
    print()
    print("📝 Files Generated:")
    print("   - atlas_processing_status_*.json (live status)")
    print("   - failure_patterns_*.json (optimization data)")
    print("   - ATLAS_FINAL_REPORT_*.md (final results)")
    print()
    print("⚠️ To monitor progress:")
    print(f"   tail -f atlas_processing_status_*.json")
    print(f"   watch -n 60 'python3 atlas_data_provider.py stats'")
    print()
    print("🚀 Starting continuous processor...")
    print("   (This will run non-stop until all episodes are processed)")
    print()

    # Start the continuous processor
    try:
        subprocess.run([sys.executable, "continuous_processor.py"], check=True)
    except KeyboardInterrupt:
        print("\n⚠️ Processing interrupted by user")
        print("💾 Status saved - can resume later")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Processing failed: {e}")
        print("💾 Status saved - check error logs")

    print("\n🏁 Atlas processing complete or interrupted")

if __name__ == "__main__":
    main()