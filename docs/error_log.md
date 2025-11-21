# Atlas Project - Error Log

This document tracks significant errors encountered during development, their root causes, and the eventual solutions. The goal is to prevent repeating the same debugging cycles for recurring or similar problems.

---

## Error: `ValueError: Evaluation files can only be created for files in the 'output/' directory.`

- **Date:** 2024-08-01
- **Status:** Resolved

### Symptom

During a full pipeline run, every single podcast episode failed at the evaluation step. The logs were flooded with hundreds of identical errors:
`ValueError: Evaluation files can only be created for files in the 'output/' directory.`

This indicated a systemic configuration issue. The `data_directory` was correctly set in the `.env` file to a custom path, but the evaluation utility was still using the default `"output/"` directory.

### Investigation & Debugging Journey

The path to the solution was complex and involved several incorrect assumptions:

1.  **Initial Hypothesis (Incorrect):** A stray, unused import (`from helpers.config import load_config`) in `helpers/podcast_ingestor.py` was suspected of creating a conflict and causing a stale or incomplete `config` object to be used. Removing this import had no effect.

2.  **Second Hypothesis (Incorrect):** The primary entrypoint, `run.py`, was assumed to be dropping or overwriting the `config` object before passing it to the ingestor functions. This led to a prolonged debugging session involving:
    *   Adding `print()` statements to trace the `id()` and contents of the `config` object through the call stack (`run.py` -> `ingest_main.py` -> `podcast_ingestor.py`).
    *   This debugging process failed repeatedly with a series of `ImportError`s (`setup_logging` not found, `ingest_articles` not found, etc.).

3.  **Realization (The "Aha!" Moment):** The recurring `ImportError`s revealed that my understanding of the project's structure was outdated. `run.py` was a broken, legacy entrypoint from a previous refactor. The *actual*, working entrypoint for the ingestion process was the standalone script `ingest/ingest_main.py`.

### Root Cause

The core issue was that `ingest/ingest_main.py` was not being called correctly. It was designed to be run as a standalone script and was responsible for loading its own configuration. My attempts to run it via the broken `run.py` script bypassed its configuration logic, leading to the `EvaluationFile` class receiving an empty `config` dictionary and falling back to the hardcoded `"output"` default.

### Solution

The solution involved two key steps:
1.  **Abandoning the broken `run.py` script** and identifying `ingest/ingest_main.py` as the correct entrypoint for the ingestion pipeline.
2.  Ensuring that when `ingest/ingest_main.py` is run, it correctly initializes its own configuration by calling `get_config()` from `helpers/config.py`. The final, successful pipeline run was initiated by calling `python3 ingest/ingest_main.py` directly from the command line.

### Lessons Learned

- Do not assume the project structure is static. If `ImportError`s occur, re-verify the current file structure and intended entrypoints before debugging logic.
- A single, unambiguous entrypoint script (`run.py`) should be maintained to avoid confusion. The presence of multiple potential entrypoints complicated the debugging process significantly.

---

## Error: `Failed to start scheduler: cannot pickle '_thread.RLock' object`

- **Date:** 2025-07-13
- **Status:** Investigating

### Symptom

When restarting the scheduler daemon with `python3 scripts/atlas_scheduler.py --start`, the following error appears in the logs:

```
ERROR - Failed to start scheduler: cannot pickle '_thread.RLock' object
Failed to start scheduler: cannot pickle '_thread.RLock' object
```

Despite this, jobs are still listed and appear to persist.

### Root Cause

This error is typically caused by attempting to pickle (serialize) an object that contains a thread lock, which is not serializable. In the context of APScheduler, this can happen if the scheduler or job store is being pickled or if a job function or argument contains a non-serializable object (such as a lock or open file handle).

### Solution Steps

- Review all job functions and arguments to ensure they are serializable.
- Ensure that the scheduler and job store are not being pickled or passed between processes/threads in a way that triggers serialization.
- If using multiprocessing or background threads, ensure only serializable objects are passed to jobs.
- Investigate if any recent changes to job definitions or the scheduler setup introduced non-serializable objects.
- If the error persists but does not affect job persistence or execution, monitor for side effects and consider reporting upstream to APScheduler if reproducible.

### Status

- Jobs persist and are listed after restart, but the error should be resolved for robustness.
- Further investigation required if job execution or persistence is affected.