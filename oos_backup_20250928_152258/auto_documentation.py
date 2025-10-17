#!/usr/bin/env python3
"""
Auto-Documentation and Consistency System

Implements automated documentation generation, GitHub commit hooks,
and consistency enforcement to "save you from yourself"
"""

import json
import asyncio
import subprocess
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import logging
import hashlib
import yaml


@dataclass
class DocumentationRule:
    """Rule for auto-generating documentation"""
    rule_id: str
    trigger_patterns: List[str]  # File patterns that trigger this rule
    documentation_type: str  # 'function', 'class', 'module', 'readme', 'changelog'
    template: str
    required_sections: List[str]
    auto_generate: bool = True
    enforce: bool = True


@dataclass
class ConsistencyCheck:
    """Consistency check configuration"""
    check_id: str
    check_type: str  # 'naming', 'structure', 'style', 'documentation'
    pattern: str
    expected: str
    severity: str  # 'error', 'warning', 'info'
    auto_fix: bool = False


@dataclass
class AutoDocResult:
    """Result of auto-documentation operation"""
    operation: str
    files_processed: List[str]
    documentation_generated: List[str]
    consistency_issues: List[Dict[str, Any]]
    commit_suggested: bool
    commit_message: Optional[str] = None


class GitIntegration:
    """Git integration for automated commits and hooks"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.logger = logging.getLogger(__name__)

    async def setup_hooks(self):
        """Setup Git hooks for auto-documentation"""
        hooks_dir = self.repo_path / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        # Pre-commit hook
        pre_commit_hook = hooks_dir / "pre-commit"
        pre_commit_content = """#!/bin/bash
# OOS Auto-documentation pre-commit hook

echo "🔍 Running OOS consistency checks..."

# Check if auto-documentation is needed
python3 -m oos.src.auto_documentation --check-consistency --pre-commit

if [ $? -ne 0 ]; then
    echo "❌ Consistency checks failed. Run: python3 -m oos.src.auto_documentation --fix"
    exit 1
fi

echo "✅ Consistency checks passed"
"""

        pre_commit_hook.write_text(pre_commit_content)
        pre_commit_hook.chmod(0o755)

        # Post-commit hook
        post_commit_hook = hooks_dir / "post-commit"
        post_commit_content = """#!/bin/bash
# OOS Auto-documentation post-commit hook

echo "📝 Checking for documentation updates..."

# Generate documentation if needed
python3 -m oos.src.auto_documentation --post-commit

