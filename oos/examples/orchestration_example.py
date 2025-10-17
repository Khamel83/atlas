#!/usr/bin/env python3
"""
Example usage of the Command Orchestration & Workflow Engine
"""

import json
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestrator import WorkflowOrchestrator, create_default_workflows


async def demonstrate_orchestration():
    """Demonstrate workflow orchestration capabilities"""
    print("Command Orchestration & Workflow Engine Demo")
    print("=" * 50)

    # Initialize orchestrator
    orchestrator = WorkflowOrchestrator()
    create_default_workflows(orchestrator)

    # List available workflows
    workflows = orchestrator.list_workflows()
    print(f"\\nAvailable workflows ({len(workflows)}):")
    for workflow in workflows:
        print(f"  {workflow['id']}: {workflow['name']} ({workflow['steps_count']} steps)")

    # Demonstrate project setup workflow
    print("\\n" + "=" * 50)
    print("Executing Project Setup Workflow")
    print("=" * 50)

    variables = {
        "project_name": "demo-project",
        "language": "python",
        "include_docker": True,
        "include_ci": True,
        "include_docs": True,
        "include_tests": True
    }

    print(f"\\nVariables: {json.dumps(variables, indent=2)}")

    # Execute workflow
    result = await orchestrator.execute_workflow("project_setup", variables)

    print(f"\\nWorkflow execution result:")
    print(f"Status: {result['status']}")
    print(f"Execution ID: {result['execution_id']}")
    print(f"Start time: {result['start_time']}")
    print(f"End time: {result['end_time']}")

    if 'results' in result:
        print("\\nStep results:")
        for step_id, step_result in result['results'].items():
            print(f"  {step_id}: {step_result.status.value} "
                  f"({step_result.execution_time:.2f}s)")

    # Demonstrate code analysis workflow
    print("\\n" + "=" * 50)
    print("Executing Code Analysis Workflow")
    print("=" * 50)

    analysis_variables = {
        "repository_path": ".",
        "output_format": "json",
        "include_security": True,
        "include_performance": True,
        "include_quality": True
    }

    print(f"\\nVariables: {json.dumps(analysis_variables, indent=2)}")

    # Execute workflow
    analysis_result = await orchestrator.execute_workflow("code_analysis", analysis_variables)

    print(f"\\nAnalysis workflow result:")
    print(f"Status: {analysis_result['status']}")
    print(f"Execution ID: {analysis_result['execution_id']}")

    if 'results' in analysis_result:
        print("\\nAnalysis step results:")
        for step_id, step_result in analysis_result['results'].items():
            print(f"  {step_id}: {step_result.status.value} "
                  f"({step_result.execution_time:.2f}s)")


def demonstrate_custom_workflow():
    """Demonstrate custom workflow creation"""
    print("\\n" + "=" * 50)
    print("Custom Workflow Creation")
    print("=" * 50)

    # Create custom workflow definition
    custom_workflow = {
        "id": "custom_deployment",
        "name": "Custom Deployment Pipeline",
        "description": "Custom deployment workflow with testing and monitoring",
        "variables": {
            "environment": "staging",
            "service_name": "my-service",
            "version": "1.0.0"
        },
        "steps": [
            {
                "id": "run_tests",
                "name": "Run Unit Tests",
                "command": "run-tests",
                "parameters": {
                    "environment": "${environment}",
                    "coverage": true
                },
                "depends_on": [],
                "condition": "success",
                "timeout": 120
            },
            {
                "id": "build_artifact",
                "name": "Build Deployment Artifact",
                "command": "build-artifact",
                "parameters": {
                    "service_name": "${service_name}",
                    "version": "${version}"
                },
                "depends_on": ["run_tests"],
                "condition": "success",
                "timeout": 180
            },
            {
                "id": "deploy_service",
                "name": "Deploy Service",
                "command": "deploy-service",
                "parameters": {
                    "service_name": "${service_name}",
                    "environment": "${environment}",
                    "version": "${version}"
                },
                "depends_on": ["build_artifact"],
                "condition": "success",
                "timeout": 300
            },
            {
                "id": "health_check",
                "name": "Perform Health Check",
                "command": "health-check",
                "parameters": {
                    "service_name": "${service_name}",
                    "environment": "${environment}"
                },
                "depends_on": ["deploy_service"],
                "condition": "success",
                "timeout": 60
            }
        ]
    }

    # Initialize orchestrator and define workflow
    orchestrator = WorkflowOrchestrator()
    workflow_id = orchestrator.define_workflow(custom_workflow)

    print(f"Created custom workflow: {workflow_id}")

    # Show workflow definition
    workflow_def = orchestrator.get_workflow_definition(workflow_id)
    print(f"\\nWorkflow definition:")
    print(f"Name: {workflow_def['name']}")
    print(f"Description: {workflow_def['description']}")
    print(f"Steps: {len(workflow_def['steps'])}")

    for step in workflow_def['steps']:
        print(f"  - {step['id']}: {step['command']} "
              f"(depends on: {step['depends_on']})")


