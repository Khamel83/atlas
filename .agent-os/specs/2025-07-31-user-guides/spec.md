# Spec: User Guides and Documentation

**Project:** TrojanHorse
**Date:** 2025-07-31
**Author:** Gemini Agent

## 1. Overview

This specification outlines the creation of comprehensive user guides and additional documentation for the TrojanHorse Context Capture System. The goal is to provide clear, accessible, and practical information for users to effectively set up, operate, and troubleshoot the system, leveraging its newly implemented features.

This effort focuses on user-centric documentation, moving beyond technical specifications to practical application.

## 2. Detailed Requirements

### 2.1. User Guide: Getting Started

This guide will provide a simplified, step-by-step walkthrough for new users to get the system up and running quickly.

**Content:**
-   **Introduction to TrojanHorse:** What it is, what it does, and its core benefits.
-   **Quick Setup Checklist:** A concise list of prerequisites and initial installation steps.
-   **First Run & Verification:** How to start the system and confirm it's working (using `health_monitor.py status`).
-   **Basic Usage:** How to ensure audio is being captured and transcribed.

### 2.2. User Guide: Daily Operation & Features

This guide will cover the day-to-day use of TrojanHorse and explain its key features in a user-friendly manner.

**Content:**
-   **Understanding Your Data:** Explanation of the daily folder structure and file types (`.txt`, `.analysis.md`).
-   **Using the Web Interface:**
    -   How to access and navigate the search interface.
    -   Performing keyword, semantic, and hybrid searches.
    -   Viewing individual transcripts and their analysis.
    -   Using the new Analytics Dashboard (Top Entities, Trends).
-   **Leveraging Workflow Integration:**
    -   Configuring and using the hotkey client for quick searches.
    -   Practical examples of how to use the hotkey in daily workflows.
-   **Basic Maintenance:** How to check system status, optimize the database, and run analytics manually.

### 2.3. User Guide: Advanced Configuration & Customization

This guide will delve into more advanced settings and customization options for power users.

**Content:**
-   **`config.json` Deep Dive:** Detailed explanation of all configuration options, including `privacy` and `workflow_integration` sections.
-   **Customizing Prompts:** How to modify the analysis prompts for local and cloud LLMs.
-   **Managing Storage:** Advanced options for `temp_path`, `base_path`, and retention policies.
-   **Troubleshooting Reference:** A more detailed version of the troubleshooting section from `README.md`, with common issues and solutions.

### 2.4. Consistency Review & Updates

Ensure all existing documentation (`README.md`, `MACHINE_SETUP.md`, `MANUAL_SETUP.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/SETUP.md`) is consistent with the latest code and features. This includes verifying that all commands, configuration options, and feature descriptions are accurate.

## 3. Success Criteria

-   Three distinct user guides are created, each targeting a specific level of user proficiency.
-   All new features (Advanced Analytics, Workflow Integration, enhanced `health_monitor` commands) are clearly explained in the user guides.
-   Existing documentation is reviewed and updated for consistency and accuracy with the current codebase.
-   The documentation is easy to understand and enables users to effectively utilize the TrojanHorse system.