echo "✅ Documentation check complete"
"""

        post_commit_hook.write_text(post_commit_content)
        post_commit_hook.chmod(0o755)

        self.logger.info("Git hooks installed successfully")

    async def suggest_commit_message(self, changed_files: List[str]) -> str:
        """Generate intelligent commit message based on changes"""

        # Analyze file changes
        change_types = self._analyze_changes(changed_files)

        # Generate message based on patterns
        if change_types['new_features']:
            primary = f"feat: add {', '.join(change_types['new_features'])}"
        elif change_types['fixes']:
            primary = f"fix: resolve {', '.join(change_types['fixes'])}"
        elif change_types['docs']:
            primary = f"docs: update {', '.join(change_types['docs'])}"
        elif change_types['refactoring']:
            primary = f"refactor: improve {', '.join(change_types['refactoring'])}"
        else:
            primary = "chore: update files"

        # Add scope if detected
        scope = self._detect_scope(changed_files)
        if scope:
            primary = primary.replace(":", f"({scope}):", 1)

        # Add details
        details = []
        if len(changed_files) > 1:
            details.append(f"Modified {len(changed_files)} files")

        if change_types['breaking']:
            details.append("BREAKING CHANGE: " + change_types['breaking'])

        # Format final message
        message = primary
        if details:
            message += "\n\n" + "\n".join(f"- {detail}" for detail in details)

        message += "\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

        return message

    def _analyze_changes(self, changed_files: List[str]) -> Dict[str, List[str]]:
        """Analyze file changes to categorize commit type"""
        change_types = {
            'new_features': [],
            'fixes': [],
            'docs': [],
            'refactoring': [],
            'breaking': []
        }

        for file_path in changed_files:
            file_name = Path(file_path).name

            # Detect change type based on file patterns and content
            if file_name.endswith(('.md', '.rst', '.txt')):
                change_types['docs'].append(file_name)
            elif 'test' in file_name.lower():
                change_types['fixes'].append(f"tests for {file_name}")
            elif file_name.endswith(('.py', '.js', '.ts', '.go', '.rs')):
                # Would need git diff analysis for more accurate detection
                change_types['refactoring'].append(file_name)

        return change_types

    def _detect_scope(self, changed_files: List[str]) -> Optional[str]:
        """Detect scope of changes"""
        scopes = set()

        for file_path in changed_files:
            parts = Path(file_path).parts

            if len(parts) > 1:
                # Use first directory as scope
                if parts[0] in ['src', 'lib', 'app']:
                    if len(parts) > 2:
                        scopes.add(parts[1])
                else:
                    scopes.add(parts[0])

        if len(scopes) == 1:
            return list(scopes)[0]
        elif 'api' in scopes:
            return 'api'
        elif 'core' in scopes:
            return 'core'

        return None

    async def create_smart_commit(self, files: List[str], user_message: Optional[str] = None) -> bool:
        """Create commit with smart message generation"""

        if user_message:
            commit_message = user_message
        else:
            commit_message = await self.suggest_commit_message(files)

        try:
            # Add files
            for file_path in files:
                subprocess.run(['git', 'add', file_path], cwd=self.repo_path, check=True)

            # Commit with message
            subprocess.run(
                ['git', 'commit', '-m', commit_message],
                cwd=self.repo_path,
                check=True
            )

            self.logger.info(f"Committed {len(files)} files with smart message")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git commit failed: {e}")
            return False


class DocumentationGenerator:
    """Generates documentation automatically"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rules = self._load_documentation_rules()

    def _load_documentation_rules(self) -> List[DocumentationRule]:
        """Load documentation generation rules"""
        return [
            DocumentationRule(
                rule_id="python_function",
                trigger_patterns=["*.py"],
                documentation_type="function",
                template='''"""
{summary}

Args:
{args}

Returns:
{returns}

Raises:
{raises}
"""''',
                required_sections=["summary", "args", "returns"],
                auto_generate=True,
                enforce=True
            ),
            DocumentationRule(
                rule_id="python_class",
                trigger_patterns=["*.py"],
                documentation_type="class",
                template='''"""
{summary}

{description}

Attributes:
{attributes}

Methods:
{methods}
"""''',
                required_sections=["summary", "description"],
                auto_generate=True,
                enforce=True
            ),
            DocumentationRule(
                rule_id="module_readme",
                trigger_patterns=["src/*.py", "lib/*.py"],
                documentation_type="readme",
                template='''# {module_name}

{description}

## Usage

```python
{usage_example}
```

## API Reference

{api_reference}

## Examples

{examples}
''',
                required_sections=["description", "usage_example"],
                auto_generate=False,  # Only suggest, don't auto-generate
                enforce=False
            )
        ]

    async def generate_function_docs(self, file_path: str) -> List[str]:
        """Generate documentation for functions in a Python file"""
        generated_docs = []

        if not file_path.endswith('.py'):
            return generated_docs

        try:
            content = Path(file_path).read_text()

            # Find functions without docstrings
            function_pattern = r'def\s+(\w+)\s*\([^)]*\):'
            functions = re.findall(function_pattern, content)

            for func_name in functions:
                if not self._has_docstring(content, func_name):
                    docstring = await self._generate_function_docstring(content, func_name)
                    if docstring:
                        generated_docs.append(f"Generated docstring for {func_name} in {file_path}")
                        # Would insert docstring into file here

        except Exception as e:
            self.logger.error(f"Failed to generate docs for {file_path}: {e}")

        return generated_docs

    def _has_docstring(self, content: str, function_name: str) -> bool:
        """Check if function already has a docstring"""
        func_pattern = rf'def\s+{function_name}\s*\([^)]*\):\s*"""'
        return bool(re.search(func_pattern, content, re.DOTALL))

    async def _generate_function_docstring(self, content: str, function_name: str) -> Optional[str]:
        """Generate docstring for a function using AI assistance"""

        # Extract function signature and body
        func_pattern = rf'def\s+({function_name}\s*\([^)]*\):.*?)(?=\ndef|\nclass|\n\n\w|\Z)'
        match = re.search(func_pattern, content, re.DOTALL)

        if not match:
            return None

        function_code = match.group(1)

        # Analyze function to generate docstring
        # This would integrate with AI service for better generation
        return self._simple_docstring_generation(function_code)

    def _simple_docstring_generation(self, function_code: str) -> str:
        """Simple docstring generation based on code analysis"""
        lines = function_code.split('\n')
        signature_line = lines[0]

        # Extract parameters
        param_match = re.search(r'\((.*?)\)', signature_line)
        if param_match:
            params = [p.strip().split(':')[0].split('=')[0].strip()
                     for p in param_match.group(1).split(',')
                     if p.strip() and p.strip() != 'self']
        else:
            params = []

        # Generate basic docstring
        docstring = '    """\n    [Generated] Function description needed.\n\n'

        if params:
            docstring += '    Args:\n'
            for param in params:
                docstring += f'        {param}: Description needed\n'
            docstring += '\n'

        docstring += '    Returns:\n        Description needed\n    """'

        return docstring

    async def check_documentation_completeness(self, file_path: str) -> List[Dict[str, Any]]:
        """Check if documentation is complete for a file"""
        issues = []

        if not file_path.endswith('.py'):
            return issues

        try:
            content = Path(file_path).read_text()

            # Check for module docstring
            if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
                issues.append({
                    "type": "missing_module_docstring",
                    "file": file_path,
                    "line": 1,
                    "message": "Module is missing a docstring",
                    "severity": "warning"
                })

            # Check for function docstrings
            function_pattern = r'def\s+(\w+)\s*\([^)]*\):'
            functions = re.finditer(function_pattern, content)

            for match in functions:
                func_name = match.group(1)
                if not func_name.startswith('_') and not self._has_docstring(content, func_name):
                    issues.append({
                        "type": "missing_function_docstring",
                        "file": file_path,
                        "line": content[:match.start()].count('\n') + 1,
                        "message": f"Function '{func_name}' is missing a docstring",
                        "severity": "warning"
                    })

        except Exception as e:
            self.logger.error(f"Failed to check documentation for {file_path}: {e}")

        return issues


