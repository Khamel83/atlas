#!/usr/bin/env python3
"""
Test suite for the Actions Gateway
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from actions_gateway import (
    ActionsGateway, ToolInfo, ActionResult,
    tool_info_to_dict, action_result_to_dict
)


class TestToolInfo:
    """Test cases for ToolInfo dataclass"""

    def test_tool_info_creation(self):
        """Test ToolInfo creation"""
        tool = ToolInfo(
            id="test-tool",
            name="Test Tool",
            description="A test tool",
            domain="test",
            required_params=["param1"],
            optional_params=["param2"],
            provenance={"source": "test"},
            auth_required=True
        )

        assert tool.id == "test-tool"
        assert tool.name == "Test Tool"
        assert tool.auth_required is True

    def test_tool_info_to_dict(self):
        """Test tool_info_to_dict function"""
        tool = ToolInfo(
            id="test-tool",
            name="Test Tool",
            description="A test tool",
            domain="test",
            required_params=["param1"],
            optional_params=[],
            provenance={"source": "test"},
            auth_required=False
        )

        data = tool_info_to_dict(tool)
        assert data['id'] == "test-tool"
        assert data['name'] == "Test Tool"
        assert data['auth_required'] is False


class TestActionResult:
    """Test cases for ActionResult dataclass"""

    def test_action_result_creation(self):
        """Test ActionResult creation"""
        result = ActionResult(
            success=True,
            tool_id="test-tool",
            result={"status": "completed"},
            error=None,
            duration_ms=100,
            audit_trail=[],
            timestamp="2025-09-27T10:00:00"
        )

        assert result.success is True
        assert result.tool_id == "test-tool"
        assert result.duration_ms == 100

    def test_action_result_to_dict(self):
        """Test action_result_to_dict function"""
        result = ActionResult(
            success=False,
            tool_id="test-tool",
            result=None,
            error="Test error",
            duration_ms=50,
            audit_trail=[{"action": "test"}],
            timestamp="2025-09-27T10:00:00"
        )

        data = action_result_to_dict(result)
        assert data['success'] is False
        assert data['error'] == "Test error"
        assert len(data['audit_trail']) == 1


class TestActionsGateway:
    """Test cases for ActionsGateway"""

    @pytest.fixture
    def gateway(self):
        """Create a test gateway"""
        return ActionsGateway()

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool for testing"""
        return ToolInfo(
            id="test-upload",
            name="Upload File",
            description="Upload a file to cloud storage",
            domain="files/cloud",
            required_params=["file_path"],
            optional_params=["destination"],
            provenance={"source": "test-mcp"},
            auth_required=True
        )

    def test_gateway_initialization(self, gateway):
        """Test gateway initializes correctly"""
        assert gateway is not None
        assert gateway.timeout is not None
        assert isinstance(gateway.remote_mcp_urls, list)

    def test_parse_remote_mcp_urls(self):
        """Test parsing remote MCP URLs"""
        with patch.dict(os.environ, {'REMOTE_MCP_URLS': 'http://server1,http://server2'}):
            gateway = ActionsGateway()
            assert len(gateway.remote_mcp_urls) == 2
            assert "http://server1" in gateway.remote_mcp_urls
            assert "http://server2" in gateway.remote_mcp_urls

    @pytest.mark.asyncio
    async def test_list_tools_meta_mcp(self, gateway, mock_tool):
        """Test listing tools from MetaMCP"""
        with patch.dict(os.environ, {'META_MCP_URL': 'http://meta-mcp:8000'}):
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "tools": [
                        {
                            "id": "test-upload",
                            "name": "Upload File",
                            "description": "Upload a file to cloud storage",
                            "domain": "files/cloud",
                            "required_params": ["file_path"],
                            "optional_params": ["destination"],
                            "provenance": {"source": "test-mcp"},
                            "auth_required": True
                        }
                    ]
                }
                mock_post.return_value = mock_response

                tools = await gateway.list_tools()

                assert len(tools) == 1
                assert tools[0].id == "test-upload"
                assert tools[0].domain == "files/cloud"

    @pytest.mark.asyncio
    async def test_list_tools_remote_mcp(self, gateway, mock_tool):
        """Test listing tools from remote MCP servers"""
        with patch.dict(os.environ, {'REMOTE_MCP_URLS': 'http://remote-mcp:8001'}):
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "tools": [
                        {
                            "id": "remote-tool",
                            "name": "Remote Tool",
                            "description": "A remote tool",
                            "domain": "general",
                            "required_params": [],
                            "optional_params": [],
                            "provenance": {"source": "http://remote-mcp:8001"},
                            "auth_required": False
                        }
                    ]
                }
                mock_post.return_value = mock_response

                tools = await gateway.list_tools()

                assert len(tools) == 1
                assert tools[0].id == "remote-tool"
                assert tools[0].provenance['source'] == "http://remote-mcp:8001"

    @pytest.mark.asyncio
    async def test_list_tools_with_domain_filter(self, gateway):
        """Test listing tools with domain filter"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tools": [
                    {
                        "id": "upload-tool",
                        "name": "Upload",
                        "description": "Upload file",
                        "domain": "files/cloud",
                        "required_params": ["file"],
                        "optional_params": [],
                        "provenance": {"source": "test"},
                        "auth_required": False
                    },
                    {
                        "id": "search-tool",
                        "name": "Search",
                        "description": "Search content",
                        "domain": "search/web",
                        "required_params": ["query"],
                        "optional_params": [],
                        "provenance": {"source": "test"},
                        "auth_required": False
                    }
                ]
            }
            mock_post.return_value = mock_response

            # Test filtering by domain
            tools = await gateway.list_tools("files/cloud")
            assert len(tools) == 1
            assert tools[0].domain == "files/cloud"

            # Test no filter
            all_tools = await gateway.list_tools()
            assert len(all_tools) == 2

    @pytest.mark.asyncio
    async def test_invoke_success(self, gateway):
        """Test successful tool invocation"""
        with patch.dict(os.environ, {'META_MCP_URL': 'http://meta-mcp:8000'}):
            with patch('requests.post') as mock_post:
                # Mock tool listing
                list_response = Mock()
                list_response.status_code = 200
                list_response.json.return_value = {
                    "tools": [
                        {
                            "id": "test-tool",
                            "name": "Test Tool",
                            "description": "Test description",
                            "domain": "test",
                            "required_params": ["param1"],
                            "optional_params": [],
                            "provenance": {"source": "test-mcp"},
                            "auth_required": False
                        }
                    ]
                }

                # Mock tool invocation
                invoke_response = Mock()
                invoke_response.status_code = 200
                invoke_response.json.return_value = {
                    "result": {"status": "success", "output": "Tool executed successfully"}
                }

                mock_post.side_effect = [list_response, invoke_response]

                result = await gateway.invoke("test-tool", {"param1": "value"})

                assert result.success is True
                assert result.tool_id == "test-tool"
                assert result.result is not None
                assert result.error is None

    @pytest.mark.asyncio
    async def test_invoke_missing_params(self, gateway):
        """Test tool invocation with missing required parameters"""
        with patch('requests.post') as mock_post:
            # Mock tool listing
            list_response = Mock()
            list_response.status_code = 200
            list_response.json.return_value = {
                "tools": [
                    {
                        "id": "test-tool",
                        "name": "Test Tool",
                        "description": "Test description",
                        "domain": "test",
                        "required_params": ["required_param"],
                        "optional_params": [],
                        "provenance": {"source": "test-mcp"},
                        "auth_required": False
                    }
                ]
            }
            mock_post.return_value = list_response

            result = await gateway.invoke("test-tool", {"wrong_param": "value"})

            assert result.success is False
            assert "Missing required parameters" in result.error

    @pytest.mark.asyncio
    async def test_invoke_tool_not_found(self, gateway):
        """Test tool invocation with non-existent tool"""
        with patch('requests.post') as mock_post:
            # Mock empty tool listing
            list_response = Mock()
            list_response.status_code = 200
            list_response.json.return_value = {"tools": []}
            mock_post.return_value = list_response

            result = await gateway.invoke("non-existent-tool", {})

            assert result.success is False
            assert "Tool non-existent-tool not found" in result.error

    @pytest.mark.asyncio
    async def test_sanitize_params(self, gateway):
        """Test parameter sanitization for audit log"""
        params = {
            "normal_param": "value",
            "password": "secret123",
            "api_key": "key-abc123",
            "auth_token": "token-xyz"
        }

        sanitized = gateway._sanitize_params(params)

        assert sanitized["normal_param"] == "value"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["auth_token"] == "***REDACTED***"

    def test_summarize_result(self, gateway):
        """Test result summarization"""
        # Test dict result
        result = {"success": True, "data": "test"}
        summary = gateway._summarize_result(result)
        assert "Success: True" in summary

        # Test list result
        result = ["item1", "item2", "item3"]
        summary = gateway._summarize_result(result)
        assert "List with 3 items" in summary

        # Test string result
        result = "A string result"
        summary = gateway._summarize_result(result)
        assert "String response" in summary

    @pytest.mark.asyncio
    async def test_health_check(self, gateway):
        """Test health check functionality"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            health = await gateway.health_check()

            assert 'meta_mcp' in health
            assert 'remote_mcps' in health

    @pytest.mark.asyncio
    async def test_get_audit_log(self, gateway):
        """Test audit log functionality"""
        # Initially empty
        audit_log = await gateway.get_audit_log()
        assert isinstance(audit_log, list)
        assert len(audit_log) == 0

        # After an action, should have entries
        with patch('requests.post') as mock_post:
            list_response = Mock()
            list_response.status_code = 200
            list_response.json.return_value = {"tools": []}
            mock_post.return_value = list_response

            await gateway.invoke("test-tool", {})

            audit_log = await gateway.get_audit_log()
            assert len(audit_log) > 0

    @pytest.mark.asyncio
    async def test_convenience_functions(self):
        """Test convenience functions"""
        from actions_gateway import list_available_tools, execute_action

        with patch('actions_gateway.ActionsGateway') as mock_gateway_class:
            mock_gateway = Mock()
            mock_tools = [ToolInfo(
                id="test-tool",
                name="Test Tool",
                description="Test",
                domain="test",
                required_params=[],
                optional_params=[],
                provenance={},
                auth_required=False
            )]
            mock_gateway.list_tools.return_value = mock_tools

            mock_result = ActionResult(
                success=True,
                tool_id="test-tool",
                result={},
                error=None,
                duration_ms=100,
                audit_trail=[],
                timestamp="2025-09-27T10:00:00"
            )
            mock_gateway.invoke.return_value = mock_result

            mock_gateway_class.return_value = mock_gateway

            # Test list_available_tools
            tools = await list_available_tools("test")
            assert tools == mock_tools

            # Test execute_action
            result = await execute_action("test-tool", {})
            assert result == mock_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])