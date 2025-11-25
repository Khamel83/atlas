"""
API command for Atlas CLI.

Provides command to start the Atlas API server.
"""

import argparse
import sys
import os
from typing import Dict, Any
from pathlib import Path

# Add web directory to Python path for API imports
web_dir = Path(__file__).parent.parent.parent.parent / "web"
sys.path.insert(0, str(web_dir / "api"))

try:
    import uvicorn
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Required dependencies not installed: {e}", file=sys.stderr)
    print("Please install with: pip install uvicorn python-dotenv", file=sys.stderr)
    sys.exit(1)


class APICommand:
    """Command for starting Atlas API server."""

    @staticmethod
    def configure_parser(parser: argparse.ArgumentParser) -> None:
        """
        Configure the argument parser for API command.

        Args:
            parser: Argument parser to configure
        """
        parser.add_argument(
            "--host",
            type=str,
            default="127.0.0.1",
            help="Host to bind the API server to (default: 127.0.0.1)"
        )
        parser.add_argument(
            "--port",
            type=int,
            default=7444,
            help="Port to bind the API server to (default: 7444)"
        )
        parser.add_argument(
            "--reload",
            action="store_true",
            help="Enable auto-reload for development"
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=1,
            help="Number of worker processes (default: 1)"
        )
        parser.add_argument(
            "--log-level",
            choices=["critical", "error", "warning", "info", "debug"],
            default="info",
            help="Log level for uvicorn (default: info)"
        )

    def execute(self, args: argparse.Namespace, context: Dict[str, Any]) -> int:
        """
        Execute the API command.

        Args:
            args: Parsed command-line arguments
            context: Command context with config and storage

        Returns:
            Exit code
        """
        try:
            # Load environment variables
            load_dotenv()

            # Import main app
            from main import app

            print(f"🚀 Starting Atlas API server on {args.host}:{args.port}")
            print(f"🔗 API docs: http://{args.host}:{args.port}/docs")
            print(f"🌍 TrojanHorse integration: http://{args.host}:{args.port}/trojanhorse/docs")
            print("Press Ctrl+C to stop")

            # Configuration
            config = {
                "app": app,
                "host": args.host,
                "port": args.port,
                "log_level": args.log_level,
                "reload": args.reload
            }

            # Add workers if not in reload mode
            if args.workers > 1 and not args.reload:
                config["workers"] = args.workers

            # Run the server
            uvicorn.run(**config)

            return 0

        except KeyboardInterrupt:
            print("\n👋 Atlas API server stopped")
            return 0
        except ImportError as e:
            print(f"❌ Failed to import API modules: {e}", file=sys.stderr)
            print("Make sure you're running from the Atlas root directory", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"❌ Failed to start API server: {e}", file=sys.stderr)
            return 1