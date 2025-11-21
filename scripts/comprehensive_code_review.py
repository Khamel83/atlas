#!/usr/bin/env python3
"""
Comprehensive Code Review for Atlas Personal Knowledge System

Reviews code against mission, values, and production standards:
1. Mission alignment - personal knowledge amplification
2. Values - privacy, security, user control
3. Code quality - maintainability, testability
4. Architecture - scalability, reliability
5. Security - data protection, secure defaults
"""

import os
import sqlite3
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any
import ast
import re

class AtlasCodeReviewer:
    def __init__(self):
        self.project_root = Path.cwd()
        self.issues = []
        self.recommendations = []

    def add_issue(self, category: str, severity: str, file_path: str, line: int, message: str):
        """Add a code review issue"""
        self.issues.append({
            'category': category,
            'severity': severity,
            'file': file_path,
            'line': line,
            'message': message
        })

    def add_recommendation(self, category: str, message: str):
        """Add a code improvement recommendation"""
        self.recommendations.append({
            'category': category,
            'message': message
        })

    def review_mission_alignment(self):
        """Review code alignment with Atlas mission: Personal Knowledge Amplification"""
        print("📋 REVIEWING MISSION ALIGNMENT...")

        # Check if cognitive modules are properly implemented
        ask_modules = list(Path("ask").glob("*.py"))
        if len(ask_modules) < 6:
            self.add_issue("Mission", "HIGH", "ask/", 0,
                          f"Only {len(ask_modules)} cognitive modules found, expected 6")

        # Check for user control features
        config_files = list(Path(".").glob("*.env*"))
        if not config_files:
            self.add_issue("Mission", "MEDIUM", ".", 0,
                          "No environment configuration files found")

        # Check database schema for user data ownership
        if Path("atlas.db").exists():
            conn = sqlite3.connect("atlas.db")
            cursor = conn.cursor()
            tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            required_tables = ["content", "user_preferences", "search_history"]
            missing_tables = [t for t in required_tables if t not in [table[0] for table in tables]]
            if missing_tables:
                self.add_issue("Mission", "MEDIUM", "atlas.db", 0,
                              f"Missing user-centric tables: {missing_tables}")
            conn.close()

    def review_privacy_security(self):
        """Review privacy and security practices"""
        print("🔒 REVIEWING PRIVACY & SECURITY...")

        # Check for hardcoded secrets
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for potential secrets
                secret_patterns = [
                    r"(api_key|API_KEY|secret|SECRET|password|PASSWORD)\s*=\s*['\"][^'\"]{10,}['\"]",
                    r"(openai|OPENAI)\s*=\s*['\"][^'\"]+['\"]",
                    r"(token|TOKEN)\s*=\s*['\"][^'\"]{20,}['\"]"
                ]

                for i, line in enumerate(content.split('\n'), 1):
                    for pattern in secret_patterns:
                        if re.search(pattern, line) and "example" not in line.lower():
                            self.add_issue("Security", "HIGH", str(py_file), i,
                                          f"Potential hardcoded secret: {line.strip()[:50]}...")
            except Exception:
                continue

        # Check for SQL injection vulnerabilities
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(r'cursor\.execute\s*\(\s*f["\'].*\{.*\}.*["\']', content):
                        self.add_issue("Security", "HIGH", str(py_file), 0,
                                      "Potential SQL injection via f-string in cursor.execute")
            except Exception:
                continue

    def review_code_quality(self):
        """Review code quality and maintainability"""
        print("⚙️ REVIEWING CODE QUALITY...")

        # Check for proper error handling
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for bare except clauses
                if "except:" in content:
                    self.add_issue("Quality", "MEDIUM", str(py_file), 0,
                                  "Bare except clause found - should specify exception types")

                # Check for print debugging
                debug_patterns = ["print(", "pprint(", "console.log"]
                for pattern in debug_patterns:
                    if pattern in content and "# DEBUG" not in content:
                        lines_with_print = [i+1 for i, line in enumerate(content.split('\n'))
                                          if pattern in line and not line.strip().startswith('#')]
                        if lines_with_print:
                            self.add_issue("Quality", "LOW", str(py_file), lines_with_print[0],
                                          f"Debug print statement found - consider using logging")

                # Check for TODO comments
                todo_count = content.count("TODO")
                if todo_count > 5:
                    self.add_issue("Quality", "LOW", str(py_file), 0,
                                  f"High number of TODO comments ({todo_count}) - consider tracking in issues")

            except Exception:
                continue

    def review_architecture(self):
        """Review system architecture and design patterns"""
        print("🏗️ REVIEWING ARCHITECTURE...")

        # Check for proper separation of concerns
        core_modules = ["ask", "ingest", "process", "web", "api"]
        missing_modules = [module for module in core_modules if not Path(module).exists()]
        if missing_modules:
            self.add_issue("Architecture", "HIGH", ".", 0,
                          f"Missing core modules: {missing_modules}")

        # Check for configuration management
        if not Path(".env.template").exists():
            self.add_issue("Architecture", "MEDIUM", ".", 0,
                          "Missing .env.template for configuration management")

        # Check for proper logging configuration
        logging_files = list(self.project_root.rglob("*log*"))
        if not logging_files:
            self.add_recommendation("Architecture",
                                  "Consider implementing centralized logging configuration")

    def review_dependencies(self):
        """Review dependency management and security"""
        print("📦 REVIEWING DEPENDENCIES...")

        if Path("requirements.txt").exists():
            with open("requirements.txt", 'r') as f:
                deps = f.read()

            # Check for pinned versions
            unpinned = [line for line in deps.split('\n')
                       if line.strip() and '==' not in line and not line.startswith('#')]
            if unpinned:
                self.add_issue("Dependencies", "MEDIUM", "requirements.txt", 0,
                              f"Unpinned dependencies found: {unpinned[:3]}")

            # Check for known vulnerable packages (basic check)
            vulnerable_patterns = ["flask==0", "django==1", "requests==2.0"]
            for pattern in vulnerable_patterns:
                if pattern in deps:
                    self.add_issue("Dependencies", "HIGH", "requirements.txt", 0,
                                  f"Potentially vulnerable dependency: {pattern}")

    def review_testing(self):
        """Review test coverage and quality"""
        print("🧪 REVIEWING TESTING...")

        test_dirs = ["tests", "test"]
        test_files = []
        for test_dir in test_dirs:
            if Path(test_dir).exists():
                test_files.extend(list(Path(test_dir).rglob("test_*.py")))
                test_files.extend(list(Path(test_dir).rglob("*_test.py")))

        py_files = list(self.project_root.rglob("*.py"))
        py_files = [f for f in py_files if "venv" not in str(f) and "__pycache__" not in str(f)]

        test_coverage = len(test_files) / max(len(py_files) // 10, 1) * 100  # Rough estimate

        if test_coverage < 20:
            self.add_issue("Testing", "MEDIUM", ".", 0,
                          f"Low test coverage estimated at {test_coverage:.1f}%")

    def review_documentation(self):
        """Review documentation completeness"""
        print("📚 REVIEWING DOCUMENTATION...")

        required_docs = ["README.md", "INSTALLATION.md", "API.md"]
        missing_docs = [doc for doc in required_docs if not Path(doc).exists()
                       and not Path(f"docs/{doc}").exists()]

        if missing_docs:
            self.add_recommendation("Documentation",
                                  f"Consider adding missing documentation: {missing_docs}")

        # Check README quality
        if Path("README.md").exists():
            with open("README.md", 'r') as f:
                readme = f.read()
            if len(readme) < 1000:
                self.add_issue("Documentation", "LOW", "README.md", 0,
                              "README appears minimal - consider expanding")

    def run_static_analysis(self):
        """Run additional static analysis tools if available"""
        print("🔍 RUNNING STATIC ANALYSIS...")

        try:
            # Check if pylint is available
            result = subprocess.run(['pylint', '--version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Run pylint on a sample of files
                sample_files = list(self.project_root.glob("*.py"))[:5]
                for py_file in sample_files:
                    try:
                        result = subprocess.run(['pylint', str(py_file), '--output-format=json'],
                                              capture_output=True, text=True, timeout=10)
                        if result.stdout:
                            issues = json.loads(result.stdout)
                            high_severity = [i for i in issues if i.get('type') == 'error']
                            if high_severity:
                                self.add_issue("Static Analysis", "MEDIUM", str(py_file), 0,
                                              f"Pylint found {len(high_severity)} errors")
                    except Exception:
                        continue
        except Exception:
            self.add_recommendation("Static Analysis",
                                  "Consider adding pylint or similar static analysis tools")

    def generate_report(self):
        """Generate comprehensive review report"""
        print("\n" + "="*80)
        print("🎯 ATLAS COMPREHENSIVE CODE REVIEW REPORT")
        print("="*80)

        # Summary
        total_issues = len(self.issues)
        high_severity = len([i for i in self.issues if i['severity'] == 'HIGH'])
        medium_severity = len([i for i in self.issues if i['severity'] == 'MEDIUM'])
        low_severity = len([i for i in self.issues if i['severity'] == 'LOW'])

        print(f"\n📊 SUMMARY:")
        print(f"   Total Issues: {total_issues}")
        print(f"   🔴 High Severity: {high_severity}")
        print(f"   🟡 Medium Severity: {medium_severity}")
        print(f"   🟢 Low Severity: {low_severity}")
        print(f"   💡 Recommendations: {len(self.recommendations)}")

        # Issues by category
        categories = {}
        for issue in self.issues:
            cat = issue['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(issue)

        print(f"\n🔍 ISSUES BY CATEGORY:")
        for category, issues in categories.items():
            print(f"\n   {category.upper()} ({len(issues)} issues):")
            for issue in issues:
                severity_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[issue['severity']]
                print(f"     {severity_icon} {issue['file']}:{issue['line']} - {issue['message']}")

        # Recommendations
        if self.recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in self.recommendations:
                print(f"   • {rec['category']}: {rec['message']}")

        # Overall assessment
        print(f"\n🎯 OVERALL ASSESSMENT:")
        if high_severity == 0 and medium_severity <= 3:
            print("   ✅ GOOD - System appears well-structured with minimal critical issues")
        elif high_severity <= 2 and medium_severity <= 10:
            print("   ⚠️  NEEDS ATTENTION - Some issues require attention before production")
        else:
            print("   🔴 CRITICAL - Significant issues that should be addressed immediately")

        # Mission alignment assessment
        mission_issues = [i for i in self.issues if i['category'] == 'Mission']
        security_issues = [i for i in self.issues if i['category'] == 'Security']

        print(f"\n🎯 MISSION & VALUES ALIGNMENT:")
        print(f"   Personal Knowledge Amplification: {'✅ Aligned' if len(mission_issues) == 0 else '⚠️ Needs Review'}")
        print(f"   Privacy & Security: {'✅ Secure' if len(security_issues) == 0 else '🔴 Security Concerns'}")
        print(f"   User Control: {'✅ User-Centric' if Path('.env.template').exists() else '⚠️ Limited Configuration'}")

        return {
            'total_issues': total_issues,
            'high_severity': high_severity,
            'categories': categories,
            'recommendations': self.recommendations
        }

    def run_comprehensive_review(self):
        """Run all review checks"""
        print("🚀 Starting Atlas Comprehensive Code Review...")
        print("="*60)

        self.review_mission_alignment()
        self.review_privacy_security()
        self.review_code_quality()
        self.review_architecture()
        self.review_dependencies()
        self.review_testing()
        self.review_documentation()
        self.run_static_analysis()

        return self.generate_report()

if __name__ == "__main__":
    reviewer = AtlasCodeReviewer()
    report = reviewer.run_comprehensive_review()