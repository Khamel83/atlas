# Tasks: User Guides and Documentation

**Objective:** Create comprehensive user guides and ensure consistency across all project documentation as specified in `@.agent-os/specs/2025-07-31-user-guides/spec.md`.

## Phase 1: User Guide: Getting Started

1.  **Create `docs/user_guides/getting_started.md`:**
    -   Write an introduction to TrojanHorse.
    -   Provide a concise quick setup checklist (prerequisites, clone, install `setup.py`).
    -   Explain how to perform the first run and verify installation using `python3 src/health_monitor.py status`.
    -   Describe basic usage: how to confirm audio capture and transcription are working.

## Phase 2: User Guide: Daily Operation & Features

1.  **Create `docs/user_guides/daily_operation.md`:**
    -   Explain the daily folder structure (`Meeting Notes/YYYY-MM-DD/transcribed_audio/`, `analysis/`).
    -   Detail how to use the web interface for search (keyword, semantic, hybrid) and viewing individual transcripts.
    -   Provide instructions on using the new Analytics Dashboard (`/dashboard`).
    -   Explain how to configure and use the hotkey client for quick searches.
    -   Cover basic maintenance commands: `health_monitor.py status`, `optimize`, `analyze`.

## Phase 3: User Guide: Advanced Configuration & Customization

1.  **Create `docs/user_guides/advanced_config.md`:**
    -   Provide a detailed breakdown of all `config.json` options, including `privacy` and `workflow_integration` sections.
    -   Explain how to modify analysis prompts.
    -   Describe advanced storage management options (temp_path, base_path, retention_days).
    -   Include a comprehensive troubleshooting section, consolidating and expanding on `README.md`'s troubleshooting.

## Phase 4: Consistency Review & Updates

1.  **Review and Update `README.md`:**
    -   Verify all commands, configuration examples, and feature descriptions are accurate and up-to-date.

2.  **Review and Update `MACHINE_SETUP.md`:**
    -   Ensure all installation steps, dependencies, and configuration instructions are current.

3.  **Review and Update `MANUAL_SETUP.md`:**
    -   Verify all manual setup steps and configuration instructions are current.

4.  **Review and Update `docs/API.md`:**
    -   Confirm all module interfaces and API endpoints are accurately documented.

5.  **Review and Update `docs/ARCHITECTURE.md`:**
    -   Ensure the architecture diagram and module descriptions reflect the current codebase.

6.  **Review and Update `docs/SETUP.md`:**
    -   Verify all detailed setup instructions are accurate and consistent.

## Phase 5: Final Documentation Review

1.  **Overall Consistency Check:** Read through all documentation files to ensure a consistent tone, style, and terminology.
2.  **Cross-referencing:** Verify that all internal links and cross-references are correct.
3.  **Completeness Check:** Ensure no major features or configurations are missing from the documentation.
