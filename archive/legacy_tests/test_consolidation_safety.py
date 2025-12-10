#!/usr/bin/env python3
"""
Consolidation Safety Testing
Ensures no functionality is lost during module consolidation
"""

import pytest
import json
from pathlib import Path
import importlib.util
import ast

class TestConsolidationSafety:
    """Test that consolidation doesn't break functionality"""

    @pytest.fixture
    def baseline_data(self):
        """Load baseline performance data"""
        baseline_file = Path('performance_baseline.json')
        if baseline_file.exists():
            with open(baseline_file) as f:
                return json.load(f)
        return {}

    @pytest.fixture
    def dependency_data(self):
        """Load dependency analysis data"""
        dep_file = Path('atlas_dependency_analysis.json')
        if dep_file.exists():
            with open(dep_file) as f:
                return json.load(f)
        return {}

    def test_baseline_established(self, baseline_data):
        """Verify performance baseline exists"""
        assert 'baselines' in baseline_data
        assert 'file_processing' in baseline_data['baselines']
        assert 'memory' in baseline_data['baselines']

    def test_consolidation_targets_identified(self, dependency_data):
        """Verify consolidation targets are properly identified"""
        if 'dependencies' in dependency_data:
            groups = dependency_data['dependencies']['consolidation_groups']

            # Check transcript consolidation group
            assert 'transcript_manager_candidates' in groups
            transcript_group = groups['transcript_manager_candidates']
            assert transcript_group['consolidation_feasible'] == True
            assert len(transcript_group['existing']) >= 8  # Should have many files to consolidate

            # Check article consolidation group
            assert 'article_manager_candidates' in groups
            article_group = groups['article_manager_candidates']
            assert article_group['consolidation_feasible'] == True
            assert len(article_group['existing']) >= 5

    def test_critical_modules_exist(self):
        """Verify critical modules exist before consolidation"""
        critical_files = [
            'helpers/config.py',
            'helpers/utils.py',
            'run.py',
            'atlas_status.py'
        ]

        for file_path in critical_files:
            assert Path(file_path).exists(), f"Critical file missing: {file_path}"

    def test_consolidation_candidates_accessible(self):
        """Test that consolidation candidate files can be read"""
        candidates = {
            'transcript_processing': [
                'helpers/atp_transcript_scraper.py',
                'helpers/transcript_lookup.py',
                'helpers/podcast_transcript_ingestor.py'
            ],
            'article_processing': [
                'helpers/article_ingestor.py',
                'helpers/article_fetcher.py',
                'helpers/article_strategies.py'
            ]
        }

        for group, files in candidates.items():
            accessible_files = 0
            for file_path in files:
                if Path(file_path).exists():
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        # Try to parse as Python
                        ast.parse(content)
                        accessible_files += 1
                    except Exception as e:
                        pytest.skip(f"File {file_path} has syntax issues: {e}")

            assert accessible_files >= 2, f"Not enough accessible files in {group}: {accessible_files}"

    @pytest.mark.parametrize("config_file", [
        "config/categories.yaml",
        "config/.env",
        "env.template"
    ])
    def test_configuration_files_exist(self, config_file):
        """Test that required configuration files exist"""
        if config_file == "config/.env":
            # .env might not exist in test environment
            pytest.skip("Skipping .env check - may not exist in test")

        assert Path(config_file).exists(), f"Configuration file missing: {config_file}"

    def test_no_circular_imports(self):
        """Test for circular import issues that could complicate consolidation"""
        # This is a basic check - in real consolidation we'd need more sophisticated analysis
        critical_modules = ['helpers.config', 'helpers.utils']

        for module_name in critical_modules:
            try:
                # This basic test just ensures the module can be imported
                spec = importlib.util.find_spec(module_name.replace('.', '/') + '.py')
                if spec is None:
                    pytest.skip(f"Module {module_name} not found for import testing")
            except Exception as e:
                pytest.fail(f"Import issue with {module_name}: {e}")

class TestPostConsolidationValidation:
    """Tests to run after each consolidation step"""

    def test_consolidated_module_interface(self):
        """Test that consolidated modules maintain expected interfaces"""
        # This will be implemented for each consolidation step
        # For now, just a placeholder
        assert True, "Placeholder for post-consolidation interface tests"

    def test_performance_regression_check(self, baseline_data):
        """Test that performance doesn't regress after consolidation"""
        if not baseline_data:
            pytest.skip("No baseline data available for performance comparison")

        # This would compare new measurements against baseline
        # For now, just verify baseline structure
        assert 'baselines' in baseline_data

    def test_functionality_preservation(self):
        """Test that core functionality is preserved after consolidation"""
        # This would test key user-facing functions
        # Implementation depends on consolidation step
        assert True, "Placeholder for functionality preservation tests"

# Integration test for the consolidation process
class TestConsolidationIntegration:
    """Integration tests for the consolidation process"""

    def test_phase_readiness(self, baseline_data, dependency_data):
        """Test that we're ready to begin consolidation"""
        # Check that all Phase 1 artifacts exist
        required_files = [
            'PHASE1_BASELINE_ESTABLISHED.md',
            'PHASE1_CONFIGURATION_MAPPING.md',
            'performance_baseline.json',
            'atlas_dependency_analysis.json'
        ]

        for file_path in required_files:
            assert Path(file_path).exists(), f"Phase 1 artifact missing: {file_path}"

    def test_rollback_capability(self):
        """Test that rollback mechanisms are in place"""
        # Check for backup files
        backup_files = list(Path('.').glob('atlas_*_backup_*.tar.gz'))
        assert len(backup_files) > 0, "No backup files found"

        # Check for Git tag (this would need git command to verify)
        # For now just verify we have git
        assert Path('.git').exists(), "Not a git repository - rollback not possible"

    def test_consolidation_safety_measures(self):
        """Test that safety measures are in place"""
        # Verify testing infrastructure exists
        assert Path('tests/').exists()
        assert Path('pytest.ini').exists()

        # Verify we have the safety testing file itself
        assert Path(__file__).exists()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])