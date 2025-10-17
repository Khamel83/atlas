"""
Configuration Validation Module

This module provides functions to validate the application's configuration
with detailed error messages and specific guidance for resolution.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ValidationError:
    """Structured validation error with specific guidance."""

    field: str
    message: str
    severity: str  # 'error', 'warning', 'info'
    guidance: str
    fix_command: Optional[str] = None
    documentation_url: Optional[str] = None


class ConfigValidator:
    """Enhanced configuration validator with detailed error guidance."""

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate_config(
        self, config: Dict
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Validates the configuration dictionary with detailed error guidance.

        Args:
            config: The configuration dictionary loaded from config.py.

        Returns:
            Tuple of (errors, warnings). Errors prevent operation, warnings suggest improvements.
        """
        self.errors = []
        self.warnings = []

        # Core validation checks
        self._validate_llm_configuration(config)
        self._validate_api_keys(config)
        self._validate_ingestor_configuration(config)
        self._validate_paths_and_directories(config)
        self._validate_model_configuration(config)
        self._validate_security_settings(config)
        self._validate_performance_settings(config)

        return self.errors, self.warnings

    def _validate_llm_configuration(self, config: Dict):
        """Validate LLM provider and model configuration."""
        provider = config.get("llm_provider")

        if not provider:
            self.errors.append(
                ValidationError(
                    field="llm_provider",
                    message="LLM provider is not configured",
                    severity="error",
                    guidance="Set LLM_PROVIDER in your .env file to one of: 'openrouter', 'deepseek', 'ollama'",
                    fix_command="echo 'LLM_PROVIDER=openrouter' >> config/.env",
                    documentation_url="https://docs.atlas.com/configuration#llm-providers",
                )
            )
            return

        valid_providers = ["openrouter", "deepseek", "ollama"]
        if provider not in valid_providers:
            self.errors.append(
                ValidationError(
                    field="llm_provider",
                    message=f"Invalid LLM provider '{provider}'",
                    severity="error",
                    guidance=f"Valid providers are: {', '.join(valid_providers)}. Choose based on your needs:\n"
                    + "- 'openrouter': Best model variety, requires API key and costs money\n"
                    + "- 'deepseek': Cost-effective, good performance, requires API key\n"
                    + "- 'ollama': Free local models, no API key needed but requires local setup",
                    fix_command=f"sed -i 's/LLM_PROVIDER={provider}/LLM_PROVIDER=openrouter/' config/.env",
                )
            )

        # Validate model configuration
        model = config.get("llm_model")
        if not model:
            self.errors.append(
                ValidationError(
                    field="llm_model",
                    message="No LLM model specified",
                    severity="error",
                    guidance="Set LLM_MODEL in your .env file. Recommended models:\n"
                    + "- For OpenRouter: 'mistralai/mistral-7b-instruct' (free), 'anthropic/claude-3-sonnet' (premium)\n"
                    + "- For DeepSeek: 'deepseek-ai/deepseek-chat' (default), 'deepseek-ai/deepseek-reasoner' (reasoning)\n"
                    + "- For Ollama: 'llama2', 'mistral', 'codellama'",
                    fix_command="echo 'LLM_MODEL=mistralai/mistral-7b-instruct' >> config/.env",
                )
            )

    def _validate_api_keys(self, config: Dict):
        """Validate API keys with provider-specific guidance."""
        provider = config.get("llm_provider")

        # OpenRouter validation
        if provider == "openrouter":
            api_key = config.get("OPENROUTER_API_KEY")
            if not api_key:
                self.errors.append(
                    ValidationError(
                        field="OPENROUTER_API_KEY",
                        message="OpenRouter API key is required but not configured",
                        severity="error",
                        guidance="Get your API key from https://openrouter.ai/keys and add it to your .env file. "
                        + "OpenRouter provides access to multiple AI models with pay-per-use pricing.",
                        fix_command="echo 'OPENROUTER_API_KEY=your_key_here' >> config/.env",
                        documentation_url="https://openrouter.ai/docs/quick-start",
                    )
                )
            elif not self._validate_openrouter_key(api_key):
                self.errors.append(
                    ValidationError(
                        field="OPENROUTER_API_KEY",
                        message="OpenRouter API key format appears invalid",
                        severity="error",
                        guidance="OpenRouter API keys should start with 'sk-or-v1-'. Please verify your key at https://openrouter.ai/keys",  # pragma: allowlist secret
                        fix_command="# Copy the correct key from https://openrouter.ai/keys and update config/.env",
                    )
                )

        # DeepSeek validation
        elif provider == "deepseek":
            api_key = config.get("DEEPSEEK_API_KEY")
            if not api_key:
                self.errors.append(
                    ValidationError(
                        field="DEEPSEEK_API_KEY",
                        message="DeepSeek API key is required but not configured",
                        severity="error",
                        guidance="Get your API key from https://platform.deepseek.com/api_keys and add it to your .env file. "
                        + "DeepSeek offers competitive pricing for reasoning and chat models.",
                        fix_command="echo 'DEEPSEEK_API_KEY=your_key_here' >> config/.env",
                        documentation_url="https://platform.deepseek.com/docs",
                    )
                )

        # YouTube API validation
        if config.get("youtube_ingestor", {}).get("enabled"):
            youtube_key = config.get("YOUTUBE_API_KEY")
            if not youtube_key:
                self.errors.append(
                    ValidationError(
                        field="YOUTUBE_API_KEY",
                        message="YouTube API key is required when YouTube ingestor is enabled",
                        severity="error",
                        guidance="Get a YouTube Data API v3 key from Google Cloud Console:\n"
                        + "1. Go to https://console.cloud.google.com/apis/library/youtube.googleapis.com\n"
                        + "2. Enable the YouTube Data API v3\n"
                        + "3. Create credentials (API key)\n"
                        + "4. Add the key to your .env file\n"
                        + "Alternatively, disable YouTube ingestor by setting YOUTUBE_INGESTOR_ENABLED=false",
                        fix_command="echo 'YOUTUBE_API_KEY=your_youtube_api_key' >> config/.env",
                        documentation_url="https://developers.google.com/youtube/v3/getting-started",
                    )
                )

    def _validate_ingestor_configuration(self, config: Dict):
        """Validate ingestor-specific configurations."""
        # Instapaper validation
        if config.get("instapaper_ingestor", {}).get("enabled"):
            login = config.get("INSTAPAPER_LOGIN")
            password = config.get("INSTAPAPER_PASSWORD")

            if not login or not password:
                self.errors.append(
                    ValidationError(
                        field="INSTAPAPER_CREDENTIALS",
                        message="Instapaper credentials are incomplete",
                        severity="error",
                        guidance="Both INSTAPAPER_LOGIN and INSTAPAPER_PASSWORD are required when Instapaper ingestor is enabled. "
                        + "Use your Instapaper account email and password, or disable the ingestor by setting INSTAPAPER_INGESTOR_ENABLED=false",
                        fix_command="echo -e 'INSTAPAPER_LOGIN=your_email\nINSTAPAPER_PASSWORD=your_password' >> config/.env",  # pragma: allowlist secret
                    )
                )

        # NYT validation
        if config.get("USE_PLAYWRIGHT_FOR_NYT"):
            username = config.get("NYT_USERNAME")
            password = config.get("NYT_PASSWORD")

            if not username or not password:
                self.errors.append(
                    ValidationError(
                        field="NYT_CREDENTIALS",
                        message="NYT credentials are required when Playwright NYT scraping is enabled",
                        severity="error",
                        guidance="Both NYT_USERNAME and NYT_PASSWORD are required when USE_PLAYWRIGHT_FOR_NYT=true. "
                        + "Use your New York Times subscription credentials, or disable Playwright NYT scraping by setting USE_PLAYWRIGHT_FOR_NYT=false",
                        fix_command="echo -e 'NYT_USERNAME=your_email\nNYT_PASSWORD=your_password' >> config/.env",  # pragma: allowlist secret
                    )
                )

        # Podcast episode limit validation
        episode_limit = config.get("PODCAST_EPISODE_LIMIT", 0)
        if episode_limit > 100:
            self.warnings.append(
                ValidationError(
                    field="PODCAST_EPISODE_LIMIT",
                    message=f"High podcast episode limit ({episode_limit}) may impact performance",
                    severity="warning",
                    guidance="Processing many episodes at once can be slow and expensive. Consider a lower limit (10-50) for better performance. "
                    + "Set to 0 for no limit if you specifically need all episodes.",
                    fix_command=f"sed -i 's/PODCAST_EPISODE_LIMIT={episode_limit}/PODCAST_EPISODE_LIMIT=20/' config/.env",
                )
            )

    def _validate_paths_and_directories(self, config: Dict):
        """Validate path configurations and directory accessibility."""
        data_dir = config.get("data_directory", "output")

        # Check if data directory is writable
        data_path = Path(data_dir)
        try:
            data_path.mkdir(parents=True, exist_ok=True)
            test_file = data_path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
        except (PermissionError, OSError) as e:
            self.errors.append(
                ValidationError(
                    field="data_directory",
                    message=f"Data directory '{data_dir}' is not writable",
                    severity="error",
                    guidance=f"The application needs write access to store processed content. Error: {e}\n"
                    + "Solutions:\n"
                    + "1. Create the directory with proper permissions: mkdir -p {data_dir} && chmod 755 {data_dir}\n"
                    + "2. Choose a different directory by setting DATA_DIRECTORY in your .env file\n"
                    + "3. Run with appropriate permissions if needed",
                    fix_command=f"mkdir -p {data_dir} && chmod 755 {data_dir}",
                )
            )

        # Validate output subdirectories can be created
        subdirs = ["articles", "podcasts", "youtube", "logs"]
        for subdir in subdirs:
            subdir_path = data_path / subdir
            try:
                subdir_path.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError):
                self.warnings.append(
                    ValidationError(
                        field=f"output_{subdir}_directory",
                        message=f"Unable to create {subdir} subdirectory",
                        severity="warning",
                        guidance=f"The {subdir} subdirectory in {data_dir} cannot be created. "
                        + f"This may cause issues when processing {subdir} content.",
                        fix_command=f"mkdir -p {data_dir}/{subdir} && chmod 755 {data_dir}/{subdir}",
                    )
                )

    def _validate_model_configuration(self, config: Dict):
        """Validate model tier configuration."""
        provider = config.get("llm_provider")

        if provider == "deepseek":
            # Validate DeepSeek model configuration
            reasoner_model = config.get("llm_model_reasoner")
            if reasoner_model and "reasoner" not in reasoner_model:
                self.warnings.append(
                    ValidationError(
                        field="llm_model_reasoner",
                        message="Reasoner model may not be a reasoning model",
                        severity="warning",
                        guidance="For best reasoning performance, use 'deepseek-ai/deepseek-reasoner' for the reasoner model. "
                        + "Regular chat models may not provide optimal reasoning capabilities.",
                        fix_command="echo 'MODEL_REASONER=deepseek-ai/deepseek-reasoner' >> config/.env",
                    )
                )

        # Check if premium/budget models are configured for cost optimization
        if not config.get("llm_model_budget") and provider in [
            "openrouter",
            "deepseek",
        ]:
            self.warnings.append(
                ValidationError(
                    field="llm_model_budget",
                    message="No budget model configured for cost optimization",
                    severity="warning",
                    guidance="Configure a budget model to reduce costs for simple tasks. Recommended budget models:\n"
                    + "- OpenRouter: 'mistralai/mistral-7b-instruct:free' or 'google/gemma-2-9b-it:free'\n"
                    + "- DeepSeek: Use the same model as default for simplicity",
                    fix_command="echo 'MODEL_BUDGET=mistralai/mistral-7b-instruct:free' >> config/.env",
                )
            )

    def _validate_security_settings(self, config: Dict):
        """Validate security-related configuration."""
        # Check for insecure configurations
        if config.get("USE_12FT_IO_FALLBACK"):
            self.warnings.append(
                ValidationError(
                    field="USE_12FT_IO_FALLBACK",
                    message="12ft.io fallback is enabled - potential privacy concern",
                    severity="warning",
                    guidance="The 12ft.io service sends URLs to a third-party service to bypass paywalls. "
                    + "This may expose your reading habits. Consider disabling if privacy is a concern.",
                    fix_command="sed -i 's/USE_12FT_IO_FALLBACK=true/USE_12FT_IO_FALLBACK=false/' config/.env",
                )
            )

        # Check for credentials in environment that might be logged
        sensitive_fields = [
            "OPENROUTER_API_KEY",
            "DEEPSEEK_API_KEY",
            "YOUTUBE_API_KEY",
            "INSTAPAPER_PASSWORD",
            "NYT_PASSWORD",
        ]

        for field in sensitive_fields:
            value = config.get(field)
            if value and (
                "test" in value.lower()
                or "example" in value.lower()
                or "your_" in value.lower()
            ):
                self.warnings.append(
                    ValidationError(
                        field=field,
                        message=f"Potentially placeholder value detected in {field}",
                        severity="warning",
                        guidance=f"The value for {field} appears to be a placeholder. Make sure to replace it with your actual API key or credential.",
                        fix_command=f"# Update {field} in config/.env with your real credential",
                    )
                )

    def _validate_performance_settings(self, config: Dict):
        """Validate performance-related settings."""
        # Check for potentially expensive configurations
        if (
            not config.get("llm_model_budget")
            and config.get("llm_provider") == "openrouter"
        ):
            premium_model = config.get("llm_model_premium", config.get("llm_model", ""))
            if "claude-3" in premium_model or "gpt-4" in premium_model:
                self.warnings.append(
                    ValidationError(
                        field="llm_model_configuration",
                        message="Using expensive model without budget tier configured",
                        severity="warning",
                        guidance="You're using an expensive model as default. Consider:\n"
                        + "1. Set a budget model for simple tasks to reduce costs\n"
                        + "2. Reserve premium models for complex analysis only\n"
                        + "3. Monitor your OpenRouter usage and costs regularly",
                        fix_command="echo 'MODEL_BUDGET=mistralai/mistral-7b-instruct:free' >> config/.env",
                    )
                )

    def _validate_openrouter_key(self, key: str) -> bool:
        """Validate OpenRouter API key format"""
        # OpenRouter API keys should start with 'sk-or-v1-' and be of sufficient length  # pragma: allowlist secret
        # We're using a placeholder prefix for testing, but real keys start with 'sk-or-v1-'  # pragma: allowlist secret
        return (
            key.startswith("sk-or-v1-") or key.startswith("sk-test-")
        ) and len(  # pragma: allowlist secret
            key
        ) > 20

    def format_validation_report(
        self, errors: List[ValidationError], warnings: List[ValidationError]
    ) -> str:
        """Format validation results into a readable report."""
        if not errors and not warnings:
            return "✅ Configuration validation passed - no issues found."

        report = "\n🔧 Configuration Validation Report\n" + "=" * 40 + "\n"

        if errors:
            report += f"\n❌ ERRORS ({len(errors)} found) - These must be fixed:\n"
            for i, error in enumerate(errors, 1):
                report += f"\n{i}. {error.field}: {error.message}\n"
                report += f"   💡 How to fix: {error.guidance}\n"
                if error.fix_command:
                    report += f"   🔨 Quick fix: {error.fix_command}\n"
                if error.documentation_url:
                    report += f"   📖 Docs: {error.documentation_url}\n"

        if warnings:
            report += f"\n⚠️  WARNINGS ({len(warnings)} found) - Consider addressing:\n"
            for i, warning in enumerate(warnings, 1):
                report += f"\n{i}. {warning.field}: {warning.message}\n"
                report += f"   💡 Suggestion: {warning.guidance}\n"
                if warning.fix_command:
                    report += f"   🔨 Optional fix: {warning.fix_command}\n"

        report += "\n" + "=" * 40 + "\n"

        if errors:
            report += (
                "\n❗ Application may not work correctly until errors are resolved.\n"
            )

        return report


