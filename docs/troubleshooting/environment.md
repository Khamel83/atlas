
# Environment Troubleshooting

This document provides guidance for troubleshooting common environment setup issues.

## Configuration Errors

If you see a "Configuration Errors" message when starting the application, it means that some required settings are missing from your `.env` file. Here are some common errors and how to fix them:

- **`OPENROUTER_API_KEY` is not set**: You need to provide an API key from [OpenRouter](https://openrouter.ai/) to use the AI features. Add `OPENROUTER_API_KEY=your_key_here` to your `.env` file.
- **`YOUTUBE_API_KEY` is not set**: If you want to ingest content from YouTube, you need to provide a YouTube Data API key. Add `YOUTUBE_API_KEY=your_key_here` to your `.env` file.
- **`INSTAPAPER_LOGIN` and `INSTAPAPER_PASSWORD` are not set**: To ingest content from Instapaper, you need to provide your Instapaper credentials. Add `INSTAPAPER_LOGIN=your_username` and `INSTAPAPER_PASSWORD=your_password` to your `.env` file.
- **`NYT_USERNAME` and `NYT_PASSWORD` are not set**: To ingest content from the New York Times, you need to provide your NYT credentials. Add `NYT_USERNAME=your_username` and `NYT_PASSWORD=your_password` to your `.env` file.

## Dependency Issues

If you encounter errors related to missing Python packages, make sure you have installed all the required dependencies by running:

```bash
pip install -r requirements.txt
```
