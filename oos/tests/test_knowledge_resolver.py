#!/usr/bin/env python3
"""
Test suite for the Knowledge Resolver
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import date

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge_resolver import (
    KnowledgeResolver, KnowledgeResult, SourceInfo, QuotaInfo,
    Context7Adapter, DocsMCPAdapter, DeepResearchAdapter
)


class TestKnowledgeResult:
    """Test cases for KnowledgeResult dataclass"""

    def test_knowledge_result_creation(self):
        """Test KnowledgeResult creation"""
        result = KnowledgeResult(
            capabilities=["API access", "Web interface"],
            limits=["Rate limits apply"],
            quotas=[],
            api_access=True,
            auth_methods=["API key"],
            pricing_notes=["Free tier available"],
            sources=[],
            summary="Test summary",
            confidence=0.8
        )

        assert result.capabilities == ["API access", "Web interface"]
        assert result.api_access is True
        assert result.confidence == 0.8

    def test_result_to_dict(self):
        """Test result_to_dict function"""
        from knowledge_resolver import result_to_dict

        result = KnowledgeResult(
            capabilities=["API access"],
            limits=[],
            quotas=[],
            api_access=True,
            auth_methods=["API key"],
            pricing_notes=[],
            sources=[SourceInfo("http://example.com", "Test", "2025-09-27", "docs")],
            summary="Test",
            confidence=0.9
        )

        data = result_to_dict(result)
        assert data['capabilities'] == ["API access"]
        assert data['api_access'] is True
        assert len(data['sources']) == 1
        assert data['sources'][0]['url'] == "http://example.com"


class TestContext7Adapter:
    """Test cases for Context7Adapter"""

    @pytest.fixture
    def adapter(self):
        """Create a test adapter"""
        return Context7Adapter()

    def test_adapter_initialization(self):
        """Test adapter initializes correctly"""
        adapter = Context7Adapter()
        assert adapter.base_url is not None
        assert adapter.timeout is not None

    @pytest.mark.asyncio
    async def test_is_available_success(self, adapter):
        """Test is_available when server is reachable"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = await adapter.is_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_failure(self, adapter):
        """Test is_available when server is not reachable"""
        with patch('requests.get', side_effect=Exception("Connection error")):
            result = await adapter.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_query_success(self, adapter):
        """Test successful query"""
        with patch('requests.post') as mock_post:
            # Mock resolve-library-uri response
            resolve_response = Mock()
            resolve_response.status_code = 200
            resolve_response.json.return_value = {
                "resourceUri": "context7://libraries/test"
            }

            # Mock search-library-docs response
            search_response = Mock()
            search_response.status_code = 200
            search_response.json.return_value = {
                "content": "API documentation with various capabilities",
                "sources": [
                    {"url": "http://docs.example.com", "title": "API Docs"}
                ]
            }

            mock_post.side_effect = [resolve_response, search_response]

            result = await adapter.query("test query", "search/web")

            assert result is not None
            assert result.capabilities is not None
            assert len(result.sources) == 1

    @pytest.mark.asyncio
    async def test_query_failure(self, adapter):
        """Test query failure"""
        with patch('requests.post', side_effect=Exception("API error")):
            result = await adapter.query("test query", "search/web")
            assert result is None


class TestDocsMCPAdapter:
    """Test cases for DocsMCPAdapter"""

    @pytest.fixture
    def adapter(self):
        """Create a test adapter"""
        return DocsMCPAdapter()

    @pytest.mark.asyncio
    async def test_query_success(self, adapter):
        """Test successful query"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"content": "API access and web interface available"}
                ],
                "sources": [
                    {"url": "http://docs.example.com", "title": "Documentation"}
                ]
            }
            mock_post.return_value = mock_response

            result = await adapter.query("test query", "search/web")

            assert result is not None
            assert "API access" in result.capabilities
            assert len(result.sources) == 1


class TestDeepResearchAdapter:
    """Test cases for DeepResearchAdapter"""

    @pytest.fixture
    def adapter(self):
        """Create a test adapter"""
        return DeepResearchAdapter()

    @pytest.mark.asyncio
    async def test_query_success(self, adapter):
        """Test successful query"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "findings": [
                    {"content": "Comprehensive API capabilities with pricing info"}
                ],
                "sources": [
                    {"url": "http://research.example.com", "title": "Research"}
                ],
                "summary": "Research completed successfully"
            }
            mock_post.return_value = mock_response

            result = await adapter.query("test query", "search/web")

            assert result is not None
            assert result.summary == "Research completed successfully"
            assert len(result.sources) == 1


