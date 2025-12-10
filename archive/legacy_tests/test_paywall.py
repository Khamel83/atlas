"""
Paywall System Tests

Note: Tests for bypass functionality require legal review flag
"""

from datetime import datetime, timedelta

import pytest

from helpers.paywall import (LegalComplianceError, PaywallBypass,
                             PaywallDetector)


def test_detector_initialization():
    """Test pattern loading."""
    detector = PaywallDetector()
    assert isinstance(detector.patterns, dict)
    assert "dom_selectors" in detector.patterns


def test_bypass_default_disabled():
    """Verify bypass is disabled by default."""
    bypass = PaywallBypass()
    assert bypass.enabled is False
    assert bypass.execute_bypass("<html></html>", "example.com") is None


def test_consent_expiration():
    """Test consent expiration logic."""
    bypass = PaywallBypass()
    test_domain = "test.com"

    # Simulate consent given 31 days ago
    bypass.allowed_domains[test_domain] = datetime.now() - timedelta(days=31)
    assert bypass.check_consent_valid(test_domain) is False


def test_jurisdiction_rules():
    """Verify jurisdiction-specific restrictions."""
    bypass = PaywallBypass()

    # Test archival prohibition
    with pytest.raises(LegalComplianceError):
        bypass.enable_for_domain("archive.example.com", "testing", "de")


@pytest.mark.legal_review
class TestBypassEnabled:
    """Tests requiring legal review flag."""

    def test_domain_enable(self):
        """Test domain-specific enablement."""
        bypass = PaywallBypass()
        bypass.enable_for_domain("example.com", "testing")
        assert "example.com" in bypass.allowed_domains

    def test_watermark_application(self):
        """Verify watermark is applied when required."""
        bypass = PaywallBypass()
        bypass.enable_for_domain("example.com", "testing")
        result = bypass.execute_bypass("<html></html>", "example.com")
        assert "BYPASSED_FOR_PERSONAL_USE_ONLY" in result
