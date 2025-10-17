"""
Intelligent Safety Guardrails for OOS
Protects users from dangerous operations and provides safe project execution
"""

import asyncio
import json
import re
import os
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import hashlib

from renderers import Colors


class SafetyLevel(Enum):
    """Safety levels for operations"""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"
    BLOCKED = "blocked"


@dataclass
class SafetyCheck:
    """Result of a safety check"""
    level: SafetyLevel
    message: str
    details: Dict[str, Any]
    recommendations: List[str]
    requires_confirmation: bool = False
    allowed_alternatives: List[str] = None


@dataclass
class CodeScan:
    """Result of code safety scanning"""
    is_safe: bool
    vulnerabilities: List[Dict[str, Any]]
    suspicious_patterns: List[str]
    recommendations: List[str]
    confidence: float


class SafetyGuardrails:
    """Intelligent safety system for OOS operations"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sandbox_enabled = config.get('sandbox_enabled', True)
        self.max_file_size = config.get('max_file_size', 10 * 1024 * 1024)  # 10MB
        self.allowed_operations = self._load_allowed_operations()
        self.blocked_patterns = self._load_blocked_patterns()
        self.safe_libraries = self._load_safe_libraries()
        self.suspicious_imports = self._load_suspicious_imports()

    def _load_allowed_operations(self) -> Set[str]:
        """Load allowed file operations"""
        return {
            'read', 'write', 'create', 'append', 'list', 'exists',
            'download', 'upload', 'copy', 'move', 'rename'
        }

    def _load_blocked_patterns(self) -> List[re.Pattern]:
        """Load patterns that are potentially dangerous"""
        patterns = [
            # System commands
            re.compile(r'system\s*\(', re.IGNORECASE),
            re.compile(r'exec\s*\(', re.IGNORECASE),
            re.compile(r'eval\s*\(', re.IGNORECASE),
            re.compile(r'subprocess\s*\.', re.IGNORECASE),
            re.compile(r'os\s*\.(system|popen|exec)', re.IGNORECASE),

            # File operations on system paths
            re.compile(r'(/[eE][tT][cC]|/[uU][sS][rR]|/[bB][iI][nN]|/[sS][bB][iI][nN])'),

            # Network operations to internal addresses
            re.compile(r'(127\.0\.0\.1|localhost|::1|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)'),

            # Cryptocurrency mining
            re.compile(r'(mining|mine|crypto|bitcoin|ethereum)', re.IGNORECASE),

            # Password/Credential theft
            re.compile(r'(password|credential|secret|token|key|auth)', re.IGNORECASE),

            # Destructive operations
            re.compile(r'(\.remove\(|\.delete\(|rmdir|shutil\.rmtree)', re.IGNORECASE),
        ]
        return patterns

    def _load_safe_libraries(self) -> Set[str]:
        """Load libraries that are generally safe to use"""
        return {
            'requests', 'beautifulsoup4', 'pandas', 'numpy', 'matplotlib',
            'seaborn', 'plotly', 'flask', 'fastapi', 'sqlalchemy',
            'openpyxl', 'pillow', 'python-dotenv', 'click', 'rich',
            'typer', 'pydantic', 'asyncio', 'aiohttp', 'discord.py',
            'slack-sdk', 'schedule', 'smtplib', 'email'
        }

    def _load_suspicious_imports(self) -> Set[str]:
        """Load imports that require extra scrutiny"""
        return {
            'os', 'sys', 'subprocess', 'shutil', 'glob', 'tempfile',
            'socket', 'urllib', 'requests', 'http', 'ftplib',
            'smtplib', 'poplib', 'imaplib', 'nntplib', 'sqlite3',
            'ctypes', 'mmap', 'win32api', 'win32con', 'win32file'
        }

    async def check_idea_safety(self, idea_content: str) -> SafetyCheck:
        """Check if an idea is safe to implement"""
        issues = []
        recommendations = []
        risk_level = SafetyLevel.SAFE

        # Check for dangerous keywords
        dangerous_keywords = [
            'hack', 'crack', 'steal', 'phish', 'malware', 'virus',
            'keylogger', 'backdoor', 'rootkit', 'exploit'
        ]

        for keyword in dangerous_keywords:
            if keyword.lower() in idea_content.lower():
                issues.append(f"Potentially malicious keyword detected: '{keyword}'")
                risk_level = SafetyLevel.DANGER

        # Check for potentially risky operations
        risky_patterns = [
            ('automated trading', 'financial risk'),
            ('medical diagnosis', 'health/safety risk'),
            ('legal advice', 'legal risk'),
            ('investment advice', 'financial risk'),
            ('surveillance', 'privacy risk'),
            ('authentication bypass', 'security risk')
        ]

        for pattern, risk in risky_patterns:
            if pattern.lower() in idea_content.lower():
                issues.append(f"High-risk area: {risk}")
                recommendations.append(f"Consider consulting a professional for {pattern}")
                if risk_level.value < 'warning':
                    risk_level = SafetyLevel.WARNING

        # Check for complexity that might be unsafe
        complexity_indicators = [
            'multiple apis', 'integrate with', 'connect to',
            'real-time', 'live data', 'production'
        ]

        high_complexity = sum(1 for indicator in complexity_indicators
                           if indicator in idea_content.lower())

        if high_complexity >= 2:
            issues.append("High complexity project - potential for bugs")
            recommendations.append("Start with a minimal viable product")
            if risk_level.value < 'warning':
                risk_level = SafetyLevel.WARNING

        return SafetyCheck(
            level=risk_level,
            message=f"Idea safety assessment: {risk_level.value}",
            details={
                'issues': issues,
                'complexity_score': high_complexity,
                'keyword_matches': len([k for k in dangerous_keywords if k.lower() in idea_content.lower()])
            },
            recommendations=recommendations,
            requires_confirmation=risk_level in [SafetyLevel.WARNING, SafetyLevel.DANGER]
        )

    async def scan_code_safety(self, code: str, file_path: str = None) -> CodeScan:
        """Scan code for potential security issues"""
        vulnerabilities = []
        suspicious_patterns = []
        recommendations = []
        confidence = 1.0

        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                continue

            # Check for blocked patterns
            for pattern in self.blocked_patterns:
                if pattern.search(line):
                    suspicious_patterns.append(f"Line {i}: {line.strip()}")
                    vulnerabilities.append({
                        'line': i,
                        'content': line.strip(),
                        'type': 'suspicious_pattern',
                        'severity': 'high' if 'system' in line.lower() or 'exec' in line.lower() else 'medium'
                    })

            # Check for suspicious imports
            for suspicious_import in self.suspicious_imports:
                if f'import {suspicious_import}' in line or f'from {suspicious_import}' in line:
                    suspicious_patterns.append(f"Line {i}: Importing {suspicious_import}")

                    # Check if the import is used safely
                    if self._is_suspicious_usage(suspicious_import, lines):
                        vulnerabilities.append({
                            'line': i,
                            'content': line.strip(),
                            'type': 'dangerous_import',
                            'severity': 'medium'
                        })
                        recommendations.append(f"Review usage of {suspicious_import} module")

            # Check for hardcoded secrets
            secret_patterns = [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']'
            ]

            for pattern in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    vulnerabilities.append({
                        'line': i,
                        'content': line.strip(),
                        'type': 'hardcoded_secret',
                        'severity': 'high'
                    })
                    recommendations.append("Move secrets to environment variables")

            # Check for unsafe file operations
            if any(op in line for op in ['open(', 'file(', 'with open']):
                if 'w' in line or 'a' in line:
                    # Check if it's writing to a safe location
                    if not self._is_safe_file_operation(line):
                        vulnerabilities.append({
                            'line': i,
                            'content': line.strip(),
                            'type': 'unsafe_file_operation',
                            'severity': 'medium'
                        })

        # Calculate confidence based on findings
        if vulnerabilities:
            confidence = max(0.1, 1.0 - (len(vulnerabilities) * 0.2))
        elif suspicious_patterns:
            confidence = max(0.5, 1.0 - (len(suspicious_patterns) * 0.1))

        # Add general recommendations
        if vulnerabilities:
            recommendations.append("Review all flagged code sections")
            recommendations.append("Consider using environment variables for secrets")
            recommendations.append("Add input validation and error handling")

        return CodeScan(
            is_safe=len(vulnerabilities) == 0,
            vulnerabilities=vulnerabilities,
            suspicious_patterns=suspicious_patterns,
            recommendations=recommendations,
            confidence=confidence
        )

    def _is_suspicious_usage(self, module: str, lines: List[str]) -> bool:
        """Check if a suspicious module is being used dangerously"""
        dangerous_methods = {
            'os': ['system', 'popen', 'exec', 'spawn'],
            'subprocess': ['call', 'run', 'Popen', 'check_output'],
            'sys': ['executable', 'path'],
            'socket': ['connect', 'bind', 'listen']
        }

        if module in dangerous_methods:
            for line in lines:
                for method in dangerous_methods[module]:
                    if f'{module}.{method}' in line:
                        return True

        return False

    def _is_safe_file_operation(self, line: str) -> bool:
        """Check if a file operation is safe"""
        # Allow writing to current directory or temp directory
        safe_paths = ['./', '../temp/', '/tmp/', 'temp/', 'data/', 'output/']

        for safe_path in safe_paths:
            if safe_path in line:
                return True

        # Block system directories
        blocked_paths = ['/etc/', '/usr/', '/bin/', '/sbin/', '/var/']
        for blocked_path in blocked_paths:
            if blocked_path in line:
                return False

        return False

    async def check_project_structure_safety(self, project_files: Dict[str, str]) -> SafetyCheck:
        """Check if project structure is safe"""
        issues = []
        recommendations = []
        risk_level = SafetyLevel.SAFE

        # Check for suspicious file names
        suspicious_files = [
            'keylogger', 'steal', 'hack', 'crack', 'backdoor',
            'malware', 'virus', 'trojan', 'spy'
        ]

        for file_path in project_files.keys():
            file_name = Path(file_path).name.lower()

            for suspicious in suspicious_files:
                if suspicious in file_name:
                    issues.append(f"Suspicious file name: {file_path}")
                    risk_level = SafetyLevel.DANGER

        # Check file sizes
        for file_path, content in project_files.items():
            if len(content) > self.max_file_size:
                issues.append(f"File too large: {file_path} ({len(content)} bytes)")
                recommendations.append("Consider splitting large files")
                if risk_level.value < 'warning':
                    risk_level = SafetyLevel.WARNING

        # Check for too many files (potential for confusion)
        if len(project_files) > 50:
            issues.append("Too many files - project may be overly complex")
            recommendations.append("Consider modularizing the project")
            if risk_level.value < 'warning':
                risk_level = SafetyLevel.WARNING

        return SafetyCheck(
            level=risk_level,
            message=f"Project structure safety: {risk_level.value}",
            details={
                'file_count': len(project_files),
                'total_size': sum(len(content) for content in project_files.values()),
                'issues_found': len(issues)
            },
            recommendations=recommendations,
            requires_confirmation=risk_level != SafetyLevel.SAFE
        )

    async def execute_in_sandbox(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute code in a sandboxed environment"""
        if not self.sandbox_enabled:
            return {
                'success': False,
                'error': 'Sandbox is disabled',
                'output': '',
                'exit_code': -1
            }

        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Execute in subprocess with timeout
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir()
            )

            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.stderr else None,
                'exit_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Execution timeout',
                'output': '',
                'exit_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'exit_code': -1
            }
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except:
                pass

    async def validate_dependencies(self, dependencies: List[str]) -> SafetyCheck:
        """Validate that dependencies are safe to install"""
        issues = []
        recommendations = []
        risk_level = SafetyLevel.SAFE

        # Check for known malicious packages
        malicious_packages = [
            'malware', 'trojan', 'backdoor', 'keylogger', 'spyware'
        ]

        for dep in dependencies:
            dep_lower = dep.lower()

            for malicious in malicious_packages:
                if malicious in dep_lower:
                    issues.append(f"Potentially malicious dependency: {dep}")
                    risk_level = SafetyLevel.DANGER

            # Check for version pinning
            if '==' not in dep and '>=' not in dep and '<=' not in dep:
                recommendations.append(f"Consider pinning version for {dep}")

            # Check if it's a well-known safe package
            if dep_lower.split('==')[0].split('>=')[0].split('<=')[0] not in self.safe_libraries:
                issues.append(f"Unfamiliar dependency: {dep}")
                recommendations.append(f"Review {dep} for security")
                if risk_level.value < 'warning':
                    risk_level = SafetyLevel.WARNING

        return SafetyCheck(
            level=risk_level,
            message=f"Dependency safety: {risk_level.value}",
            details={
                'dependencies_checked': len(dependencies),
                'safe_libraries': sum(1 for d in dependencies if d.lower().split('==')[0] in self.safe_libraries),
                'issues_found': len(issues)
            },
            recommendations=recommendations,
            requires_confirmation=risk_level != SafetyLevel.SAFE
        )

    def generate_safety_report(self, checks: List[SafetyCheck]) -> Dict[str, Any]:
        """Generate a comprehensive safety report"""
        overall_risk = SafetyLevel.SAFE

        for check in checks:
            if check.level.value == 'danger':
                overall_risk = SafetyLevel.DANGER
                break
            elif check.level.value == 'warning' and overall_risk.value != 'danger':
                overall_risk = SafetyLevel.WARNING

        all_issues = []
        all_recommendations = []

        for check in checks:
            all_issues.extend(check.details.get('issues', []))
            all_recommendations.extend(check.recommendations)

        # Remove duplicates
        all_recommendations = list(set(all_recommendations))

        return {
            'overall_risk': overall_risk.value,
            'checks_performed': len(checks),
            'total_issues': len(all_issues),
            'total_recommendations': len(all_recommendations),
            'summary': self._generate_risk_summary(overall_risk),
            'issues': all_issues,
            'recommendations': all_recommendations,
            'allow_execution': overall_risk != SafetyLevel.DANGER
        }

    def _generate_risk_summary(self, risk_level: SafetyLevel) -> str:
        """Generate a human-readable risk summary"""
        summaries = {
            SafetyLevel.SAFE: "✅ Project appears safe to execute",
            SafetyLevel.WARNING: "⚠️  Project has some risks - review recommended",
            SafetyLevel.DANGER: "🚨 Project has serious safety concerns - execution blocked",
            SafetyLevel.BLOCKED: "🚫 Project contains dangerous elements - cannot proceed"
        }
        return summaries.get(risk_level, "Unknown risk level")

    def get_safety_guidelines(self) -> Dict[str, str]:
        """Get safety guidelines for users"""
        return {
            'general': "Always review generated code before execution",
            'secrets': "Never hardcode API keys or passwords in code",
            'file_ops': "Be careful with file operations, especially writes and deletes",
            'network': "Avoid connecting to internal or sensitive network addresses",
            'dependencies': "Review all third-party dependencies for security",
            'execution': "Test in isolated environments before production use"
        }


