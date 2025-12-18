#!/usr/bin/env python3
"""
Hardcoded Path Detection and Replacement Tool

This script systematically scans the codebase to identify hardcoded paths that should
be made configurable for better reusability. It categorizes findings and suggests
environment variable replacements.

Core principle: Make Atlas portable and configurable for different environments.
"""

import os
import re
import json
import ast
from pathlib import Path
from typing import Dict, List, Set, Any
from datetime import datetime

class HardcodedPathDetector:
    """Detects and categorizes hardcoded paths in Python code."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.findings: Dict[str, List[Dict[str, Any]]] = {
            "absolute_paths": [],
            "home_references": [],
            "specific_directories": [],
            "hardcoded_files": [],
            "user_specific": [],
            "system_specific": []
        }

        # Patterns to detect various types of hardcoded paths
        self.patterns = {
            "absolute_unix": re.compile(r'["\'](/[^"\']*)["\']'),
            "home_dir": re.compile(r'["\']?(~/[^"\']*|/home/[^/\'"]*)["\']?'),
            "ubuntu_specific": re.compile(r'["\']?/home/ubuntu[^"\']*["\']?'),
            "dev_paths": re.compile(r'["\']?/[^"\']*dev/atlas[^"\']*["\']?'),
            "temp_paths": re.compile(r'["\']?/tmp/[^"\']*["\']?'),
            "specific_files": re.compile(r'["\'][^"\']*\.(txt|json|csv|html|md)["\']'),
        }

        # Directories and files to skip
        self.skip_patterns = {
            ".git", ".venv", "__pycache__", "node_modules", ".pytest_cache",
            "htmlcov", "atlas_venv", "venv", ".coverage", "coverage.xml"
        }

    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped from analysis."""
        # Skip non-Python files
        if file_path.suffix not in {'.py'}:
            return True

        # Skip files in excluded directories
        for part in file_path.parts:
            if part in self.skip_patterns:
                return True

        # Skip test files for now (they often have legitimate hardcoded test paths)
        if 'test' in file_path.name.lower():
            return True

        return False

    def analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a single Python file for hardcoded paths."""
        if self.should_skip_file(file_path):
            return []

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return self.analyze_content(content, str(file_path))
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return []

    def analyze_content(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Analyze file content for hardcoded paths."""
        issues = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            # Check each pattern
            for pattern_name, pattern in self.patterns.items():
                matches = pattern.findall(line)
                for match in matches:
                    # Filter out obvious false positives
                    if self.is_false_positive(match, line):
                        continue

                    issue = {
                        "file": file_path,
                        "line": line_num,
                        "pattern": pattern_name,
                        "match": match,
                        "context": line.strip(),
                        "severity": self.assess_severity(match, line),
                        "suggested_fix": self.suggest_fix(match, pattern_name)
                    }

                    issues.append(issue)

        return issues

    def is_false_positive(self, match: str, line: str) -> bool:
        """Filter out obvious false positives."""
        false_positive_indicators = [
            # URLs and protocols
            "http://", "https://", "ftp://",
            # Format strings
            "%s", "{}", "f\"", "f'",
            # Common system paths that are standard
            "/usr/", "/etc/", "/var/log",
            # Regex patterns
            "\\", ".*", ".+", "[",
            # Already using environment variables
            "os.environ", "config.get", ".env",
            # Path operations that build paths dynamically
            "os.path.join", "Path(", ".joinpath",
        ]

        line_lower = line.lower()
        match_lower = match.lower()

        for indicator in false_positive_indicators:
            if indicator in line_lower or indicator in match_lower:
                return True

        # Skip very short matches (likely not real paths)
        if len(match.strip('\'"')) < 4:
            return True

        return False

    def assess_severity(self, match: str, line: str) -> str:
        """Assess the severity of a hardcoded path."""
        # High severity: user-specific paths, absolute dev paths
        high_severity_patterns = [
            "/home/ubuntu", "/home/", "~/", "/dev/atlas"
        ]

        # Medium severity: temp paths, specific files
        medium_severity_patterns = [
            "/tmp/", ".txt", ".json", ".csv"
        ]

        match_lower = match.lower()

        for pattern in high_severity_patterns:
            if pattern in match_lower:
                return "HIGH"

        for pattern in medium_severity_patterns:
            if pattern in match_lower:
                return "MEDIUM"

        return "LOW"

    def suggest_fix(self, match: str, pattern_name: str) -> str:
        """Suggest environment variable replacement."""
        suggestions = {
            "ubuntu_specific": "Use config.get('data_directory') or os.environ.get('ATLAS_DATA_DIR', 'data')",
            "dev_paths": "Use Path(__file__).parent.parent for project root",
            "home_dir": "Use Path.home() or os.environ.get('HOME')",
            "temp_paths": "Use tempfile.gettempdir() or config.get('temp_directory')",
            "specific_files": "Make filename configurable via config or environment variable"
        }

        # Specific suggestions based on content
        if "/home/ubuntu/dev/atlas" in match:
            return "Replace with project root: Path(__file__).resolve().parent.parent"
        elif "/home/ubuntu" in match:
            return "Use config.get('data_directory') or Path.home() / 'atlas_data'"
        elif match.endswith('.txt') or match.endswith('.json'):
            return f"Make configurable: config.get('filename', '{Path(match).name}')"

        return suggestions.get(pattern_name, "Make path configurable via environment variable")

    def scan_codebase(self) -> None:
        """Scan entire codebase for hardcoded paths."""
        print("🔍 Scanning codebase for hardcoded paths...")

        # Get all Python files but filter more aggressively
        all_files = list(self.root_dir.rglob("*.py"))
        python_files = []

        for file_path in all_files:
            # Skip files in excluded directories more thoroughly
            path_str = str(file_path)
            skip = False

            for pattern in self.skip_patterns:
                if pattern in path_str:
                    skip = True
                    break

            # Additional filtering for virtual environments
            if any(venv_indicator in path_str for venv_indicator in
                   ['site-packages', 'lib/python', 'atlas_venv', 'bin/python']):
                skip = True

            if not skip:
                python_files.append(file_path)

        total_files = len(python_files)
        processed = 0

        print(f"Found {total_files} Python files to analyze (excluding virtual environments)")

        for file_path in python_files:
            if processed % 10 == 0 and processed > 0:
                print(f"  Progress: {processed}/{total_files} files")

            issues = self.analyze_file(file_path)

            # Categorize issues
            for issue in issues:
                category = self.categorize_issue(issue)
                self.findings[category].append(issue)

            processed += 1

        print(f"✅ Completed scanning {processed} Python files")

    def categorize_issue(self, issue: Dict[str, Any]) -> str:
        """Categorize an issue into the appropriate bucket."""
        match = issue["match"].lower()
        pattern = issue["pattern"]

        if "ubuntu" in match or "/home/" in match:
            return "user_specific"
        elif pattern == "absolute_unix" and match.startswith("/"):
            return "absolute_paths"
        elif "~/" in match or "/home/" in match:
            return "home_references"
        elif match.endswith(('.txt', '.json', '.csv', '.html', '.md')):
            return "hardcoded_files"
        elif "/tmp/" in match or "/var/" in match:
            return "system_specific"
        else:
            return "specific_directories"

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive report of findings."""
        total_issues = sum(len(issues) for issues in self.findings.values())

        # Priority analysis
        high_priority = []
        medium_priority = []
        low_priority = []

        for category, issues in self.findings.items():
            for issue in issues:
                if issue["severity"] == "HIGH":
                    high_priority.append(issue)
                elif issue["severity"] == "MEDIUM":
                    medium_priority.append(issue)
                else:
                    low_priority.append(issue)

        # File-level summary
        files_with_issues = set()
        for issues in self.findings.values():
            for issue in issues:
                files_with_issues.add(issue["file"])

        report = {
            "scan_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_issues": total_issues,
                "affected_files": len(files_with_issues),
                "high_priority": len(high_priority),
                "medium_priority": len(medium_priority),
                "low_priority": len(low_priority)
            },
            "by_category": {
                category: len(issues) for category, issues in self.findings.items()
            },
            "detailed_findings": self.findings,
            "priority_issues": {
                "high": high_priority[:20],  # Top 20 high priority
                "medium": medium_priority[:20],
                "low": low_priority[:10]
            }
        }

        return report

    def print_summary(self, report: Dict[str, Any]) -> None:
        """Print human-readable summary."""
        summary = report["summary"]

        print("\n" + "="*60)
        print("🎯 HARDCODED PATH ANALYSIS SUMMARY")
        print("="*60)

        print(f"📊 Total Issues Found: {summary['total_issues']}")
        print(f"📁 Files Affected: {summary['affected_files']}")
        print(f"🔴 High Priority: {summary['high_priority']}")
        print(f"🟡 Medium Priority: {summary['medium_priority']}")
        print(f"🟢 Low Priority: {summary['low_priority']}")

        print("\n📋 Issues by Category:")
        for category, count in report["by_category"].items():
            if count > 0:
                category_name = category.replace('_', ' ').title()
                print(f"  • {category_name}: {count}")

        print("\n🚨 Top High Priority Issues:")
        for i, issue in enumerate(report["priority_issues"]["high"][:5], 1):
            file_short = Path(issue["file"]).name
            print(f"  {i}. {file_short}:{issue['line']} - {issue['match']}")
            print(f"     💡 {issue['suggested_fix']}")

        if summary["high_priority"] == 0:
            print("  ✅ No high priority hardcoded paths found!")


def main():
    """Main function to run hardcoded path detection."""
    detector = HardcodedPathDetector()

    # Scan the codebase
    detector.scan_codebase()

    # Generate report
    report = detector.generate_report()

    # Save detailed report
    output_file = f"logs/hardcoded_paths_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("logs", exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    detector.print_summary(report)

    print(f"\n📄 Detailed report saved to: {output_file}")

    # Return for programmatic use
    return report


if __name__ == "__main__":
    main()