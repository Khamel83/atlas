#!/usr/bin/env python3
"""
Command Orchestration & Workflow Engine

Intelligent system for chaining slash commands together with conditional logic,
parameter passing, error handling, and parallel execution capabilities.
"""

import json
import yaml
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import logging
from datetime import datetime
import traceback


class ExecutionStatus(Enum):
    """Execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class WorkflowCondition(Enum):
    """Workflow condition types"""
    SUCCESS = "success"
    FAILURE = "failure"
    ALWAYS = "always"
    CUSTOM = "custom"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    id: str
    name: str
    command: str
    parameters: Dict[str, Any]
    depends_on: List[str]
    condition: WorkflowCondition
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    parallel: bool = False
    description: str = ""


@dataclass
class WorkflowContext:
    """Execution context for workflow steps"""
    workflow_id: str
    step_id: str
    variables: Dict[str, Any]
    previous_results: Dict[str, Any]
    global_config: Dict[str, Any]
    execution_start: datetime
    step_start: datetime


@dataclass
class ExecutionResult:
    """Result of a workflow step execution"""
    step_id: str
    status: ExecutionStatus
    output: Any
    error: Optional[str]
    execution_time: float
    retry_count: int
    logs: List[str]


class WorkflowOrchestrator:
    """Main orchestrator class for managing command workflows"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.workflows = {}
        self.execution_history = {}
        self.variable_store = {}
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the orchestrator"""
        logger = logging.getLogger('orchestrator')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def define_workflow(self, workflow_definition: Dict[str, Any]) -> str:
        """Define a new workflow from definition"""
        workflow_id = workflow_definition.get('id', str(uuid.uuid4()))

        workflow = {
            'id': workflow_id,
            'name': workflow_definition.get('name', workflow_id),
            'description': workflow_definition.get('description', ''),
            'version': workflow_definition.get('version', '1.0'),
            'steps': [],
            'variables': workflow_definition.get('variables', {}),
            'global_config': workflow_definition.get('config', {}),
            'created_at': datetime.now().isoformat()
        }

        # Parse steps
        for step_def in workflow_definition.get('steps', []):
            step = WorkflowStep(
                id=step_def.get('id', str(uuid.uuid4())),
                name=step_def.get('name', ''),
                command=step_def.get('command', ''),
                parameters=step_def.get('parameters', {}),
                depends_on=step_def.get('depends_on', []),
                condition=WorkflowCondition(step_def.get('condition', 'success')),
                timeout=step_def.get('timeout'),
                retry_count=0,
                max_retries=step_def.get('max_retries', 3),
                parallel=step_def.get('parallel', False),
                description=step_def.get('description', '')
            )
            workflow['steps'].append(step)

        self.workflows[workflow_id] = workflow
        self.logger.info(f"Defined workflow: {workflow['name']} ({workflow_id})")

        return workflow_id

    def load_workflow_from_file(self, file_path: str) -> str:
        """Load workflow definition from file"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")

        with open(path, 'r') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                definition = yaml.safe_load(f)
            else:
                definition = json.load(f)

        return self.define_workflow(definition)

    async def execute_workflow(self, workflow_id: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a workflow with given variables"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow = self.workflows[workflow_id]
        execution_id = str(uuid.uuid4())

        execution_context = {
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'workflow_name': workflow['name'],
            'start_time': datetime.now().isoformat(),
            'variables': {**workflow['variables'], **(variables or {})},
            'status': ExecutionStatus.RUNNING.value,
            'steps': {}
        }

        self.execution_history[execution_id] = execution_context

        try:
            # Execute workflow steps
            results = await self._execute_workflow_steps(workflow, execution_context)

            execution_context['status'] = ExecutionStatus.COMPLETED.value
            execution_context['results'] = results
            execution_context['steps'] = results
            execution_context['end_time'] = datetime.now().isoformat()

            self.logger.info(f"Workflow {workflow['name']} completed successfully")

        except Exception as e:
            execution_context['status'] = ExecutionStatus.FAILED.value
            execution_context['error'] = str(e)
            execution_context['end_time'] = datetime.now().isoformat()

            self.logger.error(f"Workflow {workflow['name']} failed: {e}")

        return execution_context

    async def _execute_workflow_steps(self, workflow: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, ExecutionResult]:
        """Execute all steps in a workflow"""
        steps = workflow['steps']
        results = {}

        # Create step ID to step object mapping
        step_map = {step.id: step for step in steps}

        # Build dependency graph
        dependency_graph = self._build_dependency_graph(steps)

        # Execute steps in order
        for step_level in self._topological_sort(dependency_graph):
            if len(step_level) > 1:
                # Execute parallel steps
                parallel_results = await asyncio.gather(*[
                    self._execute_step(step_map[step_id], workflow, context, results)
                    for step_id in step_level
                ])
                for result in parallel_results:
                    results[result.step_id] = result
            else:
                # Execute single step
                step_id = step_level[0]
                result = await self._execute_step(step_map[step_id], workflow, context, results)
                results[result.step_id] = result

        return results

    async def _execute_step(self, step: WorkflowStep, workflow: Dict[str, Any],
                          context: Dict[str, Any], previous_results: Dict[str, ExecutionResult]) -> ExecutionResult:
        """Execute a single workflow step"""
        step_context = WorkflowContext(
            workflow_id=workflow['id'],
            step_id=step.id,
            variables=context['variables'],
            previous_results={k: v.output for k, v in previous_results.items()},
            global_config=workflow['global_config'],
            execution_start=datetime.now(),
            step_start=datetime.now()
        )

        # Check if step should be executed based on conditions
        if not self._should_execute_step(step, previous_results):
            return ExecutionResult(
                step_id=step.id,
                status=ExecutionStatus.SKIPPED,
                output=None,
                error=None,
                execution_time=0.0,
                retry_count=0,
                logs=["Step skipped due to condition"]
            )

        # Execute step with retries
        for attempt in range(step.max_retries + 1):
            try:
                start_time = datetime.now()

                # Resolve parameters
                resolved_params = self._resolve_parameters(step.parameters, step_context)

                # Execute command
                output = await self._execute_command(step.command, resolved_params, step_context)

                execution_time = (datetime.now() - start_time).total_seconds()

                return ExecutionResult(
                    step_id=step.id,
                    status=ExecutionStatus.COMPLETED,
                    output=output,
                    error=None,
                    execution_time=execution_time,
                    retry_count=attempt,
                    logs=[f"Command {step.command} executed successfully"]
                )

            except Exception as e:
                error_msg = str(e)
                execution_time = (datetime.now() - start_time).total_seconds()

                if attempt < step.max_retries:
                    self.logger.warning(f"Step {step.id} failed (attempt {attempt + 1}/{step.max_retries}): {error_msg}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"Step {step.id} failed after {step.max_retries + 1} attempts: {error_msg}")

                    return ExecutionResult(
                        step_id=step.id,
                        status=ExecutionStatus.FAILED,
                        output=None,
                        error=error_msg,
                        execution_time=execution_time,
                        retry_count=attempt,
                        logs=[f"Command failed: {error_msg}"]
                    )

    def _should_execute_step(self, step: WorkflowStep, previous_results: Dict[str, ExecutionResult]) -> bool:
        """Determine if a step should be executed based on conditions"""
        if not step.depends_on:
            return True

        for dep_id in step.depends_on:
            if dep_id not in previous_results:
                return False

            dep_result = previous_results[dep_id]

            if step.condition == WorkflowCondition.SUCCESS:
                if dep_result.status != ExecutionStatus.COMPLETED:
                    return False
            elif step.condition == WorkflowCondition.FAILURE:
                if dep_result.status != ExecutionStatus.FAILED:
                    return False
            elif step.condition == WorkflowCondition.CUSTOM:
                # Custom condition evaluation would go here
                pass

        return True

    def _resolve_parameters(self, parameters: Dict[str, Any], context: WorkflowContext) -> Dict[str, Any]:
        """Resolve parameters with variable substitution"""
        resolved = {}

        for key, value in parameters.items():
            if isinstance(value, str):
                # Variable substitution
                if value.startswith('${') and value.endswith('}'):
                    var_name = value[2:-1]
                    resolved[key] = context.variables.get(var_name,
                                     context.previous_results.get(var_name, value))
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = self._resolve_parameters(value, context)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_parameters(item, context) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved

    async def _execute_command(self, command: str, parameters: Dict[str, Any],
                            context: WorkflowContext) -> Any:
        """Execute a single command"""
        # This would integrate with Claude Code command execution
        # For now, simulate command execution

        self.logger.info(f"Executing command: {command} with parameters: {parameters}")

        # Simulate command execution
        await asyncio.sleep(0.1)  # Simulate processing time

        # Return mock result
        return {
            'command': command,
            'parameters': parameters,
            'result': 'success',
            'timestamp': datetime.now().isoformat()
        }

    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> Dict[str, List[str]]:
        """Build dependency graph from steps"""
        graph = {}

        # Initialize all steps in graph
        for step in steps:
            graph[step.id] = []

        # Build edges: step depends on dep_id means edge from dep_id to step
        for step in steps:
            for dep_id in step.depends_on:
                if dep_id in graph:
                    graph[dep_id].append(step.id)

        return graph

    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Topological sort with level detection for parallel execution"""
        in_degree = {node: 0 for node in graph}

        # Calculate in-degrees
        for node in graph:
            for neighbor in graph[node]:
                if neighbor in in_degree:
                    in_degree[neighbor] += 1

        # Find nodes with no incoming edges
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []

        while queue:
            level = queue[:]
            queue = []
            result.append(level)

            for node in level:
                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        return result

    def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow execution"""
        return self.execution_history.get(execution_id)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all defined workflows"""
        return [
            {
                'id': workflow['id'],
                'name': workflow['name'],
                'description': workflow['description'],
                'version': workflow['version'],
                'steps_count': len(workflow['steps']),
                'created_at': workflow['created_at']
            }
            for workflow in self.workflows.values()
        ]

    def get_workflow_definition(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow definition"""
        return self.workflows.get(workflow_id)


# Pre-defined workflows
COMMON_WORKFLOWS = {
    "project_setup": {
        "id": "project_setup",
        "name": "Complete Project Setup",
        "description": "Set up a new project with all necessary components",
        "variables": {
            "project_name": "",
            "language": "python",
            "include_docker": True,
            "include_ci": True,
            "include_docs": True
        },
        "steps": [
            {
                "id": "setup_project",
                "name": "Initialize Project",
                "command": "setup-${language}-project",
                "parameters": {
                    "project_name": "${project_name}"
                },
                "depends_on": [],
                "condition": "success"
            },
            {
                "id": "setup_docker",
                "name": "Add Docker Support",
                "command": "setup-docker",
                "parameters": {
                    "include_compose": True
                },
                "depends_on": ["setup_project"],
                "condition": "success",
                "parallel": False
            },
            {
                "id": "setup_ci",
                "name": "Set up CI/CD",
                "command": "setup-github-actions",
                "parameters": {
                    "deploy": False
                },
                "depends_on": ["setup_project"],
                "condition": "success",
                "parallel": True
            },
            {
                "id": "setup_docs",
                "name": "Generate Documentation",
                "command": "generate-documentation",
                "parameters": {},
                "depends_on": ["setup_project"],
                "condition": "success",
                "parallel": True
            }
        ]
    },

    "code_analysis": {
        "id": "code_analysis",
        "name": "Comprehensive Code Analysis",
        "description": "Analyze codebase for issues, patterns, and metrics",
        "variables": {
            "repository_path": ".",
            "output_format": "json",
            "include_security": True,
            "include_performance": True
        },
        "steps": [
            {
                "id": "lint_code",
                "name": "Run Linter",
                "command": "lint-code",
                "parameters": {
                    "path": "${repository_path}"
                },
                "depends_on": [],
                "condition": "success"
            },
            {
                "id": "security_scan",
                "name": "Security Analysis",
                "command": "security-scan",
                "parameters": {
                    "path": "${repository_path}"
                },
                "depends_on": [],
                "condition": "success",
                "parallel": True
            },
            {
                "id": "performance_analysis",
                "name": "Performance Analysis",
                "command": "analyze-performance",
                "parameters": {
                    "path": "${repository_path}"
                },
                "depends_on": [],
                "condition": "success",
                "parallel": True
            },
            {
                "id": "generate_report",
                "name": "Generate Analysis Report",
                "command": "generate-analysis-report",
                "parameters": {
                    "format": "${output_format}"
                },
                "depends_on": ["lint_code", "security_scan", "performance_analysis"],
                "condition": "success"
            }
        ]
    }
}


def create_default_workflows(orchestrator: WorkflowOrchestrator):
    """Create default workflows"""
    for workflow_def in COMMON_WORKFLOWS.values():
        orchestrator.define_workflow(workflow_def)


async def main():
    """Main function for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Command Orchestration Engine')
    parser.add_argument('--workflow', '-w', help='Workflow file path')
    parser.add_argument('--list', '-l', action='store_true', help='List available workflows')
    parser.add_argument('--execute', '-e', help='Execute workflow by ID')
    parser.add_argument('--variables', '-v', help='Variables as JSON string')
    parser.add_argument('--status', '-s', help='Check execution status')

    args = parser.parse_args()

    orchestrator = WorkflowOrchestrator()
    create_default_workflows(orchestrator)

    if args.list:
        workflows = orchestrator.list_workflows()
        print("Available workflows:")
        for workflow in workflows:
            print(f"  {workflow['id']}: {workflow['name']} ({workflow['steps_count']} steps)")

    elif args.workflow:
        workflow_id = orchestrator.load_workflow_from_file(args.workflow)
        print(f"Loaded workflow: {workflow_id}")

    elif args.execute:
        variables = json.loads(args.variables) if args.variables else {}
        result = await orchestrator.execute_workflow(args.execute, variables)
        print(f"Workflow execution result: {result}")

    elif args.status:
        status = orchestrator.get_workflow_status(args.status)
        print(f"Execution status: {status}")


if __name__ == '__main__':
    asyncio.run(main())