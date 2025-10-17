#!/usr/bin/env python3
"""
Example usage of the Idea-to-Command Transformation System
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.command_generator import IdeaToCommandTransformer


def create_sample_patterns():
    """Create sample repository patterns for demonstration"""
    return {
        "metadata": {
            "name": "sample-project",
            "language": "Python",
            "stars": 150,
            "topics": ["python", "web", "api"]
        },
        "file_structure": {
            "directories": {
                "src": ["main.py", "utils.py", "config.py"],
                "tests": ["test_main.py", "test_utils.py"],
                "docs": ["README.md", "API.md"]
            },
            "file_types": {".py": 15, ".md": 3, ".txt": 1},
            "configuration_files": ["requirements.txt", "config.json"],
            "package_files": ["requirements.txt"],
            "entry_points": ["src/main.py"]
        },
        "patterns": {
            "architectural": [
                {
                    "type": "class_pattern",
                    "name": "UserManager",
                    "file": "src/models.py",
                    "methods": ["create_user", "get_user", "update_user", "delete_user"],
                    "decorators": [],
                    "pattern_category": "architecture"
                },
                {
                    "type": "function_pattern",
                    "name": "validate_email",
                    "file": "src/utils.py",
                    "args": ["email"],
                    "decorators": [],
                    "pattern_category": "code_structure"
                }
            ]
        },
        "workflows": [
            {
                "name": "ci.yml",
                "triggers": ["push", "pull_request"],
                "jobs": [
                    ("test", "ubuntu-latest"),
                    ("steps", ["checkout", "setup-python", "install", "test"])
                ],
                "technologies": ["python", "pytest"],
                "pattern_type": "github_actions"
            },
            {
                "type": "docker",
                "pattern_type": "containerization"
            }
        ],
        "documentation": {
            "readme_exists": True,
            "readme_structure": {
                "sections": ["Description", "Installation", "Usage", "Contributing", "License"],
                "has_badges": True,
                "has_installation": True,
                "has_usage": True,
                "has_contributing": True,
                "has_license": True,
                "code_examples": 3
            },
            "api_docs": ["docs/API.md"],
            "contributing_guide": True,
            "changelog": False,
            "examples": []
        }
    }


def demonstrate_command_generation():
    """Demonstrate command generation from patterns"""
    print("Idea-to-Command Transformation System Demo")
    print("=" * 50)

    # Create sample patterns
    patterns_data = create_sample_patterns()

    # Initialize transformer
    transformer = IdeaToCommandTransformer()

    # Generate commands
    commands = transformer.transform_patterns_to_commands(patterns_data)

    print(f"\\nGenerated {len(commands)} commands from patterns:\\n")

    # Display commands
    for i, command in enumerate(commands, 1):
        print(f"{i}. {command.name}")
        print(f"   Description: {command.description}")
        print(f"   Category: {command.category}")
        print(f"   Parameters: {[p.name for p in command.parameters]}")
        print(f"   Dependencies: {command.dependencies}")
        print(f"   Usage: {command.usage_examples[0] if command.usage_examples else 'N/A'}")
        print()

    # Generate complete command library
    library = transformer.generate_command_library(patterns_data)

    print(f"\\nCommand Library Summary:")
    print(f"Total Commands: {library['metadata']['total_commands']}")
    print("Commands by Category:")
    for category, count in library['metadata']['categories'].items():
        print(f"  {category}: {count}")

    # Save library
    with open('generated_commands.json', 'w') as f:
        json.dump(library, f, indent=2)
    print("\\nCommand library saved to: generated_commands.json")


def show_command_examples():
    """Show specific command examples"""
    print("\\n" + "=" * 50)
    print("Command Examples")
    print("=" * 50)

    examples = [
        {
            "name": "setup-python-project",
            "description": "Initialize a new Python project with standard structure",
            "usage": "/setup-python-project --project-name my-app --python-version 3.11",
            "parameters": {
                "project_name": {"type": "string", "required": True, "description": "Name of the project"},
                "python_version": {"type": "string", "default": "3.11", "description": "Python version"},
                "include_tests": {"type": "boolean", "default": True, "description": "Include test structure"}
            }
        },
        {
            "name": "setup-docker",
            "description": "Add Docker containerization to the project",
            "usage": "/setup-docker --base-image python:3.11-slim --port 8000",
            "parameters": {
                "base_image": {"type": "string", "default": "python:3.11-slim", "description": "Base Docker image"},
                "port": {"type": "integer", "default": 8000, "description": "Exposed port"},
                "include_compose": {"type": "boolean", "default": True, "description": "Include Docker Compose"}
            }
        },
        {
            "name": "setup-github-actions",
            "description": "Set up GitHub Actions CI/CD pipeline",
            "usage": "/setup-github-actions --workflow-name ci --python-versions 3.9,3.10,3.11",
            "parameters": {
                "workflow_name": {"type": "string", "default": "ci", "description": "Name of the workflow"},
                "python_versions": {"type": "array", "default": ["3.9", "3.10", "3.11"], "description": "Python versions to test"},
                "deploy": {"type": "boolean", "default": False, "description": "Include deployment steps"}
            }
        }
    ]

    for example in examples:
        print(f"\\n{example['name']}")
        print(f"Description: {example['description']}")
        print(f"Usage: {example['usage']}")
        print("Parameters:")
        for param_name, param_info in example['parameters'].items():
            required = " (required)" if param_info.get('required') else f" (default: {param_info.get('default')})"
            print(f"  --{param_name}: {param_info['description']}{required}")


def show_integration_workflow():
    """Show how commands integrate with Claude Code"""
    print("\\n" + "=" * 50)
    print("Integration Workflow")
    print("=" * 50)

    print("""
1. Repository Analysis Phase:
   python src/repository_analyzer.py https://github.com/user/repo

2. Pattern Extraction Phase:
   → Extracts architectural patterns
   → Identifies workflows
   → Analyzes file structure
   → Documents patterns

3. Command Generation Phase:
   python src/command_generator.py patterns.json --output commands.json

4. Command Integration Phase:
   → Commands are registered with Claude Code
   → Available as slash commands
   → Can be orchestrated together

5. Usage Examples:
   /setup-python-project --project-name my-app
   /setup-docker --base-image python:3.11-slim
   /setup-github-actions --deploy

6. Orchestration Examples:
   /create-full-project --name my-app --with-docker --with-ci
   /migrate-project --source repo --target new-repo
   /analyze-codebase --repository ./ --report detailed
""")


if __name__ == "__main__":
    # Demonstrate command generation
    demonstrate_command_generation()

    # Show command examples
    show_command_examples()

    # Show integration workflow
    show_integration_workflow()

    print("\\n" + "=" * 50)
    print("Command generation complete! Ready for integration with Claude Code.")