# Process & Evaluate Subsystem

This directory contains the "Smart Evaluator" components of Atlas. After content has been ingested and normalized by the scripts in `/helpers`, the scripts in this directory are responsible for the deeper, post-ingestion analysis.

## `evaluate.py`

This script contains the core AI-powered evaluation functions that enrich the raw ingested content.

### Key Functions
-   **`classify_content(text)`**: Determines the type of content (e.g., "Interview," "Technical Article," "News Report") to decide which downstream analysis is appropriate.
-   **`summarize_text(text)`**: Generates a concise, neutral summary of the input text.
-   **`extract_entities(text)`**: Identifies and extracts key people, organizations, and locations from the text, returning them as structured JSON.
-   **`diarize_speakers(text)`**: For content classified as an "Interview," this function processes the transcript to identify and label the different speakers (e.g., "Host," "Guest"), making it much more readable.

### How It Works

The ingestion scripts (e.g., `article_fetcher.py`) call these functions after successfully acquiring content. The results of these evaluations are not written into the Markdown files themselves, but are stored in corresponding `.eval.json` files in the `evaluation/` directory. This keeps the primary content clean while providing a rich, structured layer of metadata for future use in the "Ask" subsystem.

## Configurable AI Backend

The evaluation pipeline is designed to be flexible. You can choose between using a remote API service or a locally running LLM. This is controlled via the `.env` file in the project root:

- **`LLM_PROVIDER`**: Set this to `openrouter` (the default) to use the OpenRouter.ai API. You must provide an `OPENROUTER_API_KEY`.
- **`LLM_PROVIDER`**: Set this to `ollama` to use a local model running via the Ollama server.
- **`LLM_MODEL`**: Specify the model name to be used (e.g., `mistralai/mistral-7b-instruct` for OpenRouter, or `llama3` for a local Ollama model).

The system uses the `litellm` library to seamlessly switch between providers based on this configuration.
