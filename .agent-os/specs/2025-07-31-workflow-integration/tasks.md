# Tasks: Workflow Integration

**Objective:** Execute the Workflow Integration feature as specified in `@.agent-os/specs/2025-07-31-workflow-integration/spec.md`.

## Phase 1: Backend - Internal API Server

1.  **Update `requirements.txt`:**
    -   Add the `pynput` library (or `keyboard` if preferred).
    -   Add `fastapi` and `uvicorn` for the lightweight API server.

2.  **Create `src/internal_api.py`:**
    -   Create a new file for the internal API server using FastAPI.
    -   Import `SearchEngine` from `src/search_engine.py`.
    -   Instantiate the search engine.
    -   Create a single API endpoint `/search` that accepts a `query` parameter.
    -   This endpoint should call the search engine's hybrid search function.
    -   It should return the top 3 results as a JSON response.
    -   Set up the main block to run the FastAPI app using `uvicorn` on a specific port (e.g., 5001).

3.  **Update `config.template.json`:**
    -   Add a new section:
        ```json
        "workflow_integration": {
          "hotkey": "<cmd>+<shift>+c",
          "internal_api_port": 5001
        },
        ```

## Phase 2: Backend - Hotkey Client

1.  **Create `src/hotkey_client.py`:**
    -   Create a new file for the hotkey listener.
    -   Import the necessary libraries (`pynput`, `pyperclip`, `requests`, `rumps` or similar for notifications).
    -   Load the hotkey combination and API port from the `config.json` file.
    -   Create a function `on_hotkey_press()`.
    -   This function should:
        -   Get text from the clipboard using `pyperclip.paste()`.
        -   If there is text, make a `requests.get()` call to `http://localhost:PORT/search`.
        -   Parse the JSON response.
        -   If there are results, format the top result into a string.
        -   Use a library like `rumps` (macOS) or `plyer` (cross-platform) to display a system notification with the result.

2.  **Set up Hotkey Listener:**
    -   In `src/hotkey_client.py`, set up the `pynput` listener to call `on_hotkey_press()` when the configured hotkey is detected.
    -   The script should run in a continuous loop to keep listening.

## Phase 3: Integration and Management

1.  **Update `src/health_monitor.py`:**
    -   Add `internal_api.py` and `hotkey_client.py` to the list of services to be monitored.
    -   Update the `start`, `stop`, `restart`, and `status` functions to include these new components.
    -   Ensure they are started in the correct order (e.g., `internal_api.py` before `hotkey_client.py`).

2.  **Update `src/setup.py` (if necessary):**
    -   Determine if the new scripts need to be added to the main `com.contextcapture.audio.plist` LaunchAgent or if they should have their own.
    -   For simplicity, it's likely best to modify the main service to launch all three background processes (`audio_capture`, `internal_api`, `hotkey_client`). This will require modifying the shell script that the LaunchAgent calls.
    -   Alternatively, create a new `run_all_services.sh` script that starts all background processes, and have the plist file execute this script.

3.  **Update Documentation:**
    -   Briefly mention the new workflow integration feature in the main `README.md`.
    -   Add details about the new configuration options in `config.template.json` to the `docs/SETUP.md` file.
