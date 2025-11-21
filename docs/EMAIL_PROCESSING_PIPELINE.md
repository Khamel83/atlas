# Atlas Email Processing Pipeline

This document provides an overview of the complete email processing pipeline implemented for Atlas Block 16.

## Overview

The email processing pipeline automatically downloads, processes, and indexes email newsletters using the Gmail API, converting them to HTML format for better display in the Atlas web interface.

## Pipeline Components

### 1. Authentication
- Secure OAuth2 authentication with Google
- Token refresh and validation
- Credential storage

### 2. Email Download
- Incremental email download (only new emails)
- Email metadata extraction
- Newsletter filtering

### 3. Content Conversion
- Plain text to HTML conversion
- HTML cleaning and formatting
- Complete email to HTML document conversion

### 4. Integration
- Atlas content pipeline integration
- Metadata storage
- Deduplication

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements-email-pipeline.txt
   ```

2. Set up Google API credentials:
   - Create a project in the Google Cloud Console
   - Enable the Gmail API
   - Create OAuth2 credentials (client ID and secret)
   - Download the credentials JSON file

3. Run the complete pipeline demo:
   ```bash
   python scripts/demo_complete_email_pipeline.py
   ```

## Features

- Secure authentication with Google
- Automatic email download
- Newsletter identification
- HTML conversion for better display
- Integration with Atlas content pipeline
- Rate limit handling
- Progress tracking

## Security

- Credentials stored securely
- OAuth2 tokens refreshed automatically
- API calls rate-limited
- No permanent storage without user consent

## Testing

Run the unit tests:
```bash
python tests/test_email_auth.py
python tests/test_email_ingestor.py
python tests/test_email_to_html_converter.py
```

## Future Enhancements

- Support for other email providers
- Advanced newsletter categorization using NLP
- Email content summarization
- Automated tagging and organization
- Email-to-note conversion