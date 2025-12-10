#!/usr/bin/env python3
"""
Test script for Email Ingestor
"""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add the helpers directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from helpers.email_ingestor import EmailIngestor

def test_email_ingestor_initialization():
    """Test EmailIngestor initialization"""
    print("Testing EmailIngestor initialization...")

    # Create a mock auth manager
    mock_auth_manager = Mock()
    mock_auth_manager.get_service.return_value = Mock()

    # Initialize the ingestor
    ingestor = EmailIngestor(mock_auth_manager)

    # Check that the ingestor was created successfully
    assert ingestor.auth_manager == mock_auth_manager
    assert ingestor.service is not None
    print("   Initialization test passed!")

def test_extract_header():
    """Test header extraction"""
    print("Testing header extraction...")

    # Create a mock auth manager
    mock_auth_manager = Mock()
    mock_auth_manager.get_service.return_value = Mock()

    # Initialize the ingestor
    ingestor = EmailIngestor(mock_auth_manager)

    # Test headers
    headers = [
        {'name': 'From', 'value': 'test@example.com'},
        {'name': 'Subject', 'value': 'Test Subject'},
        {'name': 'Date', 'value': 'Mon, 01 Jan 2023 12:00:00 +0000'}
    ]

    # Test extraction
    assert ingestor.extract_header(headers, 'From') == 'test@example.com'
    assert ingestor.extract_header(headers, 'Subject') == 'Test Subject'
    assert ingestor.extract_header(headers, 'Date') == 'Mon, 01 Jan 2023 12:00:00 +0000'
    assert ingestor.extract_header(headers, 'Nonexistent') == ''

    print("   Header extraction test passed!")

def test_filter_newsletters():
    """Test newsletter filtering"""
    print("Testing newsletter filtering...")

    # Create a mock auth manager
    mock_auth_manager = Mock()
    mock_auth_manager.get_service.return_value = Mock()

    # Initialize the ingestor
    ingestor = EmailIngestor(mock_auth_manager)

    # Test emails
    emails = [
        {'subject': 'Weekly Newsletter', 'sender': 'news@example.com'},
        {'subject': 'Monthly Digest', 'sender': 'digest@example.com'},
        {'subject': 'Meeting Notes', 'sender': 'colleague@example.com'},
        {'subject': 'Product Update', 'sender': 'noreply@example.com'}
    ]

    # Filter for newsletters
    newsletters = ingestor.filter_newsletters(emails)

    # Check that newsletters were identified
    assert len(newsletters) >= 2  # At least 2 should be identified as newsletters

    print("   Newsletter filtering test passed!")

def main():
    """Run all tests"""
    print("Running Email Ingestor Tests")
    print("=" * 30)

    try:
        test_email_ingestor_initialization()
        test_extract_header()
        test_filter_newsletters()

        print("\nAll tests passed!")
        return True

    except Exception as e:
        print(f"\nTest failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)