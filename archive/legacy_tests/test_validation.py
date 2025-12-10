import unittest

from helpers.validate import validate_config


class TestValidation(unittest.TestCase):

    def test_missing_api_keys(self):
        config = {
            "llm_provider": "openrouter",
            "youtube_ingestor": {"enabled": True},
            "instapaper_ingestor": {"enabled": True},
            "USE_PLAYWRIGHT_FOR_NYT": True,
        }
        errors = validate_config(config)
        self.assertIn(
            "OPENROUTER_API_KEY is required when llm_provider is 'openrouter'.", errors
        )
        self.assertIn(
            "YOUTUBE_API_KEY is required when the YouTube ingestor is enabled.", errors
        )
        self.assertIn(
            "INSTAPAPER_LOGIN and INSTAPAPER_PASSWORD are required when the Instapaper ingestor is enabled.",
            errors,
        )
        self.assertIn(
            "NYT_USERNAME and NYT_PASSWORD are required when USE_PLAYWRIGHT_FOR_NYT is true.",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
