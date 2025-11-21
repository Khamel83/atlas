#!/usr/bin/env python3
"""
Quick script to copy Atlas data files to the correct location
Run this on your local Mac where the files are located
"""

import shutil
import os
from pathlib import Path

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

def copy_files_to_atlas_input():
    """Copy all files to Atlas input directory"""

    # Target directory - adjust this to where your Atlas input folder is
    target_dir = Path("/Users/khamel83/dev/atlas/input")  # Local Atlas directory

    # OR if you want to copy to a temp folder for uploading to server:
    # target_dir = Path("/Users/khamel83/Desktop/atlas_upload")

    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Copying files to: {target_dir}")
    print("=" * 50)

    copied = 0
    failed = 0

    for source_path in source_files:
        source = Path(source_path)

        if not source.exists():
            print(f"❌ File not found: {source}")
            failed += 1
            continue

        # Get just the filename
        filename = source.name
        target_path = target_dir / filename

        try:
            # Copy the file
            shutil.copy2(source, target_path)
            print(f"✅ Copied: {filename}")
            copied += 1
        except Exception as e:
            print(f"❌ Failed to copy {filename}: {e}")
            failed += 1

    print("=" * 50)
    print(f"📊 Summary: {copied} copied, {failed} failed")

    if copied > 0:
        print(f"\n🚀 Files are ready in: {target_dir}")
        print("\nNext steps:")
        print("1. If this is your local Atlas: cd ~/dev/atlas && python3 atlas_processor.py")
        print("2. If uploading to server: scp -r target_dir ubuntu@your-server:/home/ubuntu/dev/atlas/input/")

if __name__ == "__main__":
    copy_files_to_atlas_input()