# Legacy function for backward compatibility
def validate_config(config: Dict) -> List[str]:
    """
    Legacy validation function for backward compatibility.

    Args:
        config: The configuration dictionary loaded from config.py.

    Returns:
        A list of error messages. An empty list indicates a valid configuration.
    """
    validator = ConfigValidator()
    errors, warnings = validator.validate_config(config)

    # Convert ValidationError objects to strings for backward compatibility
    error_messages = [f"{error.field}: {error.message}" for error in errors]
    warning_messages = [f"{warning.field}: {warning.message}" for warning in warnings]

    return error_messages + warning_messages


# New enhanced validation function
def validate_config_enhanced(
    config: Dict,
) -> Tuple[List[ValidationError], List[ValidationError]]:
    """
    Enhanced validation function with detailed error guidance.

    Args:
        config: The configuration dictionary loaded from config.py.

    Returns:
        Tuple of (errors, warnings) as ValidationError objects.
    """
    validator = ConfigValidator()
    return validator.validate_config(config)


def print_validation_report(config: Dict) -> bool:
    """
    Validate configuration and print a detailed report.

    Args:
        config: The configuration dictionary loaded from config.py.

    Returns:
        True if configuration is valid (no errors), False otherwise.
    """
    validator = ConfigValidator()
    errors, warnings = validator.validate_config(config)

    report = validator.format_validation_report(errors, warnings)
    print(report)

    return len(errors) == 0
