#!/usr/bin/env python3
"""
Atlas Security Hardening - Task 4.2 Security Audit & Compliance

Implements comprehensive security hardening measures for Atlas production deployment.
Addresses vulnerabilities identified in security audit and implements best practices.
"""

import os
import stat
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import shutil
import hashlib
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AtlasSecurityHardening:
    """Comprehensive security hardening for Atlas system."""

    def __init__(self):
        """Initialize security hardening."""
        self.hardening_results = {
            'timestamp': datetime.now().isoformat(),
            'actions_taken': [],
            'warnings': [],
            'recommendations': [],
            'files_secured': [],
            'services_hardened': []
        }

    def secure_file_permissions(self) -> bool:
        """Secure file and directory permissions."""
        print("🔒 Securing file permissions...")

        permission_fixes = [
            # Sensitive config files - owner read only
            ('.env', 0o600),
            ('.env.production', 0o600),
            ('.env.development', 0o600),
            ('atlas.db', 0o600),

            # Script files - owner read/execute, group read
            ('scripts/', 0o750),

            # Code directories - standard permissions
            ('helpers/', 0o755),
            ('api/', 0o755),
            ('config/', 0o755),

            # Log directory - owner read/write, group read
            ('logs/', 0o750),
        ]

        for file_path, perms in permission_fixes:
            if os.path.exists(file_path):
                try:
                    os.chmod(file_path, perms)
                    self.hardening_results['files_secured'].append(f"{file_path}: {oct(perms)}")
                    self.hardening_results['actions_taken'].append(f"Secured permissions for {file_path}")
                except Exception as e:
                    self.hardening_results['warnings'].append(f"Failed to secure {file_path}: {e}")

        return True

    def create_security_headers_middleware(self) -> bool:
        """Create security headers middleware for API."""
        print("🛡️ Creating security headers middleware...")

        middleware_content = '''"""
Security headers middleware for Atlas API.
Implements security best practices with HTTP headers.
"""

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }

        for header, value in security_headers.items():
            response.headers[header] = value

        # Remove server information
        if "server" in response.headers:
            del response.headers["server"]

        return response
'''

        middleware_path = Path("api/middleware/security.py")
        middleware_path.parent.mkdir(exist_ok=True)

        with open(middleware_path, 'w') as f:
            f.write(middleware_content)

        # Create __init__.py for middleware package
        init_path = middleware_path.parent / "__init__.py"
        with open(init_path, 'w') as f:
            f.write("# Security middleware package\n")

        self.hardening_results['actions_taken'].append("Created security headers middleware")
        return True

    def create_rate_limiting_middleware(self) -> bool:
        """Create rate limiting middleware."""
        print("⏱️ Creating rate limiting middleware...")

        rate_limit_content = '''"""
Rate limiting middleware for Atlas API.
Implements request rate limiting to prevent abuse.
"""

import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with sliding window."""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # Max calls per period
        self.period = period  # Period in seconds
        self.clients = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()

        # Clean old requests
        client_requests = self.clients[client_ip]
        while client_requests and client_requests[0] <= now - self.period:
            client_requests.popleft()

        # Check rate limit
        if len(client_requests) >= self.calls:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(self.period)}
            )

        # Add current request
        client_requests.append(now)

        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, self.calls - len(client_requests))
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))

        return response
'''

        rate_limit_path = Path("api/middleware/ratelimit.py")
        with open(rate_limit_path, 'w') as f:
            f.write(rate_limit_content)

        self.hardening_results['actions_taken'].append("Created rate limiting middleware")
        return True

    def create_input_validation_helpers(self) -> bool:
        """Create comprehensive input validation helpers."""
        print("✅ Creating input validation helpers...")

        validation_content = '''"""
Input validation helpers for Atlas API.
Comprehensive validation to prevent injection attacks.
"""

import re
from typing import Optional, List
from fastapi import HTTPException


class InputValidator:
    """Comprehensive input validation utilities."""

    # Safe patterns
    SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,!?()]+$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(r'^https?://[^\s<>"]+$')
    FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')

    @staticmethod
    def validate_string(value: str, max_length: int = 1000, allow_empty: bool = False) -> str:
        """Validate general string input."""
        if not value and not allow_empty:
            raise HTTPException(status_code=400, detail="String cannot be empty")

        if len(value) > max_length:
            raise HTTPException(status_code=400, detail=f"String too long (max {max_length})")

        # Check for potential injection attempts
        dangerous_patterns = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']
        value_lower = value.lower()

        for pattern in dangerous_patterns:
            if pattern in value_lower:
                raise HTTPException(status_code=400, detail="Invalid characters detected")

        return value.strip()

    @staticmethod
    def validate_search_query(query: str) -> str:
        """Validate search query input."""
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")

        query = query.strip()

        if len(query) > 500:
            raise HTTPException(status_code=400, detail="Search query too long (max 500)")

        # Remove potentially dangerous characters but allow normal search terms
        cleaned_query = re.sub(r'[<>"\';\\]', '', query)

        return cleaned_query

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email address."""
        if not email:
            raise HTTPException(status_code=400, detail="Email cannot be empty")

        if not InputValidator.EMAIL_PATTERN.match(email):
            raise HTTPException(status_code=400, detail="Invalid email format")

        return email.lower().strip()

    @staticmethod
    def validate_url(url: str) -> str:
        """Validate URL input."""
        if not url:
            raise HTTPException(status_code=400, detail="URL cannot be empty")

        if not InputValidator.URL_PATTERN.match(url):
            raise HTTPException(status_code=400, detail="Invalid URL format")

        # Block potentially dangerous protocols
        dangerous_protocols = ['file://', 'ftp://', 'data:', 'javascript:', 'vbscript:']
        url_lower = url.lower()

        for protocol in dangerous_protocols:
            if url_lower.startswith(protocol):
                raise HTTPException(status_code=400, detail="Unsupported URL protocol")

        return url.strip()

    @staticmethod
    def validate_filename(filename: str) -> str:
        """Validate filename input."""
        if not filename:
            raise HTTPException(status_code=400, detail="Filename cannot be empty")

        if not InputValidator.FILENAME_PATTERN.match(filename):
            raise HTTPException(status_code=400, detail="Invalid filename format")

        # Block dangerous filenames
        dangerous_names = ['..', '.', 'con', 'prn', 'aux', 'nul']
        if filename.lower() in dangerous_names:
            raise HTTPException(status_code=400, detail="Invalid filename")

        return filename.strip()

    @staticmethod
    def sanitize_html(content: str) -> str:
        """Basic HTML sanitization."""
        if not content:
            return content

        # Remove potentially dangerous HTML tags and attributes
        import html
        content = html.escape(content)

        return content
'''

        validation_path = Path("api/utils/validation.py")
        validation_path.parent.mkdir(exist_ok=True)

        with open(validation_path, 'w') as f:
            f.write(validation_content)

        # Create __init__.py for utils package
        init_path = validation_path.parent / "__init__.py"
        with open(init_path, 'w') as f:
            f.write("# API utilities package\n")

        self.hardening_results['actions_taken'].append("Created input validation helpers")
        return True

    def create_security_monitoring(self) -> bool:
        """Create security event monitoring."""
        print("👁️ Creating security monitoring...")

        monitoring_content = '''"""
Security event monitoring for Atlas.
Logs security events and potential threats.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum


class SecurityEventType(Enum):
    """Types of security events."""
    AUTHENTICATION_FAILURE = "auth_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_REQUEST = "suspicious_request"
    INVALID_INPUT = "invalid_input"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"


class SecurityMonitor:
    """Monitor and log security events."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Setup security logger
        self.logger = logging.getLogger("atlas_security")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_dir / "security_events.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_security_event(
        self,
        event_type: SecurityEventType,
        client_ip: str,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "medium"
    ):
        """Log a security event."""
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "severity": severity,
            "details": details or {}
        }

        self.logger.warning(f"SECURITY EVENT: {json.dumps(event_data)}")

        # Also save to structured log file
        security_log_file = self.log_dir / "security_events.jsonl"
        with open(security_log_file, 'a') as f:
            f.write(json.dumps(event_data) + '\\n')

    def log_suspicious_request(
        self,
        client_ip: str,
        endpoint: str,
        payload: Any,
        reason: str,
        user_agent: Optional[str] = None
    ):
        """Log suspicious request patterns."""
        details = {
            "endpoint": endpoint,
            "payload": str(payload)[:500],  # Truncate long payloads
            "reason": reason
        }

        self.log_security_event(
            SecurityEventType.SUSPICIOUS_REQUEST,
            client_ip,
            user_agent,
            details,
            severity="high"
        )

    def log_authentication_failure(
        self,
        client_ip: str,
        username: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log authentication failures."""
        details = {"attempted_username": username}

        self.log_security_event(
            SecurityEventType.AUTHENTICATION_FAILURE,
            client_ip,
            user_agent,
            details,
            severity="medium"
        )

    def log_rate_limit_exceeded(
        self,
        client_ip: str,
        endpoint: str,
        user_agent: Optional[str] = None
    ):
        """Log rate limit violations."""
        details = {"endpoint": endpoint}

        self.log_security_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            client_ip,
            user_agent,
            details,
            severity="low"
        )


# Global security monitor instance
security_monitor = SecurityMonitor()
'''

        monitoring_path = Path("api/security/monitoring.py")
        monitoring_path.parent.mkdir(exist_ok=True)

        with open(monitoring_path, 'w') as f:
            f.write(monitoring_content)

        # Create __init__.py for security package
        init_path = monitoring_path.parent / "__init__.py"
        with open(init_path, 'w') as f:
            f.write("# Security monitoring package\n")

        self.hardening_results['actions_taken'].append("Created security monitoring system")
        return True

    def create_backup_encryption_script(self) -> bool:
        """Create encrypted backup system."""
        print("💾 Creating encrypted backup system...")

        backup_script_content = '''#!/usr/bin/env python3
"""
Encrypted backup system for Atlas.
Creates encrypted backups of sensitive data.
"""

import os
import gzip
import tarfile
from pathlib import Path
from cryptography.fernet import Fernet
from datetime import datetime
import json


class EncryptedBackup:
    """Create and manage encrypted backups."""

    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.key_file = self.backup_dir / ".backup_key"

        # Generate or load encryption key
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(self.key)
            os.chmod(self.key_file, 0o600)

        self.cipher = Fernet(self.key)

    def create_backup(self, include_database: bool = True) -> str:
        """Create encrypted backup of Atlas data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"atlas_backup_{timestamp}"

        # Create temporary archive
        temp_archive = self.backup_dir / f"{backup_name}.tar.gz"

        with tarfile.open(temp_archive, "w:gz") as tar:
            # Add configuration files
            config_files = [".env", ".env.production", "config/"]
            for config_file in config_files:
                if Path(config_file).exists():
                    tar.add(config_file)

            # Add database
            if include_database and Path("atlas.db").exists():
                tar.add("atlas.db")

            # Add critical scripts and helpers
            for dir_name in ["scripts/", "helpers/", "api/"]:
                if Path(dir_name).exists():
                    tar.add(dir_name)

        # Encrypt the archive
        with open(temp_archive, 'rb') as f:
            data = f.read()

        encrypted_data = self.cipher.encrypt(data)

        encrypted_backup = self.backup_dir / f"{backup_name}.enc"
        with open(encrypted_backup, 'wb') as f:
            f.write(encrypted_data)

        # Remove temporary archive
        temp_archive.unlink()

        # Create backup metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "backup_file": str(encrypted_backup),
            "includes_database": include_database,
            "size_bytes": encrypted_backup.stat().st_size
        }

        metadata_file = self.backup_dir / f"{backup_name}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Encrypted backup created: {encrypted_backup}")
        return str(encrypted_backup)

    def restore_backup(self, backup_file: str, restore_dir: str = "restored"):
        """Restore from encrypted backup."""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        # Decrypt backup
        with open(backup_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = self.cipher.decrypt(encrypted_data)

        # Create temporary archive
        temp_archive = backup_path.parent / "temp_restore.tar.gz"
        with open(temp_archive, 'wb') as f:
            f.write(decrypted_data)

        # Extract archive
        restore_path = Path(restore_dir)
        restore_path.mkdir(exist_ok=True)

        with tarfile.open(temp_archive, "r:gz") as tar:
            tar.extractall(restore_path)

        # Remove temporary archive
        temp_archive.unlink()

        print(f"✅ Backup restored to: {restore_path}")


if __name__ == "__main__":
    backup_system = EncryptedBackup()
    backup_file = backup_system.create_backup()
    print(f"Backup created: {backup_file}")
'''

        backup_script_path = Path("scripts/encrypted_backup.py")
        with open(backup_script_path, 'w') as f:
            f.write(backup_script_content)

        os.chmod(backup_script_path, 0o750)

        self.hardening_results['actions_taken'].append("Created encrypted backup system")
        return True

    def apply_all_hardening(self) -> Dict[str, Any]:
        """Apply all security hardening measures."""
        print("🔒 Applying Atlas Security Hardening...")
        print("=" * 50)

        success = True

        try:
            success &= self.secure_file_permissions()
            success &= self.create_security_headers_middleware()
            success &= self.create_rate_limiting_middleware()
            success &= self.create_input_validation_helpers()
            success &= self.create_security_monitoring()
            success &= self.create_backup_encryption_script()

            if success:
                print("\n🎉 Security hardening completed successfully!")
                print(f"Actions taken: {len(self.hardening_results['actions_taken'])}")
                print(f"Files secured: {len(self.hardening_results['files_secured'])}")

                print("\n📋 NEXT STEPS:")
                print("1. Update API main.py to include security middleware")
                print("2. Test all API endpoints for security compliance")
                print("3. Configure automated encrypted backups")
                print("4. Review security monitoring logs regularly")
            else:
                print("\n❌ Some security hardening steps failed")

        except Exception as e:
            print(f"\n❌ Security hardening failed: {e}")
            success = False

        self.hardening_results['success'] = success
        return self.hardening_results

    def save_hardening_report(self, filename: str = None) -> str:
        """Save hardening report to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"security_hardening_{timestamp}.json"

        report_path = Path("security_reports") / filename
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(self.hardening_results, f, indent=2)

        return str(report_path)


def main():
    """Main security hardening function."""
    hardener = AtlasSecurityHardening()

    results = hardener.apply_all_hardening()
    report_path = hardener.save_hardening_report()

    print(f"\n📄 Hardening report saved to: {report_path}")
    return 0 if results.get('success', False) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())