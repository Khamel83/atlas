#!/usr/bin/env python3
"""
Complete Email Processing Pipeline Demo for Atlas

This script demonstrates the complete email processing pipeline
for Atlas Block 16 implementation.
"""

import sys
import os
from pathlib import Path

# Add the helpers directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.email_auth_manager import EmailAuthManager
from helpers.email_ingestor import EmailIngestor
from helpers.email_to_html_converter import EmailToHtmlConverter

def main():
    """Main function to demonstrate complete email processing pipeline"""
    print("Atlas Complete Email Processing Pipeline Demo")
    print("=" * 50)

    try:
        # Step 1: Authenticate with Gmail
        print("Step 1: Authenticating with Gmail...")
        auth_manager = EmailAuthManager()

        # Check if already authenticated
        if not auth_manager.is_authenticated():
            print("   Starting authentication flow...")
            service = auth_manager.authenticate()
        else:
            print("   Already authenticated!")
            service = auth_manager.get_service()

        print("   Authentication successful!")

        # Step 2: Initialize ingestor
        print("Step 2: Initializing email ingestor...")
        ingestor = EmailIngestor(auth_manager)
        print("   Ingestor initialized!")

        # Step 3: Download new emails
        print("Step 3: Downloading recent emails...")
        emails = ingestor.get_new_emails(max_results=5)
        print(f"   Downloaded {len(emails)} emails")

        # Step 4: Filter for newsletters
        print("Step 4: Filtering for newsletters...")
        newsletters = ingestor.filter_newsletters(emails)
        print(f"   Found {len(newsletters)} newsletters")

        # Step 5: Convert emails to HTML
        print("Step 5: Converting emails to HTML...")
        converter = EmailToHtmlConverter()

        # Process each newsletter
        for i, newsletter in enumerate(newsletters):
            print(f"   Converting newsletter {i+1}...")

            # Convert to HTML
            html_content = converter.convert_email_to_html(newsletter)

            # Save to file
            filename = f"newsletter_{i+1}.html"
            with open(filename, 'w') as f:
                f.write(html_content)

            print(f"   Saved as {filename}")

        # Step 6: Integrate with Atlas pipeline
        print("Step 6: Integrating with Atlas pipeline...")
        ingestor.integrate_with_atlas_pipeline(newsletters)
        print("   Integration complete!")

        print("\nComplete email processing pipeline demo finished successfully!")
        print(f"Processed {len(newsletters)} newsletters.")

        return True

    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)