#!/usr/bin/env python3
"""
Continuous Atlas Runner - Auto-restarts processing if it crashes
"""

import subprocess
import time
import os
import signal
import sys
from datetime import datetime

def main():
    """Keep the enhanced processor running continuously"""

    print("🚀 Starting Continuous Atlas Runner")
    print("=" * 50)
    print("✅ Auto-restart enabled")
    print("✅ Will restart on crashes")
    print("✅ Will restart on computer reboot (via cron)")
    print("=" * 50)

    while True:
        try:
            print(f"\n🔄 Starting enhanced processor at {datetime.now()}")
            print("-" * 50)

            # Start the enhanced processor
            process = subprocess.Popen([
                "python3", "enhanced_free_processor.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
               universal_newlines=True, bufsize=1)

            # Monitor output
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[Enhanced] {line.strip()}")

            # Process finished
            return_code = process.wait()
            print(f"\n🏁 Process finished with code: {return_code}")

            if return_code == 0:
                print("✅ Normal completion - checking if more episodes to process...")

                # Check if there are still pending episodes
                result = subprocess.run([
                    "sqlite3", "podcast_processing.db",
                    "SELECT COUNT(*) FROM episodes WHERE processing_status = 'pending';"
                ], capture_output=True, text=True)

                pending_count = int(result.stdout.strip())
                print(f"📊 Pending episodes remaining: {pending_count}")

                if pending_count == 0:
                    print("🎉 All episodes processed! Stopping continuous runner.")
                    break
                else:
                    print("🔄 More episodes to process, restarting in 30 seconds...")
                    time.sleep(30)
            else:
                print(f"❌ Process crashed with code {return_code}, restarting in 60 seconds...")
                time.sleep(60)

        except KeyboardInterrupt:
            print("\n🛑 Received keyboard interrupt, stopping...")
            break
        except Exception as e:
            print(f"❌ Error in continuous runner: {e}")
            print("🔄 Restarting in 60 seconds...")
            time.sleep(60)

    print("🏁 Continuous runner stopped")

if __name__ == "__main__":
    main()