# Atlas Email Integration

This module provides email newsletter integration capabilities for Atlas, allowing automatic download, processing, and indexing of email newsletters using the Gmail API.

## Features

- OAuth2 authentication with Google
- Download emails from Gmail
- Extract email metadata
- Filter emails to identify newsletters
- Integration with Atlas content pipeline

## Installation

```bash
pip install -r requirements-email.txt
```

## Setup

1. Create a project in the Google Cloud Console
2. Enable the Gmail API
3. Create OAuth2 credentials (client ID and secret)
4. Download the credentials JSON file

## Usage

```python
from helpers.email_auth_manager import EmailAuthManager
from helpers.email_ingestor import EmailIngestor

# Authenticate with Gmail
auth_manager = EmailAuthManager()
service = auth_manager.authenticate()

# Initialize ingestor
ingestor = EmailIngestor(auth_manager)

# Download new emails
emails = ingestor.get_new_emails()

# Filter for newsletters
newsletters = ingestor.filter_newsletters(emails)
```

## Testing

Run the unit tests:

```bash
python tests/test_email_ingestor.py
python tests/test_email_auth.py
```

## Documentation

See `docs/EMAIL_INTEGRATION.md` for detailed documentation.