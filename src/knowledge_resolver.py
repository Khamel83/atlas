"""
Knowledge Resolver for OOS
Integrates multiple documentation sources to provide normalized answers
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass, asdict
import requests


@dataclass
class SourceInfo:
    """Information about a knowledge source"""
    url: str
    title: str
    date_accessed: str
    source_type: str  # "docs", "web", "api"


@dataclass
class QuotaInfo:
    """Information about service quotas/limits"""
    name: str
    value: str
    period: str
    description: str = ""


@dataclass
class KnowledgeResult:
    """Normalized knowledge query result"""
    capabilities: List[str]
    limits: List[str]
    quotas: List[QuotaInfo]
    api_access: bool
    auth_methods: List[str]
    pricing_notes: List[str]
    sources: List[SourceInfo]
    summary: str
    confidence: float


class KnowledgeResolver:
    """
    Resolves knowledge queries using multiple adapters:
    1. Context7 (official docs)
    2. Docs MCP (indexed documentation)
    3. Deep-Research MCP (web research)
    """

    def __init__(self):
        self.adapters = {
            'context7': Context7Adapter(),
            'docs_mcp': DocsMCPAdapter(),
            'deep_research': DeepResearchAdapter()
        }
        self.timeout = int(os.getenv('KNOWLEDGE_TIMEOUT', '30'))

    async def resolve_query(self, query: str, domain: str) -> KnowledgeResult:
        """
        Resolve a knowledge query using available adapters
        Tries adapters in order until one returns a result
        """
        # Try adapters in order of preference
        for adapter_name in ['context7', 'docs_mcp', 'deep_research']:
            try:
                adapter = self.adapters[adapter_name]
                if await adapter.is_available():
                    result = await adapter.query(query, domain)
                    if result and result.confidence > 0.5:
                        return result
            except Exception as e:
                print(f"Adapter {adapter_name} failed: {e}")
                continue

        # Fallback empty result
        return KnowledgeResult(
            capabilities=[],
            limits=[],
            quotas=[],
            api_access=False,
            auth_methods=[],
            pricing_notes=[],
            sources=[],
            summary="No information available for this query.",
            confidence=0.0
        )


class Context7Adapter:
    """Adapter for Context7 (official documentation)"""

    def __init__(self):
        self.base_url = os.getenv('CONTEXT7_URL', 'http://localhost:8080')
        self.api_key = os.getenv('CONTEXT7_API_KEY')

    async def is_available(self) -> bool:
        """Check if Context7 is available"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    async def query(self, query: str, domain: str) -> Optional[KnowledgeResult]:
        """Query Context7 for documentation"""
        try:
            # Try to resolve library URI first
            library_response = requests.post(
                f"{self.base_url}/resolve-library-uri",
                json={"libraryName": query.split()[0] if query.split() else query},
                timeout=self.timeout
            )

            if library_response.status_code != 200:
                return None

            library_data = library_response.json()
            resource_uri = library_data.get('resourceUri')

            if not resource_uri:
                return None

            # Search documentation
            docs_response = requests.post(
                f"{self.base_url}/search-library-docs",
                json={
                    "resourceURI": resource_uri,
                    "topic": query,
                    "tokens": 5000
                },
                timeout=self.timeout
            )

            if docs_response.status_code != 200:
                return None

            docs_data = docs_response.json()
            return self._normalize_context7_result(docs_data, query, domain)

        except Exception as e:
            print(f"Context7 query failed: {e}")
            return None

    def _normalize_context7_result(self, data: Dict, query: str, domain: str) -> KnowledgeResult:
        """Normalize Context7 response to standard format"""
        content = data.get('content', '')
        sources = data.get('sources', [])

        source_list = []
        for source in sources:
            source_list.append(SourceInfo(
                url=source.get('url', ''),
                title=source.get('title', ''),
                date_accessed=date.today().isoformat(),
                source_type='docs'
            ))

        # Extract capabilities from content (simple heuristic)
        capabilities = []
        limits = []
        pricing_notes = []

        if 'api' in content.lower():
            capabilities.append('API access')
        if 'web' in content.lower():
            capabilities.append('Web interface')
        if 'limit' in content.lower() or 'quota' in content.lower():
            limits.append('Usage limits apply')
        if 'price' in content.lower() or 'cost' in content.lower():
            pricing_notes.append('Pricing information available')

        return KnowledgeResult(
            capabilities=capabilities,
            limits=limits,
            quotas=[],
            api_access='API' in content,
            auth_methods=['API key'] if 'API' in content else [],
            pricing_notes=pricing_notes,
            sources=source_list,
            summary=content[:500] + '...' if len(content) > 500 else content,
            confidence=0.8
        )


