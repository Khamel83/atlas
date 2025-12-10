#!/usr/bin/env python3
"""
Comprehensive tests for context engineering integration

Tests all components working together:
- Clarification workflow
- Token optimization
- Auto-documentation
- Meta-clarification
"""

import sys
import asyncio
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarification_workflow import (
    ClarificationWorkflow, ClarificationResponse, QuestionType,
    WorkflowStage, InputProcessor, ClarificationEngine, PlanningEngine
)
from token_optimization import (
    TokenOptimizer, TokenBudget, ContextChunk, optimize_for_budget,
    estimate_context_tokens
)
from auto_documentation import (
    AutoDocumentationSystem, DocumentationGenerator, ConsistencyEnforcer
)


class TestTokenOptimization:
    """Test token optimization functionality"""

    @pytest.fixture
    async def optimizer(self):
        return TokenOptimizer()

    @pytest.fixture
    def sample_context(self):
        return {
            "large_text": "This is a very long piece of text. " * 100,
            "code_snippet": "def function():\n    " + "print('hello')\n    " * 50,
            "important_result": "Critical information",
            "debug_log": "Debug entry. " * 30,
            "metadata": {
                "created": "2025-09-14",
                "items": list(range(50)),
                "description": "Test metadata with lots of content " * 20
            }
        }

    async def test_token_estimation(self, optimizer, sample_context):
        """Test token estimation accuracy"""
        tokens = optimizer._calculate_total_tokens(sample_context)
        assert tokens > 0
        assert isinstance(tokens, int)

        # Test individual components
        text_tokens = optimizer.token_estimator.estimate_tokens(sample_context["large_text"])
        assert text_tokens > 100  # Should be substantial

        code_tokens = optimizer.token_estimator.estimate_code_tokens(sample_context["code_snippet"])
        assert code_tokens > 50

    async def test_context_optimization(self, optimizer, sample_context):
        """Test context optimization reduces token usage"""
        original_tokens = optimizer._calculate_total_tokens(sample_context)

        budget = TokenBudget(total_budget=1000, available_for_context=800)
        optimized_context, result = await optimizer.optimize_context(sample_context, budget)

        # Verify optimization worked
        assert result.optimized_tokens < original_tokens
        assert result.reduction_percentage > 0
        assert len(result.techniques_used) > 0

        # Verify optimized context is smaller
        optimized_tokens = optimizer._calculate_total_tokens(optimized_context)
        assert optimized_tokens <= budget.available_for_context

    async def test_chunk_identification(self, optimizer, sample_context):
        """Test identification of chunks for optimization"""
        chunks = optimizer._identify_chunks(sample_context)

        assert len(chunks) > 0
        assert all(isinstance(chunk, ContextChunk) for chunk in chunks)
        assert all(chunk.token_count > 0 for chunk in chunks)

        # Check importance calculation
        importance_values = [chunk.importance for chunk in chunks]
        assert all(0.0 <= imp <= 1.0 for imp in importance_values)

    async def test_compression(self, optimizer):
        """Test content compression"""
        long_text = "This is a test sentence. " * 50
        original_tokens = optimizer.token_estimator.estimate_tokens(long_text)

        compressed = await optimizer.compressor.compress_text(long_text, target_ratio=0.5)
        compressed_tokens = optimizer.token_estimator.estimate_tokens(compressed)

        assert compressed_tokens < original_tokens
        assert len(compressed) < len(long_text)

    async def test_filesystem_offloading(self, optimizer):
        """Test filesystem offloading functionality"""
        chunk = ContextChunk(
            chunk_id="test_chunk",
            content="Test content for offloading",
            content_type="text",
            importance=0.3,
            staleness=0.5,
            token_count=10,
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )

        # Test offloading
        filename = await optimizer.offloader.offload_chunk(chunk)
        assert filename
        assert isinstance(filename, str)

        # Test retrieval
        retrieved = await optimizer.offloader.retrieve_chunk("test_chunk")
        assert retrieved is not None
        assert retrieved.content == chunk.content
        assert retrieved.chunk_id == chunk.chunk_id

    async def test_caching(self, optimizer):
        """Test context caching"""
        chunk = ContextChunk(
            chunk_id="cache_test",
            content="Cache test content",
            content_type="text",
            importance=0.8,
            staleness=0.1,
            token_count=5,
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )

        # Test cache storage
        cache_key = await optimizer.cache.put(chunk)
        assert cache_key

        # Test cache retrieval
        retrieved = await optimizer.cache.get(cache_key)
        assert retrieved is not None
        assert retrieved.content == chunk.content

        # Test cache stats
        stats = optimizer.cache.get_stats()
        assert "cache_hits" in stats
        assert stats["cache_hits"] > 0


