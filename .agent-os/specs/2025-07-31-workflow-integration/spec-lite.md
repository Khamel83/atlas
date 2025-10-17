# Spec-Lite: Workflow Integration

**Objective:** Allow the user to access the TrojanHorse knowledge base from any application via a system-wide hotkey.

**Key Components:**

1.  **Internal API Server (`src/internal_api.py`):**
    -   A new, lightweight, local-only API server.
    -   Runs on a separate port (e.g., 5001).
    -   Exposes one endpoint: `/search?query=...`
    -   Uses the existing `search_engine.py` to perform a hybrid search.
    -   Returns the top 3 results as simple JSON.
    -   Managed by `health_monitor.py`.

2.  **Hotkey Search Client (`src/hotkey_client.py`):**
    -   A background process that listens for a configurable, system-wide hotkey (e.g., `Cmd+Shift+C`).
    -   Uses a library like `pynput`.
    -   On hotkey press, it gets the clipboard content, calls the internal API, and shows the top result as a system notification.
    -   Also managed by `health_monitor.py`.

**Configuration:**
-   A new `workflow_integration` section in `config.json` for the hotkey and port.