class DocsMCPAdapter:
    """Adapter for Docs MCP (indexed documentation)"""

    def __init__(self):
        self.server_url = os.getenv('DOCS_MCP_URL', 'http://localhost:8001')

    async def is_available(self) -> bool:
        """Check if Docs MCP is available"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    async def query(self, query: str, domain: str) -> Optional[KnowledgeResult]:
        """Query Docs MCP for documentation"""
        try:
            response = requests.post(
                f"{self.server_url}/search",
                json={
                    "query": query,
                    "domain": domain,
                    "limit": 10
                },
                timeout=self.timeout
            )

            if response.status_code != 200:
                return None

            data = response.json()
            return self._normalize_docs_mcp_result(data, query, domain)

        except Exception as e:
            print(f"Docs MCP query failed: {e}")
            return None

    def _normalize_docs_mcp_result(self, data: Dict, query: str, domain: str) -> KnowledgeResult:
        """Normalize Docs MCP response to standard format"""
        results = data.get('results', [])
        sources = data.get('sources', [])

        source_list = []
        capabilities = set()
        limits = set()

        for result in results:
            content = result.get('content', '').lower()

            if 'api' in content:
                capabilities.add('API access')
            if 'web' in content:
                capabilities.add('Web interface')
            if 'limit' in content or 'quota' in content:
                limits.add('Usage limits apply')

        for source in sources:
            source_list.append(SourceInfo(
                url=source.get('url', ''),
                title=source.get('title', ''),
                date_accessed=date.today().isoformat(),
                source_type='docs'
            ))

        return KnowledgeResult(
            capabilities=list(capabilities),
            limits=list(limits),
            quotas=[],
            api_access='API' in [c.lower() for c in capabilities],
            auth_methods=['API key', 'OAuth'] if 'API' in [c.lower() for c in capabilities] else [],
            pricing_notes=[],
            sources=source_list,
            summary=f"Found {len(results)} relevant documents",
            confidence=0.7
        )


class DeepResearchAdapter:
    """Adapter for Deep-Research MCP (web research)"""

    def __init__(self):
        self.server_url = os.getenv('DEEP_RESEARCH_MCP_URL', 'http://localhost:8002')

    async def is_available(self) -> bool:
        """Check if Deep-Research MCP is available"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    async def query(self, query: str, domain: str) -> Optional[KnowledgeResult]:
        """Query Deep-Research MCP for web research"""
        try:
            response = requests.post(
                f"{self.server_url}/research",
                json={
                    "query": query,
                    "domain": domain,
                    "max_sources": 5
                },
                timeout=self.timeout
            )

            if response.status_code != 200:
                return None

            data = response.json()
            return self._normalize_deep_research_result(data, query, domain)

        except Exception as e:
            print(f"Deep-Research query failed: {e}")
            return None

    def _normalize_deep_research_result(self, data: Dict, query: str, domain: str) -> KnowledgeResult:
        """Normalize Deep-Research response to standard format"""
        findings = data.get('findings', [])
        sources = data.get('sources', [])

        source_list = []
        capabilities = set()
        limits = set()
        pricing_notes = set()

        for finding in findings:
            content = finding.get('content', '').lower()

            if 'api' in content:
                capabilities.add('API access')
            if 'web' in content:
                capabilities.add('Web interface')
            if 'limit' in content or 'quota' in content:
                limits.add('Usage limits apply')
            if 'price' in content or 'cost' in content or 'free' in content:
                pricing_notes.add('Pricing information available')

        for source in sources:
            source_list.append(SourceInfo(
                url=source.get('url', ''),
                title=source.get('title', ''),
                date_accessed=date.today().isoformat(),
                source_type='web'
            ))

        return KnowledgeResult(
            capabilities=list(capabilities),
            limits=list(limits),
            quotas=[],
            api_access='API' in [c.lower() for c in capabilities],
            auth_methods=['API key', 'OAuth'] if 'API' in [c.lower() for c in capabilities] else [],
            pricing_notes=list(pricing_notes),
            sources=source_list,
            summary=data.get('summary', 'Research completed'),
            confidence=0.6
        )


# Global instance
resolver = KnowledgeResolver()


async def resolve_knowledge(query: str, domain: str) -> KnowledgeResult:
    """Convenience function for resolving knowledge queries"""
    return await resolver.resolve_query(query, domain)


def result_to_dict(result: KnowledgeResult) -> Dict:
    """Convert KnowledgeResult to dictionary for JSON serialization"""
    data = asdict(result)
    # Convert SourceInfo objects to dicts
    data['sources'] = [asdict(source) for source in result.sources]
    # Convert QuotaInfo objects to dicts
    data['quotas'] = [asdict(quota) for quota in result.quotas]
    return data


if __name__ == "__main__":
    import asyncio

    async def test_resolver():
        query = "What capabilities does ChatGPT Plus offer?"
        domain = "account/plan"

        result = await resolve_knowledge(query, domain)
        print("Knowledge Resolution Result:")
        print(f"Capabilities: {result.capabilities}")
        print(f"API Access: {result.api_access}")
        print(f"Auth Methods: {result.auth_methods}")
        print(f"Sources: {len(result.sources)}")
        print(f"Summary: {result.summary}")

    asyncio.run(test_resolver())