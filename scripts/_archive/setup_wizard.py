#!/usr/bin/env python3
"""
Atlas Setup Wizard - Complete new user onboarding experience.

This wizard guides new users through the complete Atlas setup process,
from dependency validation to configuration, providing a seamless
onboarding experience.

Usage:
    python scripts/setup_wizard.py [--automated] [--skip-deps] [--config-only]

Options:
    --automated: Run with minimal prompts using defaults
    --skip-deps: Skip dependency validation (assume already done)
    --config-only: Only run configuration setup
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


class AtlasSetupWizard:
    """Complete Atlas setup wizard for new user onboarding."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.setup_state = {
            "step": 0,
            "total_steps": 7,
            "completed_steps": [],
            "failed_steps": [],
            "warnings": [],
        }

    def run_setup(
        self,
        automated: bool = False,
        skip_deps: bool = False,
        config_only: bool = False,
    ) -> bool:
        """
        Run the complete Atlas setup process.

        Args:
            automated: Use defaults with minimal user interaction
            skip_deps: Skip dependency validation step
            config_only: Only run configuration setup

        Returns:
            bool: True if setup completed successfully
        """

        try:
            self._print_welcome()

            if not config_only:
                # Step 1: Environment Check
                if not self._step_environment_check():
                    return False

                # Step 2: Dependency Validation
                if not skip_deps and not self._step_dependency_validation(automated):
                    return False

                # Step 3: Directory Setup
                if not self._step_directory_setup(automated):
                    return False

            # Step 4: Environment Configuration
            if not self._step_environment_configuration(automated):
                return False

            # Step 5: Configuration Validation
            if not self._step_configuration_validation():
                return False

            if not config_only:
                # Step 6: Initial Test
                if not self._step_initial_test():
                    return False

                # Step 7: Setup Completion
                self._step_setup_completion()

            return True

        except KeyboardInterrupt:
            print("\n\n⚠️  Setup cancelled by user.")
            return False
        except Exception as e:
            print(f"\n❌ Setup failed with error: {e}")
            return False

    def _print_welcome(self):
        """Print welcome message and setup overview."""
        print("=" * 70)
        print("🚀 ATLAS SETUP WIZARD")
        print("=" * 70)
        print()
        print("Welcome to Atlas - Your Personal Cognitive Amplification Platform!")
        print()
        print("This wizard will guide you through the complete setup process:")
        print("  📋 Environment validation")
        print("  🔧 Dependency installation")
        print("  📁 Directory structure creation")
        print("  ⚙️  Configuration setup")
        print("  ✅ System validation")
        print("  🧪 Initial testing")
        print("  🎉 Setup completion")
        print()

        if not self._confirm_continue():
            raise KeyboardInterrupt()

    def _step_environment_check(self) -> bool:
        """Step 1: Basic environment validation."""
        self._print_step_header(1, "Environment Check")

        # Check Python version
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            print(f"❌ Python 3.9+ required, found {version.major}.{version.minor}")
            print("   Please install Python 3.9+ from https://python.org")
            return False

        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")

        # Check if we're in the right directory
        required_files = ["run.py", "requirements.txt", "helpers/config.py"]
        missing_files = []

        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"❌ Missing required files: {', '.join(missing_files)}")
            print("   Make sure you're running this from the Atlas project directory")
            return False

        print("✓ Project structure validated")

        # Check git
        try:
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print("✓ Git available")
            else:
                print("⚠️  Git not available (optional but recommended)")
                self.setup_state["warnings"].append("Git not available")
        except FileNotFoundError:
            print("⚠️  Git not available (optional but recommended)")
            self.setup_state["warnings"].append("Git not available")

        self._mark_step_complete(1)
        return True

    def _step_dependency_validation(self, automated: bool) -> bool:
        """Step 2: Comprehensive dependency validation."""
        self._print_step_header(2, "Dependency Validation")

        print("Running comprehensive dependency check...")

        # Run dependency validation script
        try:
            script_path = self.project_root / "scripts" / "validate_dependencies.py"

            cmd = [sys.executable, str(script_path)]
            if automated:
                cmd.extend(["--fix", "--verbose"])
            else:
                # Ask user if they want to auto-fix issues
                print("\nWould you like to automatically fix any dependency issues?")
                fix_deps = self._get_yes_no("Auto-fix dependencies", default=True)

                if fix_deps:
                    cmd.extend(["--fix", "--verbose"])
                else:
                    cmd.append("--verbose")

            result = subprocess.run(cmd, cwd=self.project_root)

            if result.returncode == 0:
                print("\n✅ All dependencies validated successfully!")
                self._mark_step_complete(2)
                return True
            else:
                print("\n❌ Dependency validation failed.")

                if not automated:
                    print("\nOptions:")
                    print("1. Continue setup anyway (may cause issues later)")
                    print("2. Exit and fix dependencies manually")

                    choice = input("Choose option (1/2, default=2): ").strip()
                    if choice == "1":
                        print("⚠️  Continuing with dependency issues...")
                        self.setup_state["warnings"].append(
                            "Dependency validation failed"
                        )
                        self._mark_step_complete(2)
                        return True

                return False

        except Exception as e:
            print(f"❌ Error running dependency validation: {e}")
            return False

    def _step_directory_setup(self, automated: bool) -> bool:
        """Step 3: Create required directory structure."""
        self._print_step_header(3, "Directory Setup")

        required_dirs = [
            "output",
            "output/articles",
            "output/articles/html",
            "output/articles/markdown",
            "output/articles/metadata",
            "output/youtube",
            "output/podcasts",
            "config",
            "logs",
            "retries",
        ]

        created_dirs = []
        failed_dirs = []

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name

            try:
                if dir_path.exists():
                    print(f"✓ {dir_name}/ (exists)")
                else:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(dir_name)
                    print(f"✓ {dir_name}/ (created)")
            except Exception as e:
                failed_dirs.append((dir_name, str(e)))
                print(f"❌ {dir_name}/ (failed: {e})")

        if created_dirs:
            print(f"\nCreated {len(created_dirs)} directories")

        if failed_dirs:
            print(f"\n❌ Failed to create {len(failed_dirs)} directories:")
            for dir_name, error in failed_dirs:
                print(f"   {dir_name}: {error}")

            if not automated:
                continue_anyway = self._get_yes_no(
                    "Continue setup despite directory creation failures", default=False
                )
                if not continue_anyway:
                    return False
            else:
                return False

        self._mark_step_complete(3)
        return True

    def _step_environment_configuration(self, automated: bool) -> bool:
        """Step 4: Generate and configure .env file."""
        self._print_step_header(4, "Environment Configuration")

        env_path = self.project_root / ".env"

        # Check if .env already exists
        if env_path.exists():
            if automated:
                print("✓ .env file already exists")
                self._mark_step_complete(4)
                return True

            print("📄 .env file already exists")

            choice = input(
                "What would you like to do?\n"
                "1. Keep existing .env file\n"
                "2. Regenerate .env file (backup current)\n"
                "3. Interactively update .env file\n"
                "Choose option (1/2/3, default=1): "
            ).strip()

            if choice == "1" or not choice:
                print("✓ Keeping existing .env file")
                self._mark_step_complete(4)
                return True
            elif choice == "2":
                force_regenerate = True
                interactive = False
            elif choice == "3":
                force_regenerate = True
                interactive = True
            else:
                print("Invalid choice, keeping existing file")
                self._mark_step_complete(4)
                return True
        else:
            force_regenerate = True
            interactive = not automated

        # Generate .env file
        try:
            script_path = self.project_root / "scripts" / "generate_env.py"
            cmd = [sys.executable, str(script_path)]

            if force_regenerate:
                cmd.append("--force")

            if automated:
                cmd.append("--quiet")
            elif interactive:
                cmd.append("--interactive")

            result = subprocess.run(cmd, cwd=self.project_root)

            if result.returncode == 0:
                print("✅ Environment configuration completed!")
                self._mark_step_complete(4)
                return True
            else:
                print("❌ Environment configuration failed")
                return False

        except Exception as e:
            print(f"❌ Error generating .env file: {e}")
            return False

    def _step_configuration_validation(self) -> bool:
        """Step 5: Validate configuration loads correctly."""
        self._print_step_header(5, "Configuration Validation")

        try:
            # Add project root to path for imports
            sys.path.insert(0, str(self.project_root))

            from helpers.config import load_config

            config = load_config()

            print("✓ Configuration loads successfully")

            # Check for common configuration issues
            issues = []

            # Check data directory
            data_dir = config.get("data_directory", "output")
            data_path = self.project_root / data_dir
            if not data_path.exists():
                issues.append(f"Data directory '{data_dir}' does not exist")

            # Check API keys if present
            openrouter_key = config.get("OPENROUTER_API_KEY")
            if openrouter_key and len(openrouter_key) < 10:
                issues.append("OpenRouter API key appears to be invalid")

            if issues:
                print("\n⚠️  Configuration issues detected:")
                for issue in issues:
                    print(f"   - {issue}")
                self.setup_state["warnings"].extend(issues)
            else:
                print("✓ Configuration validation passed")

            self._mark_step_complete(5)
            return True

        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            print("   Please check your .env file and configuration")
            return False

    def _step_initial_test(self) -> bool:
        """Step 6: Run initial system test."""
        self._print_step_header(6, "Initial Test")

        print("Running basic system test...")

        try:
            # Test basic imports
            sys.path.insert(0, str(self.project_root))

            print("✓ Testing core imports...")
            from helpers.config import load_config

            # Test configuration loading
            print("✓ Testing configuration loading...")
            load_config()

            # Test path manager
            print("✓ Testing path management...")

            # Test metadata manager
            print("✓ Testing metadata management...")

            print("✅ All basic tests passed!")
            self._mark_step_complete(6)
            return True

        except Exception as e:
            print(f"❌ Initial test failed: {e}")
            print("   Some components may not work correctly")

            continue_anyway = self._get_yes_no(
                "Continue setup despite test failures", default=True
            )

            if continue_anyway:
                self.setup_state["warnings"].append(f"Initial test failed: {e}")
                self._mark_step_complete(6)
                return True

            return False

    def _step_setup_completion(self):
        """Step 7: Setup completion and next steps."""
        self._print_step_header(7, "Setup Complete!")

        print("🎉 Congratulations! Atlas setup is complete.")
        print()

        if self.setup_state["warnings"]:
            print("⚠️  Setup completed with warnings:")
            for warning in self.setup_state["warnings"]:
                print(f"   - {warning}")
            print()

        print("📋 What's been set up:")
        for step_num in self.setup_state["completed_steps"]:
            step_names = {
                1: "✅ Environment validated",
                2: "✅ Dependencies installed and validated",
                3: "✅ Directory structure created",
                4: "✅ Environment configuration generated",
                5: "✅ Configuration validated",
                6: "✅ Initial system test passed",
                7: "✅ Setup completed",
            }
            print(f"   {step_names.get(step_num, f'Step {step_num}')}")

        print()
        print("🚀 Next Steps:")
        print("   1. Review your .env file and customize as needed")
        print("   2. Test Atlas: python run.py --help")
        print("   3. Add some content: create inputs/articles.txt with URLs")
        print("   4. Process content: python run.py")
        print("   5. Check the web interface: python web/app.py")
        print()
        print("📚 Documentation:")
        print("   - README.md: Project overview and usage")
        print("   - QUICK_START.md: Quick start guide")
        print("   - docs/: Detailed documentation")
        print()
        print("🆘 Getting Help:")
        print("   - Check docs/troubleshooting_checklist.md")
        print("   - Run: python scripts/validate_dependencies.py")
        print(
            '   - Review configuration: python -c "from helpers.config import load_config; print(load_config())"'
        )
        print()
        print("Happy content processing! 🧠✨")

        self._mark_step_complete(7)

    # Helper methods
    def _print_step_header(self, step_num: int, step_name: str):
        """Print formatted step header."""
        self.setup_state["step"] = step_num

        print()
        print("─" * 70)
        print(f"Step {step_num}/{self.setup_state['total_steps']}: {step_name}")
        print("─" * 70)

    def _mark_step_complete(self, step_num: int):
        """Mark a step as completed."""
        if step_num not in self.setup_state["completed_steps"]:
            self.setup_state["completed_steps"].append(step_num)
        time.sleep(0.5)  # Brief pause for user to see completion

    def _confirm_continue(self) -> bool:
        """Ask user to confirm they want to continue."""
        response = input("Continue with setup? (Y/n): ").strip().lower()
        return response in ["", "y", "yes"]

    def _get_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Get yes/no response from user."""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{prompt}? ({default_text}): ").strip().lower()

        if response == "":
            return default
        return response in ["y", "yes"]


def main():
    """Main entry point for the setup wizard."""
    parser = argparse.ArgumentParser(
        description="Atlas Setup Wizard - Complete new user onboarding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/setup_wizard.py                    # Full interactive setup
    python scripts/setup_wizard.py --automated        # Automated setup with defaults
    python scripts/setup_wizard.py --skip-deps        # Skip dependency validation
    python scripts/setup_wizard.py --config-only      # Only configuration setup
        """,
    )

    parser.add_argument(
        "--automated",
        action="store_true",
        help="Run with minimal prompts using defaults",
    )

    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency validation (assume already done)",
    )

    parser.add_argument(
        "--config-only", action="store_true", help="Only run configuration setup"
    )

    args = parser.parse_args()

    # Initialize and run setup wizard
    wizard = AtlasSetupWizard()

    success = wizard.run_setup(
        automated=args.automated, skip_deps=args.skip_deps, config_only=args.config_only
    )

    if success:
        print("\n🎉 Setup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Setup failed. Please check the errors above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
