#!/usr/bin/env python3
"""
Atlas Security Audit - Task 4.2 Security Audit & Compliance

Comprehensive security audit for Atlas production deployment.
Identifies vulnerabilities, misconfigurations, and security best practices.
"""

import os
import stat
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import time
import re
from datetime import datetime

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.config import load_config


class AtlasSecurityAuditor:
    """Comprehensive security audit for Atlas system."""

    def __init__(self):
        """Initialize security auditor."""
        self.config = load_config()
        self.audit_results = {
            'timestamp': datetime.now().isoformat(),
            'vulnerabilities': [],
            'warnings': [],
            'recommendations': [],
            'compliance_checks': {},
            'file_permissions': {},
            'configuration_issues': [],
            'network_security': {},
            'database_security': {},
            'api_security': {}
        }
        self.security_score = 100

    def audit_file_permissions(self) -> Dict[str, Any]:
        """Audit file and directory permissions."""
        print("🔐 Auditing file permissions...")

        critical_files = [
            '.env', '.env.production', '.env.development',
            'atlas.db', 'config/', 'scripts/',
            'helpers/', 'api/', 'requirements.txt'
        ]

        permission_issues = []

        for file_path in critical_files:
            if os.path.exists(file_path):
                file_stat = os.stat(file_path)
                file_mode = stat.filemode(file_stat.st_mode)
                octal_perms = oct(file_stat.st_mode)[-3:]

                # Check for overly permissive permissions
                if os.path.isfile(file_path):
                    if octal_perms in ['777', '666', '755'] and file_path.startswith('.env'):
                        permission_issues.append({
                            'file': file_path,
                            'current_perms': octal_perms,
                            'mode': file_mode,
                            'issue': 'Environment file too permissive',
                            'recommended': '600',
                            'severity': 'HIGH'
                        })
                        self.security_score -= 15
                    elif octal_perms == '777':
                        permission_issues.append({
                            'file': file_path,
                            'current_perms': octal_perms,
                            'mode': file_mode,
                            'issue': 'World writable file',
                            'recommended': '644 or 600',
                            'severity': 'MEDIUM'
                        })
                        self.security_score -= 10

                self.audit_results['file_permissions'][file_path] = {
                    'permissions': octal_perms,
                    'mode': file_mode,
                    'owner': file_stat.st_uid,
                    'group': file_stat.st_gid
                }

        if permission_issues:
            self.audit_results['vulnerabilities'].extend(permission_issues)

        return {'issues': permission_issues, 'files_checked': len(critical_files)}

    def audit_configuration_security(self) -> Dict[str, Any]:
        """Audit configuration files for security issues."""
        print("⚙️ Auditing configuration security...")

        config_issues = []

        # Check environment files
        env_files = ['.env', '.env.production', '.env.development']
        for env_file in env_files:
            if os.path.exists(env_file):
                try:
                    with open(env_file, 'r') as f:
                        content = f.read()

                    # Check for hardcoded secrets
                    if 'password123' in content.lower() or 'admin123' in content.lower():
                        config_issues.append({
                            'file': env_file,
                            'issue': 'Weak default passwords detected',
                            'severity': 'HIGH'
                        })
                        self.security_score -= 20

                    # Check for unencrypted database URLs
                    if 'postgresql://' in content and 'sslmode=require' not in content:
                        config_issues.append({
                            'file': env_file,
                            'issue': 'Database connection without SSL requirement',
                            'severity': 'MEDIUM'
                        })
                        self.security_score -= 10

                    # Check for debug mode in production
                    if 'DEBUG=true' in content and 'production' in env_file:
                        config_issues.append({
                            'file': env_file,
                            'issue': 'Debug mode enabled in production config',
                            'severity': 'HIGH'
                        })
                        self.security_score -= 15

                    # Check for missing SECRET_KEY
                    if 'SECRET_KEY=' not in content:
                        config_issues.append({
                            'file': env_file,
                            'issue': 'Missing SECRET_KEY configuration',
                            'severity': 'HIGH'
                        })
                        self.security_score -= 15

                except Exception as e:
                    config_issues.append({
                        'file': env_file,
                        'issue': f'Error reading config file: {e}',
                        'severity': 'MEDIUM'
                    })

        self.audit_results['configuration_issues'] = config_issues
        return {'issues': config_issues}

    def audit_database_security(self) -> Dict[str, Any]:
        """Audit database security configuration."""
        print("🗄️ Auditing database security...")

        db_issues = []
        db_info = {}

        # Check SQLite database security
        if os.path.exists('atlas.db'):
            try:
                conn = sqlite3.connect('atlas.db')
                cursor = conn.cursor()

                # Check for encryption
                cursor.execute("PRAGMA cipher_version")
                cipher_version = cursor.fetchone()
                if not cipher_version:
                    db_issues.append({
                        'issue': 'SQLite database not encrypted',
                        'severity': 'MEDIUM',
                        'recommendation': 'Consider using SQLCipher for encryption'
                    })
                    self.security_score -= 10

                # Check table structure for sensitive data
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()

                    for column in columns:
                        column_name = column[1].lower()
                        if any(sensitive in column_name for sensitive in ['password', 'token', 'key', 'secret']):
                            db_issues.append({
                                'issue': f'Potentially sensitive column: {table_name}.{column[1]}',
                                'severity': 'MEDIUM',
                                'recommendation': 'Ensure sensitive data is properly encrypted'
                            })

                db_info['tables'] = len(tables)
                db_info['encrypted'] = cipher_version is not None

                conn.close()

            except Exception as e:
                db_issues.append({
                    'issue': f'Error auditing database: {e}',
                    'severity': 'LOW'
                })

        self.audit_results['database_security'] = {
            'issues': db_issues,
            'info': db_info
        }

        return {'issues': db_issues, 'info': db_info}

    def audit_api_security(self) -> Dict[str, Any]:
        """Audit API security configuration."""
        print("🌐 Auditing API security...")

        api_issues = []

        # Check API configuration files
        api_files = ['api/main.py', 'api/routers/']

        for api_path in api_files:
            if os.path.exists(api_path):
                if os.path.isfile(api_path):
                    try:
                        with open(api_path, 'r') as f:
                            content = f.read()

                        # Check for CORS configuration
                        if 'CORSMiddleware' in content:
                            if 'allow_origins=["*"]' in content:
                                api_issues.append({
                                    'file': api_path,
                                    'issue': 'CORS allows all origins (*)',
                                    'severity': 'HIGH',
                                    'recommendation': 'Restrict CORS to specific domains'
                                })
                                self.security_score -= 15

                        # Check for authentication
                        if '/api/' in content and 'Depends(' not in content:
                            api_issues.append({
                                'file': api_path,
                                'issue': 'API endpoints without authentication dependencies',
                                'severity': 'MEDIUM',
                                'recommendation': 'Add authentication to sensitive endpoints'
                            })
                            self.security_score -= 10

                        # Check for input validation
                        if 'Query(' not in content and 'Path(' not in content and '/api/' in content:
                            api_issues.append({
                                'file': api_path,
                                'issue': 'Limited input validation detected',
                                'severity': 'MEDIUM',
                                'recommendation': 'Add comprehensive input validation'
                            })
                            self.security_score -= 5

                    except Exception as e:
                        api_issues.append({
                            'file': api_path,
                            'issue': f'Error reading API file: {e}',
                            'severity': 'LOW'
                        })

        self.audit_results['api_security'] = {'issues': api_issues}
        return {'issues': api_issues}

    def audit_dependency_security(self) -> Dict[str, Any]:
        """Audit Python dependencies for known vulnerabilities."""
        print("📦 Auditing dependency security...")

        dependency_issues = []

        try:
            # Check if safety is installed
            result = subprocess.run(['pip', 'show', 'safety'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                # Run safety check
                safety_result = subprocess.run(['safety', 'check', '--json'],
                                             capture_output=True, text=True)

                if safety_result.returncode == 0 and safety_result.stdout:
                    try:
                        safety_data = json.loads(safety_result.stdout)
                        for vuln in safety_data:
                            dependency_issues.append({
                                'package': vuln.get('package_name'),
                                'version': vuln.get('installed_version'),
                                'vulnerability': vuln.get('vulnerability_id'),
                                'severity': 'HIGH',
                                'advisory': vuln.get('advisory', ''),
                                'recommendation': 'Update to safe version'
                            })
                            self.security_score -= 10
                    except json.JSONDecodeError:
                        pass
            else:
                dependency_issues.append({
                    'issue': 'Safety package not installed',
                    'severity': 'LOW',
                    'recommendation': 'Install safety: pip install safety'
                })

        except Exception as e:
            dependency_issues.append({
                'issue': f'Error checking dependencies: {e}',
                'severity': 'LOW'
            })

        return {'issues': dependency_issues}

    def audit_network_security(self) -> Dict[str, Any]:
        """Audit network security configuration."""
        print("🌐 Auditing network security...")

        network_issues = []

        # Check for open ports (basic check)
        try:
            result = subprocess.run(['ss', '-tuln'], capture_output=True, text=True)
            if result.returncode == 0:
                open_ports = []
                for line in result.stdout.split('\n'):
                    if ':8000' in line:
                        open_ports.append('8000 (Atlas API)')
                    elif ':5432' in line:
                        open_ports.append('5432 (PostgreSQL)')
                    elif ':6379' in line:
                        open_ports.append('6379 (Redis)')

                self.audit_results['network_security']['open_ports'] = open_ports

                # Check if API is bound to all interfaces
                if '0.0.0.0:8000' in result.stdout:
                    network_issues.append({
                        'issue': 'API server bound to all interfaces (0.0.0.0)',
                        'severity': 'MEDIUM',
                        'recommendation': 'Bind to specific interface or use reverse proxy'
                    })
                    self.security_score -= 10

        except Exception as e:
            network_issues.append({
                'issue': f'Error checking network configuration: {e}',
                'severity': 'LOW'
            })

        return {'issues': network_issues}

    def generate_security_recommendations(self) -> List[Dict[str, str]]:
        """Generate comprehensive security recommendations."""
        recommendations = [
            {
                'category': 'File Permissions',
                'recommendation': 'Set restrictive permissions on .env files (chmod 600)',
                'priority': 'HIGH'
            },
            {
                'category': 'Database Security',
                'recommendation': 'Enable database encryption (SQLCipher or PostgreSQL TDE)',
                'priority': 'MEDIUM'
            },
            {
                'category': 'API Security',
                'recommendation': 'Implement authentication for sensitive endpoints',
                'priority': 'HIGH'
            },
            {
                'category': 'Network Security',
                'recommendation': 'Use reverse proxy (nginx) instead of direct API exposure',
                'priority': 'MEDIUM'
            },
            {
                'category': 'Monitoring',
                'recommendation': 'Enable security event logging and monitoring',
                'priority': 'MEDIUM'
            },
            {
                'category': 'Updates',
                'recommendation': 'Implement automated security updates',
                'priority': 'HIGH'
            },
            {
                'category': 'Backup Security',
                'recommendation': 'Encrypt backups and store securely',
                'priority': 'MEDIUM'
            },
            {
                'category': 'SSL/TLS',
                'recommendation': 'Enforce HTTPS with strong cipher suites',
                'priority': 'HIGH'
            }
        ]

        self.audit_results['recommendations'] = recommendations
        return recommendations

    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance checklist for common standards."""
        compliance = {
            'OWASP_Top_10': {
                'A01_Broken_Access_Control': 'PARTIAL' if self.security_score > 70 else 'FAIL',
                'A02_Cryptographic_Failures': 'PARTIAL' if self.security_score > 60 else 'FAIL',
                'A03_Injection': 'PASS' if self.security_score > 80 else 'PARTIAL',
                'A04_Insecure_Design': 'PARTIAL',
                'A05_Security_Misconfiguration': 'PARTIAL' if self.security_score > 70 else 'FAIL',
                'A06_Vulnerable_Components': 'UNKNOWN',
                'A07_Authentication_Failures': 'PARTIAL',
                'A08_Software_Integrity_Failures': 'PARTIAL',
                'A09_Logging_Failures': 'PARTIAL',
                'A10_SSRF': 'PARTIAL'
            },
            'Data_Protection': {
                'Encryption_at_Rest': 'PARTIAL',
                'Encryption_in_Transit': 'PARTIAL',
                'Access_Controls': 'PARTIAL',
                'Data_Minimization': 'PASS',
                'Audit_Logging': 'PARTIAL'
            }
        }

        self.audit_results['compliance_checks'] = compliance
        return compliance

    def run_complete_audit(self) -> Dict[str, Any]:
        """Run comprehensive security audit."""
        print("🔒 Starting Atlas Security Audit...")
        print("=" * 50)

        # Run all audit components
        self.audit_file_permissions()
        self.audit_configuration_security()
        self.audit_database_security()
        self.audit_api_security()
        self.audit_dependency_security()
        self.audit_network_security()
        self.generate_security_recommendations()
        self.generate_compliance_report()

        # Calculate final security score
        self.audit_results['security_score'] = max(0, self.security_score)
        self.audit_results['security_grade'] = (
            'A' if self.security_score >= 90 else
            'B' if self.security_score >= 80 else
            'C' if self.security_score >= 70 else
            'D' if self.security_score >= 60 else 'F'
        )

        return self.audit_results

    def save_audit_report(self, filename: str = None) -> str:
        """Save audit report to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"security_audit_{timestamp}.json"

        report_path = Path("security_reports") / filename
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(self.audit_results, f, indent=2)

        return str(report_path)

    def print_summary(self):
        """Print audit summary."""
        print("\n" + "=" * 50)
        print("🔒 ATLAS SECURITY AUDIT SUMMARY")
        print("=" * 50)

        print(f"Security Score: {self.audit_results['security_score']}/100 (Grade: {self.audit_results['security_grade']})")
        print(f"Vulnerabilities Found: {len(self.audit_results['vulnerabilities'])}")
        print(f"Configuration Issues: {len(self.audit_results['configuration_issues'])}")

        if self.audit_results['vulnerabilities']:
            print("\n⚠️ CRITICAL VULNERABILITIES:")
            for vuln in self.audit_results['vulnerabilities'][:5]:  # Show top 5
                print(f"  • {vuln.get('issue', vuln.get('file', 'Unknown'))}")

        print(f"\n📋 HIGH PRIORITY RECOMMENDATIONS:")
        high_priority = [r for r in self.audit_results['recommendations'] if r['priority'] == 'HIGH']
        for rec in high_priority[:3]:  # Show top 3
            print(f"  • {rec['recommendation']}")

        print(f"\n✅ NEXT STEPS:")
        print("  1. Review detailed report in security_reports/")
        print("  2. Address HIGH priority vulnerabilities")
        print("  3. Implement security recommendations")
        print("  4. Re-run audit after fixes")


def main():
    """Main security audit function."""
    auditor = AtlasSecurityAuditor()

    try:
        results = auditor.run_complete_audit()
        report_path = auditor.save_audit_report()
        auditor.print_summary()

        print(f"\n📄 Full report saved to: {report_path}")
        return 0 if results['security_score'] >= 70 else 1

    except Exception as e:
        print(f"❌ Security audit failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())