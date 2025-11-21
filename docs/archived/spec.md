# Atlas Ingest - System Specification

## Purpose

Atlas Ingest is the first module in a larger system for building a local, durable, AI-augmented memory system. Its job is to automatically ingest, parse, and persist useful information from common input streams (YouTube, podcasts, articles, and link dumps) into structured Markdown + metadata files. It is explicitly designed for local-first workflows, long-term viability, and future semantic processing.

## Design Goals

* **Local-first**: Runs entirely offline unless using optional APIs (e.g., OpenRouter for transcription).
* **Composable**: Each ingestor is standalone, swappable, testable.
* **Durable**: Output uses open formats (e.g., Markdown, plain text, JSON sidecars).
* **Headless**: Meant to be run via cron, CLI, or batch jobs — no UI.
* **Minimal dependencies**: Only standard Python packages + explicitly declared ones.

## Ingest Types

### 1. YouTube

* Input: YouTube watch history JSON export.
* Uses `youtube_transcript_api` to retrieve English transcript.
* Output: Markdown file with transcript, title, video ID, and metadata.

### 2. Podcasts

* Input: OPML export (e.g., from Overcast).
* Uses `feedparser` to crawl feeds and download recent episodes.
* Audio is transcribed via:

  * Local Whisper CLI (`WHISPER_PATH`)
  * or OpenRouter API (e.g., Gemini Flash).
* Output: `.md` file with transcript + metadata, stored in the configurable data directory (e.g., `<data_dir>/podcasts/`).

### 3. Articles

* Input: List of URLs (or pre-saved `.txt` file).
* Uses `readability-lxml` + BeautifulSoup to clean and parse content.
* Output: `.md` file with extracted article body + metadata.

## Folder Layout

```
Atlas/
├── input/
│   ├── youtube_history.json
│   ├── podcasts.opml
│   ├── urls.txt
├── output/
│   ├── youtube/
│   ├── podcasts/
│   └── articles/
├── helpers/
│   ├── youtube_ingestor.py
│   ├── podcast_ingestor.py
│   ├── article_fetcher.py
│   ├── transcription.py
│   └── utils.py
├── ingest/
│   └── ingest_main.py
├── requirements.txt
└── .env
```

## .env Configuration

```
TRANSCRIBE_ENABLED=true
TRANSCRIBE_BACKEND=api
WHISPER_PATH=/usr/local/bin/whisper
OPENROUTER_API_KEY=sk-...
MODEL=google/gemini-2.0-flash-lite-001
```

## Planned Extensions

* Summarization layer after ingestion
* Persistent error logging and retry queue
* Optional tagging/categorization using lightweight LLM prompt chains
* Self-describing output bundles with frontmatter or JSON sidecars

## Usage

1. Place all input files in `/input`
2. Run `python3 ingest/ingest_main.py`
3. Processed, structured content appears in `/output` subfolders.

## Constraints

* Python 3.10+
* All dependencies declared in `requirements.txt`
* No hidden API keys, all via `.env`
* OpenRouter API is optional

## Status

MVP working end-to-end for:

* YouTube transcript ingestion
* OPML podcast + Whisper/OpenRouter transcription
* Article cleanup from URL

Everything else is polish, monitoring, and layering AI on top.

## Sample Inputs & Outputs

- See `inputs/articles.txt`, `inputs/youtube.txt`, and `inputs/podcasts.opml` for example input files.
- Outputs are written to the configurable data directory (`DATA_DIRECTORY` in `.env`).

## Troubleshooting

- **YouTube downloads fail:**
  - Ensure `yt-dlp` is installed. Some videos may be region-locked or removed.
- **Podcast episodes skipped:**
  - Some feeds lack standard audio fields. Check logs for 'No audio URL found'.
- **Transcription skipped:**
  - Set `TRANSCRIBE_ENABLED=true` in `.env` and configure Whisper or OpenRouter API.
- **Errors and retries:**
  - See the end-of-run error summary, or check `<data_dir>/*/ingest.log` and `retries.json`.

For more, see the README or open an issue.

## 🧠 Categorization Philosophy for Atlas

This project separates ingestion (getting data) from categorization (understanding it). Categorization must be:

- **Cheap**: No need to re-download or re-parse content.
- **Reversible**: We can refine categories or fix mistakes later.
- **Incremental**: Only reprocess what changed.

### Key Rules

1. **Raw Content is Sacred**
   - Always store original text/transcripts in Markdown or JSON.
   - Never overwrite raw data when tagging or processing.

2. **Categorization is Stateless**
   - All tags are generated as a pure function of:
     - Content
     - Config (e.g. `categories.yaml`)
     - Optional model metadata (e.g. model version, hash)

3. **Tags Stored Separately**
   - Either:
     - Embedded in frontmatter (`.md`)
     - Stored in `.meta.json` sidecar
   - This allows us to rerun or diff tag state easily.

4. **Rerun-Friendly**
   - Categorization can be rerun:
     - On all files (`--rerun-all`)
     - Only where tags are missing/stale (`--fix-missing`)
     - As a dry-run diff (`--check --diff`)

5. **Eventually Replaceable**
   - We can swap models or pipelines without re-ingesting.
   - If embeddings or classifiers improve, just rerun.

### Optional Metadata

Each content file can track:

```jsonc
{
  "last_tagged_at": "2025-07-10T12:34:56Z",
  "category_version": "v1.0",
  "source_hash": "abc123...",
  "tag_confidence": 0.92
}
```

## Guiding Principles

These principles guide the architecture of Atlas.

- **Idempotent & Rerun-Friendly**: Scripts can be run multiple times without creating duplicate content. If an output file already exists, it's skipped. This makes the system resilient to interruptions.
- **Stateless & File-Based**: The state of the system is stored entirely on the filesystem. There is no database. This makes it easy to backup, move, and inspect the data.
  - Inputs are read from the `inputs/` directory.
  - Outputs are written to the configurable data directory (`DATA_DIRECTORY` in `.env`).
  - A `retries.json` file tracks items that failed all ingestion attempts.
- **Cheap First, Expensive Later**: The initial ingestion step is designed to be fast and cheap (downloading files). The expensive AI processing can be run later, separately, and even on a different machine.
- **Explicit over Implicit**: Configuration is handled through a single `.env` file and a `categories.yaml`, not hidden in code.
- **Local-First AI**: The system is designed to use local models (Ollama, local Whisper) for transcription and analysis, falling back to APIs only when necessary. This is configurable via the `LLM_PROVIDER` setting in `.env`.

## FAQ

- **How do I add a new article/podcast/YouTube video?**
  - Add the URL to the corresponding file in `inputs/`.
- **How do I configure the AI models?**
  - Set the `LLM_PROVIDER` (`openrouter` or `ollama`) and `LLM_MODEL` in your `.env` file. If using OpenRouter, you must also provide an `OPENROUTER_API_KEY`.
- **How do I enable transcription?**
  - Set `TRANSCRIBE_ENABLED=true` in `.env` and configure Whisper or OpenRouter API.
- **How do I know what went wrong?**
  - See the end-of-run error summary, or check `output/*/ingest.log` and `retries.json`.

## Future-Proofing
The file-based, stateless design makes Atlas adaptable. Future changes, like adding a new data source or changing the AI models, can be implemented with minimal disruption to the existing archive. The `process/recategorize.py` script is an example of this, allowing for bulk updates without re-fetching any source content.