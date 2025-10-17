#!/usr/bin/env python3
"""
Repository Analysis & Pattern Extraction Engine

Analyzes GitHub repositories to extract recurring patterns, architectural decisions,
and development workflows for conversion into Claude Code slash commands.
"""

import os
import json
import re
import ast
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from collections import defaultdict, Counter
import requests
from github import Github
from github.Repository import Repository
from github.ContentFile import ContentFile


class RepositoryAnalyzer:
    """Main analyzer class for extracting patterns from GitHub repositories"""

    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.github = Github(self.github_token) if self.github_token else None
        self.patterns = {
            'architectural': [],
            'workflows': [],
            'testing': [],
            'deployment': [],
            'documentation': [],
            'automation': []
        }

    def analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        """Analyze a single repository and extract patterns"""
        if not self.github:
            raise ValueError("GitHub token required for repository analysis")

        # Extract owner/repo from URL
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            raise ValueError(f"Invalid repository URL: {repo_url}")

        repo = self.github.get_repo(repo_path)

        analysis = {
            'repository': repo_url,
            'metadata': {
                'name': repo.name,
                'description': repo.description,
                'language': repo.language,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'topics': repo.get_topics()
            },
            'file_structure': self._analyze_file_structure(repo),
            'patterns': self._extract_patterns(repo),
            'workflows': self._extract_workflows(repo),
            'documentation': self._analyze_documentation(repo)
        }

        return analysis

    def _extract_repo_path(self, repo_url: str) -> Optional[str]:
        """Extract owner/repo path from GitHub URL"""
        patterns = [
            r'github\.com/([^/]+/[^/]+?)(?:\.git)?/?$',
            r'github\.com/([^/]+/[^/]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, repo_url)
            if match:
                return match.group(1)
        return None

    def _analyze_file_structure(self, repo: Repository) -> Dict[str, Any]:
        """Analyze repository file structure and organization patterns"""
        structure = {
            'directories': defaultdict(list),
            'file_types': Counter(),
            'configuration_files': [],
            'package_files': [],
            'entry_points': []
        }

        try:
            contents = repo.get_contents("")
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    structure['directories'][file_content.path].extend(
                        [item.name for item in repo.get_contents(file_content.path)]
                    )
                    contents.extend(repo.get_contents(file_content.path))
                else:
                    file_ext = Path(file_content.name).suffix.lower()
                    structure['file_types'][file_ext] += 1

                    # Identify configuration files
                    if self._is_config_file(file_content.name):
                        structure['configuration_files'].append(file_content.path)

                    # Identify package/dependency files
                    if self._is_package_file(file_content.name):
                        structure['package_files'].append(file_content.path)

                    # Identify entry points
                    if self._is_entry_point(file_content.name, file_content.path):
                        structure['entry_points'].append(file_content.path)

        except Exception as e:
            print(f"Error analyzing file structure: {e}")

        return dict(structure)

    def _extract_patterns(self, repo: Repository) -> Dict[str, List[Dict[str, Any]]]:
        """Extract code patterns and architectural decisions"""
        patterns = {
            'architectural': [],
            'code_patterns': [],
            'design_patterns': [],
            'technical_patterns': []
        }

        # Analyze code files for patterns
        code_files = self._get_code_files(repo)

        for file_path in code_files:
            try:
                content = repo.get_contents(file_path)
                if content.type == "file":
                    file_content = content.decoded_content.decode('utf-8')

                    # Extract language-specific patterns
                    if file_path.endswith('.py'):
                        patterns['architectural'].extend(
                            self._analyze_python_patterns(file_content, file_path)
                        )
                    elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
                        patterns['architectural'].extend(
                            self._analyze_javascript_patterns(file_content, file_path)
                        )
                    elif file_path.endswith('.go'):
                        patterns['architectural'].extend(
                            self._analyze_go_patterns(file_content, file_path)
                        )

            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")

        return patterns

    def _extract_workflows(self, repo: Repository) -> List[Dict[str, Any]]:
        """Extract CI/CD and automation workflows"""
        workflows = []

        try:
            # Check for GitHub Actions workflows
            workflow_files = repo.get_contents('.github/workflows')
            for workflow_file in workflow_files:
                if workflow_file.name.endswith('.yml') or workflow_file.name.endswith('.yaml'):
                    try:
                        content = workflow_file.decoded_content.decode('utf-8')
                        workflow_analysis = self._analyze_github_workflow(content, workflow_file.name)
                        workflows.append(workflow_analysis)
                    except Exception as e:
                        print(f"Error analyzing workflow {workflow_file.name}: {e}")

        except Exception as e:
            # No .github/workflows directory
            pass

        # Check for other workflow systems
        workflows.extend(self._analyze_other_workflows(repo))

        return workflows

    def _analyze_documentation(self, repo: Repository) -> Dict[str, Any]:
        """Analyze documentation patterns and structure"""
        docs_analysis = {
            'readme_exists': False,
            'readme_structure': None,
            'api_docs': [],
            'contributing_guide': False,
            'changelog': False,
            'examples': []
        }

        try:
            # Check for README
            readme_files = [f for f in repo.get_contents("") if f.name.upper().startswith('README')]
            if readme_files:
                docs_analysis['readme_exists'] = True
                readme_content = readme_files[0].decoded_content.decode('utf-8')
                docs_analysis['readme_structure'] = self._analyze_readme_structure(readme_content)

            # Check for documentation directory
            try:
                docs_dir = repo.get_contents('docs')
                docs_analysis['api_docs'] = [f.path for f in docs_dir if f.type == "file"]
            except:
                pass

            # Check for contributing guide
            try:
                contributing = repo.get_contents('CONTRIBUTING.md')
                docs_analysis['contributing_guide'] = True
            except:
                pass

            # Check for changelog
            try:
                changelog = repo.get_contents('CHANGELOG.md')
                docs_analysis['changelog'] = True
            except:
                pass

            # Check for examples
            try:
                examples = repo.get_contents('examples')
                docs_analysis['examples'] = [f.path for f in examples if f.type == "file"]
            except:
                pass

        except Exception as e:
            print(f"Error analyzing documentation: {e}")

        return docs_analysis

    def _is_config_file(self, filename: str) -> bool:
        """Check if file is a configuration file"""
        config_patterns = [
            r'.*\.conf$', r'.*\.config$', r'.*\.cfg$', r'.*\.ini$',
            r'.*\.json$', r'.*\.yml$', r'.*\.yaml$', r'.*\.toml$',
            r'package\.json$', r'pyproject\.toml$', r'requirements.*\.txt$',
            r'dockerfile.*', r'\.dockerignore$', r'\.env.*'
        ]
        return any(re.match(pattern, filename.lower()) for pattern in config_patterns)

    def _is_package_file(self, filename: str) -> bool:
        """Check if file is a package/dependency file"""
        package_files = [
            'package.json', 'requirements.txt', 'pyproject.toml',
            'pom.xml', 'build.gradle', 'cargo.toml', 'go.mod'
        ]
        return filename.lower() in package_files

    def _is_entry_point(self, filename: str, filepath: str) -> bool:
        """Check if file is a main entry point"""
        entry_patterns = [
            r'main\.(py|js|go|rs)$',
            r'index\.(js|ts)$',
            r'app\.(py|js)$',
            r'cli\.(py|js)$',
            r'bin/.*'
        ]
        return any(re.match(pattern, filepath.lower()) for pattern in entry_patterns)

    def _get_code_files(self, repo: Repository) -> List[str]:
        """Get list of code files to analyze"""
        code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', 'java', 'cpp', 'c']
        code_files = []

        try:
            contents = repo.get_contents("")
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    if file_content.path not in ['node_modules', '.git', 'venv', '__pycache__']:
                        contents.extend(repo.get_contents(file_content.path))
                else:
                    if any(file_content.name.endswith(ext) for ext in code_extensions):
                        code_files.append(file_content.path)
        except Exception as e:
            print(f"Error getting code files: {e}")

        return code_files

    def _analyze_python_patterns(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Analyze Python code for patterns"""
        patterns = []

        try:
            tree = ast.parse(content)

            # Analyze class structure
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    pattern = {
                        'type': 'class_pattern',
                        'name': node.name,
                        'file': file_path,
                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                        'decorators': [ast.unparse(d) for d in node.decorator_list],
                        'pattern_category': 'architecture'
                    }
                    patterns.append(pattern)

                elif isinstance(node, ast.FunctionDef):
                    # Analyze function patterns
                    pattern = {
                        'type': 'function_pattern',
                        'name': node.name,
                        'file': file_path,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [ast.unparse(d) for d in node.decorator_list],
                        'pattern_category': 'code_structure'
                    }
                    patterns.append(pattern)

        except Exception as e:
            print(f"Error parsing Python code in {file_path}: {e}")

        return patterns

    def _analyze_javascript_patterns(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Analyze JavaScript/TypeScript code for patterns"""
        patterns = []

        # Simple pattern detection for JS/TS
        js_patterns = [
            (r'export\s+(?:default\s+)?(?:class|function|const)\s+(\w+)', 'export_pattern'),
            (r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]', 'import_pattern'),
            (r'(?:React\.(?:Component|createContext|useEffect|useState))', 'react_pattern'),
            (r'(?:async\s+function|const\s+\w+\s*=\s*async)', 'async_pattern'),
            (r'(?:fetch\(|axios\.)', 'api_pattern')
        ]

        for pattern_name, pattern_type in js_patterns:
            matches = re.findall(pattern_name, content, re.MULTILINE)
            if matches:
                patterns.append({
                    'type': pattern_type,
                    'matches': matches[:10],  # Limit to first 10 matches
                    'file': file_path,
                    'pattern_category': 'javascript'
                })

        return patterns

    def _analyze_go_patterns(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Analyze Go code for patterns"""
        patterns = []

        go_patterns = [
            (r'package\s+(\w+)', 'package_pattern'),
            (r'type\s+(\w+)\s+(?:struct|interface)', 'type_pattern'),
            (r'func\s+\([^)]*\)\s*(\w+)', 'method_pattern'),
            (r'func\s+(\w+)', 'function_pattern'),
            (r'import\s*\((.*?)\)', 'import_block')
        ]

        for pattern_name, pattern_type in go_patterns:
            matches = re.findall(pattern_name, content, re.MULTILINE | re.DOTALL)
            if matches:
                patterns.append({
                    'type': pattern_type,
                    'matches': matches[:10],
                    'file': file_path,
                    'pattern_category': 'go'
                })

        return patterns

    def _analyze_github_workflow(self, content: str, filename: str) -> Dict[str, Any]:
        """Analyze GitHub Actions workflow"""
        workflow_analysis = {
            'name': filename,
            'triggers': [],
            'jobs': [],
            'technologies': [],
            'pattern_type': 'github_actions'
        }

        # Extract triggers
        trigger_patterns = [
            r'on:\s*\[(.*?)\]',
            r'on:\s*(push|pull_request|schedule|workflow_dispatch)',
            r'push:\s*{[^}]*branches:\s*\[(.*?)\]'
        ]

        for pattern in trigger_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            workflow_analysis['triggers'].extend(matches)

        # Extract job patterns
        job_patterns = [
            r'(\w+):\s*{[^}]*runs-on:\s*([^}]+)',
            r'steps:\s*\[(.*?)\]',
            r'(uses|run):\s*([^\n]+)'
        ]

        for pattern in job_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            if matches:
                workflow_analysis['jobs'].extend(matches[:5])

        return workflow_analysis

    def _analyze_other_workflows(self, repo: Repository) -> List[Dict[str, Any]]:
        """Analyze other workflow systems"""
        workflows = []

        # Check for Makefile
        try:
            makefile = repo.get_contents('Makefile')
            makefile_content = makefile.decoded_content.decode('utf-8')
            targets = re.findall(r'^(\w+):', makefile_content, re.MULTILINE)
            workflows.append({
                'type': 'makefile',
                'targets': targets,
                'pattern_type': 'build_system'
            })
        except:
            pass

        # Check for Docker
        try:
            dockerfile = repo.get_contents('Dockerfile')
            workflows.append({
                'type': 'docker',
                'pattern_type': 'containerization'
            })
        except:
            pass

        return workflows

    def _analyze_readme_structure(self, content: str) -> Dict[str, Any]:
        """Analyze README structure and content patterns"""
        structure = {
            'sections': [],
            'has_badges': bool(re.search(r'\[!\[.*?\]\(.*?\)\]', content)),
            'has_installation': bool(re.search(r'##\s*Installation', content, re.IGNORECASE)),
            'has_usage': bool(re.search(r'##\s*Usage', content, re.IGNORECASE)),
            'has_contributing': bool(re.search(r'##\s*Contributing', content, re.IGNORECASE)),
            'has_license': bool(re.search(r'##\s*License', content, re.IGNORECASE)),
            'code_examples': len(re.findall(r'```[\s\S]*?```', content))
        }

        # Extract sections
        sections = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        structure['sections'] = sections

        return structure


def main():
    """Main function for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Repository Pattern Analyzer')
    parser.add_argument('repo_url', help='GitHub repository URL')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--token', '-t', help='GitHub token (or set GITHUB_TOKEN env var)')

    args = parser.parse_args()

    analyzer = RepositoryAnalyzer(args.token)

    try:
        result = analyzer.analyze_repository(args.repo_url)

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Analysis saved to {args.output}")
        else:
            print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())