#!/usr/bin/env python3
"""
Email Download Demonstration Script

This script demonstrates the email download functionality
for Atlas Block 16 implementation.
"""

import sys
import os
from pathlib import Path

# Add the helpers directory to the path
sys.path.append(str(Path(__file__).parent))

from helpers.email_auth_manager import EmailAuthManager
from helpers.email_ingestor import EmailIngestor

def main():
    """Main function to demonstrate email download"""
    print("Atlas Email Download Demonstration")
    print("=" * 40)

    # Initialize authentication
    print("1. Initializing authentication...")
    auth_manager = EmailAuthManager()

    try:
        # Authenticate with Gmail
        print("2. Authenticating with Gmail...")
        service = auth_manager.authenticate()
        print("   Authentication successful!")

        # Initialize ingestor
        print("3. Initializing email ingestor...")
        ingestor = EmailIngestor(auth_manager)

        # Download new emails
        print("4. Downloading recent emails...")
        emails = ingestor.get_new_emails(max_results=10)

        print(f"   Downloaded {len(emails)} emails")

        # Display email information
        if emails:
            print("\n5. Email Summary:")
            for i, email in enumerate(emails[:5], 1):  # Show first 5 emails
                print(f"   {i}. From: {email.get('sender', 'Unknown')}")
                print(f"      Subject: {email.get('subject', 'No Subject')}")
                print(f"      Date: {email.get('date', 'Unknown')}")
                print(f"      Size: {email.get('size', 0)} bytes")
                print()

        # Filter for newsletters
        print("6. Filtering for newsletters...")
        newsletters = ingestor.filter_newsletters(emails)
        print(f"   Found {len(newsletters)} newsletters")

        # Integration with Atlas pipeline
        print("7. Integrating with Atlas pipeline...")
        ingestor.integrate_with_atlas_pipeline(newsletters)
        print("   Integration complete!")

        print("\nDemonstration completed successfully!")

    except Exception as e:
        print(f"Error during demonstration: {e}")
        return False

    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)