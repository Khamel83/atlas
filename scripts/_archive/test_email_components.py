#!/usr/bin/env python3
"""
Simple Test Script for Atlas Email Components

This script tests the email components without requiring authentication.
"""

import sys
import os
from pathlib import Path

# Add the helpers directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.email_to_html_converter import EmailToHtmlConverter

def main():
    """Main function to test email components without authentication"""
    print("Atlas Email Components Test")
    print("=" * 30)

    try:
        # Test the email-to-HTML converter
        print("Testing Email-to-HTML Converter...")
        converter = EmailToHtmlConverter()

        # Test email data
        email_data = {
            'subject': 'Weekly Newsletter',
            'sender': 'newsletter@example.com',
            'date': 'Mon, 01 Jan 2023 12:00:00 +0000',
            'to': 'user@example.com',
            'content': '''Hello,

Welcome to our weekly newsletter!

Check out our latest articles:
- How to improve your productivity: http://example.com/productivity
- New features in Atlas: http://example.com/atlas-features

Best regards,
The Team'''
        }

        # Convert to HTML
        print("   Converting email to HTML...")
        html_output = converter.convert_email_to_html(email_data)

        # Save to file
        print("   Saving to file...")
        with open('test_newsletter.html', 'w') as f:
            f.write(html_output)

        print("   Conversion successful!")
        print("   HTML output saved to test_newsletter.html")

        # Verify the output
        assert '<h1' in html_output
        assert 'Weekly Newsletter' in html_output
        assert 'http://example.com/productivity' in html_output
        assert '<a href=' in html_output

        print("\nAll tests passed!")
        print("Email components are working correctly.")

        return True

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)