# Global instance
_safety_guardrails = None


def get_safety_guardrails(config: Dict[str, Any]) -> SafetyGuardrails:
    """Get or create safety guardrails instance"""
    global _safety_guardrails
    if _safety_guardrails is None:
        _safety_guardrails = SafetyGuardrails(config)
    return _safety_guardrails


async def check_idea_safety(idea_content: str, config: Dict[str, Any]) -> SafetyCheck:
    """Convenience function for idea safety checking"""
    guardrails = get_safety_guardrails(config)
    return await guardrails.check_idea_safety(idea_content)


async def scan_code_safety(code: str, config: Dict[str, Any]) -> CodeScan:
    """Convenience function for code safety scanning"""
    guardrails = get_safety_guardrails(config)
    return await guardrails.scan_code_safety(code)


if __name__ == "__main__":
    # Test the safety guardrails
    import sys

    async def test():
        config = {'sandbox_enabled': True}
        guardrails = SafetyGuardrails(config)

        # Test idea safety
        idea = "Create a Discord bot for my gaming community"
        safety_check = await guardrails.check_idea_safety(idea)
        print(f"Idea safety: {safety_check.level}")

        # Test code scanning
        safe_code = """
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')

@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')
"""

        code_scan = await guardrails.scan_code_safety(safe_code)
        print(f"Code is safe: {code_scan.is_safe}")
        print(f"Confidence: {code_scan.confidence}")

    asyncio.run(test())