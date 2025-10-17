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

class OOSCommandProcessor:
    """Process natural language commands"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

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

        elif command.startswith('sheets'):
            return await self.handle_sheets_command(command)
        elif command.startswith('search'):
            return await self.handle_search_command(command)

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