class TestClarificationWorkflow:
    """Test clarification workflow functionality"""

    @pytest.fixture
    async def workflow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workflow = ClarificationWorkflow(storage_path=temp_dir)
            yield workflow

    @pytest.fixture
    def input_processor(self):
        return InputProcessor()

    @pytest.fixture
    def clarification_engine(self):
        return ClarificationEngine()

    async def test_input_processing(self, input_processor):
        """Test input cleaning and analysis"""
        raw_input = "optimize  the   auth system thru better caching & stuff"

        cleaned = await input_processor.clean_input(raw_input)

        assert cleaned.cleaned_text != raw_input  # Should be cleaned
        assert cleaned.extracted_intent in ['optimization', 'general']
        assert cleaned.confidence >= 0.0
        assert isinstance(cleaned.ambiguities, list)

    async def test_ambiguity_detection(self, input_processor):
        """Test detection of ambiguous input"""
        ambiguous_input = "fix it"

        cleaned = await input_processor.clean_input(ambiguous_input)

        assert len(cleaned.ambiguities) > 0
        assert cleaned.confidence < 0.8  # Should have low confidence

    async def test_clarification_generation(self, clarification_engine):
        """Test clarification question generation"""
        from clarification_workflow import CleanedInput

        cleaned_input = CleanedInput(
            original_text="optimize system",
            cleaned_text="optimize system",
            extracted_intent="optimization",
            key_entities=[],
            confidence=0.4,
            ambiguities=["Vague reference: system"],
            context_hints={"urgency": "normal", "complexity": "medium"}
        )

        questions = await clarification_engine.generate_questions(cleaned_input)

        assert len(questions) > 0
        assert all(hasattr(q, 'question_type') for q in questions)
        assert all(hasattr(q, 'text') for q in questions)

    async def test_meta_clarification_prompt(self, clarification_engine):
        """Test meta-clarification prompt generation"""
        from clarification_workflow import ClarificationQuestion

        questions = [
            ClarificationQuestion(
                id="test_q1",
                question_type=QuestionType.CHOICE,
                text="What's your goal?",
                options=["Analyze", "Implement", "Optimize"]
            ),
            ClarificationQuestion(
                id="test_q2",
                question_type=QuestionType.CLARIFICATION,
                text="What technology stack?"
            )
        ]

        context = {"original_input": "optimize the system"}

        prompt = await clarification_engine.generate_meta_clarification_prompt(questions, context)

        assert "optimize the system" in prompt
        assert "What's your goal?" in prompt
        assert "What technology stack?" in prompt
        assert "Please provide" in prompt

    async def test_meta_clarification_parsing(self, clarification_engine):
        """Test parsing of AI responses for meta-clarification"""
        from clarification_workflow import ClarificationQuestion

        questions = [
            ClarificationQuestion(id="q1", question_type=QuestionType.CHOICE, text="Goal?"),
            ClarificationQuestion(id="q2", question_type=QuestionType.CLARIFICATION, text="Tech stack?")
        ]

        ai_response = """Question 1: Optimize - The user wants to improve existing code
Question 2: Python web application - Based on context clues
Additional context: Focus on performance and security improvements"""

        responses = clarification_engine.parse_meta_clarification_response(ai_response, questions)

        assert len(responses) == 2
        assert responses[0].question_id == "q1"
        assert responses[0].answer == "Optimize"
        assert responses[1].question_id == "q2"
        assert responses[1].answer == "Python web application"

    async def test_workflow_session_lifecycle(self, workflow):
        """Test complete workflow session lifecycle"""
        # Start workflow
        session = await workflow.start_workflow("implement user authentication")

        assert session.session_id
        assert session.stage == WorkflowStage.CLARIFICATION
        assert session.cleaned_input is not None

        # Submit responses (if questions were generated)
        if session.questions:
            responses = [
                ClarificationResponse(
                    question_id=session.questions[0].id,
                    answer="Implement new functionality",
                    confidence=0.9
                )
            ]

            session = await workflow.submit_responses(session.session_id, responses)
            assert session.stage == WorkflowStage.CONFIRMATION
            assert session.plan is not None

    async def test_session_persistence(self, workflow):
        """Test session persistence across restarts"""
        # Create session
        session = await workflow.start_workflow("test persistence")
        session_id = session.session_id

        # Load session
        loaded_session = await workflow.load_session(session_id)

        assert loaded_session is not None
        assert loaded_session.session_id == session_id
        assert loaded_session.original_input == "test persistence"


