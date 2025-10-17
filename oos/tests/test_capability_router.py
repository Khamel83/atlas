#!/usr/bin/env python3
"""
Test suite for the Capability Router
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from capability_router import CapabilityRouter, RoutingResult


class TestCapabilityRouter:
    """Test cases for CapabilityRouter"""

    @pytest.fixture
    def router(self):
        """Create a test router instance"""
        return CapabilityRouter()

    @pytest.fixture
    def test_ontology_file(self, tmp_path):
        """Create a test ontology file"""
        ontology_content = """
domains:
  search/web:
    aliases: ["search", "find", "research"]
  files/cloud:
    aliases: ["files", "storage", "upload"]
  account/plan:
    aliases: ["plan", "subscription", "pricing"]

mode_patterns:
  info_keywords: ["what", "how", "tell me", "capabilities"]
  action_keywords: ["create", "upload", "execute", "run"]
"""
        ontology_file = tmp_path / "test_ontology.yaml"
        ontology_file.write_text(ontology_content)
        return str(ontology_file)

    def test_router_initialization(self, router):
        """Test router initializes correctly"""
        assert router is not None
        assert isinstance(router.domains, dict)
        assert isinstance(router.mode_patterns, dict)

    def test_deterministic_match_exact(self, router, test_ontology_file):
        """Test exact word matching"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        result = router.deterministic_match("I want to search for information")
        assert result is not None
        assert result[0] == "search/web"
        assert result[2] == "search"

    def test_deterministic_match_alias(self, router, test_ontology_file):
        """Test alias matching"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        result = router.deterministic_match("I need to upload a file")
        assert result is not None
        assert result[0] == "files/cloud"
        assert result[2] == "upload"

    def test_deterministic_match_no_match(self, router, test_ontology_file):
        """Test no match case"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        result = router.deterministic_match("I want to do something random")
        assert result is None

    def test_detect_mode_info(self, router, test_ontology_file):
        """Test info mode detection"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        mode = router.detect_mode("What can this service do?", "search/web")
        assert mode == "info"

    def test_detect_mode_action(self, router, test_ontology_file):
        """Test action mode detection"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        mode = router.detect_mode("Create a new file", "files/cloud")
        assert mode == "action"

    def test_detect_mode_default(self, router, test_ontology_file):
        """Test default mode detection"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        mode = router.detect_mode("Something about service", "search/web")
        assert mode == "info"

    def test_classify_success(self, router, test_ontology_file):
        """Test successful classification"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        result = router.classify("What can I search for?")
        assert isinstance(result, RoutingResult)
        assert result.domain == "search/web"
        assert result.mode == "info"
        assert result.method == "deterministic"
        assert result.confidence > 0.5

    def test_classify_action(self, router, test_ontology_file):
        """Test action classification"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        result = router.classify("Upload my file to storage")
        assert isinstance(result, RoutingResult)
        assert result.domain == "files/cloud"
        assert result.mode == "action"
        assert result.method == "deterministic"

    def test_classify_fallback(self, router, test_ontology_file):
        """Test fallback classification"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        result = router.classify("something completely unrelated")
        assert isinstance(result, RoutingResult)
        assert result.method == "llm" or result.method == "fallback"

    def test_get_available_domains(self, router, test_ontology_file):
        """Test getting available domains"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        domains = router.get_available_domains()
        assert isinstance(domains, list)
        assert "search/web" in domains
        assert "files/cloud" in domains
        assert "account/plan" in domains

    def test_get_domain_aliases(self, router, test_ontology_file):
        """Test getting domain aliases"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        aliases = router.get_domain_aliases("search/web")
        assert isinstance(aliases, list)
        assert "search" in aliases
        assert "find" in aliases
        assert "research" in aliases

    def test_get_domain_aliases_nonexistent(self, router, test_ontology_file):
        """Test getting aliases for non-existent domain"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        aliases = router.get_domain_aliases("nonexistent")
        assert aliases == []

    def test_route_request_convenience_function(self, test_ontology_file):
        """Test convenience route_request function"""
        # Temporarily set ontology path for global router
        import capability_router
        original_path = capability_router.router.ontology_path
        capability_router.router.ontology_path = test_ontology_file
        capability_router.router._load_ontology()

        try:
            result = capability_router.route_request("search for information")
            assert isinstance(result, RoutingResult)
            assert result.domain == "search/web"
        finally:
            capability_router.router.ontology_path = original_path
            capability_router.router._load_ontology()

    def test_get_domains_convenience_function(self, test_ontology_file):
        """Test convenience get_domains function"""
        # Temporarily set ontology path for global router
        import capability_router
        original_path = capability_router.router.ontology_path
        capability_router.router.ontology_path = test_ontology_file
        capability_router.router._load_ontology()

        try:
            domains = capability_router.get_domains()
            assert isinstance(domains, list)
            assert len(domains) > 0
        finally:
            capability_router.router.ontology_path = original_path
            capability_router.router._load_ontology()

    @pytest.mark.parametrize("query,expected_domain,expected_mode", [
        ("What does ChatGPT offer?", "search/web", "info"),
        ("Upload file to cloud", "files/cloud", "action"),
        ("Tell me about pricing", "account/plan", "info"),
        ("Find API documentation", "search/web", "info"),
        ("Create storage bucket", "files/cloud", "action"),
    ])
    def test_various_queries(self, router, test_ontology_file, query, expected_domain, expected_mode):
        """Test various query types"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        result = router.classify(query)
        assert result.domain == expected_domain
        assert result.mode == expected_mode

    def test_case_insensitive_matching(self, router, test_ontology_file):
        """Test case insensitive matching"""
        router.ontology_path = test_ontology_file
        router._load_ontology()

        result = router.deterministic_match("I want to SEARCH for info")
        assert result is not None
        assert result[0] == "search/web"

        result = router.deterministic_match("I need to UPLOAD files")
        assert result is not None
        assert result[0] == "files/cloud"