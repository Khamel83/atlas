#!/usr/bin/env python3
"""
OOS Interactive Launcher - Modern UX for Organized Operational Setup
One command to rule them all: ./run.py
"""
import os
import sys
import subprocess
from pathlib import Path
import json
import shutil
from lib.health_check import run_health_check, Colors



def print_header():
    print(f"\n{Colors.BOLD}🚀 OOS - Organized Operational Setup{Colors.END}")
    print("=" * 50)

def detect_context():
    """Figure out where user is and what they probably want"""
    current_dir = Path.cwd()

    # Check if we're in the OOS repo itself
    if (current_dir / "scripts/bootstrap_enhanced.sh").exists():
        return "oos_repo"

    # Check if this is an existing project
    if (current_dir / '.git').exists():
        return "existing_project"

    # Check if directory has files
    files = list(current_dir.iterdir())
    non_hidden_files = [f for f in files if not f.name.startswith('.')]

    if not non_hidden_files:
        return "empty_dir"
    else:
        return "non_empty_dir"

def is_op_signed_in():
    """Check if 1Password CLI is signed in"""
    try:
        result = subprocess.run(['op', 'whoami'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def ensure_op_signin():
    """Ensure user is signed into 1Password with a clear, guided process."""
    if is_op_signed_in():
        print(f"{Colors.GREEN}✅ 1Password is authenticated.{Colors.END}")
        return

    print(f"\n{Colors.YELLOW}🔐 1Password authentication required.{Colors.END}")

    while not is_op_signed_in():
        print("\n" + "-"*50)
        print(f"{Colors.BOLD}To continue, please sign in to the 1Password CLI:{Colors.END}")
        print("1. 👉 Open a new, separate terminal window.")
        print("2. 👇 Copy and paste the following command into the new terminal:")
        print(f"\n   {Colors.CYAN}eval $(op signin){Colors.END}\n")
        print("3.  Follow the prompts in that terminal to unlock your vault.")
        print("4. ✅ Once you are signed in, come back here and press Enter.")
        print("-" * 50)

        try:
            input(f"\n{Colors.YELLOW}Press Enter to continue or Ctrl+C to exit...{Colors.END}")
            if not is_op_signed_in():
                print(f"\n{Colors.RED}❌ Still not signed in. Please follow the steps above carefully.{Colors.END}")
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}👋 Setup cancelled. Goodbye!{Colors.END}")
            sys.exit(0)

    print(f"\n{Colors.GREEN}✅ 1Password authenticated successfully!{Colors.END}")

def get_user_choice(options, prompt="Choice"):
    """Get user choice from numbered options"""
    while True:
        try:
            choice = input(f"\n{prompt} [1-{len(options)}]: ")
            if choice == "":
                return 1  # Default to first option
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                return choice_num
            print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}👋 Goodbye!{Colors.END}")
            sys.exit(0)

def auth_only_setup():
    """Just pull .env from 1Password - minimal setup"""
    print(f"\n{Colors.BLUE}🔑 Setting up secure environment only...{Colors.END}")

    ensure_op_signin()

    # Get environment from 1Password
    try:
        result = subprocess.run([
            'op', 'item', 'get', 'bootstrap-env',
            '--vault', 'Private',
            '--field', 'env'
        ], capture_output=True, text=True, check=True)

        env_content = result.stdout

        # Write .env file
        with open('.env', 'w') as f:
            f.write(env_content)

        # Add to .gitignore if it doesn't exist
        gitignore_path = Path('.gitignore')
        if gitignore_path.exists():
            with open('.gitignore', 'r') as f:
                content = f.read()
            if '.env' not in content:
                with open('.gitignore', 'a') as f:
                    f.write('\n.env\n')
        else:
            with open('.gitignore', 'w') as f:
                f.write('.env\n')

        line_count = len(env_content.splitlines())
        print(f"{Colors.GREEN}✅ Created .env with {line_count} secure variables{Colors.END}")
        print(f"{Colors.GREEN}✅ Added .env to .gitignore{Colors.END}")
        print(f"\n{Colors.BOLD}🎉 Done! Your secure environment is ready.{Colors.END}")

    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Failed to get environment from 1Password{Colors.END}")
        print(f"Error: {e.stderr}")
        sys.exit(1)

