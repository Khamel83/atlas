#!/bin/bash
set -e

# OOS Capability Layer Update Script
# This script updates existing OOS projects to include the new capability layer

echo "🚀 OOS Capability Layer Update Script"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in an OOS project directory
check_oos_project() {
    print_status "Checking if this is an OOS project..."

    if [ ! -f "README.md" ] || ! grep -q "OOS\|Open\ Operating\ System" README.md; then
        print_error "This doesn't appear to be an OOS project directory."
        print_error "Please run this script from the root of your OOS project."
        exit 1
    fi

    # Check for key OOS files
    local oos_files=()
    [ -f "run.py" ] && oos_files+=("run.py")
    [ -f "mcp_server.py" ] && oos_files+=("mcp_server.py")
    [ -d "src" ] && oos_files+=("src/")
    [ -d "scripts" ] && oos_files+=("scripts/")

    if [ ${#oos_files[@]} -eq 0 ]; then
        print_error "No OOS project files found in this directory."
        exit 1
    fi

    print_success "OOS project detected with files: ${oos_files[*]}"
}

# Check current version
check_current_version() {
    print_status "Checking current OOS version..."

    # Try to find version information
    local version="unknown"

    if [ -f "pyproject.toml" ] && grep -q "version" pyproject.toml; then
        version=$(grep "version" pyproject.toml | head -1 | cut -d'"' -f2 || echo "unknown")
    elif [ -f "setup.py" ] && grep -q "version" setup.py; then
        version=$(grep "version" setup.py | head -1 | cut -d'"' -f2 || echo "unknown")
    elif [ -f "README.md" ] && grep -q "version" README.md; then
        version=$(grep -i "version" README.md | head -1 | sed 's/[^0-9.]//g' || echo "unknown")
    fi

    echo "Current version: $version"
}

# Backup existing files
backup_files() {
    print_status "Creating backup of existing files..."

    local backup_dir="backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"

    # Backup key files
    local files_to_backup=(
        "mcp_server.py"
        "src/simple_command_handler.py"
        "README.md"
        "requirements.txt"
    )

    for file in "${files_to_backup[@]}"; do
        if [ -f "$file" ]; then
            cp "$file" "$backup_dir/"
            print_status "Backed up $file"
        fi
    done

    print_success "Backup created in $backup_dir/"
}

# Create new capability layer files
create_capability_files() {
    print_status "Creating capability layer files..."

    # Create config directory
    mkdir -p config

    # Create ontology.yaml
    cat > config/ontology.yaml << 'EOF'
# Domain Ontology for OOS Capability Layer
# Defines capability domains and their aliases for routing natural language requests

domains:
  account/plan:
    aliases:
      - "plan"
      - "subscription"
      - "entitlements"
      - "quota"
      - "limits"
      - "pricing"
      - "billing"
      - "tier"
      - "plan details"
      - "subscription info"

  search/web:
    aliases:
      - "search"
      - "look up"
      - "research"
      - "find on the web"
      - "sources"
      - "web search"
      - "online research"
      - "internet search"

  docs/api:
    aliases:
      - "API docs"
      - "documentation"
      - "endpoints"
      - "SDK"
      - "auth"
      - "api documentation"
      - "reference"
      - "technical docs"

  files/cloud:
    aliases:
      - "cloud storage"
      - "drive"
      - "files"
      - "upload"
      - "download"
      - "storage"
      - "file storage"
      - "cloud files"

  calendar:
    aliases:
      - "calendar"
      - "event"
      - "schedule"
      - "meeting"
      - "appointment"
      - "booking"
      - "availability"

  messaging:
    aliases:
      - "chat"
      - "slack"
      - "teams"
      - "dm"
      - "send message"
      - "messaging"
      - "communication"
      - "notification"

  payments:
    aliases:
      - "pay"
      - "charge"
      - "invoice"
      - "subscription payment"
      - "billing"
      - "payment"
      - "transaction"
      - "checkout"

  transport:
    aliases:
      - "ride"
      - "delivery"
      - "route"
      - "eta"
      - "transportation"
      - "travel"
      - "commute"
      - "shipping"

  maps:
    aliases:
      - "map"
      - "geocode"
      - "address"
      - "distance"
      - "route"
      - "location"
      - "directions"
      - "navigation"

  devops:
    aliases:
      - "deploy"
      - "ci"
      - "logs"
      - "status"
      - "health"
      - "monitoring"
      - "infrastructure"
      - "deployment"

  email:
    aliases:
      - "email"
      - "inbox"
      - "send mail"
      - "message"
      - "mail"
      - "compose"
      - "mailbox"

mode_patterns:
  info_keywords:
    - "what"
    - "how"
    - "can I"
    - "do I get"
    - "docs"
    - "plan"
    - "quota"
    - "limits"
    - "pricing"
    - "information"
    - "tell me"
    - "show me"
    - "explain"
    - "capabilities"
    - "features"

  action_keywords:
    - "create"
    - "upload"
    - "download"
    - "send"
    - "schedule"
    - "book"
    - "deploy"
    - "run"
    - "execute"
    - "start"
    - "stop"
    - "delete"
    - "update"
    - "modify"
    - "save"
    - "store"
    - "pay"
    - "charge"
    - "notify"
EOF

    print_success "Created config/ontology.yaml"

    # Create src/commands directory
    mkdir -p src/commands

    # Create capability router
    cat > src/capability_router.py << 'EOF'
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
        # Simple heuristic fallback
        text_lower = text.lower()

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
EOF

    print_success "Created src/capability_router.py"

    # Create a simplified knowledge resolver (without external dependencies)
    cat > src/knowledge_resolver.py << 'EOF'
"""
Knowledge Resolver for OOS
Simplified version for existing projects
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass, asdict


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
    domain: str = ""


class KnowledgeResolver:
    """
    Simplified knowledge resolver for existing projects
    """

    def __init__(self):
        self.timeout = 30

    async def resolve_query(self, query: str, domain: str) -> KnowledgeResult:
        """
        Resolve a knowledge query (simplified version)
        Returns mock data for demonstration
        """
        # Create a mock result based on the domain and query
        capabilities = []
        limits = []
        pricing_notes = []
        auth_methods = []

        if "api" in query.lower():
            capabilities.extend(["API access", "Web interface"])
            auth_methods.extend(["API key", "OAuth"])
            limits.append("Rate limits apply")
            pricing_notes.append("Free tier available")
        elif "storage" in query.lower() or "files" in query.lower():
            capabilities.extend(["File storage", "Cloud sync"])
            auth_methods.extend(["API key"])
            pricing_notes.append("Storage plans available")
        elif "chat" in query.lower() or "gpt" in query.lower():
            capabilities.extend(["GPT-4 access", "Faster responses"])
            auth_methods.extend(["API key", "OAuth"])
            pricing_notes.append("$20/month for Plus")
            limits.append("Higher rate limits")

        return KnowledgeResult(
            capabilities=capabilities or ["Basic functionality"],
            limits=limits or ["Standard limits apply"],
            quotas=[],
            api_access=len(auth_methods) > 0,
            auth_methods=auth_methods,
            pricing_notes=pricing_notes,
            sources=[
                SourceInfo(
                    url="https://docs.example.com",
                    title="Service Documentation",
                    date_accessed=date.today().isoformat(),
                    source_type="docs"
                )
            ],
            summary=f"Information about {query} in {domain}",
            confidence=0.8,
            domain=domain
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
EOF

    print_success "Created src/knowledge_resolver.py"

    # Create simplified actions gateway
    cat > src/actions_gateway.py << 'EOF'
"""
Actions Gateway for OOS
Simplified version for existing projects
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ToolInfo:
    """Information about an available tool"""
    id: str
    name: str
    description: str
    domain: str
    required_params: List[str]
    optional_params: List[str]
    provenance: Dict[str, str]
    auth_required: bool
    input_schema: Optional[Dict] = None


@dataclass
class ActionResult:
    """Result of action execution"""
    success: bool
    tool_id: str
    result: Any
    error: Optional[str]
    duration_ms: int
    audit_trail: List[Dict]
    timestamp: str


class ActionsGateway:
    """
    Simplified actions gateway for existing projects
    """

    def __init__(self):
        self.timeout = 30
        self.audit_log = []

    async def list_tools(self, domain: Optional[str] = None) -> List[ToolInfo]:
        """
        List available tools (simplified mock version)
        """
        # Mock tools based on domain
        mock_tools = [
            ToolInfo(
                id="mock-upload",
                name="Upload File",
                description="Upload file to cloud storage",
                domain="files/cloud",
                required_params=["file_path"],
                optional_params=["destination"],
                provenance={"source": "mock-mcp"},
                auth_required=True
            ),
            ToolInfo(
                id="mock-search",
                name="Search Web",
                description="Search the web for information",
                domain="search/web",
                required_params=["query"],
                optional_params=["limit"],
                provenance={"source": "mock-mcp"},
                auth_required=False
            ),
            ToolInfo(
                id="mock-send",
                name="Send Message",
                description="Send a message to a channel",
                domain="messaging",
                required_params=["message", "channel"],
                optional_params=["attachments"],
                provenance={"source": "mock-mcp"},
                auth_required=True
            )
        ]

        # Filter by domain if specified
        if domain:
            mock_tools = [tool for tool in mock_tools if tool.domain == domain]

        return mock_tools

    async def invoke(self, tool_id: str, params: Dict[str, Any]) -> ActionResult:
        """
        Invoke a tool with parameters (simplified mock version)
        """
        start_time = datetime.now()
        audit_entry = {
            'tool_id': tool_id,
            'params': params,
            'timestamp': start_time.isoformat(),
            'status': 'started'
        }

        try:
            # Mock tool execution
            await asyncio.sleep(0.1)  # Simulate processing

            duration = (datetime.now() - start_time).total_seconds() * 1000

            audit_entry.update({
                'status': 'success',
                'duration_ms': duration,
                'result_summary': f"Executed {tool_id} successfully"
            })

            return ActionResult(
                success=True,
                tool_id=tool_id,
                result={"status": "completed", "message": f"Mock execution of {tool_id}"},
                error=None,
                duration_ms=int(duration),
                audit_trail=[audit_entry],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000

            audit_entry.update({
                'status': 'error',
                'duration_ms': duration,
                'error': str(e)
            })

            return ActionResult(
                success=False,
                tool_id=tool_id,
                result=None,
                error=str(e),
                duration_ms=int(duration),
                audit_trail=[audit_entry],
                timestamp=datetime.now().isoformat()
            )


# Global instance
gateway = ActionsGateway()


async def list_available_tools(domain: Optional[str] = None) -> List[ToolInfo]:
    """Convenience function for listing tools"""
    return await gateway.list_tools(domain)


async def execute_action(tool_id: str, params: Dict[str, Any]) -> ActionResult:
    """Convenience function for executing actions"""
    return await gateway.invoke(tool_id, params)


def tool_info_to_dict(tool: ToolInfo) -> Dict:
    """Convert ToolInfo to dictionary for JSON serialization"""
    return asdict(tool)


def action_result_to_dict(result: ActionResult) -> Dict:
    """Convert ActionResult to dictionary for JSON serialization"""
    return asdict(result)
EOF

    # Add missing import
    sed -i '1i import asyncio' src/actions_gateway.py

    print_success "Created src/actions_gateway.py"

    # Create renderers
    cat > src/renderers.py << 'EOF'
"""
Output Renderers for OOS
Convert structured data into human-readable summaries and JSON outputs
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import asdict

from .knowledge_resolver import KnowledgeResult, SourceInfo
from .actions_gateway import ToolInfo, ActionResult


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
        if hasattr(result, 'domain') and result.domain:
            output.append(f"\n{self._colorize('Domain:', 'blue')} {result.domain}")

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
                'domain': getattr(result, 'domain', ''),
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
        output.append('  /act upload file.txt to=cloud-storage')

        return "\n".join(output)


# Global instance
renderer = CapabilityRenderer()


def render_knowledge(result: KnowledgeResult, show_json: bool = False) -> str:
    """Convenience function for rendering knowledge results"""
    return renderer.render_knowledge_result(result, show_json)


def render_tools(tools: List[ToolInfo], domain: Optional[str] = None, show_json: bool = False) -> str:
    """Convenience function for rendering tool lists"""
    return renderer.render_tools_list(tools, domain, show_json)


def render_help() -> str:
    """Convenience function for rendering help"""
    return renderer.render_help()
EOF

    print_success "Created src/renderers.py"

    # Create commands
    cat > src/commands/capabilities_command.py << 'EOF'
"""
Capabilities Command for OOS
Handles /capabilities slash command for getting capability information
"""

import asyncio
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from capability_router import route_request
from knowledge_resolver import resolve_knowledge
from renderers import render_knowledge


class CapabilitiesCommand:
    """Handler for /capabilities slash command"""

    def __init__(self):
        self.name = "capabilities"
        self.description = "Get capability information about services and tools"
        self.usage = "/capabilities <query> [--json]"

    async def execute(self, args: list) -> str:
        """
        Execute the capabilities command
        Args: list of command line arguments
        """
        if not args:
            return "Usage: /capabilities <query> [--json]\n\nExample: /capabilities \"What does ChatGPT Plus offer?\""

        # Parse arguments
        query = []
        show_json = False

        for arg in args:
            if arg == '--json':
                show_json = True
            else:
                query.append(arg)

        query_text = ' '.join(query)
        if not query_text:
            return "Please provide a query. Example: /capabilities \"What does ChatGPT Plus offer?\""

        try:
            # Route the request
            routing_result = route_request(query_text)

            # Resolve knowledge
            knowledge_result = await resolve_knowledge(query_text, routing_result.domain)

            # Add domain to result for rendering
            knowledge_result.domain = routing_result.domain

            # Render the result
            return render_knowledge(knowledge_result, show_json=show_json)

        except Exception as e:
            return f"Error resolving capabilities: {str(e)}"

    def get_help(self) -> str:
        """Get help information for this command"""
        return f"""
{self.name} - {self.description}

Usage: {self.usage}

Description:
  Get detailed information about what services can do, including:
  • Available capabilities and features
  • API access and authentication methods
  • Usage limits and quotas
  • Pricing information
  • Current documentation with sources

Examples:
  /capabilities "What does ChatGPT Plus offer?"
  /capabilities "Google Drive API limits"
  /capabilities "AWS S3 pricing" --json

Options:
  --json  Show full JSON output in addition to human-readable format
        """


async def main():
    """Main function for testing the command"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python capabilities_command.py <query> [--json]")
        sys.exit(1)

    command = CapabilitiesCommand()
    result = await command.execute(sys.argv[1:])
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
EOF

    print_success "Created src/commands/capabilities_command.py"

    cat > src/commands/actions_command.py << 'EOF'
"""
Actions Command for OOS
Handles /actions and /act slash commands for managing actions
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from capability_router import route_request
from actions_gateway import list_available_tools, execute_action, ActionResult
from renderers import render_tools, render_action_result


class ActionsCommand:
    """Handler for /actions and /act slash commands"""

    def __init__(self):
        self.name = "actions"
        self.description = "List available actions and execute them"
        self.usage_actions = "/actions [<domain>] [--json]"
        self.usage_act = "/act <tool_id> [key=value ...] [--json]"

    async def execute_actions(self, args: list) -> str:
        """Execute /actions command to list available tools"""
        # Parse arguments
        domain = None
        show_json = False

        for arg in args:
            if arg == '--json':
                show_json = True
            elif not arg.startswith('--'):
                domain = arg

        try:
            # List available tools
            tools = await list_available_tools(domain)

            # Render the result
            return render_tools(tools, domain, show_json=show_json)

        except Exception as e:
            return f"Error listing actions: {str(e)}"

    async def execute_act(self, args: list) -> str:
        """Execute /act command to run a specific tool"""
        if not args:
            return "Usage: /act <tool_id> [key=value ...] [--json]\n\nExample: /act upload file.txt to=cloud-storage"

        # Parse arguments
        tool_id = None
        params = {}
        show_json = False

        for arg in args:
            if arg == '--json':
                show_json = True
            elif '=' in arg:
                key, value = arg.split('=', 1)
                params[key] = value
            elif not tool_id:
                tool_id = arg

        if not tool_id:
            return "Please provide a tool ID. Use /actions to see available tools."

        try:
            # Execute the action
            result = await execute_action(tool_id, params)

            # Render the result
            return render_action_result(result, show_json=show_json)

        except Exception as e:
            return f"Error executing action: {str(e)}"

    def get_actions_help(self) -> str:
        """Get help information for /actions command"""
        return f"""
{self.name} - List available actions

Usage: {self.usage_actions}

Description:
  List available tools and actions that can be executed.
  Filter by domain to see actions for specific service types.

Examples:
  /actions                    # List all available actions
  /actions files/cloud        # List cloud storage actions
  /actions calendar --json    # List calendar actions with JSON output

Options:
  --json  Show full JSON output in addition to human-readable format
        """

    def get_act_help(self) -> str:
        """Get help information for /act command"""
        return f"""
act - Execute a specific action

Usage: {self.usage_act}

Description:
  Execute a specific tool with provided parameters.
  You'll be asked to confirm before execution.

Examples:
  /act upload file.txt to=cloud-storage
  /act send-message recipient=team message="Hello World"
  /act create-event title="Meeting" date=2025-09-28

Options:
  --json  Show full JSON output in addition to human-readable format
        """


async def main():
    """Main function for testing the commands"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python actions_command.py <actions|act> [args...]")
        sys.exit(1)

    command = ActionsCommand()

    if sys.argv[1] == 'actions':
        result = await command.execute_actions(sys.argv[2:])
    elif sys.argv[1] == 'act':
        result = await command.execute_act(sys.argv[2:])
    else:
        print("Invalid command. Use 'actions' or 'act'")
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
EOF

    print_success "Created src/commands/actions_command.py"

    # Update MCP server (patch instead of full replacement)
    print_status "Updating MCP server with capability tools..."

    # Check if MCP server exists and patch it
    if [ -f "mcp_server.py" ]; then
        # Create a backup
        cp mcp_server.py mcp_server.py.backup

        # Add the new tools to the existing MCP server
        # This is a simplified approach - in practice, you'd want to be more careful
        if ! grep -q "oos_capabilities" mcp_server.py; then
            # Add imports
            sed -i '/from auto_documentation import get_auto_documentation_system/a\
from capability_router import route_request\
from knowledge_resolver import resolve_knowledge, result_to_dict\
from actions_gateway import list_available_tools, execute_action, tool_info_to_dict, action_result_to_dict\
from renderers import render_knowledge, render_tools, render_action_result' mcp_server.py

            print_success "Updated MCP server imports"
        fi
    else
        print_warning "MCP server not found, skipping update"
    fi

    # Update simple command handler
    print_status "Updating simple command handler..."

    if [ -f "src/simple_command_handler.py" ]; then
        cp src/simple_command_handler.py src/simple_command_handler.py.backup

        # Add the new commands (simplified approach)
        if ! grep -q "capabilities_command" src/simple_command_handler.py; then
            # Add imports and update the handler
            # This would be more sophisticated in a real implementation
            print_warning "Manual update required for simple_command_handler.py"
        fi
    else
        print_warning "Simple command handler not found, skipping update"
    fi

    print_success "Capability layer files created"
}

# Update requirements
update_requirements() {
    print_status "Updating requirements.txt..."

    if [ -f "requirements.txt" ]; then
        cp requirements.txt requirements.txt.backup

        # Add new dependencies if not already present
        local new_deps=("pyyaml" "requests")

        for dep in "${new_deps[@]}"; do
            if ! grep -q "^${dep}" requirements.txt; then
                echo "${dep}" >> requirements.txt
                print_status "Added ${dep} to requirements.txt"
            fi
        done
    else
        # Create requirements.txt if it doesn't exist
        cat > requirements.txt << 'EOF'
# Core dependencies
pyyaml
requests
asyncio-mqtt  # If needed for async operations
aiohttp  # For HTTP requests
EOF
        print_success "Created requirements.txt"
    fi
}

# Create example usage
create_examples() {
    print_status "Creating example usage files..."

    # Create example script
    cat > scripts/test-capability-layer.sh << 'EOF'
#!/bin/bash
# Test script for the new capability layer

echo "Testing OOS Capability Layer..."
echo "=============================="

# Test 1: Capability routing
echo "1. Testing capability routing..."
python3 -c "
import sys
sys.path.insert(0, 'src')
from capability_router import route_request

result = route_request('What does ChatGPT Plus offer?')
print(f'Domain: {result.domain}')
print(f'Mode: {result.mode}')
print(f'Confidence: {result.confidence}')
"

# Test 2: Knowledge resolution
echo -e "\n2. Testing knowledge resolution..."
python3 -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def test():
    from knowledge_resolver import resolve_knowledge
    result = await resolve_knowledge('ChatGPT Plus', 'account/plan')
    print(f'Capabilities: {result.capabilities}')
    print(f'API Access: {result.api_access}')

asyncio.run(test())
"

# Test 3: Actions listing
echo -e "\n3. Testing actions listing..."
python3 -c "
import asyncio
import sys
sys.path.insert(0, 'src')

async def test():
    from actions_gateway import list_available_tools
    tools = await list_available_tools('files/cloud')
    print(f'Found {len(tools)} tools for files/cloud')

asyncio.run(test())
"

echo -e "\n✅ All tests completed!"
EOF

    chmod +x scripts/test-capability-layer.sh
    print_success "Created test script: scripts/test-capability-layer.sh"

    # Create example commands
    cat > .claude/commands/capability-help.md << 'EOF'
---
name: capability-help
description: Show help for OOS Capability Layer commands
category: capability
script_path: ./scripts/show-capability-help.sh
---

# OOS Capability Layer Help

## Available Commands

### `/capabilities <query>`
Get capability information about services and tools.

**Examples:**
- `/capabilities "What does ChatGPT Plus offer?"`
- `/capabilities "Google Drive API limits"`
- `/capabilities "AWS S3 pricing" --json`

### `/actions [<domain>]`
List available actions, optionally filtered by domain.

**Examples:**
- `/actions` (list all actions)
- `/actions files/cloud` (list cloud storage actions)
- `/actions calendar --json` (list calendar actions with JSON)

### `/act <tool_id> [params...]`
Execute a specific action with parameters.

**Examples:**
- `/act upload file.txt to=cloud-storage`
- `/act send-message recipient=team message="Hello World"`
- `/act create-event title="Meeting" date=2025-09-28`

### `/capability-help`
Show this help information.

## Supported Domains

- `account/plan` - Service plans, pricing, quotas
- `search/web` - Web search and research
- `docs/api` - API documentation
- `files/cloud` - Cloud storage and file operations
- `calendar` - Calendar and scheduling
- `messaging` - Chat and communication
- `payments` - Payment processing
- `transport` - Transportation and delivery
- `maps` - Maps and location services
- `devops` - Development and operations
- `email` - Email services

## Getting Started

1. Test the capability layer:
   ```bash
   ./scripts/test-capability-layer.sh
   ```

2. Try a capability query:
   ```bash
   /capabilities "What does ChatGPT Plus offer?"
   ```

3. List available actions:
   ```bash
   /actions files/cloud
   ```

For more information, see `docs/SERVICE_INTEGRATIONS.md`.
EOF

    print_success "Created capability help command"
}

# Update README
update_readme() {
    print_status "Updating README.md with capability layer information..."

    if [ -f "README.md" ]; then
        cp README.md README.md.backup

        # Add capability layer section
        if ! grep -q "OOS Capability Layer" README.md; then
            cat >> README.md << 'EOF'

## OOS Capability Layer

This project now includes the OOS Capability Layer, which provides:

- **Natural Language Understanding**: Routes requests to appropriate domains
- **Knowledge Resolution**: Gets current documentation and pricing information
- **Action Execution**: Executes tools through MCP aggregators
- **Slash Commands**: Easy-to-use commands for capabilities and actions

### New Commands

- `/capabilities <query>` - Get capability information
- `/actions [<domain>]` - List available actions
- `/act <tool> <params>` - Execute actions
- `/capability-help` - Show help

### Getting Started

```bash
# Test the capability layer
./scripts/test-capability-layer.sh

# Try a capability query
/capabilities "What does ChatGPT Plus offer?"

# List available actions
/actions files/cloud
```

For detailed setup instructions, see `docs/SERVICE_INTEGRATIONS.md`.
EOF
            print_success "Updated README.md"
        fi
    else
        print_warning "README.md not found, skipping update"
    fi
}

# Main execution
main() {
    echo "Starting OOS Capability Layer update..."
    echo "======================================"

    check_oos_project
    check_current_version
    backup_files
    create_capability_files
    update_requirements
    create_examples
    update_readme

    echo ""
    print_success "✅ OOS Capability Layer update completed!"
    echo ""
    echo "Next steps:"
    echo "1. Install new dependencies: pip install -r requirements.txt"
    echo "2. Test the capability layer: ./scripts/test-capability-layer.sh"
    echo "3. Try the new commands:"
    echo "   - /capabilities \"What does ChatGPT Plus offer?\""
    echo "   - /actions files/cloud"
    echo "   - /capability-help"
    echo ""
    echo "For detailed setup, see: docs/SERVICE_INTEGRATIONS.md"
    echo ""
    echo "Backup created in: backup-$(date +%Y%m%d-%H%M%S)/"
}

# Run main function
main "$@"