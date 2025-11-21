#!/usr/bin/env python3
"""
Test script for Email-to-HTML Converter
"""

import sys
import os
from pathlib import Path

# Add the helpers directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.email_to_html_converter import EmailToHtmlConverter

def test_text_to_html():
    """Test converting text to HTML"""
    print("Testing text to HTML conversion...")

    converter = EmailToHtmlConverter()

    # Test plain text
    text_content = """Hello,

Welcome to our newsletter!

Check out our latest articles:
- How to improve your productivity: http://example.com/productivity
- New features in Atlas: http://example.com/atlas-features

Best regards,
The Team"""

    html_content = converter.convert_text_to_html(text_content)

    # Check that conversion worked
    assert '<br>' in html_content
    assert '<a href=' in html_content
    assert 'http://example.com/productivity' in html_content
    print("   Text to HTML conversion test passed!")

def test_html_to_clean_html():
    """Test cleaning HTML content"""
    print("Testing HTML cleaning...")

    converter = EmailToHtmlConverter()

    # Test HTML content
    html_content = """<html>
<head>
    <title>Test</title>
    <script>alert('test');</script>
    <style>body { color: red; }</style>
</head>
<body>
    <h1>Welcome</h1>
    <p>Hello <strong>world</strong>!</p>
</body>
</html>"""

    clean_html = converter.convert_html_to_clean_html(html_content)

    # Check that cleaning worked
    # Script tags should be removed
    assert '<script>' not in clean_html
    # Original style tags should be removed
    assert 'body { color: red; }' not in clean_html
    # But new style tags should be added
    assert '<style>' in clean_html
    assert '<h1>Welcome</h1>' in clean_html
    print("   HTML cleaning test passed!")

def test_email_to_html():
    """Test converting email data to HTML"""
    print("Testing email to HTML conversion...")

    converter = EmailToHtmlConverter()

    # Test email data
    email_data = {
        'subject': 'Weekly Newsletter',
        'sender': 'newsletter@example.com',
        'date': 'Mon, 01 Jan 2023 12:00:00 +0000',
        'to': 'user@example.com',
        'content': 'Hello world!'
    }

    html_output = converter.convert_email_to_html(email_data)

    # Check that conversion worked
    assert '<h1' in html_output
    assert 'Weekly Newsletter' in html_output
    assert 'Hello world!' in html_output
    print("   Email to HTML conversion test passed!")

def main():
    """Run all tests"""
    print("Running Email-to-HTML Converter Tests")
    print("=" * 40)

    try:
        test_text_to_html()
        test_html_to_clean_html()
        test_email_to_html()

        print("\nAll tests passed!")
        return True

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)