def existing_project_setup():
    """Add OOS tools to existing project"""
    print(f"\n{Colors.BLUE}🛠️  Enhancing existing project...{Colors.END}")

    project_name = Path.cwd().name
    print(f"Project: {Colors.BOLD}{project_name}{Colors.END}")

    options = [
        "🔐 Add secure environment (.env from 1Password)",
        "🤖 Add AI CLI runners (Claude, Gemini, etc.)",
        "🔧 Add development tools (diagnostics, health checks)",
        "📋 All of the above"
    ]

    print("\nWhat would you like to add?")
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")

    choice = get_user_choice(options)

    if choice == 1:
        auth_only_setup()
    elif choice == 4:
        full_project_setup(project_name, Path.cwd(), existing=True)
    else:
        print(f"{Colors.YELLOW}🚧 Feature coming soon!{Colors.END}")
        print("For now, use option 1 (secure environment) or 4 (full setup)")

def new_project_setup():
    """Create new project with full bootstrap"""
    print(f"\n{Colors.BLUE}🆕 Creating new project...{Colors.END}")

    # Get project details
    project_name = input("Project name: ").strip()
    if not project_name:
        print(f"{Colors.RED}❌ Project name required{Colors.END}")
        sys.exit(1)

    # Default to current directory if empty, otherwise ask
    current_dir = Path.cwd()
    if list(current_dir.iterdir()):
        project_path = input(f"Project path [{current_dir / project_name}]: ").strip()
        if not project_path:
            project_path = current_dir / project_name
        else:
            project_path = Path(project_path)
    else:
        # Current directory is empty, offer to use it
        use_current = input(f"Create project in current directory? [Y/n]: ").strip()
        if use_current.lower().startswith('n'):
            project_path = Path(input("Project path: ").strip())
        else:
            project_path = current_dir

    full_project_setup(project_name, project_path)

def full_project_setup(project_name, project_path, existing=False):
    """Run the full bootstrap process"""
    print(f"\n{Colors.BLUE}🚀 Running full OOS setup...{Colors.END}")

    # Find the bootstrap script
    script_path = Path(__file__).parent / "scripts/bootstrap_enhanced.sh"
    if not script_path.exists():
        print(f"{Colors.RED}❌ scripts/bootstrap_enhanced.sh not found{Colors.END}")
        sys.exit(1)

    # Build command
    cmd = [
        str(script_path),
        project_name,
        str(project_path),
        "--no-github",  # Skip GitHub for now to avoid auth issues
        "--verbose"
    ]

    # Set environment
    env = os.environ.copy()
    env['OP_VAULT'] = 'Private'

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, env=env, check=True)
        print(f"\n{Colors.GREEN}🎉 Project setup complete!{Colors.END}")
        if not existing:
            print(f"\nNext steps:")
            print(f"  cd {project_path}")
            print(f"  .agents/runners/run_claude.sh")
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Setup failed with exit code {e.returncode}{Colors.END}")
        sys.exit(1)

def show_oos_management_menu():
    """Menu when run from OOS repo itself"""
    print(f"\n{Colors.BLUE}🔧 OOS Management{Colors.END}")
    print("You're in the OOS repository")

    options = [
        "🆕 Create new project elsewhere",
        "🔧 Run diagnostics",
        "📖 Show documentation",
        "🔍 Test OOS installation"
    ]

    print("\nWhat would you like to do?")
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")

    choice = get_user_choice(options)

    if choice == 1:
        new_project_setup()
    else:
        print(f"{Colors.YELLOW}🚧 Feature coming soon!{Colors.END}")

def show_general_menu():
    """General menu for non-empty directories"""
    print(f"\n{Colors.YELLOW}📁 Non-empty directory detected{Colors.END}")

    options = [
        "🔐 Add secure environment here (.env from 1Password)",
        "🆕 Create new project elsewhere",
        "❓ Show help"
    ]

    print("\nWhat would you like to do?")
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")

    choice = get_user_choice(options)

    if choice == 1:
        auth_only_setup()
    elif choice == 2:
        new_project_setup()
    else:
        show_help()



