# Ingestion Subsystem

This directory contains the primary scripts and logic for ingesting content from various sources into Atlas.

## Process

1.  **Input Sources**: The ingestors read from files in the `inputs/` directory (e.g., `articles.txt`, `podcasts.opml`, `youtube.txt`).
2.  **Fetching**: Each module fetches the raw content (HTML for articles, .mp3s for podcasts, transcripts for YouTube).
3.  **Processing**: The core logic in each script fetches the content, extracts key information (like text from an article or a transcript from a video), and saves it.
4.  **Output**: All artifacts—Markdown, metadata, and original media (where applicable)—are stored in the directory specified by `DATA_DIRECTORY` in the root `.env` file, organized by type.
5.  **Logging**: Detailed logs of every operation, including successes, skips, and failures, are written to `<DATA_DIRECTORY>/<type>/ingest.log`.
6.  **Evaluation**: As content is processed, "evaluation" files are generated in the `evaluation/` directory. These are structured JSON files that track every processing step, from initial fetch to summarization and tagging.
7.  **Retries**: If an item fails repeatedly, its ID is added to `retries.json` for manual review.

## Monitoring and Error Handling

While you can monitor the process by tailing the log files, the recommended method is to use the **Error Triage UI**. It provides a powerful, centralized interface for reviewing logs, filtering for issues, and quickly diagnosing problems with the ingestion pipeline.

To launch the UI, run the following command from the project root:

```bash
streamlit run error_review.py
```

This is the most effective way to stay on top of any ingestion failures.
