# Spec-Lite: Foundational Enhancements

**Objective:** Address technical debt in the TrojanHorse system by improving configuration, error handling, performance, and privacy.

**Key Areas & Requirements:**

1.  **Config Validation (`src/config_manager.py`):**
    -   Create a central validation function for `config.json`.
    -   Check for required keys, correct data types, and valid paths.
    -   Called by all main components at startup.
    -   Exit gracefully with clear error messages on failure.

2.  **Error Handling:**
    -   `src/cloud_analyze.py`: Add retry with exponential backoff for API calls.
    -   `src/audio_capture.py`: Improve `health_monitor` restart logic to prevent rapid failure loops.
    -   `src/transcribe.py`: Move failed transcription files to a `failed/` directory.

3.  **Performance (`src/search_engine.py`):**
    -   Analyze and optimize database queries.
    -   Add a database index to `transcripts.timestamp`.
    -   Implement a periodic `VACUUM` command for database maintenance.

4.  **Privacy (`src/analysis_router.py`):**
    -   Add a `privacy.redaction_keywords` list to `config.json`.
    -   Before analysis, replace these keywords in transcripts with `[REDACTED]`.