class TestKnowledgeResolver:
    """Test cases for KnowledgeResolver"""

    @pytest.fixture
    def resolver(self):
        """Create a test resolver"""
        return KnowledgeResolver()

    @pytest.mark.asyncio
    async def test_resolver_initialization(self, resolver):
        """Test resolver initializes correctly"""
        assert resolver is not None
        assert 'context7' in resolver.adapters
        assert 'docs_mcp' in resolver.adapters
        assert 'deep_research' in resolver.adapters

    @pytest.mark.asyncio
    async def test_resolve_query_success(self, resolver):
        """Test successful query resolution"""
        # Mock a successful adapter
        mock_adapter = AsyncMock()
        mock_result = KnowledgeResult(
            capabilities=["Test capability"],
            limits=[],
            quotas=[],
            api_access=True,
            auth_methods=[],
            pricing_notes=[],
            sources=[],
            summary="Test summary",
            confidence=0.8
        )
        mock_adapter.query.return_value = mock_result
        mock_adapter.is_available.return_value = True

        # Replace first adapter with mock
        resolver.adapters['context7'] = mock_adapter

        result = await resolver.resolve_query("test query", "search/web")

        assert result is not None
        assert result.capabilities == ["Test capability"]
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_resolve_query_fallback(self, resolver):
        """Test fallback to other adapters"""
        # Mock first adapter as unavailable
        mock_adapter1 = AsyncMock()
        mock_adapter1.is_available.return_value = False

        # Mock second adapter as available but low confidence
        mock_adapter2 = AsyncMock()
        mock_adapter2.is_available.return_value = True
        mock_adapter2.query.return_value = KnowledgeResult(
            capabilities=[],
            limits=[],
            quotas=[],
            api_access=False,
            auth_methods=[],
            pricing_notes=[],
            sources=[],
            summary="Low confidence result",
            confidence=0.3
        )

        # Mock third adapter as available with good result
        mock_adapter3 = AsyncMock()
        mock_adapter3.is_available.return_value = True
        mock_result = KnowledgeResult(
            capabilities=["Good capability"],
            limits=[],
            quotas=[],
            api_access=True,
            auth_methods=[],
            pricing_notes=[],
            sources=[],
            summary="Good result",
            confidence=0.8
        )
        mock_adapter3.query.return_value = mock_result

        # Replace adapters
        resolver.adapters['context7'] = mock_adapter1
        resolver.adapters['docs_mcp'] = mock_adapter2
        resolver.adapters['deep_research'] = mock_adapter3

        result = await resolver.resolve_query("test query", "search/web")

        assert result is not None
        assert result.capabilities == ["Good capability"]
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_resolve_query_all_fail(self, resolver):
        """Test when all adapters fail"""
        # Mock all adapters as unavailable
        for adapter_name in resolver.adapters:
            mock_adapter = AsyncMock()
            mock_adapter.is_available.return_value = False
            resolver.adapters[adapter_name] = mock_adapter

        result = await resolver.resolve_query("test query", "search/web")

        assert result is not None
        assert result.capabilities == []
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_resolve_knowledge_convenience_function(self):
        """Test convenience resolve_knowledge function"""
        from knowledge_resolver import resolve_knowledge

        with patch('knowledge_resolver.KnowledgeResolver') as mock_resolver_class:
            mock_resolver = Mock()
            mock_result = KnowledgeResult(
                capabilities=["Test"],
                limits=[],
                quotas=[],
                api_access=True,
                auth_methods=[],
                pricing_notes=[],
                sources=[],
                summary="Test",
                confidence=0.9
            )
            mock_resolver.resolve_query.return_value = mock_result
            mock_resolver_class.return_value = mock_resolver

            result = await resolve_knowledge("test query", "search/web")

            assert result == mock_result
            mock_resolver.resolve_query.assert_called_once_with("test query", "search/web")


class TestIntegration:
    """Integration tests for knowledge resolver"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete workflow from query to result"""
        # This would test with real adapters in a real scenario
        # For now, we'll mock the external dependencies
        pass