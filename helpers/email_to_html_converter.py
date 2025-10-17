#!/usr/bin/env python3
"""
Email-to-HTML Converter for Atlas

This script converts email content to HTML format for better display
in the Atlas web interface.
"""

import re
import html
from bs4 import BeautifulSoup

class EmailToHtmlConverter:
    """Converts email content to HTML format"""

    def __init__(self):
        """Initialize the converter"""
        pass

    def convert_text_to_html(self, text_content):
        """
        Convert plain text email content to HTML

        Args:
            text_content (str): Plain text email content

        Returns:
            str: HTML formatted content
        """
        if not text_content:
            return ""

        # Escape HTML characters
        html_content = html.escape(text_content)

        # Convert line breaks to <br> tags
        html_content = html_content.replace('\n', '<br>')

        # Convert URLs to links
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        html_content = re.sub(url_pattern, r'<a href="\g<0>" target="_blank">\g<0></a>', html_content)

        # Wrap in a div with basic styling
        html_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px;">
            {html_content}
        </div>
        """

        return html_content

    def convert_html_to_clean_html(self, html_content):
        """
        Clean and format HTML email content

        Args:
            html_content (str): HTML email content

        Returns:
            str: Cleaned HTML content
        """
        if not html_content:
            return ""

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Add basic styling
        if soup.body:
            body = soup.body
        else:
            body = soup

        # Add inline styles for better display
        style_tag = soup.new_tag('style')
        style_tag.string = """
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
 margin: 0 auto;
            padding: 20px;
        }
        a {
            color: #0066cc;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        """
        soup.head.append(style_tag) if soup.head else soup.insert(0, style_tag)

        return str(soup)

    def convert_email_to_html(self, email_data):
        """
        Convert email data to HTML format

        Args:
            email_data (dict): Email data from EmailIngestor

        Returns:
            str: HTML formatted email
        """
        # Create HTML header
        header_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; border-bottom: 1px solid #eee;">
            <h1 style="color: #333;">{html.escape(email_data.get('subject', 'No Subject'))}</h1>
            <div style="margin-bottom: 10px;">
                <strong>From:</strong> {html.escape(email_data.get('sender', 'Unknown'))}<br>
                <strong>Date:</strong> {html.escape(email_data.get('date', 'Unknown'))}<br>
                <strong>To:</strong> {html.escape(email_data.get('to', 'Unknown'))}
            </div>
        </div>
        """

        # Convert content based on type
        content = email_data.get('content', '')
        if content.strip().startswith('<'):
            # HTML content
            content_html = self.convert_html_to_clean_html(content)
        else:
            # Plain text content
            content_html = self.convert_text_to_html(content)

        # Combine header and content
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{html.escape(email_data.get('subject', 'Email'))}</title>
        </head>
        <body>
            {header_html}
            <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
                {content_html}
            </div>
        </body>
        </html>
        """

        return full_html

def main():
    """Example usage of EmailToHtmlConverter"""
    converter = EmailToHtmlConverter()

    # Example email data
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
    html_output = converter.convert_email_to_html(email_data)
    print("HTML conversion successful!")

    # Save to file for viewing
    with open('email_sample.html', 'w') as f:
        f.write(html_output)

    print("Sample HTML saved to email_sample.html")

if __name__ == "__main__":
    main()