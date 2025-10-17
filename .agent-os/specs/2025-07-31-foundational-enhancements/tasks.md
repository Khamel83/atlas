# Tasks: Foundational Enhancements

**Objective:** Execute the foundational enhancements as specified in `@.agent-os/specs/2025-07-31-foundational-enhancements/spec.md`.

## Phase 1: Configuration Management

1.  **Modify `src/config_manager.py`:**
    -   Create a new function `validate_config(config)`.
    -   Inside this function, add checks to ensure the following keys exist: `audio`, `transcription`, `storage`, `analysis`.
    -   Add checks for nested keys: `audio.chunk_duration`, `storage.base_path`, etc.
    -   Verify that `audio.chunk_duration` is an integer.
    -   Verify that `storage.base_path` is a string, and that the directory exists and is writable (`os.path.isdir` and `os.access`).
    -   The function should raise a `ValueError` with a descriptive message if any check fails.

2.  **Integrate Validation:**
    -   In `src/main.py`, `src/audio_capture.py`, `src/transcribe.py`, and `src/web_interface.py`, import `validate_config`.
    -   At the beginning of the main execution block of each file, call `validate_config(config)` within a `try...except` block.
    -   If a `ValueError` is caught, print the error message to the console and exit the script using `sys.exit(1)`.

## Phase 2: Error Handling

1.  **Implement Retry Mechanism in `src/cloud_analyze.py`:**
    -   In the function that calls the OpenRouter API, wrap the API call in a loop.
    -   Use a library like `tenacity` or implement a manual loop with `time.sleep` for retries.
    -   Configure it for 3 retries with an exponential backoff (e.g., wait 1s, then 2s, then 4s).
    -   If all retries fail, log the final error and return `None` or raise a custom exception.

2.  **Improve `src/transcribe.py`:**
    -   In the main processing loop, when an exception occurs during the transcription of a file:
        -   Create a `failed` subdirectory inside the same folder as the audio file if it doesn't exist.
        -   Move the problematic audio file to this `failed` directory.
        -   Log the error with the original and new file paths.

3.  **Enhance `src/health_monitor.py`:**
    -   In the `restart` function, when a service is restarted, add a 5-second delay before the next check.
    -   This is a simple way to prevent rapid restart loops. A more advanced solution could involve tracking restart counts and increasing delays, but a simple sleep is sufficient for now.

## Phase 3: Performance Optimization

1.  **Update `src/database_schema.sql`:**
    -   Add the following line to the schema: `CREATE INDEX IF NOT EXISTS idx_transcripts_timestamp ON transcripts(timestamp);`

2.  **Modify `src/search_engine.py`:**
    -   Add a new function `optimize_database()`.
    -   This function should execute the `VACUUM;` SQL command on the database.
    -   Log a message before and after the vacuum process.

3.  **Expose Optimization in `src/health_monitor.py`:**
    -   Add a new command-line argument to `health_monitor.py` called `optimize`.
    -   When run with `python3 src/health_monitor.py optimize`, it should call the `optimize_database()` function from `search_engine.py`.

## Phase 4: Security & Privacy Hardening

1.  **Update `config.template.json`:**
    -   Add a new section:
        ```json
        "privacy": {
          "redaction_keywords": []
        },
        ```

2.  **Modify `src/analysis_router.py`:**
    -   Create a new function `redact_text(text, keywords)`.
    -   This function should take a string and a list of keywords, and replace all occurrences of those keywords (case-insensitive) with `[REDACTED]`.
    -   In the main analysis function, before passing the transcript text to the local or cloud analyzer, check if `config.get('privacy', {}).get('redaction_keywords')` exists and is not empty.
    -   If it is, call `redact_text` on the transcript content before sending it for analysis.
