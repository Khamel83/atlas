#!/usr/bin/env python3
"""
Example usage of the Repository Analysis & Pattern Extraction Engine
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.repository_analyzer import RepositoryAnalyzer


def analyze_personal_repositories():
    """Analyze a list of personal repositories to extract patterns"""

    # Example repositories to analyze
    repositories = [
        "https://github.com/Khamel83/oos",  # Current repository
        # Add more personal repositories here
    ]

    analyzer = RepositoryAnalyzer()

    for repo_url in repositories:
        print(f"\\nAnalyzing repository: {repo_url}")

        try:
            # Analyze the repository
            analysis = analyzer.analyze_repository(repo_url)

            # Extract key insights
            print(f"\\n=== Repository: {analysis['metadata']['name']} ===")
            print(f"Language: {analysis['metadata']['language']}")
            print(f"Stars: {analysis['metadata']['stars']}")
            print(f"Topics: {', '.join(analysis['metadata']['topics'])}")

            # Show file structure insights
            file_types = analysis['file_structure']['file_types']
            print(f"\\nFile Types: {dict(file_types)}")

            # Show patterns found
            patterns = analysis['patterns']['architectural']
            print(f"\\nArchitectural Patterns Found: {len(patterns)}")

            # Show workflows
            workflows = analysis['workflows']
            print(f"Workflows Found: {len(workflows)}")

            # Show documentation
            docs = analysis['documentation']
            print(f"Documentation: README={'✓' if docs['readme_exists'] else '✗'}, "
                  f"Contributing={'✓' if docs['contributing_guide'] else '✗'}")

            # Save analysis
            output_file = f"analysis_{analysis['metadata']['name']}.json"
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            print(f"Analysis saved to: {output_file}")

        except Exception as e:
            print(f"Error analyzing {repo_url}: {e}")


def extract_command_templates():
    """Extract command templates from analyzed patterns"""

    print("\\n=== Extracting Command Templates ===")

    # Example pattern to command mappings
    command_templates = {
        "python_setup": {
            "name": "setup-python-project",
            "description": "Create a new Python project with standard structure",
            "parameters": {
                "project_name": {"type": "string", "required": true},
                "venv_name": {"type": "string", "default": "venv"},
                "python_version": {"type": "string", "default": "3.11"}
            }
        },
        "docker_setup": {
            "name": "setup-docker-container",
            "description": "Add Docker containerization to a project",
            "parameters": {
                "base_image": {"type": "string", "default": "python:3.11-slim"},
                "port": {"type": "integer", "default": 8000}
            }
        },
        "github_actions": {
            "name": "setup-github-actions",
            "description": "Set up GitHub Actions CI/CD pipeline",
            "parameters": {
                "python_versions": {"type": "array", "default": ["3.9", "3.10", "3.11"]},
                "test_command": {"type": "string", "default": "pytest"}
            }
        }
    }

    for template_name, template in command_templates.items():
        print(f"\\nCommand Template: {template['name']}")
        print(f"Description: {template['description']}")
        print(f"Parameters: {json.dumps(template['parameters'], indent=2)}")


def generate_pattern_report():
    """Generate a comprehensive report of patterns found"""

    print("\\n=== Pattern Analysis Report ===")

    # This would be generated from actual repository analysis
    pattern_categories = {
        "Architecture": {
            "microservices": 3,
            "monorepo": 1,
            "serverless": 0,
            "mvc": 2
        },
        "Testing": {
            "pytest": 2,
            "jest": 1,
            "unit_tests": 4,
            "integration_tests": 2
        },
        "Deployment": {
            "docker": 3,
            "kubernetes": 0,
            "github_actions": 2,
            "terraform": 0
        },
        "Documentation": {
            "readme": 4,
            "api_docs": 1,
            "contributing": 2,
            "changelog": 1
        }
    }

    for category, patterns in pattern_categories.items():
        print(f"\\n{category}:")
        for pattern, count in patterns.items():
            print(f"  - {pattern}: {count} occurrences")


if __name__ == "__main__":
    print("Repository Analysis & Pattern Extraction Engine")
    print("=" * 50)

    # Example 1: Analyze repositories
    analyze_personal_repositories()

    # Example 2: Extract command templates
    extract_command_templates()

    # Example 3: Generate pattern report
    generate_pattern_report()

    print("\\n" + "=" * 50)
    print("Analysis complete! Patterns extracted and ready for command generation.")