def show_help():
    """Show help information"""
    help_text = """
{bold}📖 OOS Help{end}
OOS provides secure, AI-ready development environments.

Usage:
  oos                 # Interactive mode (recommended)
  oos --help          # Show this help
  oos --integrate     # Add OOS spec-driven workflow to an existing project
  oos health          # Run a health check of your environment

Context-aware behavior:
  • Empty directory       → Offers to create new project
  • Existing git project  → Offers to enhance project
  • OOS repository        → Management options
  • Other directories     → Flexible options

For advanced usage, see the full documentation in the repository.
""".format(bold=Colors.BOLD, end=Colors.END)
    print(help_text)

def integrate_oos():
    """Integrate OOS scaffolding into an existing project."""
    print(f"\n{Colors.BLUE}🚀 Integrating OOS into the current project...{Colors.END}")

    # This script runs from the oos repo, so its path is the source
    oos_repo_path = Path(__file__).resolve().parent
    target_path = Path.cwd()

    if oos_repo_path == target_path:
        print(f"{Colors.RED}❌ Cannot integrate OOS into itself.{Colors.END}")
        sys.exit(1)

    # 1. Copy scaffolding
    scaffolding_dirs = ['.gemini', 'memory', 'specs', 'scripts', 'templates']

    print("    - Copying spec-kit scaffolding...")
    for d in scaffolding_dirs:
        source = oos_repo_path / d
        target = target_path / d
        if not target.exists() and source.exists():
            print(f"      Creating {target}")
            shutil.copytree(source, target)
        else:
            print(f"      Skipping {target} (already exists)")

    # 2. Update .gitignore
    print("    - Updating .gitignore...")
    gitignore_content = "\n# OOS Files\n.env*\n!/.env.example\nCODE_MANIFEST.md\n/site/\n"
    try:
        with open(target_path / '.gitignore', 'a') as f:
            f.write(gitignore_content)
    except IOError as e:
        print(f"{Colors.YELLOW}    Could not write to .gitignore: {e}{Colors.END}")

    # 3. Update requirements-dev.txt
    print("    - Updating requirements-dev.txt...")
    dev_deps = ['ruff', 'black', 'pytest']
    req_file = target_path / 'requirements-dev.txt'
    try:
        existing_deps = []
        if req_file.exists():
            with open(req_file, 'r') as f:
                existing_deps = [line.strip() for line in f.readlines()]

        with open(req_file, 'a') as f:
            for dep in dev_deps:
                if dep not in existing_deps:
                    f.write(f"{dep}\n")

    except IOError as e:
        print(f"{Colors.YELLOW}    Could not write to requirements-dev.txt: {e}{Colors.END}")

    print(f"\n{Colors.GREEN}✅ OOS integration complete!{Colors.END}")
    print("\nNext Steps:")
    print("1. If you haven't already, install dev dependencies: pip install -r requirements-dev.txt")
    print(f"2. Set up your secure environment by running: {Colors.CYAN}oos{Colors.END}")

def main():
    """Main entry point"""

    # Handle command line args
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            show_help()
            return
        if sys.argv[1] == '--integrate':
            # This is a special case where we don't want to be in the oos repo
            if (Path.cwd() / "scripts/bootstrap_enhanced.sh").exists():
                 print(f"{Colors.RED}❌ Cannot integrate OOS into itself.{Colors.END}")
                 sys.exit(1)
            integrate_oos()
            return
        if sys.argv[1] == 'health':
            run_health_check()
            return
        else:
            print(f"{Colors.RED}❌ Unknown option: {sys.argv[1]}{Colors.END}")
            print("Use --help for usage information")
            sys.exit(1)

    print_header()

    context = detect_context()

    if context == "empty_dir":
        print(f"{Colors.GREEN}📂 Empty directory - perfect for a new project!{Colors.END}")

        options = [
            "🔐 Just secure environment (.env from 1Password)",
            "🆕 Full project setup with AI tools",
            "❓ Show help"
        ]

        print("\nWhat do you need?")
        for i, option in enumerate(options, 1):
            highlight = " ← RECOMMENDED" if i == 1 else ""
            print(f"{i}. {option}{Colors.YELLOW}{highlight}{Colors.END}")

        choice = get_user_choice(options)

        if choice == 1:
            auth_only_setup()
        elif choice == 2:
            new__project_setup()
        else:
            show_help()

    elif context == "existing_project":
        existing_project_setup()

    elif context == "oos_repo":
        show_oos_management_menu()

    else:  # non_empty_dir
        show_general_menu()

if __name__ == "__main__":
    main()