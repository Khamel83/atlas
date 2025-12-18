import os
import subprocess
import sys
from pathlib import Path

# Use rich for better terminal output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich.table import Table
except ImportError:
    print("Rich library not found. Please run 'pip install rich'.")
    sys.exit(1)

console = Console()

# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent.parent
REQUIRED_DIRS = ["data", "output", "logs", "inputs"]
ENV_FILE = ".env"
REQ_FILE = "requirements.txt"
LOG_DIR = "logs"

# List of essential environment variables. Add more as needed.
# Set to None if the value can be blank.
ESSENTIAL_ENV_VARS = {
    "INSTAPAPER_USERNAME": "your_instapaper_username",
    "INSTAPAPER_PASSWORD": "your_instapaper_password",
    "OPENROUTER_API_KEY": "your_openrouter_api_key",
    "OPENAI_API_KEY": "your_openai_api_key (only if provider is OpenAI)",
    "LLM_PROVIDER": "OpenRouter",  # Default value
}


def print_header():
    """Prints the header for the health check report."""
    console.print(Rule("[bold magenta]Atlas Project Health Check", style="magenta"))
    console.print()


def check_git_branch():
    """Checks the current Git branch and warns if on 'main'."""
    console.print("[bold cyan]0. Checking Git Branch...[/bold cyan]")
    try:
        # Using subprocess to run the git command
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()

        if current_branch == "main":
            warning_panel = Panel(
                "[bold yellow]You are currently on the 'main' branch.[/bold yellow]\n\n"
                "Direct commits to `main` are discouraged. Please use a feature branch for your changes.\n\n"
                "Example: [cyan]git checkout -b feature/my-new-feature[/cyan]",
                title="[bold red]Warning[/bold red]",
                border_style="red",
                expand=False,
            )
            console.print(warning_panel)
        else:
            console.print(
                f"[green]✔ On branch '[bold]{current_branch}[/bold]'. Good job![/green]"
            )

    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(
            "[yellow]Could not determine Git branch. Is this a Git repository?[/yellow]"
        )
    console.print()


def check_directory_structure():
    """Checks if all required directories exist."""
    console.print("[bold cyan]1. Checking Directory Structure...[/bold cyan]")
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Directory", style="dim", width=30)
    table.add_column("Status")

    all_ok = True
    for req_dir in REQUIRED_DIRS:
        dir_path = PROJECT_ROOT / req_dir
        if dir_path.is_dir():
            table.add_row(f"./{req_dir}", "[green]✔ OK[/green]")
        else:
            table.add_row(f"./{req_dir}", "[red]✖ NOT FOUND[/red]")
            all_ok = False

    console.print(table)
    if not all_ok:
        console.print(
            "[yellow]Some directories are missing. The application might fail.[/yellow]"
        )
    console.print()


def check_env_file():
    """Checks for the .env file and essential variables."""
    console.print("[bold cyan]2. Checking Environment Configuration...[/bold cyan]")

    # The config loader checks both the root and the /config directory.
    # We must replicate that logic here for an accurate health check.
    root_env_path = PROJECT_ROOT / ".env"
    config_env_path = PROJECT_ROOT / "config" / ".env"

    env_path_to_load = None
    if config_env_path.is_file():
        env_path_to_load = config_env_path
        # Also load the root one for fallbacks, but don't override.
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=root_env_path, override=False)
    elif root_env_path.is_file():
        env_path_to_load = root_env_path

    table = Table(show_header=True, header_style="bold green")
    table.add_column("Configuration", style="dim", width=30)
    table.add_column("Status")

    if not env_path_to_load:
        table.add_row(".env file", "[red]✖ NOT FOUND[/red]")
        console.print(table)
        console.print(
            "[yellow]Please create a '.env' file in the root or /config directory.[/yellow]"
        )
        return

    # Load the primary .env file
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=env_path_to_load, override=True)

    table.add_row(
        ".env file",
        f"[green]✔ Found at {env_path_to_load.relative_to(PROJECT_ROOT)}[/green]",
    )

    for var, placeholder in ESSENTIAL_ENV_VARS.items():
        value = os.getenv(var)

        # --- Special Handling for Aliases and Defaults ---
        # 1. Handle INSTAPAPER_LOGIN as an alias for INSTAPAPER_USERNAME
        if var == "INSTAPAPER_USERNAME" and not value:
            value = os.getenv("INSTAPAPER_LOGIN")

        # 2. Handle default LLM_PROVIDER
        if var == "LLM_PROVIDER" and not value:
            value = "OpenRouter (default)"  # Use the known default

        # --- Smart logic for API keys ---
        is_api_key = "API_KEY" in var
        provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
        # Allow OPENAI_API_KEY to hold an OpenRouter key
        openai_key_is_openrouter = (os.getenv("OPENAI_API_KEY") or "").startswith(
            "sk-or-v1-"
        )

        if value:
            display_value = "********"
            table.add_row(
                f"  - {var}", f"[green]✔ Set[/green] (Value: {display_value})"
            )

        elif var == "OPENROUTER_API_KEY" and openai_key_is_openrouter:
            table.add_row(
                f"  - {var}",
                "[grey70]○ Not Needed[/grey70] (Using OpenRouter key from OPENAI_API_KEY)",
            )

        elif is_api_key and provider not in var.lower().replace("_api_key", ""):
            table.add_row(
                f"  - {var}",
                f"[grey70]○ Not Needed[/grey70] (Provider is {provider.capitalize()})",
            )

        else:
            table.add_row(
                f"  - {var}", f"[yellow]✖ Not Set[/yellow] (placeholder: {placeholder})"
            )

    console.print(table)
    console.print()


