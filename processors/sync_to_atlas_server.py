#!/usr/bin/env python3
"""
Sync Atlas data files to server
Run this repeatedly - it will only copy new/changed files
"""

import shutil
import os
import time
from pathlib import Path
import subprocess

# Server details
SERVER_IP = "141.148.146.79"
SERVER_USER = "ubuntu"
SERVER_PATH = "/home/ubuntu/dev/atlas/input/"

# Your local files (Mac paths)
source_files = [
    '/Users/khamel83/Desktop/data for atlas/comprehensive_instapaper_urls_6712_deduplicated.csv',
    '/Users/khamel83/Desktop/data for atlas/Instapaper-Export-2025-03-26_20_23_56.csv',
    '/Users/khamel83/Desktop/data for atlas/MISSING_CONTENT_ALL.csv',
    '/Users/khamel83/Desktop/data for atlas/MISSING_CONTENT_WEB.csv',
    '/Users/khamel83/Desktop/data for atlas/MISSING_PRIVATE_NEWSLETTERS.csv',
    '/Users/khamel83/Desktop/data for atlas/atlas_unified.db',
    '/Users/khamel83/Desktop/data for atlas/instapaper_urls_for_atlas_queue_2025-08-05_21-31-50.txt',
    '/Users/khamel83/Desktop/data for atlas/instapaper_urls_for_atlas_queue_2025-08-05_21-35-44.txt',
    '/Users/khamel83/Desktop/data for atlas/instapaper_urls_for_atlas_queue_2025-08-05_23-00-08.txt',
    '/Users/khamel83/Desktop/data for atlas/instapaper_content_analysis_report_2025-08-05_21-31-22.json',
    '/Users/khamel83/Desktop/data for atlas/instapaper_content_analysis_report_2025-08-05_21-31-50.json',
    '/Users/khamel83/Desktop/data for atlas/instapaper_content_analysis_report_2025-08-05_21-35-44.json',
    '/Users/khamel83/Desktop/data for atlas/instapaper_content_analysis_report_2025-08-05_23-00-08.json',
    '/Users/khamel83/Desktop/data for atlas/private_newsletter_batch_0-49_2025-08-05_21-58-52.json',
    '/Users/khamel83/Desktop/data for atlas/private_newsletter_batch_50-99_2025-08-05_22-01-13.json',
    '/Users/khamel83/Desktop/data for atlas/private_newsletter_batch_100-149_2025-08-05_22-03-18.json'
]

def file_exists_on_server(local_file_path, server_filename):
    """Check if file exists on server and compare sizes"""
    try:
        # Get local file size
        local_size = os.path.getsize(local_file_path)

        # Check server file size
        cmd = f'ssh {SERVER_USER}@{SERVER_IP} "test -f {SERVER_PATH}{server_filename} && stat -f%z {SERVER_PATH}{server_filename} 2>/dev/null || echo 0"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            server_size = int(result.stdout.strip())
            return server_size == local_size and server_size > 0
        return False
    except:
        return False

def upload_file_to_server(local_path, server_filename):
    """Upload single file to server using scp"""
    try:
        cmd = f'scp "{local_path}" {SERVER_USER}@{SERVER_IP}:{SERVER_PATH}{server_filename}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def sync_files_to_atlas_server():
    """Sync files to Atlas server - only uploads new/changed files"""

    print(f"🌐 Syncing to Atlas server: {SERVER_IP}")
    print(f"📁 Target directory: {SERVER_PATH}")
    print("=" * 60)

    uploaded = 0
    skipped = 0
    failed = 0

    for source_path in source_files:
        source = Path(source_path)
        filename = source.name

        # Check if local file exists
        if not source.exists():
            print(f"❌ Local file not found: {filename}")
            failed += 1
            continue

        print(f"📄 Checking: {filename}")

        # Check if file needs upload
        if file_exists_on_server(source_path, filename):
            print(f"⏭️  Already exists with same size - skipping")
            skipped += 1
            continue

        # Upload the file
        print(f"⬆️  Uploading to server...")
        if upload_file_to_server(source_path, filename):
            print(f"✅ Uploaded: {filename}")
            uploaded += 1
        else:
            print(f"❌ Failed to upload: {filename}")
            failed += 1

        # Brief pause between uploads
        time.sleep(0.5)

    print("=" * 60)
    print(f"📊 Sync Summary:")
    print(f"✅ Uploaded: {uploaded}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Failed: {failed}")

    if uploaded > 0:
        print(f"\n🚀 {uploaded} new files uploaded to Atlas server!")
        print("💬 Tell Claude to run: python3 atlas_processor.py")
    else:
        print(f"\n💤 No new files to upload")
        print("💡 Run this script again after iCloud downloads complete")

def continuous_sync():
    """Keep running sync every 5 minutes"""
    print("🔄 Starting continuous sync (every 5 minutes)")
    print("Press Ctrl+C to stop")

    try:
        while True:
            print(f"\n⏰ {time.strftime('%H:%M:%S')} - Running sync...")
            sync_files_to_atlas_server()
            print("💤 Sleeping 5 minutes...")
            time.sleep(300)  # 5 minutes
    except KeyboardInterrupt:
        print("\n🛑 Stopped continuous sync")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        continuous_sync()
    else:
        sync_files_to_atlas_server()

        print(f"\n💡 To run continuously:")
        print(f"   python3 {__file__} --continuous")
        print(f"\n💡 Once files are uploaded, tell Claude to:")
        print(f"   cd /home/ubuntu/dev/atlas && python3 atlas_processor.py")