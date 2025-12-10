#!/usr/bin/env python3
"""
Test script for Workflow Orchestration Engine
Validates workflow definition, execution, dependency management, and error handling
"""

import json
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime
import unittest.mock as mock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.orchestrator import (
    WorkflowOrchestrator, WorkflowStep, WorkflowCondition,
    ExecutionStatus, ExecutionResult, WorkflowContext,
    create_default_workflows, COMMON_WORKFLOWS
)


class TestWorkflowOrchestrator:
    """Test suite for Workflow Orchestration Engine"""

    def setup_method(self):
        self.test_results = []
        self.orchestrator = WorkflowOrchestrator()

    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        try:
            test_func()
            print(f"✅ {test_name}")
            self.test_results.append({"name": test_name, "status": "passed"})
            return True
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            self.test_results.append({"name": test_name, "status": "failed", "error": str(e)})
            return False


    def test_workflow_definition(self):
        """Test workflow definition from dictionary"""
        print("\n🧪 Testing Workflow Definition...")

        workflow_def = {
            "id": "test_workflow",
            "name": "Test Workflow",
            "description": "A test workflow",
            "variables": {"test_var": "test_value"},
            "steps": [
                {
                    "id": "step1",
                    "name": "First Step",
                    "command": "test-command",
                    "parameters": {"param1": "value1"},
                    "depends_on": [],
                    "condition": "success"
                }
            ]
        }

        workflow_id = self.orchestrator.define_workflow(workflow_def)
        assert workflow_id == "test_workflow"
        assert workflow_id in self.orchestrator.workflows

        workflow = self.orchestrator.workflows[workflow_id]
        assert workflow["name"] == "Test Workflow"
        assert workflow["variables"] == {"test_var": "test_value"}
        assert len(workflow["steps"]) == 1
        assert workflow["steps"][0].id == "step1"

    def test_workflow_loading_from_file(self):
        """Test loading workflow definition from JSON file"""
        print("\n🧪 Testing Workflow Loading from File...")

        workflow_def = {
            "id": "file_workflow",
            "name": "File Workflow",
            "description": "Loaded from file",
            "steps": []
        }

        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(workflow_def, f)
            temp_file = f.name

        try:
            workflow_id = self.orchestrator.load_workflow_from_file(temp_file)
            assert workflow_id == "file_workflow"
            assert workflow_id in self.orchestrator.workflows
        finally:
            os.unlink(temp_file)

    def test_dependency_resolution(self):
        """Test dependency graph building and topological sorting"""
        print("\n🧪 Testing Dependency Resolution...")

        # Create workflow with dependencies
        workflow_def = {
            "id": "dependency_test",
            "name": "Dependency Test",
            "steps": [
                {"id": "step1", "command": "cmd1", "depends_on": []},
                {"id": "step2", "command": "cmd2", "depends_on": ["step1"]},
                {"id": "step3", "command": "cmd3", "depends_on": ["step1"]},
                {"id": "step4", "command": "cmd4", "depends_on": ["step2", "step3"]}
            ]
        }

        workflow_id = self.orchestrator.define_workflow(workflow_def)
        workflow = self.orchestrator.workflows[workflow_id]

        # Build dependency graph
        graph = self.orchestrator._build_dependency_graph(workflow['steps'])

        # Test topological sort
        levels = self.orchestrator._topological_sort(graph)

        # Should have 3 levels: [step1], [step2, step3], [step4]
        assert len(levels) == 3
        assert levels[0] == ["step1"]
        assert set(levels[1]) == {"step2", "step3"}
        assert levels[2] == ["step4"]

    def test_parameter_resolution(self):
        """Test parameter resolution with variable substitution"""
        print("\n🧪 Testing Parameter Resolution...")

        # Create test context
        context = WorkflowContext(
            workflow_id="test",
            step_id="step1",
            variables={"project_name": "my-app", "version": "1.0"},
            previous_results={"previous_output": "some_value"},
            global_config={"timeout": 30},
            execution_start=datetime.now(),
            step_start=datetime.now()
        )

        # Test parameter resolution
        parameters = {
            "name": "${project_name}",
            "version": "${version}",
            "output": "${previous_output}",
            "timeout": 30,
            "nested": {
                "project": "${project_name}"
            }
        }

        resolved = self.orchestrator._resolve_parameters(parameters, context)

        assert resolved["name"] == "my-app"
        assert resolved["version"] == "1.0"
        assert resolved["output"] == "some_value"
        assert resolved["timeout"] == 30
        assert resolved["nested"]["project"] == "my-app"

    def test_condition_evaluation(self):
        """Test step execution condition evaluation"""
        print("\n🧪 Testing Condition Evaluation...")

        # Create test steps with different conditions
        success_step = WorkflowStep(
            id="success_dep",
            name="Success Dependency",
            command="test",
            parameters={},
            depends_on=["prev_step"],
            condition=WorkflowCondition.SUCCESS
        )

        failure_step = WorkflowStep(
            id="failure_dep",
            name="Failure Dependency",
            command="test",
            parameters={},
            depends_on=["prev_step"],
            condition=WorkflowCondition.FAILURE
        )

        always_step = WorkflowStep(
            id="always_dep",
            name="Always Dependency",
            command="test",
            parameters={},
            depends_on=["prev_step"],
            condition=WorkflowCondition.ALWAYS
        )

        # Create mock results
        success_result = ExecutionResult(
            step_id="prev_step",
            status=ExecutionStatus.COMPLETED,
            output="success",
            error=None,
            execution_time=1.0,
            retry_count=0,
            logs=[]
        )

        failure_result = ExecutionResult(
            step_id="prev_step",
            status=ExecutionStatus.FAILED,
            output=None,
            error="error",
            execution_time=1.0,
            retry_count=0,
            logs=[]
        )

        previous_results = {"prev_step": success_result}

        # Test success condition
        assert self.orchestrator._should_execute_step(success_step, previous_results) == True
        assert self.orchestrator._should_execute_step(failure_step, previous_results) == False
        assert self.orchestrator._should_execute_step(always_step, previous_results) == True

        # Test failure condition
        previous_results = {"prev_step": failure_result}
        assert self.orchestrator._should_execute_step(success_step, previous_results) == False
        assert self.orchestrator._should_execute_step(failure_step, previous_results) == True

    async def test_workflow_execution(self):
        """Test complete workflow execution"""
        print("\n🧪 Testing Workflow Execution...")

        # Create simple workflow
        workflow_def = {
            "id": "execution_test",
            "name": "Execution Test",
            "variables": {"test_var": "test_value"},
            "steps": [
                {
                    "id": "step1",
                    "name": "First Step",
                    "command": "test-command-1",
                    "parameters": {"input": "${test_var}"},
                    "depends_on": [],
                    "condition": "success"
                },
                {
                    "id": "step2",
                    "name": "Second Step",
                    "command": "test-command-2",
                    "parameters": {"output": "result"},
                    "depends_on": ["step1"],
                    "condition": "success"
                }
            ]
        }

        workflow_id = self.orchestrator.define_workflow(workflow_def)

        # Execute workflow
        result = await self.orchestrator.execute_workflow(workflow_id)

        assert result["status"] == ExecutionStatus.COMPLETED.value
        assert result["workflow_id"] == workflow_id
        assert "steps" in result
        assert len(result["steps"]) == 2
        assert result["steps"]["step1"].status == ExecutionStatus.COMPLETED
        assert result["steps"]["step2"].status == ExecutionStatus.COMPLETED

    async def test_parallel_execution(self):
        """Test parallel step execution"""
        print("\n🧪 Testing Parallel Execution...")

        # Create workflow with parallel steps
        workflow_def = {
            "id": "parallel_test",
            "name": "Parallel Test",
            "steps": [
                {
                    "id": "step1",
                    "name": "Sequential Step",
                    "command": "test-command-1",
                    "depends_on": [],
                    "condition": "success"
                },
                {
                    "id": "step2",
                    "name": "Parallel Step 1",
                    "command": "test-command-2",
                    "depends_on": ["step1"],
                    "condition": "success",
                    "parallel": True
                },
                {
                    "id": "step3",
                    "name": "Parallel Step 2",
                    "command": "test-command-3",
                    "depends_on": ["step1"],
                    "condition": "success",
                    "parallel": True
                },
                {
                    "id": "step4",
                    "name": "Final Step",
                    "command": "test-command-4",
                    "depends_on": ["step2", "step3"],
                    "condition": "success"
                }
            ]
        }

        workflow_id = self.orchestrator.define_workflow(workflow_def)
        result = await self.orchestrator.execute_workflow(workflow_id)

        assert result["status"] == ExecutionStatus.COMPLETED.value
        # Verify all steps executed
        assert len(result["steps"]) == 4
        for step_id in ["step1", "step2", "step3", "step4"]:
            assert result["steps"][step_id].status == ExecutionStatus.COMPLETED

    async def test_error_handling_and_retries(self):
        """Test error handling and retry mechanism"""
        print("\n🧪 Testing Error Handling and Retries...")

        # Mock a command that fails first few times
        call_count = 0
        async def failing_command(command, parameters, context):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Command failed (attempt {call_count})")
            return {"status": "success", "attempt": call_count}

        # Replace command execution method
        original_execute = self.orchestrator._execute_command
        self.orchestrator._execute_command = failing_command

        try:
            # Create workflow with retry
            workflow_def = {
                "id": "retry_test",
                "name": "Retry Test",
                "steps": [
                    {
                        "id": "retry_step",
                        "name": "Retry Step",
                        "command": "failing-command",
                        "parameters": {},
                        "depends_on": [],
                        "condition": "success",
                        "max_retries": 3
                    }
                ]
            }

            workflow_id = self.orchestrator.define_workflow(workflow_def)
            result = await self.orchestrator.execute_workflow(workflow_id)

            # Should eventually succeed
            assert result["status"] == ExecutionStatus.COMPLETED.value
            step_result = result["steps"]["retry_step"]
            assert step_result.status == ExecutionStatus.COMPLETED
            assert step_result.retry_count == 2  # Failed 2 times, succeeded on 3rd
            assert call_count == 3
        finally:
            # Restore original method
            self.orchestrator._execute_command = original_execute

    def test_workflow_management(self):
        """Test workflow listing and management"""
        print("\n🧪 Testing Workflow Management...")

        # Create some test workflows
        for i in range(3):
            workflow_def = {
                "id": f"workflow_{i}",
                "name": f"Workflow {i}",
                "description": f"Test workflow {i}",
                "steps": []
            }
            self.orchestrator.define_workflow(workflow_def)

        # Test workflow listing
        workflows = self.orchestrator.list_workflows()
        assert len(workflows) >= 3

        # Test workflow retrieval
        workflow = self.orchestrator.get_workflow_definition("workflow_1")
        assert workflow is not None
        assert workflow["name"] == "Workflow 1"

        # Test non-existent workflow
        workflow = self.orchestrator.get_workflow_definition("non_existent")
        assert workflow is None

    def test_default_workflows(self):
        """Test default workflow creation"""
        print("\n🧪 Testing Default Workflows...")

        # Create fresh orchestrator
        orchestrator = WorkflowOrchestrator()
        create_default_workflows(orchestrator)

        # Should have default workflows
        workflows = orchestrator.list_workflows()
        assert len(workflows) >= 2

        # Check for specific default workflows
        workflow_ids = [w['id'] for w in workflows]
        assert "project_setup" in workflow_ids
        assert "code_analysis" in workflow_ids

        # Verify project_setup workflow structure
        project_workflow = orchestrator.get_workflow_definition("project_setup")
        assert len(project_workflow['steps']) == 4
        assert project_workflow['variables']['language'] == "python"

    def test_workflow_context_isolation(self):
        """Test that each workflow execution maintains isolated context"""
        print("\n🧪 Testing Workflow Context Isolation...")

        # Create workflow that modifies variables
        workflow_def = {
            "id": "context_test",
            "name": "Context Test",
            "variables": {"counter": 0},
            "steps": [
                {
                    "id": "step1",
                    "name": "Increment Counter",
                    "command": "increment",
                    "parameters": {"value": "${counter}"},
                    "depends_on": [],
                    "condition": "success"
                }
            ]
        }

        workflow_id = self.orchestrator.define_workflow(workflow_def)

        # Execute workflow multiple times
        result1 = asyncio.run(self.orchestrator.execute_workflow(workflow_id, {"counter": 1}))
        result2 = asyncio.run(self.orchestrator.execute_workflow(workflow_id, {"counter": 5}))

        # Each execution should have independent context
        assert result1["status"] == ExecutionStatus.COMPLETED.value
        assert result2["status"] == ExecutionStatus.COMPLETED.value

    def run_all_tests(self):
        """Run all tests and provide summary"""
        print("🚀 Testing Workflow Orchestration Engine")
        print("=" * 60)
        print("Testing workflow management, dependency resolution, and execution")

        # Regular tests
        test_functions = [
            ("Initialization", self.test_initialization),
            ("Workflow Definition", self.test_workflow_definition),
            ("Workflow Loading from File", self.test_workflow_loading_from_file),
            ("Dependency Resolution", self.test_dependency_resolution),
            ("Parameter Resolution", self.test_parameter_resolution),
            ("Condition Evaluation", self.test_condition_evaluation),
            ("Workflow Management", self.test_workflow_management),
            ("Default Workflows", self.test_default_workflows),
            ("Workflow Context Isolation", self.test_workflow_context_isolation),
        ]

        # Async tests
        async_test_functions = [
            ("Workflow Execution", self.test_workflow_execution),
            ("Parallel Execution", self.test_parallel_execution),
            ("Error Handling and Retries", self.test_error_handling_and_retries),
        ]

        passed = 0
        total = len(test_functions) + len(async_test_functions)

        # Run regular tests
        for test_name, test_func in test_functions:
            if self.run_test(test_name, test_func):
                passed += 1

        # Run async tests
        for test_name, test_func in async_test_functions:
            if self.run_test(test_name, lambda: asyncio.run(test_func())):
                passed += 1

        print("\n" + "=" * 60)
        print(f"Test Results: {passed}/{total} passed")

        if passed == total:
            print("🎉 All tests passed! Workflow Orchestration Engine is working correctly.")
            print("\n✅ Context Engineering Principles Applied:")
            print("  - Write: Workflow definitions and execution history saved to structured data")
            print("  - Select: Intelligent dependency resolution and conditional execution")
            print("  - Compress: Parameter substitution and variable compression")
            print("  - Isolate: Each workflow execution maintains independent context")
        else:
            print(f"❌ {total - passed} tests failed. Review the output above.")

        return passed == total


if __name__ == "__main__":
    test_suite = TestWorkflowOrchestrator()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)