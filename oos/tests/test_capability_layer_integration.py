#!/usr/bin/env python3
"""
Integration tests for the OOS Capability Layer
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from capability_router import CapabilityRouter, RoutingResult
from knowledge_resolver import KnowledgeResolver, KnowledgeResult
from actions_gateway import ActionsGateway, ToolInfo
from renderers import CapabilityRenderer
from simple_command_handler import SimpleCommandHandler
from commands.capabilities_command import CapabilitiesCommand
from commands.actions_command import ActionsCommand


class TestCapabilityLayerIntegration:
    """Integration tests for the complete capability layer"""

    @pytest.fixture
    def router(self):
        """Create a test router"""
        return CapabilityRouter()

    @pytest.fixture
    def knowledge_resolver(self):
        """Create a test knowledge resolver"""
        return KnowledgeResolver()

    @pytest.fixture
    def actions_gateway(self):
        """Create a test actions gateway"""
        return ActionsGateway()

    @pytest.fixture
    def renderer(self):
        """Create a test renderer"""
        return CapabilityRenderer()

    @pytest.fixture
    def command_handler(self):
        """Create a test command handler"""
        return SimpleCommandHandler()

    @pytest.mark.asyncio
    async def test_complete_capabilities_workflow(self, router, knowledge_resolver, renderer):
        """Test complete workflow from natural language to rendered result"""
        # Step 1: Route the request
        query = "What does ChatGPT Plus offer?"
        routing_result = router.classify(query)

        assert routing_result.domain == "account/plan"
        assert routing_result.mode == "info"
        assert routing_result.confidence > 0.5

        # Step 2: Mock knowledge resolution
        mock_knowledge_result = KnowledgeResult(
            capabilities=["GPT-4 access", "Faster response times", "File upload"],
            limits=["Higher rate limits"],
            quotas=[],
            api_access=True,
            auth_methods=["API key", "OAuth"],
            pricing_notes=["$20/month"],
            sources=[],
            summary="ChatGPT Plus offers enhanced capabilities",
            confidence=0.9
        )

        # Step 3: Render the result
        output = renderer.render_knowledge_result(mock_knowledge_result)

        assert "ChatGPT Plus" in output
        assert "GPT-4 access" in output
        assert "API Access" in output

    @pytest.mark.asyncio
    async def test_complete_actions_workflow(self, router, actions_gateway, renderer):
        """Test complete workflow from action request to execution"""
        # Step 1: Route the request
        query = "Upload my file to cloud storage"
        routing_result = router.classify(query)

        assert routing_result.domain == "files/cloud"
        assert routing_result.mode == "action"

        # Step 2: Mock tool listing
        mock_tools = [
            ToolInfo(
                id="cloud-upload",
                name="Upload to Cloud",
                description="Upload file to cloud storage",
                domain="files/cloud",
                required_params=["file_path"],
                optional_params=["destination"],
                provenance={"source": "test-mcp"},
                auth_required=True
            )
        ]

        # Step 3: Render tools list
        output = renderer.render_tools_list(mock_tools, routing_result.domain)

        assert "Upload to Cloud" in output
        assert "file_path" in output
        assert "Authentication Required" in output

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, router, knowledge_resolver, renderer):
        """Test error handling in the workflow"""
        # Step 1: Route the request
        query = "Tell me about non-existent-service"
        routing_result = router.classify(query)

        # Step 2: Mock empty knowledge result
        mock_knowledge_result = KnowledgeResult(
            capabilities=[],
            limits=[],
            quotas=[],
            api_access=False,
            auth_methods=[],
            pricing_notes=[],
            sources=[],
            summary="No information available",
            confidence=0.0
        )

        # Step 3: Render the result
        output = renderer.render_knowledge_result(mock_knowledge_result)

        assert "No information available" in output

    @pytest.mark.asyncio
    async def test_command_handler_integration(self, command_handler):
        """Test command handler integration with capability commands"""
        # Test capabilities command
        with patch.object(command_handler.capabilities_cmd, 'execute') as mock_execute:
            mock_execute.return_value = "Capabilities result"
            result = await command_handler.execute_command("capabilities", "ChatGPT Plus")

            assert result["output"] == "Capabilities result"
            mock_execute.assert_called_once_with(["ChatGPT", "Plus"])

        # Test actions command
        with patch.object(command_handler.actions_cmd, 'execute_actions') as mock_execute:
            mock_execute.return_value = "Actions result"
            result = await command_handler.execute_command("actions", "files/cloud")

            assert result["output"] == "Actions result"
            mock_execute.assert_called_once_with(["files/cloud"])

        # Test act command
        with patch.object(command_handler.actions_cmd, 'execute_act') as mock_execute:
            mock_execute.return_value = "Act result"
            result = await command_handler.execute_command("act", "upload file=test.txt")

            assert result["output"] == "Act result"
            mock_execute.assert_called_once_with(["upload", "file=test.txt"])

        # Test help command
        with patch('src.renderers.render_help') as mock_help:
            mock_help.return_value = "Help information"
            result = await command_handler.execute_command("capability-help", "")

            assert result["output"] == "Help information"

    @pytest.mark.asyncio
    async def test_mcp_tools_integration(self):
        """Test MCP tools integration (requires MCP server setup)"""
        # This would test the actual MCP tools if the server is running
        # For now, we'll test the structure
        from mcp_server import OOSContextEngineeringServer

        server = OOSContextEngineeringServer()

        # Check that the server has the new tools
        tools = server.server._tools if hasattr(server.server, '_tools') else []
        tool_names = [tool.name for tool in tools] if tools else []

        # The tools should be available in the list_tools method
        assert hasattr(server, '_oos_capabilities')
        assert hasattr(server, '_oos_actions_list')
        assert hasattr(server, '_oos_actions_invoke')

    def test_ontology_loading(self):
        """Test that the ontology loads correctly"""
        from capability_router import router

        # Check that domains are loaded
        assert isinstance(router.domains, dict)
        assert len(router.domains) > 0

        # Check for expected domains
        expected_domains = ["search/web", "files/cloud", "account/plan"]
        for domain in expected_domains:
            assert domain in router.domains

        # Check that mode patterns are loaded
        assert isinstance(router.mode_patterns, dict)
        assert "info_keywords" in router.mode_patterns
        assert "action_keywords" in router.mode_patterns

    @pytest.mark.asyncio
    async def test_renderer_output_formats(self, renderer):
        """Test different renderer output formats"""
        from knowledge_resolver import KnowledgeResult, SourceInfo

        # Create test knowledge result
        test_result = KnowledgeResult(
            domain="account/plan",
            capabilities=["API access", "Web interface"],
            limits=["Rate limits: 1000/hour"],
            quotas=[],
            api_access=True,
            auth_methods=["API key"],
            pricing_notes=["Free tier: 1000 requests/month"],
            sources=[
                SourceInfo(
                    url="https://example.com/docs",
                    title="API Documentation",
                    date_accessed="2025-09-27",
                    source_type="docs"
                )
            ],
            summary="Test service offers comprehensive capabilities",
            confidence=0.85
        )

        # Test human-readable format
        output = renderer.render_knowledge_result(test_result, show_json=False)
        assert "API access" in output
        assert "Web interface" in output
        assert "Rate limits" in output
        assert "Free tier" in output
        assert "API Documentation" in output
        assert "```json" not in output  # No JSON block

        # Test with JSON format
        output = renderer.render_knowledge_result(test_result, show_json=True)
        assert "API access" in output
        assert "```json" in output  # Should include JSON block

    @pytest.mark.asyncio
    async def test_cross_component_error_handling(self):
        """Test error handling across components"""
        # Test router with invalid input
        router = CapabilityRouter()
        result = router.classify("")
        assert result.method == "fallback"

        # Test knowledge resolver with no adapters available
        resolver = KnowledgeResolver()
        knowledge_result = await resolver.resolve_query("test", "test")
        assert knowledge_result.confidence == 0.0

        # Test actions gateway with invalid tool
        gateway = ActionsGateway()
        action_result = await gateway.invoke("non-existent-tool", {})
        assert action_result.success is False
        assert "not found" in action_result.error

    def test_configuration_fallbacks(self):
        """Test that components handle missing configuration gracefully"""
        # Test router with missing ontology file
        router = CapabilityRouter("/non/existent/path.yaml")
        assert len(router.domains) > 0  # Should have fallback domains

        # Test actions gateway with no environment variables
        gateway = ActionsGateway()
        assert gateway.meta_mcp_url is None
        assert isinstance(gateway.remote_mcp_urls, list)

    @pytest.mark.asyncio
    async def test_performance_characteristics(self):
        """Test performance characteristics of the capability layer"""
        import time

        # Test routing performance
        router = CapabilityRouter()
        start_time = time.time()
        for _ in range(100):
            router.classify("What does this service offer?")
        routing_time = time.time() - start_time

        assert routing_time < 1.0  # Should be fast for 100 requests

        # Test knowledge resolver with mocked adapters
        resolver = KnowledgeResolver()
        with patch.object(resolver.adapters['context7'], 'is_available', return_value=False):
            with patch.object(resolver.adapters['docs_mcp'], 'is_available', return_value=False):
                with patch.object(resolver.adapters['deep_research'], 'is_available', return_value=False):
                    start_time = time.time()
                    for _ in range(10):
                        await resolver.resolve_query("test", "test")
                    resolve_time = time.time() - start_time

                    assert resolve_time < 1.0  # Should be fast even with no adapters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])