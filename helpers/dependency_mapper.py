#!/usr/bin/env python3
"""
Comprehensive Dependency Mapping Tool
Maps all imports, function calls, and file dependencies before consolidation
"""

import ast
import os
import json
from pathlib import Path
from collections import defaultdict
import re

class DependencyMapper:
    def __init__(self):
        self.dependencies = {
            'imports': defaultdict(list),           # file -> [imported modules]
            'imported_by': defaultdict(list),      # module -> [files that import it]
            'function_calls': defaultdict(list),   # file -> [function calls]
            'config_usage': defaultdict(list),     # file -> [config keys used]
            'external_deps': set(),                # external libraries used
            'internal_modules': set(),             # our internal modules
        }
        self.python_files = []
        self.consolidation_safety = {}

    def scan_python_files(self):
        """Find all Python files in the project"""
        for root, dirs, files in os.walk('.'):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.mypy_cache',
                                                   'venv', 'venv', 'htmlcov', 'node_modules'}]

            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    self.python_files.append(filepath)

        print(f"📂 Found {len(self.python_files)} Python files to analyze")
        return self.python_files

    def analyze_imports(self, filepath):
        """Analyze imports in a single Python file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if node.level == 0:  # Absolute import
                            imports.append(node.module)
                        else:  # Relative import
                            imports.append(f".{node.module}" if node.module else ".")

            return imports
        except Exception as e:
            print(f"⚠️  Failed to analyze {filepath}: {e}")
            return []

    def analyze_function_calls(self, filepath):
        """Find function calls that might break during consolidation"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for potential function calls to consolidate
            calls = []
            patterns = [
                r'fetch_and_save_articles\(',
                r'ingest_podcasts\(',
                r'ingest_youtube_history\(',
                r'process_transcripts?\(',
                r'find_transcripts?\(',
                r'scrape_transcript\(',
                r'discover_episodes\(',
                r'enhance_transcript\(',
                r'index_transcript\(',
                r'search_transcripts?\(',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    calls.extend([pattern.replace('\\(', '') for _ in matches])

            return calls
        except Exception as e:
            print(f"⚠️  Failed to analyze function calls in {filepath}: {e}")
            return []

    def analyze_config_usage(self, filepath):
        """Find configuration keys used in file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            config_keys = []
            patterns = [
                r'config\[[\'"](.*?)[\'"]\]',
                r'config\.get\([\'"](.*?)[\'"]\)',
                r'getenv\([\'"](.*?)[\'"]\)',
                r'os\.environ\[[\'"](.*?)[\'"]\]',
                r'OPENAI_API_KEY',
                r'YOUTUBE_API_KEY',
                r'FIRECRAWL_API_KEY',
                r'DATABASE_URL',
                r'OUTPUT_DIR',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                config_keys.extend(matches)

            # Also look for direct env var usage
            env_patterns = re.findall(r'[A-Z_]{3,}_(?:API_)?KEY', content)
            config_keys.extend(env_patterns)

            return list(set(config_keys))  # Remove duplicates
        except Exception as e:
            print(f"⚠️  Failed to analyze config usage in {filepath}: {e}")
            return []

    def categorize_dependencies(self):
        """Categorize imports as internal vs external"""
        for file_path, imports in self.dependencies['imports'].items():
            for imp in imports:
                if (imp.startswith('helpers.') or
                    imp.startswith('modules.') or
                    imp.startswith('process.') or
                    imp.startswith('.') or  # Relative imports
                    imp in {'run', 'atlas_status', 'process_podcasts'}):
                    self.dependencies['internal_modules'].add(imp)
                else:
                    self.dependencies['external_deps'].add(imp)

    def identify_consolidation_candidates(self):
        """Identify which modules are safe to consolidate"""
        consolidation_groups = {
            'transcript_processing': [
                'helpers.atp_transcript_scraper',
                'helpers.atp_enhanced_transcript',
                'helpers.network_transcript_scrapers',
                'helpers.universal_transcript_discoverer',
                'helpers.transcript_first_processor',
                'helpers.transcript_lookup',
                'helpers.transcript_parser',
                'helpers.transcript_search_indexer',
                'helpers.transcript_search_ranking',
                'helpers.podcast_transcript_ingestor'
            ],
            'article_processing': [
                'helpers.article_ingestor',
                'helpers.article_fetcher',
                'helpers.article_strategies',
                'helpers.skyvern_enhanced_ingestor',
                'helpers.firecrawl_strategy',
                'helpers.persistent_auth_strategy',
                'helpers.simple_auth_strategy',
                'helpers.paywall'
            ],
            'content_processing': [
                'helpers.content_classifier',
                'helpers.content_detector',
                'helpers.content_exporter',
                'helpers.document_processor',
                'helpers.document_ingestor'
            ]
        }

        for group_name, modules in consolidation_groups.items():
            safe_to_consolidate = []
            dependencies = []

            for module in modules:
                # Check if module exists
                file_path = None
                for fp in self.python_files:
                    if str(fp).replace('/', '.').replace('.py', '') == module:
                        file_path = fp
                        break

                if file_path:
                    safe_to_consolidate.append(module)
                    # Get dependencies for this module
                    deps = self.dependencies['imports'].get(str(file_path), [])
                    dependencies.extend(deps)

            self.consolidation_safety[group_name] = {
                'modules': safe_to_consolidate,
                'dependencies': list(set(dependencies)),
                'safe': len(safe_to_consolidate) > 0,
                'consolidation_complexity': len(safe_to_consolidate)
            }

    def run_full_analysis(self):
        """Run complete dependency analysis"""
        print("🔍 Starting comprehensive dependency mapping...")

        # Scan for Python files
        self.scan_python_files()

        # Analyze each file
        for i, filepath in enumerate(self.python_files):
            if i % 50 == 0:
                print(f"  📄 Analyzing file {i+1}/{len(self.python_files)}: {filepath}")

            # Analyze imports
            imports = self.analyze_imports(filepath)
            self.dependencies['imports'][str(filepath)] = imports

            # Build reverse mapping
            for imp in imports:
                self.dependencies['imported_by'][imp].append(str(filepath))

            # Analyze function calls
            calls = self.analyze_function_calls(filepath)
            self.dependencies['function_calls'][str(filepath)] = calls

            # Analyze config usage
            config_keys = self.analyze_config_usage(filepath)
            self.dependencies['config_usage'][str(filepath)] = config_keys

        # Categorize dependencies
        self.categorize_dependencies()

        # Identify consolidation candidates
        self.identify_consolidation_candidates()

        print("✅ Dependency analysis complete!")
        return self.dependencies

    def save_analysis(self, filename='dependency_analysis.json'):
        """Save analysis results"""
        # Convert sets to lists for JSON serialization
        result = {
            'imports': dict(self.dependencies['imports']),
            'imported_by': dict(self.dependencies['imported_by']),
            'function_calls': dict(self.dependencies['function_calls']),
            'config_usage': dict(self.dependencies['config_usage']),
            'external_deps': list(self.dependencies['external_deps']),
            'internal_modules': list(self.dependencies['internal_modules']),
            'consolidation_safety': self.consolidation_safety,
            'summary': {
                'total_python_files': len(self.python_files),
                'total_internal_modules': len(self.dependencies['internal_modules']),
                'total_external_deps': len(self.dependencies['external_deps']),
                'consolidation_groups': len(self.consolidation_safety)
            }
        }

        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"💾 Dependency analysis saved to {filename}")

    def print_summary(self):
        """Print human-readable summary"""
        print("\n📊 DEPENDENCY ANALYSIS SUMMARY")
        print("=" * 60)

        print(f"📄 Python Files Analyzed: {len(self.python_files)}")
        print(f"🔗 Internal Modules: {len(self.dependencies['internal_modules'])}")
        print(f"📦 External Dependencies: {len(self.dependencies['external_deps'])}")

        print(f"\n🎯 CONSOLIDATION ANALYSIS:")
        for group, analysis in self.consolidation_safety.items():
            status = "✅ SAFE" if analysis['safe'] else "❌ RISKY"
            print(f"  {group}: {status}")
            print(f"    Modules to consolidate: {len(analysis['modules'])}")
            print(f"    Dependencies: {len(analysis['dependencies'])}")

        print(f"\n🔧 HIGH-IMPACT MODULES (most imported):")
        # Find most imported internal modules
        import_counts = {}
        for module, importers in self.dependencies['imported_by'].items():
            if module in self.dependencies['internal_modules']:
                import_counts[module] = len(importers)

        top_modules = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for module, count in top_modules:
            print(f"  {module}: imported by {count} files")

        print("=" * 60)

if __name__ == '__main__':
    mapper = DependencyMapper()
    mapper.run_full_analysis()
    mapper.print_summary()
    mapper.save_analysis()