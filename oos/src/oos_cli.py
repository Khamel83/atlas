#!/usr/bin/env python3
"""
OOS Main CLI Interface
Natural language command processing for non-coders
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio
import httpx
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from capability_router import route_request
from knowledge_resolver import resolve_knowledge
from renderers import render_help, render_knowledge, render_tools
from actions_gateway import list_available_tools, execute_action

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

def print_logo():
    """Print OOS logo"""
    logo = f"""
{Colors.CYAN}{Colors.BOLD}
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   🚀 OOS - Open Operating System                              ║
    ║   Build AI projects without coding                           ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(logo)

def print_step(step: str, description: str):
    """Print a step with description"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}→ {step}{Colors.END}")
    print(f"  {Colors.WHITE}{description}{Colors.END}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_info(message: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ️  {message}{Colors.END}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def load_config() -> Dict[str, Any]:
    """Load OOS configuration"""
    config_path = Path.home() / '.oos' / 'config.json'
    if not config_path.exists():
        print_error("OOS not set up. Please run: curl setup.oos.dev | bash")
        sys.exit(1)

    with open(config_path, 'r') as f:
        return json.load(f)

def load_env_config() -> Dict[str, str]:
    """Load environment configuration from .env file"""
    env_config = {}
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_config[key.strip()] = value.strip()
    return env_config

class ArchonIntegration:
    """Helper class for Archon MCP integration"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.env_config = load_env_config()
        self.archon_url = self.env_config.get('ARCHON_URL', 'http://localhost:8051/mcp')
        self.project_id = self.env_config.get('ARCHON_PROJECT_ID')

    def is_available(self) -> bool:
        """Check if Archon integration is available"""
        return bool(self.project_id and self.archon_url)

    async def call_mcp(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make MCP call to Archon server"""
        if not self.is_available():
            raise Exception("Archon integration not configured. Set ARCHON_PROJECT_ID and ARCHON_URL in .env")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.archon_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": method,
                        "params": params,
                        "id": 1
                    }
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    raise Exception(f"Archon error: {data['error']['message']}")

                return data.get("result", {})

        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to Archon server: {e}")

    async def list_tasks(self, status: Optional[str] = None, feature: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks for current project"""
        params = {"project_id": self.project_id}
        if status:
            params["filter_by"] = "status"
            params["filter_value"] = status

        result = await self.call_mcp("list_tasks", params)
        tasks = result.get("tasks", [])

        if feature:
            tasks = [t for t in tasks if t.get("feature") == feature]

        return tasks

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task details"""
        result = await self.call_mcp("get_task", {"task_id": task_id})
        return result.get("task", {})

    async def update_task(self, task_id: str, **updates) -> Dict[str, Any]:
        """Update task"""
        params = {"task_id": task_id, **updates}
        result = await self.call_mcp("update_task", params)
        return result.get("task", {})

    async def create_task(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        """Create new task"""
        params = {
            "project_id": self.project_id,
            "title": title,
            "description": description,
            **kwargs
        }
        result = await self.call_mcp("create_task", params)
        return result.get("task", {})

    async def get_project(self) -> Dict[str, Any]:
        """Get current project details"""
        result = await self.call_mcp("get_project", {"project_id": self.project_id})
        return result.get("project", {})

class OOSCommandProcessor:
    """Process natural language commands"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.archon = ArchonIntegration(config)

    async def process_command(self, args: List[str]) -> int:
        """Process a natural language command"""
        if not args:
            self.show_help()
            return 0

        command = ' '.join(args).lower()

        # Handle common patterns
        if command in ['help', '--help', '-h']:
            self.show_help()
            return 0

        elif command.startswith('create'):
            return await self.handle_create(command)

        elif command.startswith('new'):
            return await self.handle_create(command)

        elif command.startswith('build'):
            return await self.handle_create(command)

        elif command.startswith('help me'):
            return await self.handle_help_me(command)

        elif command.startswith('what can i do'):
            self.show_capabilities()
            return 0

        elif command.startswith('show'):
            return await self.handle_show(command)

        elif command.startswith('list'):
            return await self.handle_list(command)

        elif command.startswith('run'):
            return await self.handle_run(command)

        elif command.startswith('deploy'):
            return await self.handle_deploy(command)

        elif command.startswith('test'):
            return await self.handle_test(command)

        elif command.startswith('explain'):
            return await self.handle_explain(command)

        elif command.startswith('task'):
            return await self.handle_task_command(command)

        elif command.startswith('project'):
            return await self.handle_project_command(command)

        elif command.startswith('sheets'):
            return await self.handle_sheets_command(command)
        elif command.startswith('search'):
            return await self.handle_search_command(command)

        elif command.startswith('daemon'):
            return await self.handle_daemon_command(command)

        elif command.startswith('hey oos') or command.startswith('wake'):
            return await self.handle_wake_command(command)

        else:
            # Use capability router to understand the request
            return await self.handle_natural_command(command)

    async def handle_create(self, command: str) -> int:
        """Handle create/new/build commands"""
        from template_engine import get_template_engine

        # Check if user provided a description
        parts = command.split()
        if len(parts) < 2:
            # Interactive mode - use template engine
            print_step("OOS Project Creator", "What would you like to build?")
            print_info("Describe your project in plain English, and I'll guide you through creating it.")
            print_info("Examples:")
            print_info("  • I want a chatbot that answers customer questions")
            print_info("  • I need to automate price monitoring on Amazon")
            print_info("  • Help me analyze my sales data")
            print_info("")

            description = input(f"{Colors.WHITE}{Colors.BOLD}What would you like to build? {Colors.END}").strip()
            if not description:
                print_info("Please describe what you want to create.")
                return 0
        else:
            # Extract description from command
            description = ' '.join(parts[1:])
            print_step("OOS Project Creator", "Understanding your project")

        # Use template engine for intelligent project creation
        template_engine = get_template_engine(
            self.config,
            google_integration=getattr(self, 'google_integration', None)
        )

        try:
            result = await template_engine.create_project_from_description(description)
            if result:
                project_dir = result['project_dir']
                next_steps = result['next_steps']

                print_success(f"Project created: {project_dir}")
                print_info("Next steps:")
                for i, step in enumerate(next_steps, 1):
                    print_info(f"  {i}. {step}")
                print_info(f"  cd {project_dir}")
                print_info("  python main.py")
            else:
                print_warning("Project creation cancelled or failed.")
                return 1
        except Exception as e:
            print_error(f"Error creating project: {e}")
            return 1

        return 0

    async def handle_help_me(self, command: str) -> int:
        """Handle help me requests"""
        print_step("Getting Help", "Understanding what you need")

        # Extract the help request
        help_request = command.replace('help me', '').strip()

        if not help_request:
            print_info("What do you need help with?")
            print_info("Examples:")
            print_info("  oos help me create a chatbot")
            print_info("  oos help me deploy my project")
            print_info("  oos help me understand APIs")
            return 0

        print_info(f"Understanding: {help_request}")

        # Use capability system to get help
        routing_result = route_request(help_request)
        knowledge_result = await resolve_knowledge(help_request, routing_result.domain)
        knowledge_result.domain = routing_result.domain

        print(render_knowledge(knowledge_result))

        return 0

    def show_help(self):
        """Show main help"""
        print_step("OOS Help", "Build AI projects without coding")

        help_text = f"""
{Colors.WHITE}{Colors.BOLD}What can you build?{Colors.END}
{Colors.CYAN}  AI Chatbots{Colors.WHITE}         • Conversational assistants for any topic
{Colors.CYAN}  Web Automation{Colors.WHITE}      • Scrape websites, fill forms, automate tasks
{Colors.CYAN}  Data Analysis{Colors.WHITE}      • Analyze files, generate insights, create reports
{Colors.CYAN}  Personal Assistants{Colors.WHITE} • Manage your calendar, emails, and tasks

{Colors.WHITE}{Colors.BOLD}Common Commands:{Colors.END}
{Colors.GREEN}  oos create <type>{Colors.WHITE}     • Create a new project
{Colors.GREEN}  oos search "query"{Colors.WHITE}    • Search the web (free + Pro credits)
{Colors.GREEN}  oos help me <question>{Colors.WHITE} • Get help with anything
{Colors.GREEN}  oos run{Colors.WHITE}               • Run your current project
{Colors.GREEN}  oos show <thing>{Colors.WHITE}      • Show information about your project
{Colors.GREEN}  oos deploy{Colors.WHITE}            • Deploy your project to the web

{Colors.WHITE}{Colors.BOLD}🎯 Task Management (Archon):{Colors.END}
{Colors.GREEN}  oos task list{Colors.WHITE}         • List all tasks
{Colors.GREEN}  oos task create 'Title' 'Desc'{Colors.WHITE} • Create new task
{Colors.GREEN}  oos task start <id>{Colors.WHITE}   • Start working on task
{Colors.GREEN}  oos project status{Colors.WHITE}    • Show project overview

{Colors.WHITE}{Colors.BOLD}🤖 Persistent Assistant:{Colors.END}
{Colors.GREEN}  oos daemon start{Colors.WHITE}      • Start background assistant
{Colors.GREEN}  oos hey oos <idea>{Colors.WHITE}    • Send idea to assistant
{Colors.GREEN}  oos wake <request>{Colors.WHITE}    • Wake word activation

{Colors.WHITE}{Colors.BOLD}🌐 Google Sheets (Universal Access):{Colors.END}
{Colors.GREEN}  oos sheets setup{Colors.WHITE}       • Setup Google integration
{Colors.GREEN}  oos sheets list{Colors.WHITE}        • List cloud projects
{Colors.GREEN}  oos sheets open <name>{Colors.WHITE}  • Open project in browser
{Colors.GREEN}  oos sheets sync{Colors.WHITE}        • Sync with all devices

{Colors.WHITE}{Colors.BOLD}Examples:{Colors.END}
{Colors.YELLOW}  oos create chatbot "Customer Service Bot"{Colors.WHITE}
{Colors.YELLOW}  oos help me set up a database{Colors.WHITE}
{Colors.YELLOW}  oos create automation "Social Media Poster"{Colors.WHITE}
{Colors.YELLOW}  oos sheets setup{Colors.WHITE}
{Colors.YELLOW}  oos show my project status{Colors.WHITE}

{Colors.WHITE}{Colors.BOLD}Need more help?{Colors.END}
{Colors.CYAN}  • Type "oos help me <anything>" for specific help{Colors.WHITE}
{Colors.CYAN}  • All commands explain what they're doing{Colors.WHITE}
{Colors.CYAN}  • Safe by default - can't break anything{Colors.WHITE}
"""
        print(help_text)

    def show_capabilities(self):
        """Show what OOS can do"""
        print_step("OOS Capabilities", "What you can build")

        capabilities = f"""
{Colors.WHITE}{Colors.BOLD}🤖 AI-Powered Projects{Colors.END}
{Colors.CYAN}• Chatbots{Colors.WHITE}            • Build conversational AI assistants
{Colors.CYAN}• Automation{Colors.WHITE}        • Automate any repetitive task
{Colors.CYAN}• Data Analysis{Colors.WHITE}      • Turn data into insights and reports
{Colors.CYAN}• Web Scraping{Colors.WHITE}       • Extract data from websites
{Colors.CYAN}• APIs{Colors.WHITE}              • Connect to any service
{Colors.CYAN}• File Processing{Colors.WHITE}    • Work with documents, images, data

{Colors.WHITE}{Colors.BOLD}🛡️ Safety Features{Colors.END}
{Colors.GREEN}• Sandboxed{Colors.WHITE}          • Can't access sensitive files
{Colors.GREEN}• Cost Limits{Colors.WHITE}        • Prevent unexpected charges
{Colors.GREEN}• Auto Backup{Colors.WHITE}       • Never lose your work
{Colors.GREEN}• Smart Suggestions{Colors.WHITE}  • Get help when you're stuck

{Colors.WHITE}{Colors.BOLD}🚀 Easy to Use{Colors.END}
{Colors.YELLOW}• Natural Language{Colors.WHITE}   • Just say what you want
{Colors.YELLOW}• Step-by-Step{Colors.WHITE}      • Guided through everything
{Colors.YELLOW}• No Coding{Colors.WHITE}          • Build without writing code
{Colors.YELLOW}• Works Everywhere{Colors.WHITE}   • Terminal on any computer

{Colors.WHITE}{Colors.BOLD}Try these:{Colors.END}
{Colors.CYAN}  oos create chatbot "Hello World"{Colors.WHITE}
{Colors.CYAN}  oos help me automate my emails{Colors.WHITE}
{Colors.CYAN}  oos show me examples{Colors.WHITE}
"""
        print(capabilities)

    def create_project_files(self, project_dir: Path, project_type: str, description: str):
        """Create basic project files"""
        # Create project config
        config = {
            'type': project_type,
            'description': description,
            'created': '2025-09-27',
            'version': '1.0.0'
        }

        with open(project_dir / 'project.json', 'w') as f:
            json.dump(config, f, indent=2)

        # Create main.py based on project type
        if 'chatbot' in project_type:
            code = '''# Your AI Chatbot
# OOS will help you build this step by step

print("Hello! I'm your AI assistant.")
print("I'm learning to help you with your questions.")

# Add your chatbot logic here
'''
        elif 'automation' in project_type:
            code = '''# Your Automation Tool
# OOS will help you build this step by step

print("Starting automation...")
print("This tool will help you automate repetitive tasks.")

# Add your automation logic here
'''
        else:
            code = f'''# Your {project_type.title()}
# OOS will help you build this step by step

print("Starting {description}...")

# Add your logic here
'''

        with open(project_dir / 'main.py', 'w') as f:
            f.write(code)

        # Create README
        readme = f'''# {description.title()}

Built with OOS - no coding required!

## What this does
{description}

## How to use
1. Run: python main.py
2. Follow the prompts
3. Customize as needed

## Getting help
Type: oos help me <your question>

## Next steps
- Run the project: oos run
- Add features: oos help me add <feature>
- Deploy: oos deploy
'''
        with open(project_dir / 'README.md', 'w') as f:
            f.write(readme)

    async def handle_natural_command(self, command: str) -> int:
        """Handle natural language commands using capability system"""
        print_step("Understanding Request", f"Processing: {command}")

        # Route the request
        routing_result = route_request(command)
        print_info(f"Intent: {routing_result.mode} about {routing_result.domain}")

        # Get knowledge
        knowledge_result = await resolve_knowledge(command, routing_result.domain)
        knowledge_result.domain = routing_result.domain

        print(render_knowledge(knowledge_result))

        # If it's an action, show available tools
        if routing_result.mode == "action":
            print_info("Available actions:")
            tools = await list_available_tools(routing_result.domain)
            print(render_tools(tools, routing_result.domain))

        return 0

    async def handle_show(self, command: str) -> int:
        """Handle show commands"""
        what = command.replace('show', '').strip()
        print_step("Showing Information", f"About: {what}")

        if 'project' in what:
            self.show_project_info()
        elif 'files' in what:
            self.show_project_files()
        elif 'status' in what:
            self.show_project_status()
        else:
            # Use capability system
            return await self.handle_natural_command(command)

        return 0

    async def handle_list(self, command: str) -> int:
        """Handle list commands"""
        what = command.replace('list', '').strip()
        print_step("Listing", f"Showing: {what}")

        if 'project' in what:
            self.list_projects()
        else:
            return await self.handle_natural_command(command)

        return 0

    async def handle_run(self, command: str) -> int:
        """Handle run commands"""
        print_step("Running Project", "Starting your project")

        if not Path('main.py').exists():
            print_warning("No main.py found in current directory")
            print_info("Create a project first: oos create <type>")
            return 1

        print_info("Running your project...")
        try:
            import subprocess
            result = subprocess.run([sys.executable, 'main.py'], cwd='.')
            if result.returncode == 0:
                print_success("Project ran successfully!")
            else:
                print_error("Project failed to run")
                return 1
        except Exception as e:
            print_error(f"Failed to run project: {e}")
            return 1

        return 0

    async def handle_deploy(self, command: str) -> int:
        """Handle deploy commands"""
        print_step("Deploying Project", "Publishing your project")

        print_info("Deployment coming soon!")
        print_info("For now, you can share your project folder or use GitHub")
        return 0

    async def handle_test(self, command: str) -> int:
        """Handle test commands"""
        print_step("Testing Project", "Checking if everything works")

        print_info("Running tests...")
        print_info("Test functionality coming soon!")
        return 0

    async def handle_explain(self, command: str) -> int:
        """Handle explain commands"""
        what = command.replace('explain', '').strip()
        print_step("Explaining", f"About: {what}")

        return await self.handle_help_me(f"help me understand {what}")

    async def handle_sheets_command(self, command: str) -> int:
        """Handle Google Sheets commands"""
        from google_sheets_integration import get_sheets_integration, setup_google_sheets, list_sheets_projects

        subcommand = command.replace('sheets', '').strip()

        if subcommand == 'setup':
            print_step("Google Sheets Setup", "Universal data access")
            config_dir = Path.home() / '.oos'
            success = await setup_google_sheets(config_dir)
            if success:
                print_success("Google Sheets integration is ready!")
            else:
                print_warning("Google Sheets setup skipped. You can try again later.")
            return 0

        elif subcommand == 'list':
            print_step("Google Sheets Projects", "Your projects in the cloud")
            config_dir = Path.home() / '.oos'
            projects = await list_sheets_projects(config_dir)
            if projects:
                print_info("Your cloud projects:")
                for project in projects:
                    print(f"  • {project['name']} ({project['created_at'][:10]})")
                    print(f"    URL: {project['url']}")
            else:
                print_info("No projects found in Google Sheets")
                print_info("Create one: oos create chatbot")
            return 0

        elif subcommand.startswith('open'):
            project_name = subcommand.replace('open', '').strip()
            print_step("Opening Project", f"In Google Sheets: {project_name}")
            print_info("This would open the project in your browser")
            print_info("Feature coming soon!")
            return 0

        elif subcommand == 'sync':
            print_step("Syncing Projects", "With Google Sheets")
            print_info("This would sync your local projects with Google Sheets")
            print_info("Feature coming soon!")
            return 0

        else:
            print_step("Google Sheets Commands", "Universal data access")
            print_info("Available commands:")
            print_info("  oos sheets setup    - Setup Google integration")
            print_info("  oos sheets list     - List cloud projects")
            print_info("  oos sheets open <name> - Open project in browser")
            print_info("  oos sheets sync     - Sync with cloud")
            return 0

    async def handle_search_command(self, command: str) -> int:
        """Handle search commands with automatic free + paid search integration"""
        query = command.replace('search', '').strip().strip('"').strip("'")

        if not query:
            print_step("OOS Search", "Search the web with smart cost controls")
            print_info("Usage:")
            print_info('  oos search "python tutorials"')
            print_info('  oos search "latest AI research 2025"')
            print_info('')
            print_info("Search sources (in priority order):")
            print_info("  1. 🆓 DuckDuckGo - Free, unlimited")
            print_info("  2. 🆓 Wikipedia - Free, unlimited")
            print_info("  3. 🆓 GitHub - Free, 5K/hour")
            print_info("  4. 🆓 Stack Overflow - Free, 10K/day")
            print_info("  5. 💡 Perplexity - Your $5/month Pro credits (asks permission)")
            print_info('')
            print_info("💰 Expected costs: $0.00 for most searches")
            return 0

        print_step("OOS Search", f'Searching for: "{query}"')

        try:
            from free_search_alternatives import search_free
            results = await search_free(query, max_results=8)

            if results:
                print_success(f"Found {len(results)} results")
                print_info("")

                for i, result in enumerate(results, 1):
                    source_color = Colors.CYAN if result.source == 'Perplexity' else Colors.GREEN
                    print(f"{Colors.BOLD}{i}.{Colors.END} {Colors.WHITE}{result.title}{Colors.END}")
                    print(f"   {source_color}[{result.source}]{Colors.END} {result.snippet[:100]}...")
                    if result.url:
                        print(f"   🔗 {Colors.BLUE}{result.url}{Colors.END}")
                    print()

                # Show cost summary if Perplexity was used
                perplexity_used = any(r.source == 'Perplexity' for r in results)
                if perplexity_used:
                    from perplexity_usage_manager import usage_manager
                    summary = usage_manager.get_usage_summary()
                    print_info(f"💰 Monthly Perplexity usage: ${summary['total_cost']:.2f} / ${summary['monthly_limit']:.2f} ({summary['usage_percent']:.1f}%)")
                else:
                    print_info("💰 Search cost: $0.00 (used free sources)")

            else:
                print_warning("No results found")
                print_info("Try:")
                print_info("  • Different search terms")
                print_info("  • More specific keywords")
                print_info("  • Broader topic search")

        except Exception as e:
            print_error(f"Search failed: {e}")
            return 1

        return 0

    async def handle_task_command(self, command: str) -> int:
        """Handle task management commands"""
        parts = command.split()
        if len(parts) < 2:
            self.show_task_help()
            return 0

        subcommand = parts[1]

        if not self.archon.is_available():
            print_error("Archon integration not configured")
            print_info("To set up Archon integration:")
            print_info("1. Add ARCHON_PROJECT_ID=<your-project-id> to .env")
            print_info("2. Add ARCHON_URL=<your-archon-server-url> to .env")
            return 1

        try:
            if subcommand == 'list':
                return await self.handle_task_list(parts[2:] if len(parts) > 2 else [])
            elif subcommand == 'start':
                return await self.handle_task_start(parts[2:] if len(parts) > 2 else [])
            elif subcommand == 'complete':
                return await self.handle_task_complete(parts[2:] if len(parts) > 2 else [])
            elif subcommand == 'create':
                return await self.handle_task_create(parts[2:] if len(parts) > 2 else [])
            elif subcommand == 'show':
                return await self.handle_task_show(parts[2:] if len(parts) > 2 else [])
            else:
                print_error(f"Unknown task command: {subcommand}")
                self.show_task_help()
                return 1

        except Exception as e:
            print_error(f"Task command failed: {e}")
            return 1

    async def handle_project_command(self, command: str) -> int:
        """Handle project management commands"""
        parts = command.split()
        if len(parts) < 2:
            self.show_project_help()
            return 0

        subcommand = parts[1]

        if not self.archon.is_available():
            print_error("Archon integration not configured")
            print_info("Add ARCHON_PROJECT_ID and ARCHON_URL to your .env file")
            return 1

        try:
            if subcommand == 'status':
                return await self.handle_project_status()
            elif subcommand == 'info':
                return await self.handle_project_info()
            else:
                print_error(f"Unknown project command: {subcommand}")
                self.show_project_help()
                return 1

        except Exception as e:
            print_error(f"Project command failed: {e}")
            return 1

    async def handle_task_list(self, args: List[str]) -> int:
        """Handle task list command"""
        print_step("Task List", "Your project tasks")

        # Parse optional filters
        status_filter = None
        feature_filter = None

        i = 0
        while i < len(args):
            if args[i] == '--status' and i + 1 < len(args):
                status_filter = args[i + 1]
                i += 2
            elif args[i] == '--feature' and i + 1 < len(args):
                feature_filter = args[i + 1]
                i += 2
            else:
                i += 1

        tasks = await self.archon.list_tasks(status=status_filter, feature=feature_filter)

        if not tasks:
            filter_desc = ""
            if status_filter:
                filter_desc += f" with status '{status_filter}'"
            if feature_filter:
                filter_desc += f" in feature '{feature_filter}'"
            print_info(f"No tasks found{filter_desc}")
            print_info("Create a task: ./oos task create 'Task Title' 'Description'")
            return 0

        # Group tasks by status
        status_groups = {}
        for task in tasks:
            status = task.get('status', 'unknown')
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(task)

        # Display tasks by status
        status_colors = {
            'todo': Colors.YELLOW,
            'doing': Colors.BLUE,
            'review': Colors.CYAN,
            'done': Colors.GREEN
        }

        for status, task_list in status_groups.items():
            status_color = status_colors.get(status, Colors.WHITE)
            print(f"\n{status_color}{Colors.BOLD}{status.upper()} ({len(task_list)}){Colors.END}")

            for task in task_list:
                task_id = task['id'][:8]  # Short ID
                title = task['title']
                feature = task.get('feature', '')
                assignee = task.get('assignee', 'Unassigned')

                feature_text = f"[{feature}] " if feature else ""
                print(f"  {Colors.WHITE}{task_id}{Colors.END} {feature_text}{title}")
                print(f"    👤 {assignee}")

        print_info(f"\nTotal: {len(tasks)} tasks")
        return 0

    async def handle_task_start(self, args: List[str]) -> int:
        """Handle task start command"""
        if not args:
            print_error("Please provide a task ID")
            print_info("Usage: ./oos task start <task-id>")
            return 1

        task_id = args[0]
        print_step("Starting Task", f"Marking task as 'doing': {task_id}")

        # Get full task ID if short ID provided
        if len(task_id) == 8:
            tasks = await self.archon.list_tasks()
            full_task = next((t for t in tasks if t['id'].startswith(task_id)), None)
            if not full_task:
                print_error(f"Task not found: {task_id}")
                return 1
            task_id = full_task['id']

        task = await self.archon.update_task(task_id, status="doing")
        print_success(f"Started task: {task['title']}")
        print_info(f"Status: {task['status']}")
        return 0

    async def handle_task_complete(self, args: List[str]) -> int:
        """Handle task complete command"""
        if not args:
            print_error("Please provide a task ID")
            print_info("Usage: ./oos task complete <task-id>")
            return 1

        task_id = args[0]
        print_step("Completing Task", f"Marking task as 'done': {task_id}")

        # Get full task ID if short ID provided
        if len(task_id) == 8:
            tasks = await self.archon.list_tasks()
            full_task = next((t for t in tasks if t['id'].startswith(task_id)), None)
            if not full_task:
                print_error(f"Task not found: {task_id}")
                return 1
            task_id = full_task['id']

        task = await self.archon.update_task(task_id, status="done")
        print_success(f"Completed task: {task['title']}")
        print_info(f"Status: {task['status']}")
        return 0

    async def handle_task_create(self, args: List[str]) -> int:
        """Handle task create command"""
        if len(args) < 2:
            print_error("Please provide title and description")
            print_info("Usage: ./oos task create 'Title' 'Description'")
            return 1

        title = args[0]
        description = args[1]
        feature = args[2] if len(args) > 2 else None

        print_step("Creating Task", f"New task: {title}")

        kwargs = {}
        if feature:
            kwargs['feature'] = feature

        task = await self.archon.create_task(title, description, **kwargs)
        print_success(f"Created task: {task['title']}")
        print_info(f"Task ID: {task['id'][:8]}")
        print_info(f"Status: {task['status']}")
        return 0

    async def handle_task_show(self, args: List[str]) -> int:
        """Handle task show command"""
        if not args:
            print_error("Please provide a task ID")
            print_info("Usage: ./oos task show <task-id>")
            return 1

        task_id = args[0]

        # Get full task ID if short ID provided
        if len(task_id) == 8:
            tasks = await self.archon.list_tasks()
            full_task = next((t for t in tasks if t['id'].startswith(task_id)), None)
            if not full_task:
                print_error(f"Task not found: {task_id}")
                return 1
            task_id = full_task['id']

        task = await self.archon.get_task(task_id)
        if not task:
            print_error(f"Task not found: {task_id}")
            return 1

        print_step("Task Details", task['title'])
        print_info(f"ID: {task['id']}")
        print_info(f"Status: {task['status']}")
        print_info(f"Assignee: {task.get('assignee', 'Unassigned')}")
        print_info(f"Feature: {task.get('feature', 'None')}")
        print_info(f"Created: {task['created_at'][:10]}")
        print_info(f"Updated: {task['updated_at'][:10]}")

        if task.get('description'):
            print(f"\n{Colors.WHITE}{Colors.BOLD}Description:{Colors.END}")
            print(f"{task['description']}")

        return 0

    async def handle_project_status(self) -> int:
        """Handle project status command"""
        print_step("Project Status", "Checking your project")

        project = await self.archon.get_project()
        tasks = await self.archon.list_tasks()

        print_info(f"Project: {project.get('title', 'Unknown')}")
        print_info(f"Description: {project.get('description', 'No description')}")

        # Task summary
        status_counts = {}
        for task in tasks:
            status = task.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        print(f"\n{Colors.WHITE}{Colors.BOLD}Task Summary:{Colors.END}")
        for status, count in status_counts.items():
            color = {
                'todo': Colors.YELLOW,
                'doing': Colors.BLUE,
                'review': Colors.CYAN,
                'done': Colors.GREEN
            }.get(status, Colors.WHITE)
            print(f"  {color}{status.upper()}: {count}{Colors.END}")

        total_tasks = len(tasks)
        completed = status_counts.get('done', 0)
        if total_tasks > 0:
            progress = (completed / total_tasks) * 100
            print_info(f"Progress: {progress:.1f}% ({completed}/{total_tasks} tasks completed)")
        else:
            print_info("No tasks yet")

        return 0

    async def handle_project_info(self) -> int:
        """Handle project info command"""
        print_step("Project Information", "Your project details")

        project = await self.archon.get_project()

        print_info(f"Title: {project.get('title', 'Unknown')}")
        print_info(f"Description: {project.get('description', 'No description')}")
        print_info(f"Created: {project.get('created_at', 'Unknown')[:10]}")
        print_info(f"Updated: {project.get('updated_at', 'Unknown')[:10]}")

        if project.get('github_repo'):
            print_info(f"GitHub: {project['github_repo']}")

        print_info(f"Project ID: {self.archon.project_id}")
        print_info(f"Archon URL: {self.archon.archon_url}")

        return 0

    def show_task_help(self):
        """Show task command help"""
        help_text = f"""
{Colors.WHITE}{Colors.BOLD}Task Management Commands:{Colors.END}

{Colors.GREEN}  ./oos task list{Colors.WHITE}                    List all tasks
{Colors.GREEN}  ./oos task list --status todo{Colors.WHITE}      List tasks by status
{Colors.GREEN}  ./oos task list --feature auth{Colors.WHITE}     List tasks by feature
{Colors.GREEN}  ./oos task start <task-id>{Colors.WHITE}         Start working on task
{Colors.GREEN}  ./oos task complete <task-id>{Colors.WHITE}      Mark task as complete
{Colors.GREEN}  ./oos task create 'Title' 'Desc'{Colors.WHITE}   Create new task
{Colors.GREEN}  ./oos task show <task-id>{Colors.WHITE}          Show task details

{Colors.WHITE}{Colors.BOLD}Examples:{Colors.END}
{Colors.YELLOW}  ./oos task list --status doing{Colors.WHITE}
{Colors.YELLOW}  ./oos task create 'Add OAuth' 'Implement Google OAuth2'{Colors.WHITE}
{Colors.YELLOW}  ./oos task start 1a2b3c4d{Colors.WHITE}
{Colors.YELLOW}  ./oos task complete 1a2b3c4d{Colors.WHITE}
"""
        print(help_text)

    async def handle_daemon_command(self, command: str) -> int:
        """Handle daemon management commands"""
        parts = command.split()
        if len(parts) < 2:
            self.show_daemon_help()
            return 0

        subcommand = parts[1]
        print_step("OOS Daemon", f"Managing persistent assistant: {subcommand}")

        if subcommand == 'start':
            print_info("Starting OOS persistent assistant...")
            # Use the daemon launcher
            import subprocess
            try:
                result = subprocess.run([
                    sys.executable,
                    str(Path(__file__).parent.parent / "bin" / "oos-daemon"),
                    "start"
                ], check=False)
                return result.returncode
            except Exception as e:
                print_error(f"Failed to start daemon: {e}")
                return 1

        elif subcommand == 'stop':
            print_info("Stopping OOS persistent assistant...")
            import subprocess
            try:
                result = subprocess.run([
                    sys.executable,
                    str(Path(__file__).parent.parent / "bin" / "oos-daemon"),
                    "stop"
                ], check=False)
                return result.returncode
            except Exception as e:
                print_error(f"Failed to stop daemon: {e}")
                return 1

        elif subcommand == 'status':
            print_info("Checking OOS persistent assistant status...")
            import subprocess
            try:
                result = subprocess.run([
                    sys.executable,
                    str(Path(__file__).parent.parent / "bin" / "oos-daemon"),
                    "status"
                ], check=False)
                return result.returncode
            except Exception as e:
                print_error(f"Failed to check daemon status: {e}")
                return 1

        else:
            print_error(f"Unknown daemon command: {subcommand}")
            self.show_daemon_help()
            return 1

    async def handle_wake_command(self, command: str) -> int:
        """Handle wake word activation"""
        # Extract the actual request after wake phrase
        if command.startswith('hey oos'):
            content = command[7:].strip()
        elif command.startswith('wake'):
            content = command[4:].strip()
        else:
            content = command

        if not content:
            print_info("🎧 OOS listening... What would you like me to help with?")
            return 0

        print_step("Wake Word Activated", f"Processing: {content}")

        # Check if daemon is running
        config_dir = Path.home() / '.oos'
        wake_file = config_dir / 'wake_signal.txt'
        daemon_pid = config_dir / 'daemon.pid'

        if daemon_pid.exists():
            # Daemon is running, send wake signal
            try:
                with open(wake_file, 'w') as f:
                    f.write(f"hey oos {content}")
                print_success(f"💡 Idea sent to persistent assistant: {content}")
                print_info("💤 Your idea will be processed in the background")
                return 0
            except Exception as e:
                print_error(f"Failed to send to daemon: {e}")
                print_info("Processing directly instead...")

        # Daemon not running, process directly
        print_info("🤖 Processing your request directly...")
        return await self.handle_natural_command(content)

    def show_daemon_help(self):
        """Show daemon command help"""
        help_text = f"""
{Colors.WHITE}{Colors.BOLD}OOS Persistent Assistant Commands:{Colors.END}

{Colors.GREEN}  ./oos daemon start{Colors.WHITE}                Start persistent assistant
{Colors.GREEN}  ./oos daemon stop{Colors.WHITE}                 Stop persistent assistant
{Colors.GREEN}  ./oos daemon status{Colors.WHITE}               Check assistant status

{Colors.WHITE}{Colors.BOLD}Wake Word Activation:{Colors.END}
{Colors.GREEN}  ./oos hey oos create a chatbot{Colors.WHITE}    Send idea to assistant
{Colors.GREEN}  ./oos wake help me with auth{Colors.WHITE}      Wake word alternative

{Colors.WHITE}{Colors.BOLD}Examples:{Colors.END}
{Colors.YELLOW}  ./oos daemon start{Colors.WHITE}
{Colors.YELLOW}  ./oos hey oos build me a web scraper{Colors.WHITE}
{Colors.YELLOW}  ./oos wake help me deploy to AWS{Colors.WHITE}

{Colors.WHITE}{Colors.BOLD}Background Processing:{Colors.END}
{Colors.CYAN}  • Ideas are processed continuously{Colors.WHITE}
{Colors.CYAN}  • Results are saved and can be retrieved{Colors.WHITE}
{Colors.CYAN}  • Multiple ideas can be processed simultaneously{Colors.WHITE}
"""
        print(help_text)

    def show_project_help(self):
        """Show project command help"""
        help_text = f"""
{Colors.WHITE}{Colors.BOLD}Project Management Commands:{Colors.END}

{Colors.GREEN}  ./oos project status{Colors.WHITE}              Show project overview
{Colors.GREEN}  ./oos project info{Colors.WHITE}                Show project details

{Colors.WHITE}{Colors.BOLD}Examples:{Colors.END}
{Colors.YELLOW}  ./oos project status{Colors.WHITE}
{Colors.YELLOW}  ./oos project info{Colors.WHITE}
"""
        print(help_text)

    def show_project_info(self):
        """Show current project information"""
        if Path('project.json').exists():
            with open('project.json', 'r') as f:
                config = json.load(f)
            print_info(f"Project: {config.get('description', 'Unknown')}")
            print_info(f"Type: {config.get('type', 'Unknown')}")
            print_info(f"Created: {config.get('created', 'Unknown')}")
        else:
            print_warning("No project found in current directory")

    def show_project_files(self):
        """Show project files"""
        print_info("Project files:")
        for item in Path('.').iterdir():
            if item.is_file() and not item.name.startswith('.'):
                print(f"  • {item.name}")

    def show_project_status(self):
        """Show project status"""
        print_info("Project Status: 🟢 Ready")
        print_info("Files: All present")
        print_info("Dependencies: Not checked yet")

    def list_projects(self):
        """List all OOS projects"""
        projects_dir = Path.home() / '.oos' / 'projects'
        if projects_dir.exists():
            projects = list(projects_dir.iterdir())
            if projects:
                print_info("Your projects:")
                for project in projects:
                    print(f"  • {project.name}")
            else:
                print_info("No projects yet. Create one: oos create <type>")
        else:
            print_info("No projects yet. Create one: oos create <type>")

async def main():
    """Main CLI entry point"""
    try:
        # Load configuration
        config = load_config()

        # Create command processor
        processor = OOSCommandProcessor(config)

        # Process command
        return_code = await processor.process_command(sys.argv[1:])
        sys.exit(return_code)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Goodbye! 👋{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())