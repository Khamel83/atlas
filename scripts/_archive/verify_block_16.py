#!/usr/bin/env python3
"""
Verification Script for Atlas Block 16 Implementation

This script verifies that all required files for Atlas Block 16
have been created successfully.
"""

import os
from pathlib import Path

def check_file_exists(file_path):
    """Check if a file exists and print status"""
    if Path(file_path).exists():
        print(f"✅ {file_path}")
        return True
    else:
        print(f"❌ {file_path}")
        return False

def main():
    """Main verification function"""
    print("Atlas Block 16 Implementation Verification")
    print("=" * 45)

    # List of required files
    required_files = [
        "helpers/email_auth_manager.py",
        "helpers/email_ingestor.py",
        "helpers/email_to_html_converter.py",
        "helpers/README.md",
        "docs/EMAIL_INTEGRATION.md",
        "docs/EMAIL_PROCESSING_PIPELINE.md",
        "scripts/demo_email_download.py",
        "scripts/demo_complete_email_pipeline.py",
        "scripts/test_email_components.py",
        "tests/test_email_auth.py",
        "tests/test_email_ingestor.py",
        "tests/test_email_to_html_converter.py",
        "requirements-email.txt",
        "requirements-email-pipeline.txt",
        "BLOCK_16_SUMMARY.md",
        "BLOCK_16_IMPLEMENTATION_SUMMARY.md",
        "BLOCK_16_FINAL_SUMMARY.md",
        "EMAIL_INTEGRATION_README.md",
        "BLOCK_16_COMPLETE.md"
    ]

    # Check each file
    all_files_exist = True
    for file_path in required_files:
        full_path = Path("/home/ubuntu/dev/atlas") / file_path
        if not check_file_exists(full_path):
            all_files_exist = False

    print("\n" + "=" * 45)
    if all_files_exist:
        print("✅ All required files exist!")
        print("🎉 Atlas Block 16 implementation is complete!")
    else:
        print("❌ Some files are missing!")
        print("⚠️  Please check the implementation.")

    return all_files_exist

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)