class ConsistencyEnforcer:
    """Enforces consistency across the codebase"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.checks = self._load_consistency_checks()

    def _load_consistency_checks(self) -> List[ConsistencyCheck]:
        """Load consistency check rules"""
        return [
            ConsistencyCheck(
                check_id="python_naming",
                check_type="naming",
                pattern=r"def\s+([A-Z][a-zA-Z]*)\s*\(",
                expected="Function names should use snake_case",
                severity="error",
                auto_fix=False
            ),
            ConsistencyCheck(
                check_id="python_imports",
                check_type="structure",
                pattern=r"^from\s+\.\s+import",
                expected="Use absolute imports instead of relative imports",
                severity="warning",
                auto_fix=True
            ),
            ConsistencyCheck(
                check_id="file_headers",
                check_type="structure",
                pattern=r"^#!/usr/bin/env python3",
                expected="Python files should start with shebang",
                severity="info",
                auto_fix=True
            )
        ]

    async def check_consistency(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Check consistency across files"""
        all_issues = []

        for file_path in file_paths:
            file_issues = await self._check_file_consistency(file_path)
            all_issues.extend(file_issues)

        return all_issues

    async def _check_file_consistency(self, file_path: str) -> List[Dict[str, Any]]:
        """Check consistency for a single file"""
        issues = []

        if not Path(file_path).exists():
            return issues

        try:
            content = Path(file_path).read_text()

            for check in self.checks:
                if self._file_matches_check(file_path, check):
                    file_issues = self._apply_check(content, file_path, check)
                    issues.extend(file_issues)

        except Exception as e:
            self.logger.error(f"Failed to check consistency for {file_path}: {e}")

        return issues

    def _file_matches_check(self, file_path: str, check: ConsistencyCheck) -> bool:
        """Check if a file should be checked by this consistency check"""
        if check.check_type == "naming" and file_path.endswith('.py'):
            return True
        elif check.check_type == "structure" and file_path.endswith('.py'):
            return True
        return False

    def _apply_check(self, content: str, file_path: str, check: ConsistencyCheck) -> List[Dict[str, Any]]:
        """Apply a specific consistency check"""
        issues = []

        if check.check_id == "python_naming":
            # Check for CamelCase function names
            matches = re.finditer(check.pattern, content)
            for match in matches:
                issues.append({
                    "type": "naming_convention",
                    "file": file_path,
                    "line": content[:match.start()].count('\n') + 1,
                    "message": f"Function '{match.group(1)}' uses CamelCase. {check.expected}",
                    "severity": check.severity,
                    "auto_fix": check.auto_fix
                })

        elif check.check_id == "file_headers":
            # Check for shebang
            if not content.startswith('#!/usr/bin/env python3'):
                issues.append({
                    "type": "missing_shebang",
                    "file": file_path,
                    "line": 1,
                    "message": check.expected,
                    "severity": check.severity,
                    "auto_fix": check.auto_fix
                })

        return issues

    async def auto_fix_issues(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Automatically fix issues that can be auto-fixed"""
        fixed_files = []

        # Group issues by file
        issues_by_file = {}
        for issue in issues:
            if issue.get('auto_fix', False):
                file_path = issue['file']
                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []
                issues_by_file[file_path].append(issue)

        # Fix issues file by file
        for file_path, file_issues in issues_by_file.items():
            if await self._fix_file_issues(file_path, file_issues):
                fixed_files.append(file_path)

        return fixed_files

    async def _fix_file_issues(self, file_path: str, issues: List[Dict[str, Any]]) -> bool:
        """Fix issues in a single file"""
        try:
            content = Path(file_path).read_text()
            modified = False

            for issue in issues:
                if issue['type'] == 'missing_shebang':
                    content = '#!/usr/bin/env python3\n' + content
                    modified = True

            if modified:
                Path(file_path).write_text(content)
                self.logger.info(f"Auto-fixed issues in {file_path}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to fix issues in {file_path}: {e}")

        return False


class AutoDocumentationSystem:
    """Main auto-documentation system orchestrator"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.git_integration = GitIntegration(repo_path)
        self.doc_generator = DocumentationGenerator()
        self.consistency_enforcer = ConsistencyEnforcer()
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize the auto-documentation system"""
        await self.git_integration.setup_hooks()

    async def process_files(self, file_paths: List[str], auto_commit: bool = False) -> AutoDocResult:
        """Process files for documentation and consistency"""

        # Generate documentation
        docs_generated = []
        for file_path in file_paths:
            file_docs = await self.doc_generator.generate_function_docs(file_path)
            docs_generated.extend(file_docs)

        # Check consistency
        consistency_issues = await self.consistency_enforcer.check_consistency(file_paths)

        # Auto-fix if possible
        fixed_files = []
        if consistency_issues:
            fixable_issues = [issue for issue in consistency_issues if issue.get('auto_fix', False)]
            if fixable_issues:
                fixed_files = await self.consistency_enforcer.auto_fix_issues(fixable_issues)

        # Generate commit message if needed
        commit_message = None
        commit_suggested = False

        if docs_generated or fixed_files:
            commit_suggested = True
            if auto_commit:
                all_changed = list(set(file_paths + fixed_files))
                commit_message = await self.git_integration.suggest_commit_message(all_changed)

        return AutoDocResult(
            operation="process_files",
            files_processed=file_paths,
            documentation_generated=docs_generated,
            consistency_issues=consistency_issues,
            commit_suggested=commit_suggested,
            commit_message=commit_message
        )

    async def check_and_prompt(self, file_paths: List[str]) -> Dict[str, Any]:
        """Check files and prompt user for actions"""

        result = await self.process_files(file_paths)

        # Prepare user prompt
        prompt_data = {
            "files_processed": len(result.files_processed),
            "documentation_needed": len(result.documentation_generated) > 0,
            "consistency_issues": len(result.consistency_issues),
            "auto_fixable": len([i for i in result.consistency_issues if i.get('auto_fix', False)]),
            "commit_suggested": result.commit_suggested,
            "suggested_commit_message": result.commit_message,
            "actions": []
        }

        # Suggest actions
        if result.documentation_generated:
            prompt_data["actions"].append("Generate missing documentation")

        if any(issue.get('auto_fix', False) for issue in result.consistency_issues):
            prompt_data["actions"].append("Auto-fix consistency issues")

        if result.commit_suggested:
            prompt_data["actions"].append("Create commit with generated message")

        return prompt_data

    async def run_pre_commit_check(self) -> bool:
        """Run pre-commit consistency checks"""
        # Get staged files
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            staged_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]

            if not staged_files:
                return True

            # Check consistency
            issues = await self.consistency_enforcer.check_consistency(staged_files)
            error_issues = [issue for issue in issues if issue['severity'] == 'error']

            if error_issues:
                print("❌ Consistency check failed:")
                for issue in error_issues:
                    print(f"  {issue['file']}:{issue['line']} - {issue['message']}")
                return False

            return True

        except subprocess.CalledProcessError:
            return True  # If git command fails, allow commit

    async def run_post_commit_check(self):
        """Run post-commit documentation check"""
        # Get files from last commit
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            changed_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]

            if changed_files:
                # Check for documentation needs
                doc_result = await self.process_files(changed_files)

                if doc_result.documentation_generated or doc_result.consistency_issues:
                    print("📝 Documentation updates suggested:")
                    print(f"  Files needing docs: {len(doc_result.documentation_generated)}")
                    print(f"  Consistency issues: {len(doc_result.consistency_issues)}")
                    print("  Run: python3 -m oos.src.auto_documentation --fix")

        except subprocess.CalledProcessError:
            pass  # Ignore git errors


# Global instance
_auto_doc_instance = None


def get_auto_documentation_system() -> AutoDocumentationSystem:
    """Get or create global auto-documentation system"""
    global _auto_doc_instance
    if _auto_doc_instance is None:
        _auto_doc_instance = AutoDocumentationSystem()
    return _auto_doc_instance


# CLI interface
async def main():
    """Main CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="OOS Auto-Documentation System")
    parser.add_argument("files", nargs="*", help="Files to process")
    parser.add_argument("--init", action="store_true", help="Initialize auto-documentation system")
    parser.add_argument("--check-consistency", action="store_true", help="Check consistency only")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues")
    parser.add_argument("--pre-commit", action="store_true", help="Run pre-commit checks")
    parser.add_argument("--post-commit", action="store_true", help="Run post-commit checks")
    parser.add_argument("--auto-commit", action="store_true", help="Auto-commit changes")

    args = parser.parse_args()

    system = get_auto_documentation_system()

    if args.init:
        await system.initialize()
        print("✅ Auto-documentation system initialized")

    elif args.pre_commit:
        success = await system.run_pre_commit_check()
        exit(0 if success else 1)

    elif args.post_commit:
        await system.run_post_commit_check()

    elif args.check_consistency:
        if args.files:
            issues = await system.consistency_enforcer.check_consistency(args.files)
            if issues:
                for issue in issues:
                    print(f"{issue['file']}:{issue['line']} - {issue['message']} ({issue['severity']})")
                exit(1)
        else:
            print("No files specified")

    elif args.fix:
        if args.files:
            result = await system.process_files(args.files, auto_commit=args.auto_commit)
            print(f"Processed {len(result.files_processed)} files")
            print(f"Generated docs: {len(result.documentation_generated)}")
            print(f"Consistency issues: {len(result.consistency_issues)}")

            if result.commit_suggested:
                print(f"Commit suggested: {result.commit_message}")
        else:
            print("No files specified")

    else:
        if args.files:
            prompt_data = await system.check_and_prompt(args.files)
            print(json.dumps(prompt_data, indent=2))
        else:
            print("No action specified. Use --help for options.")


if __name__ == "__main__":
    asyncio.run(main())