def demonstrate_workflow_features():
    """Demonstrate advanced workflow features"""
    print("\\n" + "=" * 50)
    print("Advanced Workflow Features")
    print("=" * 50)

    features = [
        {
            "feature": "Parallel Execution",
            "description": "Multiple steps can run simultaneously when dependencies allow",
            "example": "linting, security scan, and performance analysis can run in parallel"
        },
        {
            "feature": "Conditional Execution",
            "description": "Steps can execute based on success/failure of previous steps",
            "example": "deployment only runs if tests pass"
        },
        {
            "feature": "Parameter Passing",
            "description": "Output from one step can be used as input to subsequent steps",
            "example": "build output version passed to deployment step"
        },
        {
            "feature": "Error Handling",
            "description": "Automatic retries and error recovery mechanisms",
            "example": "failed steps retry with exponential backoff"
        },
        {
            "feature": "Variable Substitution",
            "description": "Dynamic parameter values using variables and expressions",
            "example": "base_image selected based on project language"
        },
        {
            "feature": "Progress Tracking",
            "description": "Real-time status updates and execution monitoring",
            "example": "track workflow progress with execution IDs"
        }
    ]

    for feature in features:
        print(f"\\n{feature['feature']}:")
        print(f"  Description: {feature['description']}")
        print(f"  Example: {feature['example']}")


def show_integration_examples():
    """Show how orchestrator integrates with other systems"""
    print("\\n" + "=" * 50)
    print("Integration Examples")
    print("=" * 50)

    print("""
1. Integration with Repository Analysis:
   - Analysis results trigger workflow execution
   - Workflows adapt based on repository characteristics
   - Automated workflow generation from patterns

2. Integration with Command Generation:
   - Generated commands become workflow steps
   - Command parameters map to workflow variables
   - Command execution within workflow context

3. Integration with Claude Code:
   - Workflows executed as slash commands
   - Interactive workflow modification
   - Real-time status reporting

4. Integration with Learning System:
   - Workflows improve based on execution results
   - Automatic optimization of step ordering
   - Adaptive parameter tuning

Example Usage in Claude Code:
  /execute-workflow --id project_setup --variables '{"project_name": "my-app", "language": "python"}'
  /execute-workflow --id code_analysis --variables '{"repository_path": "./", "include_security": true}'
  /list-workflows
  /workflow-status --execution-id abc123
""")


async def main():
    """Main demonstration function"""
    # Demonstrate orchestration
    await demonstrate_orchestration()

    # Demonstrate custom workflow creation
    demonstrate_custom_workflow()

    # Show advanced features
    demonstrate_workflow_features()

    # Show integration examples
    show_integration_examples()

    print("\\n" + "=" * 50)
    print("Orchestration demonstration complete!")
    print("Workflows can be combined with repository analysis and command generation")
    print("to create powerful automation within Claude Code.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())