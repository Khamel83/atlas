# Spec: Foundational Enhancements

**Project:** TrojanHorse
**Date:** 2025-07-31
**Author:** Gemini Agent

## 1. Overview

This specification outlines a series of foundational enhancements to the TrojanHorse system. The goal is to address technical debt and improve the overall robustness, performance, and security of the application before building new features.

This effort is divided into four key areas:
1.  **Configuration Management:** Make the system more resilient to invalid or incomplete configuration.
2.  **Error Handling:** Improve how the application handles unexpected errors and recovers from them.
3.  **Performance Optimization:** Enhance the performance of database queries to ensure the system remains fast as data grows.
4.  **Security & Privacy Hardening:** Add more granular privacy controls for the user.

## 2. Detailed Requirements

### 2.1. Configuration Management

The current system relies on a `config.json` file but lacks robust validation. This can lead to cryptic errors if the configuration is malformed or missing required values.

**Requirements:**
-   A central validation function must be implemented in `src/config_manager.py`.
-   This function must be called at the startup of all relevant application components (`main.py`, `audio_capture.py`, `transcribe.py`, `web_interface.py`, etc.).
-   The validation should check for the presence of all required keys.
-   It should also check for the correct data types (e.g., `chunk_duration` is an integer).
-   For file paths like `storage.base_path`, it should verify that the path exists and is writable.
-   If validation fails, the application should exit gracefully with a clear, user-friendly error message indicating what is wrong with the configuration.

### 2.2. Error Handling

Core components should be more resilient to transient errors, such as network hiccups when calling a cloud API or temporary file access issues.

**Requirements:**
-   In `src/cloud_analyze.py`, implement a retry mechanism with exponential backoff for API calls to OpenRouter.
-   In `src/audio_capture.py`, if an FFmpeg process fails, the `health_monitor` should not just restart it but also log a structured error and potentially wait for a short period before restarting to prevent rapid failure loops.
-   In `src/transcribe.py`, if a file cannot be processed, it should be moved to a `failed/` directory within the day's folder structure instead of being left in the queue, preventing repeated processing attempts.

### 2.3. Performance Optimization

As the `trojan_search.db` database grows, queries for the web interface may slow down. Proactive optimization is needed.

**Requirements:**
-   Analyze the queries made by `src/search_engine.py`.
-   Ensure that appropriate database indexes are present for all columns used in `WHERE` clauses and `JOIN`s.
-   Specifically, the `transcripts.timestamp` column should be indexed to speed up date-range filtering.
-   The FTS5 table itself should be reviewed for potential optimizations.
-   A `VACUUM` command should be periodically runnable via a maintenance command in `health_monitor.py` to reclaim space and prevent fragmentation.

### 2.4. Security & Privacy Hardening

The user requires more control over what information is included in the AI analysis to enhance privacy.

**Requirements:**
-   Add a new section to `config.json` called `privacy`.
-   This section will contain a list of `redaction_keywords`.
-   In `src/analysis_router.py`, before sending a transcript to either the local or cloud analysis engine, it must be processed to replace any of the `redaction_keywords` with a placeholder like `[REDACTED]`.
-   This feature should be optional and only active if the `privacy.redaction_keywords` list is present and not empty in the config.

## 3. Success Criteria

-   The application will refuse to start if `config.json` is invalid, providing clear error messages.
-   The system will be more stable and less prone to crashing from transient errors.
-   The web interface search and filtering will remain responsive even with a large database.
-   The user will be able to prevent sensitive keywords from being included in AI-generated analysis.
