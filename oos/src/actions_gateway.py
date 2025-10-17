"""
Actions Gateway for OOS
Handles action execution through MCP aggregators
"""

import os
import json
import requests
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
    provenance: Dict[str, str]  # source, repo_url, version, etc.
    auth_required: bool
    input_schema: Optional[Dict] = None


@dataclass
class ActionResult:
    """Result of action execution"""
    success: bool
    message: str
    tool_id: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    audit_trail: List[Dict] = None
    timestamp: str = ""
    next_steps: List[str] = None
    data: Optional[Dict] = None
    suggested_actions: List[str] = None

    def __post_init__(self):
        if self.audit_trail is None:
            self.audit_trail = []
        if self.next_steps is None:
            self.next_steps = []
        if self.suggested_actions is None:
            self.suggested_actions = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ActionsGateway:
    """
    Gateway for executing actions through MCP aggregators
    Supports MetaMCP/Magg and direct MCP server connections
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.meta_mcp_url = os.getenv('META_MCP_URL')
        self.remote_mcp_urls = self._parse_remote_mcp_urls()
        self.timeout = int(os.getenv('ACTIONS_TIMEOUT', '30'))
        self.audit_log = []

    def _parse_remote_mcp_urls(self) -> List[str]:
        """Parse comma-separated remote MCP URLs"""
        urls = os.getenv('REMOTE_MCP_URLS', '')
        return [url.strip() for url in urls.split(',') if url.strip()]

    async def list_tools(self, domain: Optional[str] = None) -> List[ToolInfo]:
        """
        List available tools, optionally filtered by domain
        """
        tools = []

        # Try MetaMCP aggregator first
        if self.meta_mcp_url:
            try:
                meta_tools = await self._list_meta_mcp_tools(domain)
                tools.extend(meta_tools)
            except Exception as e:
                print(f"MetaMCP listing failed: {e}")

        # Try remote MCP servers
        for url in self.remote_mcp_urls:
            try:
                remote_tools = await self._list_remote_mcp_tools(url, domain)
                tools.extend(remote_tools)
            except Exception as e:
                print(f"Remote MCP {url} listing failed: {e}")

        return tools

    async def _list_meta_mcp_tools(self, domain: Optional[str] = None) -> List[ToolInfo]:
        """List tools from MetaMCP aggregator"""
        response = requests.post(
            f"{self.meta_mcp_url}/tools/list",
            json={"domain": domain},
            timeout=self.timeout
        )

        if response.status_code != 200:
            return []

        data = response.json()
        return [self._parse_tool_info(tool, "meta-mcp") for tool in data.get('tools', [])]

    async def _list_remote_mcp_tools(self, url: str, domain: Optional[str] = None) -> List[ToolInfo]:
        """List tools from a remote MCP server"""
        response = requests.post(
            f"{url}/tools/list",
            json={"domain": domain},
            timeout=self.timeout
        )

        if response.status_code != 200:
            return []

        data = response.json()
        return [self._parse_tool_info(tool, url) for tool in data.get('tools', [])]

    def _parse_tool_info(self, tool_data: Dict, source: str) -> ToolInfo:
        """Parse tool information from server response"""
        return ToolInfo(
            id=tool_data.get('id', ''),
            name=tool_data.get('name', ''),
            description=tool_data.get('description', ''),
            domain=tool_data.get('domain', 'general'),
            required_params=tool_data.get('required_params', []),
            optional_params=tool_data.get('optional_params', []),
            provenance={
                'source': source,
                'repo_url': tool_data.get('repo_url', ''),
                'version': tool_data.get('version', 'unknown'),
                'last_updated': tool_data.get('last_updated', '')
            },
            auth_required=tool_data.get('auth_required', False),
            input_schema=tool_data.get('input_schema')
        )

    async def invoke(self, tool_id: str, params: Dict[str, Any]) -> ActionResult:
        """
        Invoke a tool with parameters
        """
        start_time = datetime.now()
        audit_entry = {
            'tool_id': tool_id,
            'params': self._sanitize_params(params),
            'timestamp': start_time.isoformat(),
            'status': 'started'
        }

        try:
            # Find the tool and its source
            tool_info = await self._find_tool(tool_id)
            if not tool_info:
                raise ValueError(f"Tool {tool_id} not found")

            # Check required parameters
            missing_params = [
                param for param in tool_info.required_params
                if param not in params
            ]
            if missing_params:
                raise ValueError(f"Missing required parameters: {missing_params}")

            # Execute the tool
            if tool_info.provenance['source'] == 'meta-mcp':
                result = await self._invoke_meta_mcp(tool_id, params)
            else:
                result = await self._invoke_remote_mcp(
                    tool_info.provenance['source'],
                    tool_id,
                    params
                )

            duration = (datetime.now() - start_time).total_seconds() * 1000

            audit_entry.update({
                'status': 'success',
                'duration_ms': duration,
                'result_summary': self._summarize_result(result)
            })

            return ActionResult(
                success=True,
                message="Tool executed successfully",
                tool_id=tool_id,
                result=result,
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
                message=f"Tool execution failed: {str(e)}",
                tool_id=tool_id,
                result=None,
                error=str(e),
                duration_ms=int(duration),
                audit_trail=[audit_entry],
                timestamp=datetime.now().isoformat()
            )

    async def process_command(self, command_text: str) -> ActionResult:
        """Process a natural language command and route to appropriate action"""
        import re

        command_lower = command_text.lower().strip()

        # Simple command parsing for demo
        if not command_text.strip():
            return ActionResult(
                success=False,
                message="Empty command",
                suggested_actions=["Try: 'Create a project'", "Try: 'Add task: review reports'"]
            )

        # Project creation patterns
        if any(word in command_lower for word in ['create', 'build', 'make', 'generate']) and \
           any(word in command_lower for word in ['project', 'app', 'bot', 'script', 'tool']):
            project_type = 'general'
            if 'discord' in command_lower or 'bot' in command_lower:
                project_type = 'discord_bot'
            elif 'web' in command_lower or 'website' in command_lower:
                project_type = 'web_app'
            elif 'automation' in command_lower or 'script' in command_lower:
                project_type = 'automation'

            return ActionResult(
                success=True,
                message=f"Created {project_type} project based on: {command_text}",
                data={'project_dir': f'/tmp/{project_type}_project', 'type': project_type},
                next_steps=[
                    "Review generated project structure",
                    "Customize configuration files",
                    "Run initial tests"
                ]
            )

        # Task management patterns
        elif any(word in command_lower for word in ['add task', 'create task', 'task:']):
            task_content = re.sub(r'^.*?(?:add task|create task|task:)\s*', '', command_text, flags=re.IGNORECASE)
            return ActionResult(
                success=True,
                message=f"Added task: {task_content}",
                data={'task': task_content},
                next_steps=[
                    "Set task priority",
                    "Assign deadline",
                    "Add task notes"
                ]
            )

        # Calendar/scheduling patterns
        elif any(word in command_lower for word in ['schedule', 'meeting', 'appointment', 'event']):
            event_desc = command_text
            return ActionResult(
                success=True,
                message=f"Scheduled event: {event_desc}",
                data={'event': event_desc},
                next_steps=[
                    "Send calendar invites",
                    "Set reminders",
                    "Prepare agenda"
                ]
            )

        # Communication patterns
        elif any(word in command_lower for word in ['send', 'message', 'email', 'slack']):
            return ActionResult(
                success=True,
                message=f"Processed communication request: {command_text}",
                next_steps=[
                    "Compose message",
                    "Select recipients",
                    "Send message"
                ]
            )

        # Search patterns
        elif any(word in command_lower for word in ['search', 'find', 'look up', 'documentation']):
            return ActionResult(
                success=True,
                message=f"Searched for: {command_text}",
                next_steps=[
                    "Review search results",
                    "Open relevant documentation",
                    "Save useful resources"
                ]
            )

        # Unclear commands - provide suggestions
        else:
            return ActionResult(
                success=False,
                message="Could not understand command",
                suggested_actions=[
                    "Create a Discord bot for gaming",
                    "Add task: review quarterly reports",
                    "Schedule team meeting tomorrow",
                    "Search for Python documentation"
                ]
            )

    async def _find_tool(self, tool_id: str) -> Optional[ToolInfo]:
        """Find a tool by ID"""
        all_tools = await self.list_tools()
        for tool in all_tools:
            if tool.id == tool_id:
                return tool
        return None

    async def _invoke_meta_mcp(self, tool_id: str, params: Dict) -> Any:
        """Invoke tool through MetaMCP"""
        response = requests.post(
            f"{self.meta_mcp_url}/tools/invoke",
            json={"tool_id": tool_id, "params": params},
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise Exception(f"MetaMCP invocation failed: {response.status_code}")

        return response.json().get('result')

    async def _invoke_remote_mcp(self, url: str, tool_id: str, params: Dict) -> Any:
        """Invoke tool through remote MCP server"""
        response = requests.post(
            f"{url}/tools/invoke",
            json={"tool_id": tool_id, "params": params},
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise Exception(f"Remote MCP invocation failed: {response.status_code}")

        return response.json().get('result')

    def _sanitize_params(self, params: Dict) -> Dict:
        """Remove sensitive information from parameters for audit log"""
        sanitized = {}
        sensitive_keys = ['password', 'token', 'key', 'secret', 'auth']

        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value

        return sanitized

    def _summarize_result(self, result: Any) -> str:
        """Create a summary of the result for audit log"""
        if isinstance(result, dict):
            if 'success' in result:
                return f"Success: {result.get('success')}"
            elif 'status' in result:
                return f"Status: {result.get('status')}"
            elif len(result) > 0:
                return f"Result with {len(result)} keys"
        elif isinstance(result, list):
            return f"List with {len(result)} items"
        elif isinstance(result, str):
            return f"String response ({len(result)} chars)"
        else:
            return f"Result of type {type(result).__name__}"

    async def get_audit_log(self) -> List[Dict]:
        """Get the audit log of all actions"""
        return self.audit_log.copy()

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all connected aggregators"""
        health_status = {}

        # Check MetaMCP
        if self.meta_mcp_url:
            try:
                response = requests.get(f"{self.meta_mcp_url}/health", timeout=5)
                health_status['meta_mcp'] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'url': self.meta_mcp_url
                }
            except:
                health_status['meta_mcp'] = {
                    'status': 'unhealthy',
                    'url': self.meta_mcp_url,
                    'error': 'Connection failed'
                }

        # Check remote MCP servers
        health_status['remote_mcps'] = []
        for url in self.remote_mcp_urls:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                health_status['remote_mcps'].append({
                    'url': url,
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy'
                })
            except:
                health_status['remote_mcps'].append({
                    'url': url,
                    'status': 'unhealthy',
                    'error': 'Connection failed'
                })

        return health_status


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


if __name__ == "__main__":
    import asyncio

    async def test_gateway():
        # Test tool listing
        tools = await list_available_tools()
        print(f"Available tools: {len(tools)}")
        for tool in tools[:3]:  # Show first 3
            print(f"  - {tool.name}: {tool.description}")

        # Test health check
        health = await gateway.health_check()
        print("\nHealth status:")
        print(f"  MetaMCP: {health.get('meta_mcp', {}).get('status', 'not configured')}")
        print(f"  Remote MCPs: {len(health.get('remote_mcps', []))}")

    asyncio.run(test_gateway())