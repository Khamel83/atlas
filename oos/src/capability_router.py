"""
Capability Router for OOS
Routes natural language requests to capability domains and modes (info/action)
"""

import re
import yaml
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class RoutingResult:
    """Result of capability routing"""
    domain: str
    mode: str  # "info" or "action"
    confidence: float
    matched_text: str
    remainder_text: str
    method: str  # "deterministic" or "llm"


class CapabilityRouter:
    """
    Routes natural language requests to capability domains using:
    1. Deterministic matching (primary)
    2. LLM classification (fallback)
    """

    def __init__(self, ontology_path: str = "config/ontology.yaml"):
        self.ontology_path = ontology_path
        self.domains = {}
        self.mode_patterns = {}
        self._load_ontology()

    def _load_ontology(self) -> None:
        """Load domain ontology from YAML file"""
        try:
            with open(self.ontology_path, 'r') as f:
                ontology = yaml.safe_load(f)

            self.domains = ontology.get('domains', {})
            self.mode_patterns = ontology.get('mode_patterns', {})

        except FileNotFoundError:
            # Default ontology if file not found
            self.domains = {
                "search/web": {"aliases": ["search", "find", "research"]},
                "docs/api": {"aliases": ["docs", "api", "documentation"]},
                "files/cloud": {"aliases": ["files", "storage", "upload"]},
            }
            self.mode_patterns = {
                "info_keywords": ["what", "how", "tell me", "explain"],
                "action_keywords": ["create", "upload", "send", "run"]
            }

    def deterministic_match(self, text: str) -> Optional[Tuple[str, float, str]]:
        """
        Try deterministic matching against domain aliases
        Returns: (domain, confidence, matched_text) or None
        """
        text_lower = text.lower()

        for domain, config in self.domains.items():
            aliases = config.get('aliases', [])

            for alias in aliases:
                alias_lower = alias.lower()

                # Exact word match
                if re.search(rf'\b{re.escape(alias_lower)}\b', text_lower):
                    return domain, 0.9, alias

                # Partial match for multi-word aliases
                if len(alias.split()) > 1 and alias_lower in text_lower:
                    return domain, 0.8, alias

        return None

    def detect_mode(self, text: str, domain: str) -> str:
        """
        Detect whether request is for info or action based on keywords
        """
        text_lower = text.lower()

        # Check for action keywords
        action_keywords = self.mode_patterns.get('action_keywords', [])
        for keyword in action_keywords:
            if keyword.lower() in text_lower:
                return "action"

        # Check for info keywords
        info_keywords = self.mode_patterns.get('info_keywords', [])
        for keyword in info_keywords:
            if keyword.lower() in text_lower:
                return "info"

        # Default to info for ambiguous cases
        return "info"

    def _llm_classify(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Fallback LLM classification for ambiguous cases
        Returns structured classification result
        """
        # This would integrate with an LLM service
        # For now, return a simple classification based on heuristics
        text_lower = text.lower()

        # Simple heuristic fallback
        if any(word in text_lower for word in ['what', 'how', 'tell', 'explain', 'show']):
            return {"domain": "search/web", "mode": "info", "confidence": 0.6}
        elif any(word in text_lower for word in ['create', 'make', 'build', 'do']):
            return {"domain": "search/web", "mode": "action", "confidence": 0.6}

        return None

    def classify(self, text: str) -> RoutingResult:
        """
        Classify natural language request into domain and mode
        """
        # Try deterministic matching first
        det_match = self.deterministic_match(text)
        if det_match:
            domain, confidence, matched_text = det_match
            mode = self.detect_mode(text, domain)

            # Remove matched text from remainder
            remainder = text.replace(matched_text, "", 1).strip()

            return RoutingResult(
                domain=domain,
                mode=mode,
                confidence=confidence,
                matched_text=matched_text,
                remainder_text=remainder,
                method="deterministic"
            )

        # Fallback to LLM classification
        llm_result = self._llm_classify(text)
        if llm_result:
            return RoutingResult(
                domain=llm_result["domain"],
                mode=llm_result["mode"],
                confidence=llm_result["confidence"],
                matched_text="",
                remainder_text=text,
                method="llm"
            )

        # Ultimate fallback
        return RoutingResult(
            domain="search/web",
            mode="info",
            confidence=0.3,
            matched_text="",
            remainder_text=text,
            method="fallback"
        )

    def get_available_domains(self) -> List[str]:
        """Get list of all available domains"""
        return list(self.domains.keys())

    def get_domain_aliases(self, domain: str) -> List[str]:
        """Get aliases for a specific domain"""
        return self.domains.get(domain, {}).get('aliases', [])


# Global instance
router = CapabilityRouter()


def route_request(text: str) -> RoutingResult:
    """Convenience function for routing requests"""
    return router.classify(text)


def get_domains() -> List[str]:
    """Convenience function for getting available domains"""
    return router.get_available_domains()


if __name__ == "__main__":
    # Test examples
    test_requests = [
        "What do I get with my ChatGPT plan?",
        "Upload this file to my cloud storage",
        "Search for information about REST APIs",
        "Tell me about Google Drive capabilities",
        "Schedule a meeting for tomorrow",
        "Send a message to the team"
    ]

    for request in test_requests:
        result = route_request(request)
        print(f"Request: {request}")
        print(f"  Domain: {result.domain}")
        print(f"  Mode: {result.mode}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Method: {result.method}")
        print(f"  Remainder: {result.remainder_text}")
        print()