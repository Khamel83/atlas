"""
Safety and compliance monitoring for Atlas.
Helps users avoid common legal and security pitfalls.
"""

import logging
import os
import re
from typing import Any, Dict, List
from urllib.parse import urlparse


class SafetyMonitor:
    """Monitor for potential safety and compliance issues."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_dir = config.get("data_directory", "output")
        self.logger = logging.getLogger(__name__)

        # Load compliance rules
        self.blocked_domains = self._load_blocked_domains()
        self.sensitive_patterns = self._load_sensitive_patterns()

    def _load_blocked_domains(self) -> List[str]:
        """Load list of domains that should not be accessed."""
        # Common domains that might violate terms of service
        return [
            "facebook.com",  # Often blocks automated access
            "instagram.com",
            "twitter.com",  # API required
            "linkedin.com",  # Terms of service restrictions
        ]

    def _load_sensitive_patterns(self) -> List[str]:
        """Load patterns that might indicate sensitive content."""
        return [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
            r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # Credit card pattern
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email pattern
        ]

    def check_url_safety(self, url: str) -> Dict[str, Any]:
        """Check if a URL is safe to access."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        issues = []
        warnings = []

        # Check blocked domains
        for blocked in self.blocked_domains:
            if blocked in domain:
                issues.append(f"Domain {domain} may block automated access")

        # Check for suspicious patterns
        if "login" in url.lower() or "auth" in url.lower():
            warnings.append("URL appears to require authentication")

        if "paywall" in url.lower() or "subscription" in url.lower():
            warnings.append("URL may be behind a paywall")

        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "domain": domain,
        }

    def scan_content_for_sensitive_data(
        self, content: str, source: str
    ) -> Dict[str, Any]:
        """Scan content for potentially sensitive information."""
        findings = []

        for pattern in self.sensitive_patterns:
            matches = re.findall(pattern, content)
            if matches:
                findings.append(
                    {
                        "pattern": "REDACTED_PATTERN",  # Don't log the actual pattern
                        "count": len(matches),
                        "type": "potentially_sensitive",
                    }
                )

        if findings:
            self.logger.warning(
                f"Sensitive data detected in {source}: {len(findings)} patterns found"
            )

        return {
            "has_sensitive_data": len(findings) > 0,
            "findings_count": len(findings),
            "source": source,
        }

    def check_api_compliance(self, api_name: str, usage_count: int) -> Dict[str, Any]:
        """Check API usage for compliance issues."""
        limits = {
            "openai": {"daily": 1000, "monthly": 30000},
            "openrouter": {"daily": 5000, "monthly": 150000},
        }

        api_limits = limits.get(api_name.lower(), {})
        warnings = []

        if "daily" in api_limits and usage_count > api_limits["daily"] * 0.8:
            warnings.append(f"Approaching daily limit for {api_name}")

        return {
            "compliant": len(warnings) == 0,
            "warnings": warnings,
            "usage_count": usage_count,
        }

    def generate_safety_report(self) -> Dict[str, Any]:
        """Generate a comprehensive safety and compliance report."""
        report = {
            "timestamp": "",
            "data_directory": self.data_dir,
            "total_files": 0,
            "potential_issues": [],
            "recommendations": [],
        }

        # Check file permissions
        if os.path.exists(self.data_dir):
            stat_info = os.stat(self.data_dir)
            permissions = oct(stat_info.st_mode)[-3:]
            if permissions != "700":
                report["potential_issues"].append(
                    f"Data directory permissions are {permissions}, recommend 700"
                )

        # Check for .env file security (check both config/.env and root .env)
        env_files = ["config/.env", ".env"]
        for env_file in env_files:
            if os.path.exists(env_file):
                stat_info = os.stat(env_file)
                permissions = oct(stat_info.st_mode)[-3:]
                if permissions != "600":
                    report["potential_issues"].append(
                        f"{env_file} file permissions are {permissions}, recommend 600"
                    )
                break  # Only check the first one that exists

        # Add general recommendations
        report["recommendations"] = [
            "Use full-disk encryption on devices running Atlas",
            "Regularly backup your data directory",
            "Review and rotate API keys periodically",
            "Monitor system logs for errors or warnings",
            "Keep Atlas and dependencies updated",
        ]

        return report


def check_pre_run_safety(config: Dict[str, Any]) -> bool:
    """Run safety checks before starting Atlas operations."""
    SafetyMonitor(config)

    # Check basic security setup
    issues = []

    # Check .env file permissions (check both config/.env and root .env)
    env_files = ["config/.env", ".env"]
    for env_file in env_files:
        if os.path.exists(env_file):
            stat_info = os.stat(env_file)
            permissions = oct(stat_info.st_mode)[-3:]
            if permissions not in ["600", "400"]:
                issues.append(
                    f"⚠️  {env_file} file should have 600 permissions: chmod 600 {env_file}"
                )
            break  # Only check the first one that exists

    # Check data directory permissions
    data_dir = config.get("data_directory", "output")
    if os.path.exists(data_dir):
        stat_info = os.stat(data_dir)
        permissions = oct(stat_info.st_mode)[-3:]
        if permissions not in ["700", "755"]:
            issues.append(
                f"⚠️  Data directory should have 700 permissions: chmod 700 {data_dir}"
            )

    if issues:
        print("\n🔒 Security Issues Detected:")
        for issue in issues:
            print(f"   {issue}")
        print()

        # Auto-continue for YOLO mode
        print("⚠️  Auto-continuing despite security issues (YOLO mode)")
        return True

    return True
