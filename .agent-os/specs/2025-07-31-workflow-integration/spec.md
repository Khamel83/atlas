# Spec: Workflow Integration

**Project:** TrojanHorse
**Date:** 2025-07-31
**Author:** Gemini Agent

## 1. Overview

This specification outlines the development of a **Workflow Integration** feature. The purpose is to allow the user to seamlessly access the knowledge stored in the TrojanHorse system from any application, without needing to open the web interface and manually perform a search. This moves the system from a passive repository to an active, real-time assistant.

This will be achieved by creating two key components:

1.  **An Internal API:** A local, lightweight, and fast API server that exposes the core search functionality of the system. This is for internal use by other components, not for public access.
2.  **A Hotkey-Based Search Client:** A background process that listens for a system-wide hotkey. When triggered, it will take the content of the user's clipboard, query the internal API, and display the top search result as a system notification.

## 2. Detailed Requirements

### 2.1. Internal API Server

A new script, `src/internal_api.py`, will be created. This will be a separate, lightweight web server (e.g., using Flask or FastAPI) that runs locally.

**Requirements:**
-   The API server must be designed for speed and low resource usage.
-   It will run on a different port than the main web interface (e.g., 5001).
-   It will expose a single, primary endpoint: `/search`.
-   The `/search` endpoint will accept a `query` parameter (the text to search for).
-   It will utilize the existing `search_engine.py` to perform a hybrid keyword and semantic search.
-   It must return the top 3 search results in a simple JSON format, including the transcript text snippet and the timestamp.
-   This server should be managed by the `health_monitor.py` service, just like the other core components.

### 2.2. Hotkey Search Client

A new script, `src/hotkey_client.py`, will be created. This script will run in the background and listen for a user-configurable hotkey.

**Requirements:**
-   The client will use a library like `pynput` or `keyboard` to listen for a system-wide hotkey combination (e.g., `Cmd+Shift+C`).
-   This hotkey must be configurable in `config.json`.
-   When the hotkey is pressed, the client will:
    1.  Get the current content of the system clipboard.
    2.  Make a GET request to the internal API's `/search` endpoint with the clipboard content as the query.
    3.  Receive the JSON response.
    4.  Display the top search result as a system notification. The notification should show the timestamp of the result and a snippet of the text.
-   The client must be robust and handle cases where the clipboard is empty or the API is unavailable.
-   This client will also be managed as a service by `health_monitor.py`.

### 2.3. Configuration and Management

**Requirements:**
-   The `config.json` file will be updated to include a new `workflow_integration` section, specifying the hotkey combination and the internal API port.
-   `health_monitor.py` will be updated to manage the `internal_api.py` and `hotkey_client.py` processes, allowing them to be started, stopped, and monitored along with the rest of the system.
-   The main `setup.py` script may need to be updated to handle the installation of these new services if they require separate launch agents, or they can be managed under the main application's service.

## 3. Success Criteria

-   The internal API server runs successfully and provides fast search results.
-   The hotkey client runs in the background with minimal resource usage.
-   Pressing the configured hotkey with text in the clipboard triggers a search and displays a relevant system notification.
-   The entire feature is managed by the existing health monitor and feels like a cohesive part of the TrojanHorse system.