def check_dependencies():
    """Checks if dependencies from requirements.txt are installed."""
    console.print("[bold cyan]3. Checking Dependencies...[/bold cyan]")
    req_path = PROJECT_ROOT / REQ_FILE
    if not req_path.is_file():
        console.print(f"[red]✖ {REQ_FILE} not found.[/red]")
        return

    try:
        # Use importlib.metadata, which is standard in Python >= 3.8
        from importlib.metadata import PackageNotFoundError, version

        with open(req_path, "r") as f:
            # Parse requirements, ignoring version specifiers for the check
            requirements = [
                line.strip().split("==")[0].split(">")[0].split("<")[0]
                for line in f
                if line.strip() and not line.startswith("#")
            ]

        table = Table(show_header=True, header_style="bold green")
        table.add_column("Dependency", style="dim", width=30)
        table.add_column("Status")

        all_ok = True
        for req in requirements:
            try:
                # This will raise PackageNotFoundError if the package isn't installed
                version(req)
                table.add_row(req, "[green]✔ Installed[/green]")
            except PackageNotFoundError:
                table.add_row(req, "[red]✖ Not Installed[/red]")
                all_ok = False

        console.print(table)
        if not all_ok:
            console.print(
                f"[yellow]Some dependencies are missing. Please run 'pip install -r {REQ_FILE}'.[/yellow]"
            )

    except ImportError:
        console.print(
            "[red]Could not check dependencies: `importlib.metadata` not found. Are you on Python 3.8+?[/red]"
        )
    except Exception as e:
        console.print(f"[red]Could not check dependencies: {e}[/red]")

    # Special check for yt-dlp
    try:
        subprocess.run(
            ["yt-dlp", "--version"], capture_output=True, check=True, text=True
        )
        console.print("\n[green]✔ yt-dlp is installed and accessible.[/green]")
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(
            "\n[red]✖ yt-dlp command failed. Ensure it's installed and in your system's PATH.[/red]"
        )
    console.print()


def scan_for_todos():
    """Scans the codebase for TODO/FIXME comments."""
    console.print("[bold cyan]4. Scanning for Code Todos...[/bold cyan]")
    console.print("Searching for 'TODO' and 'FIXME' comments in Python files...")

    try:
        # Using ripgrep (rg) for speed if available, otherwise fallback to simple grep.
        # We search in .py files, excluding notebooks and virtual envs.
        cmd = [
            "rg",
            "-i",
            r"(TODO|FIXME)",
            "-g",
            "*.py",
            "-g",
            "!__pycache__",
            "-g",
            "!.venv",
            "-g",
            "!venv",
            "--no-ignore",
            "--vimgrep",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)

        if result.returncode == 0 and result.stdout:
            # Vimgrep format: file:line:col:text
            lines = result.stdout.strip().split("\n")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("File", style="cyan", no_wrap=True)
            table.add_column("Line", style="magenta")
            table.add_column("Comment", style="white")

            for line in lines[:20]:  # Limit to first 20 findings
                parts = line.split(":", 3)
                if len(parts) == 4:
                    file, lnum, _, text = parts
                    table.add_row(file, lnum, text.strip())

            console.print(table)
            if len(lines) > 20:
                console.print(f"... and {len(lines) - 20} more.")

        elif result.returncode == 1:
            console.print("[green]✔ No 'TODO' or 'FIXME' comments found.[/green]")
        else:
            console.print(
                f"[yellow]rg command failed. Is ripgrep installed? Error: {result.stderr}[/yellow]"
            )

    except FileNotFoundError:
        console.print(
            "[yellow]ripgrep (rg) not found. Cannot scan for todos. Please install it for this feature.[/yellow]"
        )

    console.print()


def check_error_logs():
    """Scans log files for recent errors."""
    console.print("[bold cyan]5. Scanning Error Logs...[/bold cyan]")
    log_path = PROJECT_ROOT / LOG_DIR
    if not log_path.is_dir():
        console.print(
            f"[yellow]Log directory '{LOG_DIR}' not found. Skipping scan.[/yellow]"
        )
        return

    error_found = False
    log_files = sorted(log_path.glob("*.log"), key=os.path.getmtime, reverse=True)

    if not log_files:
        console.print("[green]✔ No log files found.[/green]")
        return

    table = Table(show_header=True, header_style="bold red")
    table.add_column("Log File", style="cyan")
    table.add_column("Last Error Entry")

    for log_file in log_files[:5]:  # Check 5 most recent logs
        with open(log_file, "r", errors="ignore") as f:
            lines = f.readlines()

        error_lines = [
            line.strip() for line in lines if "ERROR" in line or "CRITICAL" in line
        ]
        if error_lines:
            error_found = True
            last_error = error_lines[-1]
            table.add_row(
                log_file.name,
                Syntax(last_error, "log", theme="default", word_wrap=True),
            )

    if error_found:
        console.print(table)
        console.print(
            f"[yellow]Errors found in recent logs. Check '{LOG_DIR}/' for details.[/yellow]"
        )
    else:
        console.print(
            "[green]✔ No 'ERROR' or 'CRITICAL' entries found in recent logs.[/green]"
        )
    console.print()


def main():
    """Main function to run all health checks."""
    print_header()
    check_git_branch()
    check_directory_structure()
    check_env_file()
    check_dependencies()
    scan_for_todos()
    check_error_logs()

    console.print(Rule("[bold magenta]Health Check Complete", style="magenta"))
    console.print(
        "For a detailed project roadmap, see [bold]'docs/project_status_and_roadmap.md'[/bold]."
    )


if __name__ == "__main__":
    main()
