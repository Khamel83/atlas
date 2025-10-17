#!/usr/bin/env python3
"""
Auto Documentation System

Provides automatic documentation generation and checking capabilities.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class DocumentationCheck:
    """Result of a documentation check"""
    is_complete: bool
    missing_sections: List[str]
    suggestions: List[str]
    score: float

class AutoDocumentationSystem:
    """Automatic documentation generation and checking"""

    def __init__(self):
        self.logger = logging.getLogger("auto_documentation")

    async def check_documentation_completeness(self, file_paths: List[str]) -> Dict[str, DocumentationCheck]:
        """Check documentation completeness for given files"""
        results = {}

        for file_path in file_paths:
            results[file_path] = await self._check_single_file(file_path)

        return results

    async def _check_single_file(self, file_path: str) -> DocumentationCheck:
        """Check documentation for a single file"""
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return DocumentationCheck(
                is_complete=False,
                missing_sections=["File not found"],
                suggestions=["Check file path"],
                score=0.0
            )

        # Different checks based on file type
        if file_path_obj.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c']:
            return await self._check_code_documentation(file_path)
        elif file_path_obj.suffix in ['.md', '.rst', '.txt']:
            return await self._check_document_file(file_path)
        else:
            return DocumentationCheck(
                is_complete=True,  # Assume non-code/docs files are fine
                missing_sections=[],
                suggestions=[],
                score=1.0
            )

    async def _check_code_documentation(self, file_path: str) -> DocumentationCheck:
        """Check if code file has adequate documentation"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            missing_sections = []
            suggestions = []

            # Check for module/class level docstring
            if not self._has_module_docstring(content):
                missing_sections.append("Module docstring")
                suggestions.append("Add module-level docstring describing purpose and usage")

            # Check for function docstrings
            if not self._has_function_docstrings(content):
                missing_sections.append("Function docstrings")
                suggestions.append("Add docstrings to functions and methods")

            # Check for type hints (if applicable)
            if not self._has_type_hints(content):
                missing_sections.append("Type hints")
                suggestions.append("Add type hints for better code clarity")

            # Calculate completeness score
            score = 1.0 - (len(missing_sections) * 0.2)  # Each missing section reduces score by 20%
            score = max(0.0, score)

            return DocumentationCheck(
                is_complete=len(missing_sections) == 0,
                missing_sections=missing_sections,
                suggestions=suggestions,
                score=score
            )

        except Exception as e:
            self.logger.error(f"Error checking documentation for {file_path}: {e}")
            return DocumentationCheck(
                is_complete=False,
                missing_sections=["Error reading file"],
                suggestions=[f"Check file access: {e}"],
                score=0.0
            )

    async def _check_document_file(self, file_path: str) -> DocumentationCheck:
        """Check if documentation file has required sections"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            missing_sections = []
            suggestions = []

            # Check for common documentation sections
            required_sections = [
                '# Description', '## Description',
                '# Installation', '## Installation',
                '# Usage', '## Usage',
                '# Examples', '## Examples',
                'README', 'TUTORIAL'
            ]

            content_lower = content.lower()
            found_sections = []

            for section in required_sections:
                if section.lower() in content_lower:
                    found_sections.append(section)

            # If it's a README, check for more sections
            if 'readme' in file_path.lower():
                expected_sections = ['description', 'installation', 'usage']
                for expected in expected_sections:
                    if not any(expected in section.lower() for section in found_sections):
                        missing_sections.append(f"{expected.title()} section")
                        suggestions.append(f"Add {expected} section to README")

            # Calculate completeness score
            if found_sections:
                score = len(found_sections) / max(len(required_sections), 1)
            else:
                score = 0.5  # Give some credit for having content

            return DocumentationCheck(
                is_complete=len(missing_sections) == 0,
                missing_sections=missing_sections,
                suggestions=suggestions,
                score=score
            )

        except Exception as e:
            self.logger.error(f"Error checking documentation file {file_path}: {e}")
            return DocumentationCheck(
                is_complete=False,
                missing_sections=["Error reading file"],
                suggestions=[f"Check file access: {e}"],
                score=0.0
            )

    def _has_module_docstring(self, content: str) -> bool:
        """Check if file has module-level docstring"""
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('"""') or line.startswith("'''"):
                return True
        return False

    def _has_function_docstrings(self, content: str) -> bool:
        """Check if functions have docstrings"""
        # Simple check - look for def followed by docstring
        import re
        functions = re.findall(r'def\s+\w+\([^)]*\):', content)
        if not functions:
            return True  # No functions to document

        # Look for docstrings after function definitions
        docstring_pattern = r'def\s+\w+\([^)]*\):\s*("""|\'\'\')'
        docstrings = re.findall(docstring_pattern, content, re.DOTALL)

        # If we have functions, at least some should have docstrings
        return len(docstrings) > 0 or len(functions) == 0

    def _has_type_hints(self, content: str) -> bool:
        """Check if code uses type hints"""
        # Simple check for type annotations
        import re
        type_patterns = [
            r':\s*[A-Za-z_][A-Za-z0-9_]*(?:\[[A-Za-z0-9_,\s]*\])?',
            r'->\s*[A-Za-z_][A-Za-z0-9_]*(?:\[[A-Za-z0-9_,\s]*\])?'
        ]

        for pattern in type_patterns:
            if re.search(pattern, content):
                return True
        return False

    async def generate_documentation_summary(self, results: Dict[str, DocumentationCheck]) -> str:
        """Generate a summary of documentation check results"""
        total_files = len(results)
        complete_files = sum(1 for check in results.values() if check.is_complete)
        average_score = sum(check.score for check in results.values()) / total_files if total_files > 0 else 0

        summary = f"""
📊 Documentation Analysis Summary:
   • Total files checked: {total_files}
   • Complete documentation: {complete_files}/{total_files}
   • Average completeness score: {average_score:.1%}

"""

        # Group by score ranges
        excellent_files = [path for path, check in results.items() if check.score >= 0.9]
        good_files = [path for path, check in results.items() if 0.7 <= check.score < 0.9]
        needs_work = [path for path, check in results.items() if check.score < 0.7]

        if excellent_files:
            summary += f"✅ Excellent documentation: {len(excellent_files)} files\n"

        if good_files:
            summary += f"⚠️  Good but could improve: {len(good_files)} files\n"

        if needs_work:
            summary += f"❌ Needs attention: {len(needs_work)} files\n"

        # Top suggestions
        all_suggestions = []
        for check in results.values():
            all_suggestions.extend(check.suggestions)

        if all_suggestions:
            suggestion_counts = {}
            for suggestion in all_suggestions:
                suggestion_counts[suggestion] = suggestion_counts.get(suggestion, 0) + 1

            top_suggestions = sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            summary += "\n🔧 Top recommendations:\n"
            for suggestion, count in top_suggestions:
                summary += f"   • {suggestion} ({count} files)\n"

        return summary

def get_auto_documentation_system() -> AutoDocumentationSystem:
    """Factory function to create auto documentation system instance"""
    return AutoDocumentationSystem()