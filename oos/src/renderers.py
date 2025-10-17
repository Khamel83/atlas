"""
Output Renderers for OOS
Convert structured data into human-readable summaries and JSON outputs
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import asdict

from knowledge_resolver import KnowledgeResult, SourceInfo
from actions_gateway import ToolInfo, ActionResult


# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'
    INFO = '\033[96m'  # Same as CYAN for info messages


class CapabilityRenderer:
    """Renders capability/knowledge results in human-readable format"""

    def __init__(self):
        self.colors_enabled = self._check_color_support()

    def _check_color_support(self) -> bool:
        """Check if terminal supports colors"""
        import sys
        return sys.stdout.isatty()

    def _colorize(self, text: str, color: str) -> str:
        """Add color to text if colors are enabled"""
        if not self.colors_enabled:
            return text

        colors = {
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'reset': '\033[0m'
        }

        return f"{colors.get(color, '')}{text}{colors['reset']}"

    def render_knowledge_result(self, result: KnowledgeResult, show_json: bool = False) -> str:
        """Render knowledge result in human-readable format"""
        output = []

        # Header
        output.append(self._colorize("📋 Capability Information", "cyan"))
        output.append("=" * 50)

        # Domain info
        output.append(f"\n{self._colorize('Domain:', 'blue')} {result.domain}")
        output.append(f"{self._colorize('Confidence:', 'blue')} {result.confidence:.0%}")

        # Capabilities
        if result.capabilities:
            output.append(f"\n{self._colorize('🚀 Capabilities:', 'green')}")
            for cap in result.capabilities:
                output.append(f"  • {cap}")

        # API Access
        if result.api_access:
            output.append(f"\n{self._colorize('🔌 API Access:', 'green')} Available")
            if result.auth_methods:
                output.append(f"{self._colorize('   Auth Methods:', 'blue')}")
                for method in result.auth_methods:
                    output.append(f"    • {method}")

        # Limits and Quotas
        if result.limits:
            output.append(f"\n{self._colorize('⚠️  Limits:', 'yellow')}")
            for limit in result.limits:
                output.append(f"  • {limit}")

        if result.quotas:
            output.append(f"\n{self._colorize('📊 Quotas:', 'yellow')}")
            for quota in result.quotas:
                output.append(f"  • {quota.name}: {quota.value} ({quota.period})")
                if quota.description:
                    output.append(f"    {quota.description}")

        # Pricing
        if result.pricing_notes:
            output.append(f"\n{self._colorize('💰 Pricing:', 'yellow')}")
            for note in result.pricing_notes:
                output.append(f"  • {note}")

        # Summary
        if result.summary:
            output.append(f"\n{self._colorize('📝 Summary:', 'white')}")
            output.append(f"  {result.summary}")

        # Sources
        if result.sources:
            output.append(f"\n{self._colorize('🔗 Sources:', 'blue')}")
            for i, source in enumerate(result.sources, 1):
                output.append(f"  {i}. {source.title}")
                output.append(f"     {source.url} ({source.date_accessed})")

        # JSON output if requested
        if show_json:
            output.append(f"\n{self._colorize('📄 JSON Output:', 'cyan')}")
            json_data = {
                'domain': result.domain,
                'capabilities': result.capabilities,
                'limits': result.limits,
                'quotas': [asdict(q) for q in result.quotas],
                'api_access': result.api_access,
                'auth_methods': result.auth_methods,
                'pricing_notes': result.pricing_notes,
                'sources': [asdict(s) for s in result.sources],
                'summary': result.summary,
                'confidence': result.confidence
            }
            output.append("```json")
            output.append(json.dumps(json_data, indent=2))
            output.append("```")

        return "\n".join(output)

    def render_tools_list(self, tools: List[ToolInfo], domain: Optional[str] = None, show_json: bool = False) -> str:
        """Render list of available tools"""
        output = []

        # Header
        title = f"Available Tools for {domain}" if domain else "Available Tools"
        output.append(self._colorize(f"🔧 {title}", "cyan"))
        output.append("=" * 50)

        if not tools:
            output.append("\nNo tools available.")
            return "\n".join(output)

        # Group by domain
        by_domain = {}
        for tool in tools:
            domain_key = tool.domain or 'general'
            if domain_key not in by_domain:
                by_domain[domain_key] = []
            by_domain[domain_key].append(tool)

        for domain_name, domain_tools in by_domain.items():
            output.append(f"\n{self._colorize(f'📂 {domain_name.title()}:', 'blue')}")

            for tool in domain_tools:
                output.append(f"\n  {self._colorize(tool.name, 'green')}")
                output.append(f"    ID: {tool.id}")
                output.append(f"    {tool.description}")

                if tool.auth_required:
                    output.append(f"    {self._colorize('🔒 Authentication Required', 'yellow')}")

                if tool.required_params:
                    output.append(f"    Required: {', '.join(tool.required_params)}")

                if tool.optional_params:
                    output.append(f"    Optional: {', '.join(tool.optional_params)}")

                if tool.provenance.get('source'):
                    source = tool.provenance['source']
                    output.append(f"    Source: {source}")

        # JSON output if requested
        if show_json:
            output.append(f"\n{self._colorize('📄 JSON Output:', 'cyan')}")
            json_data = {
                'domain': domain,
                'tools': [asdict(tool) for tool in tools],
                'count': len(tools)
            }
            output.append("```json")
            output.append(json.dumps(json_data, indent=2))
            output.append("```")

        return "\n".join(output)

    def render_action_result(self, result: ActionResult, show_json: bool = False) -> str:
        """Render action execution result"""
        output = []

        # Header
        status_color = 'green' if result.success else 'red'
        status_icon = '✅' if result.success else '❌'
        status_text = 'Success' if result.success else 'Failed'

        output.append(self._colorize(f"{status_icon} Action Result", status_color))
        output.append("=" * 50)
        output.append(f"\nTool: {result.tool_id}")
        output.append(f"Duration: {result.duration_ms}ms")
        output.append(f"Timestamp: {result.timestamp}")

        if result.error:
            output.append(f"\n{self._colorize('❌ Error:', 'red')} {result.error}")

        if result.success and result.result:
            output.append(f"\n{self._colorize('📤 Result:', 'green')}")
            if isinstance(result.result, dict):
                for key, value in result.result.items():
                    output.append(f"  {key}: {value}")
            elif isinstance(result.result, list):
                output.append(f"  {len(result.result)} items returned")
            else:
                output.append(f"  {result.result}")

        # Audit trail
        if result.audit_trail:
            output.append(f"\n{self._colorize('🔍 Audit Trail:', 'blue')}")
            for entry in result.audit_trail:
                output.append(f"  {entry['timestamp']}: {entry['status']}")
                if 'error' in entry:
                    output.append(f"    Error: {entry['error']}")

        # JSON output if requested
        if show_json:
            output.append(f"\n{self._colorize('📄 JSON Output:', 'cyan')}")
            json_data = asdict(result)
            output.append("```json")
            output.append(json.dumps(json_data, indent=2))
            output.append("```")

        return "\n".join(output)

    def render_routing_result(self, routing_result) -> str:
        """Render routing result for debugging"""
        output = []

        output.append(self._colorize("🔀 Routing Analysis", "cyan"))
        output.append("=" * 50)

        output.append(f"\nDomain: {routing_result.domain}")
        output.append(f"Mode: {routing_result.mode}")
        output.append(f"Confidence: {routing_result.confidence:.0%}")
        output.append(f"Method: {routing_result.method}")
        output.append(f"Matched: '{routing_result.matched_text}'")
        output.append(f"Remainder: '{routing_result.remainder_text}'")

        return "\n".join(output)

    def render_help(self) -> str:
        """Render help information for capability layer"""
        output = []

        output.append(self._colorize("🚀 OOS Capability Layer", "cyan"))
        output.append("=" * 50)

        output.append("\nThe OOS Capability Layer helps you:")
        output.append("  • Understand what services can do")
        output.append("  • Get current documentation and pricing")
        output.append("  • Execute actions when appropriate")

        output.append(f"\n{self._colorize('📋 Available Commands:', 'green')}")
        output.append("  /capabilities <query>    - Get capability information")
        output.append("  /actions <domain>       - List available actions")
        output.append("  /act <tool> <params>    - Execute a specific action")

        output.append(f"\n{self._colorize('🔍 Supported Domains:', 'blue')}")
        domains = [
            "account/plan", "search/web", "docs/api", "files/cloud",
            "calendar", "messaging", "payments", "transport",
            "maps", "devops", "email"
        ]
        for domain in domains:
            output.append(f"  • {domain}")

        output.append(f"\n{self._colorize('💡 Examples:', 'yellow')}")
        output.append('  /capabilities "What does ChatGPT Plus offer?"')
        output.append('  /actions files/cloud')
        output.append('  /act upload file.txt to cloud-storage')

        return "\n".join(output)


# Global instance
renderer = CapabilityRenderer()


def render_knowledge(result: KnowledgeResult, show_json: bool = False) -> str:
    """Convenience function for rendering knowledge results"""
    return renderer.render_knowledge_result(result, show_json)


def render_tools(tools: List[ToolInfo], domain: Optional[str] = None, show_json: bool = False) -> str:
    """Convenience function for rendering tool lists"""
    return renderer.render_tools_list(tools, domain, show_json)


def render_routing(routing_result) -> str:
    """Convenience function for rendering routing results"""
    return renderer.render_routing_result(routing_result)


def render_help() -> str:
    """Convenience function for rendering help"""
    return renderer.render_help()


if __name__ == "__main__":
    # Test rendering with sample data
    from .knowledge_resolver import KnowledgeResult, SourceInfo, QuotaInfo

    sample_result = KnowledgeResult(
        domain="account/plan",
        capabilities=["API access", "Web interface", "File storage"],
        limits=["Rate limits apply"],
        quotas=[
            QuotaInfo(name="API calls", value="1000/day", period="daily"),
            QuotaInfo(name="Storage", value="10GB", period="monthly")
        ],
        api_access=True,
        auth_methods=["API key", "OAuth"],
        pricing_notes=["Free tier available", "Pro tier: $20/month"],
        sources=[
            SourceInfo(
                url="https://example.com/docs",
                title="Service Documentation",
                date_accessed="2025-09-27",
                source_type="docs"
            )
        ],
        summary="This service offers comprehensive capabilities including...",
        confidence=0.85
    )

    print(render_knowledge(sample_result, show_json=True))
    print("\n" + "="*60 + "\n")
    print(render_help())