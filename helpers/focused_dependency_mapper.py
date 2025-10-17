#!/usr/bin/env python3
"""
Focused Dependency Mapping - Atlas Core Files Only
Maps dependencies for consolidation planning
"""

import ast
import os
import json
from pathlib import Path
from collections import defaultdict
import re

class FocusedDependencyMapper:
    def __init__(self):
        self.dependencies = {
            'imports': {},
            'function_calls': {},
            'config_usage': {},
            'consolidation_groups': {}
        }
        self.atlas_dirs = ['helpers', 'modules', 'process', 'api', 'scripts', 'tests', 'analytics', 'content', 'search']

    def scan_atlas_files(self):
        """Scan only Atlas core directories"""
        python_files = []

        # Add root level Python files
        for file in Path('.').glob('*.py'):
            python_files.append(file)

        # Add Atlas core directories
        for dir_name in self.atlas_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                for file in dir_path.rglob('*.py'):
                    python_files.append(file)

        print(f"📂 Found {len(python_files)} Atlas Python files")
        return python_files

    def analyze_file(self, filepath):
        """Analyze a single file for consolidation planning"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Get imports
            imports = self.extract_imports(content)

            # Get function calls relevant to consolidation
            calls = self.extract_consolidation_calls(content)

            # Get config usage
            config = self.extract_config_usage(content)

            return {
                'imports': imports,
                'function_calls': calls,
                'config_usage': config
            }
        except Exception as e:
            return {'error': str(e)}

    def extract_imports(self, content):
        """Extract import statements"""
        imports = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except:
            # Fallback to regex for syntax errors
            import_patterns = [
                r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import',
                r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)'
            ]
            for pattern in import_patterns:
                imports.extend(re.findall(pattern, content))

        return imports

    def extract_consolidation_calls(self, content):
        """Extract function calls relevant to consolidation"""
        patterns = {
            'transcript_functions': [
                r'fetch_transcript\s*\(',
                r'scrape_transcript\s*\(',
                r'discover_transcripts?\s*\(',
                r'enhance_transcript\s*\(',
                r'process_transcript\s*\(',
                r'index_transcript\s*\(',
                r'search_transcripts?\s*\(',
                r'parse_transcript\s*\(',
                r'rank_transcripts?\s*\('
            ],
            'article_functions': [
                r'fetch_and_save_articles\s*\(',
                r'fetch_article\s*\(',
                r'process_article\s*\(',
                r'recover_article\s*\(',
                r'authenticate_\w+\s*\(',
                r'wayback_fetch\s*\(',
                r'firecrawl_fetch\s*\(',
                r'skyvern_fetch\s*\('
            ],
            'content_functions': [
                r'classify_content\s*\(',
                r'detect_content_type\s*\(',
                r'process_document\s*\(',
                r'export_content\s*\(',
                r'summarize_content\s*\('
            ]
        }

        calls = {}
        for category, pattern_list in patterns.items():
            calls[category] = []
            for pattern in pattern_list:
                matches = re.findall(pattern, content)
                calls[category].extend([pattern.replace(r'\s*\(', '').replace(r'\\', '') for _ in matches])

        return calls

    def extract_config_usage(self, content):
        """Extract configuration usage"""
        config_patterns = [
            r'config\[[\'"](.*?)[\'"]\]',
            r'config\.get\([\'"](.*?)[\'"]\)',
            r'getenv\([\'"](.*?)[\'"]\)',
            r'os\.environ\[[\'"](.*?)[\'"]\]'
        ]

        config_keys = []
        for pattern in config_patterns:
            config_keys.extend(re.findall(pattern, content))

        # Look for common env vars
        env_vars = re.findall(r'[A-Z][A-Z_]*(?:API_)?KEY|DATABASE_URL|OUTPUT_DIR', content)
        config_keys.extend(env_vars)

        return list(set(config_keys))

    def identify_consolidation_targets(self):
        """Identify specific consolidation opportunities"""
        consolidation_map = {
            'transcript_manager_candidates': [
                'helpers/atp_transcript_scraper.py',
                'helpers/atp_enhanced_transcript.py',
                'helpers/network_transcript_scrapers.py',
                'helpers/universal_transcript_discoverer.py',
                'helpers/transcript_first_processor.py',
                'helpers/transcript_lookup.py',
                'helpers/transcript_parser.py',
                'helpers/transcript_search_indexer.py',
                'helpers/transcript_search_ranking.py',
                'helpers/podcast_transcript_ingestor.py'
            ],
            'article_manager_candidates': [
                'helpers/article_ingestor.py',
                'helpers/article_fetcher.py',
                'helpers/article_strategies.py',
                'helpers/skyvern_enhanced_ingestor.py',
                'helpers/firecrawl_strategy.py',
                'helpers/persistent_auth_strategy.py',
                'helpers/simple_auth_strategy.py',
                'helpers/paywall.py'
            ],
            'content_pipeline_candidates': [
                'helpers/content_classifier.py',
                'helpers/content_detector.py',
                'helpers/content_exporter.py',
                'helpers/document_processor.py',
                'helpers/document_ingestor.py'
            ]
        }

        for group, candidates in consolidation_map.items():
            existing_files = []
            missing_files = []

            for candidate in candidates:
                if Path(candidate).exists():
                    existing_files.append(candidate)
                else:
                    missing_files.append(candidate)

            self.dependencies['consolidation_groups'][group] = {
                'existing': existing_files,
                'missing': missing_files,
                'consolidation_feasible': len(existing_files) >= 2,
                'complexity_reduction': len(existing_files)
            }

    def run_analysis(self):
        """Run focused analysis on Atlas core files"""
        print("🎯 Running focused dependency analysis for consolidation...")

        files = self.scan_atlas_files()

        for filepath in files:
            print(f"  📄 {filepath}")
            analysis = self.analyze_file(filepath)

            self.dependencies['imports'][str(filepath)] = analysis.get('imports', [])
            self.dependencies['function_calls'][str(filepath)] = analysis.get('function_calls', {})
            self.dependencies['config_usage'][str(filepath)] = analysis.get('config_usage', [])

        self.identify_consolidation_targets()

        return self.dependencies

    def save_analysis(self, filename='atlas_dependency_analysis.json'):
        """Save analysis results"""
        summary = {
            'timestamp': '2025-08-21T11:20:00',
            'analysis_scope': 'Atlas core files only',
            'files_analyzed': len(self.dependencies['imports']),
            'consolidation_groups': len(self.dependencies['consolidation_groups'])
        }

        result = {
            'summary': summary,
            'dependencies': self.dependencies
        }

        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"💾 Analysis saved to {filename}")

    def print_consolidation_summary(self):
        """Print consolidation opportunities"""
        print("\n🎯 CONSOLIDATION ANALYSIS")
        print("=" * 60)

        for group, analysis in self.dependencies['consolidation_groups'].items():
            existing = len(analysis['existing'])
            missing = len(analysis['missing'])
            feasible = "✅ FEASIBLE" if analysis['consolidation_feasible'] else "❌ LIMITED"

            print(f"\n📦 {group.upper()}:")
            print(f"   Status: {feasible}")
            print(f"   Files to consolidate: {existing}")
            print(f"   Missing/not found: {missing}")
            print(f"   Complexity reduction: {existing} → 1 file")

            if existing > 0:
                print("   Existing files:")
                for file in analysis['existing'][:5]:  # Show first 5
                    print(f"     • {file}")
                if len(analysis['existing']) > 5:
                    print(f"     • ... and {len(analysis['existing']) - 5} more")

        print("\n🚀 CONSOLIDATION IMPACT:")
        total_files = sum(len(g['existing']) for g in self.dependencies['consolidation_groups'].values())
        consolidated_files = len([g for g in self.dependencies['consolidation_groups'].values() if g['consolidation_feasible']])

        print(f"   Files that can be consolidated: {total_files}")
        print(f"   Consolidation groups ready: {consolidated_files}")
        print(f"   Estimated complexity reduction: {total_files} → {consolidated_files} files")

        print("=" * 60)

if __name__ == '__main__':
    mapper = FocusedDependencyMapper()
    mapper.run_analysis()
    mapper.print_consolidation_summary()
    mapper.save_analysis()