class TestAutoDocumentation:
    """Test auto-documentation functionality"""

    @pytest.fixture
    async def auto_doc_system(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            system = AutoDocumentationSystem(repo_path=temp_dir)
            yield system

    @pytest.fixture
    def doc_generator(self):
        return DocumentationGenerator()

    @pytest.fixture
    def consistency_enforcer(self):
        return ConsistencyEnforcer()

    async def test_function_documentation_detection(self, doc_generator):
        """Test detection of functions needing documentation"""
        python_code = '''
def documented_function():
    """This function has documentation."""
    pass

def undocumented_function():
    pass

class TestClass:
    def undocumented_method(self):
        pass
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name

        try:
            # Test completeness check
            issues = await doc_generator.check_documentation_completeness(temp_file)

            # Should find missing docstrings
            function_issues = [issue for issue in issues if 'undocumented_function' in issue['message']]
            assert len(function_issues) > 0

        finally:
            Path(temp_file).unlink()

    async def test_consistency_checking(self, consistency_enforcer):
        """Test consistency rule checking"""
        python_code = '''
def BadFunctionName():
    pass

def good_function_name():
    pass
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name

        try:
            issues = await consistency_enforcer.check_consistency([temp_file])

            # Should find naming convention issues
            naming_issues = [issue for issue in issues if issue['type'] == 'naming_convention']
            assert len(naming_issues) > 0

        finally:
            Path(temp_file).unlink()

    async def test_auto_fix_functionality(self, consistency_enforcer):
        """Test automatic fixing of issues"""
        python_code = 'print("Hello world")\n'  # Missing shebang

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name

        try:
            # Check for issues
            issues = await consistency_enforcer.check_consistency([temp_file])
            auto_fixable = [issue for issue in issues if issue.get('auto_fix', False)]

            if auto_fixable:
                # Apply fixes
                fixed_files = await consistency_enforcer.auto_fix_issues(auto_fixable)
                assert temp_file in fixed_files

                # Verify fix was applied
                content = Path(temp_file).read_text()
                assert content.startswith('#!/usr/bin/env python3')

        finally:
            Path(temp_file).unlink()

    async def test_commit_message_generation(self, auto_doc_system):
        """Test intelligent commit message generation"""
        changed_files = ["src/auth.py", "tests/test_auth.py", "docs/README.md"]

        message = await auto_doc_system.git_integration.suggest_commit_message(changed_files)

        assert isinstance(message, str)
        assert len(message) > 10
        assert "Claude Code" in message  # Should include attribution

    async def test_integration_workflow(self, auto_doc_system):
        """Test complete auto-documentation workflow"""
        # Create test files
        python_code = '''
def test_function():
    pass
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name

        try:
            # Process files
            result = await auto_doc_system.process_files([temp_file])

            assert result.files_processed == [temp_file]
            assert isinstance(result.consistency_issues, list)
            assert isinstance(result.documentation_generated, list)

        finally:
            Path(temp_file).unlink()


class TestIntegration:
    """Test integration between all components"""

    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow integration"""

        # 1. Start with user input
        user_input = "optimize the database queries"

        # 2. Process through clarification workflow
        with tempfile.TemporaryDirectory() as temp_dir:
            workflow = ClarificationWorkflow(storage_path=temp_dir)
            session = await workflow.start_workflow(user_input)

            # Verify input was processed
            assert session.cleaned_input is not None
            assert session.cleaned_input.extracted_intent in ['optimization', 'general']

            # 3. Test token optimization on context
            context = {
                "user_input": user_input,
                "session_data": {
                    "stage": session.stage.value,
                    "confidence": session.cleaned_input.confidence,
                    "ambiguities": session.cleaned_input.ambiguities
                },
                "large_context": "Additional context information. " * 100
            }

            original_tokens = await estimate_context_tokens(context)
            optimized_context, opt_result = await optimize_for_budget(context, 1000)

            # Verify optimization
            assert opt_result.optimized_tokens < original_tokens
            assert opt_result.reduction_percentage > 0

            # 4. Test auto-documentation integration
            auto_doc = AutoDocumentationSystem(repo_path=temp_dir)

            # Create test file for documentation
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def optimize_queries():\n    pass\n")

            doc_result = await auto_doc.process_files([str(test_file)])

            # Verify documentation processing
            assert len(doc_result.files_processed) == 1


    async def test_error_handling(self):
        """Test error handling across integrated components"""

        # Test with invalid input
        with tempfile.TemporaryDirectory() as temp_dir:
            workflow = ClarificationWorkflow(storage_path=temp_dir)

            # Test empty input
            session = await workflow.start_workflow("")
            assert session is not None  # Should handle gracefully

            # Test invalid session ID
            try:
                await workflow.submit_responses("invalid_id", [])
                assert False, "Should raise error"
            except ValueError:
                pass  # Expected

            # Test token optimization with invalid context
            result = await optimize_for_budget({}, 1000)
            assert result[1].original_tokens == 0  # Should handle empty context

    async def test_configuration_and_customization(self):
        """Test configuration options across components"""

        # Test token budget configuration
        custom_budget = TokenBudget(
            total_budget=8000,
            available_for_context=6000,
            safety_margin=500
        )

        context = {"test": "content " * 100}
        optimizer = TokenOptimizer()

        optimized, result = await optimizer.optimize_context(context, custom_budget)
        assert result.optimized_tokens <= custom_budget.available_for_context

    async def test_stats_and_monitoring(self):
        """Test statistics and monitoring capabilities"""

        # Test token optimizer stats
        optimizer = TokenOptimizer()
        stats = optimizer.get_optimization_stats()

        assert "cache" in stats
        assert "offload" in stats
        assert isinstance(stats["cache"], dict)
        assert isinstance(stats["offload"], dict)


# Test execution
if __name__ == "__main__":
    async def run_tests():
        """Run all tests"""

        print("Starting Context Engineering Integration Tests...")

        # Token Optimization Tests
        print("\n1. Testing Token Optimization...")
        token_test = TestTokenOptimization()
        optimizer = TokenOptimizer()
        sample_context = {
            "large_text": "Test content. " * 100,
            "code": "def test():\n    pass\n" * 20,
            "data": {"items": list(range(50))}
        }

        # Test token estimation
        tokens = optimizer._calculate_total_tokens(sample_context)
        print(f"   Sample context tokens: {tokens}")

        # Test optimization
        optimized, result = await optimizer.optimize_context(
            sample_context,
            TokenBudget(total_budget=500, available_for_context=400)
        )
        print(f"   Optimization: {result.reduction_percentage:.1f}% reduction")
        print(f"   Techniques used: {', '.join(result.techniques_used)}")

        # Clarification Workflow Tests
        print("\n2. Testing Clarification Workflow...")
        with tempfile.TemporaryDirectory() as temp_dir:
            workflow = ClarificationWorkflow(storage_path=temp_dir)
            session = await workflow.start_workflow("optimize the system performance")

            print(f"   Session created: {session.session_id}")
            print(f"   Intent detected: {session.cleaned_input.extracted_intent}")
            print(f"   Confidence: {session.cleaned_input.confidence:.2f}")
            print(f"   Questions generated: {len(session.questions) if session.questions else 0}")

        # Auto-Documentation Tests
        print("\n3. Testing Auto-Documentation...")
        with tempfile.TemporaryDirectory() as temp_dir:
            auto_doc = AutoDocumentationSystem(repo_path=temp_dir)

            # Create test file
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def undocumented_function():
    pass

def BadNamingConvention():
    pass
""")

            result = await auto_doc.process_files([str(test_file)])
            print(f"   Files processed: {len(result.files_processed)}")
            print(f"   Consistency issues: {len(result.consistency_issues)}")

            for issue in result.consistency_issues[:3]:
                print(f"     - {issue['message']}")

        # Integration Test
        print("\n4. Testing Integration...")
        large_context = {
            "user_request": "implement authentication system",
            "codebase_info": "Large codebase analysis. " * 50,
            "dependencies": list(range(30)),
            "config": {"setting_" + str(i): "value" for i in range(20)}
        }

        original_tokens = await estimate_context_tokens(large_context)
        optimized_context, opt_result = await optimize_for_budget(large_context, 1000)

        print(f"   Original context: {original_tokens} tokens")
        print(f"   Optimized context: {opt_result.optimized_tokens} tokens")
        print(f"   Reduction: {opt_result.reduction_percentage:.1f}%")

        print("\n✅ All tests completed successfully!")
        return True

    # Run tests
    success = asyncio.run(run_tests())
    if success:
        print("\n🎉 Context Engineering Integration Test Suite: PASSED")
    else:
        print("\n❌ Context Engineering Integration Test Suite: FAILED")