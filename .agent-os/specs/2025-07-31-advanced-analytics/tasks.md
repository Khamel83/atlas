# Tasks: Advanced Analytics

**Objective:** Execute the Advanced Analytics feature as specified in `@.agent-os/specs/2025-07-31-advanced-analytics/spec.md`.

## Phase 1: Backend Development - Analytics Engine

1.  **Update `requirements.txt`:**
    -   Add the `spacy` library.
    -   After adding, instruct the user to run `pip install -r requirements.txt` and `python -m spacy download en_core_web_sm`.

2.  **Update `src/database_schema.sql`:**
    -   Add a new table for entities:
        ```sql
        CREATE TABLE IF NOT EXISTS analytics_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transcript_id INTEGER,
            entity_text TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (transcript_id) REFERENCES transcripts (id)
        );
        ```
    -   Add a new table for trends:
        ```sql
        CREATE TABLE IF NOT EXISTS analytics_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_text TEXT NOT NULL,
            trend_score REAL NOT NULL,
            last_updated DATETIME NOT NULL
        );
        ```

3.  **Create `src/analytics_engine.py`:**
    -   Create a new file for the analytics engine.
    -   Import `spacy` and load the `en_core_web_sm` model.
    -   Create a main function `run_full_analysis()`.
    -   This function should:
        -   Connect to the database.
        -   Fetch all transcripts that have not yet been analyzed.
        -   For each transcript, process its text with the spaCy NER model.
        -   For each entity found, insert it into the `analytics_entities` table.
        -   Mark the transcript as analyzed to avoid reprocessing.

4.  **Implement Trend Calculation:**
    -   In `src/analytics_engine.py`, create a new function `calculate_trends()`.
    -   This function should:
        -   Query the `analytics_entities` table to get entity frequencies for the last 7 days and the 7 days prior.
        -   Implement a simple trend scoring algorithm (e.g., `(new_frequency - old_frequency) / old_frequency`).
        -   Store the top 5 trending entities in the `analytics_trends` table.

5.  **Expose Engine via `health_monitor.py`:**
    -   Add a new command `analyze` to `health_monitor.py`.
    -   When run with `python3 src/health_monitor.py analyze`, it should call `run_full_analysis()` and then `calculate_trends()` from the analytics engine.

## Phase 2: Frontend Development - Analytics Dashboard

1.  **Create New API Endpoints in `src/web_interface.py`:**
    -   Create an endpoint `/api/analytics/top_entities`:
        -   It should accept `start_date` and `end_date` as query parameters.
        -   It will query the `analytics_entities` table to find the most frequent entities (People, Orgs, Locations) in that date range.
        -   It should return the data in a JSON format suitable for Chart.js.
    -   Create an endpoint `/api/analytics/trends`:
        -   It will query the `analytics_trends` table.
        -   It should return the top 5 trending entities as JSON.

2.  **Create New HTML Template:**
    -   Create a new file `templates/dashboard.html`.
    -   This file should extend `base.html`.
    -   Add canvas elements for the charts (e.g., `<canvas id="topEntitiesChart"></canvas>`).
    -   Add a table structure for the trending entities.

3.  **Update `src/web_interface.py` to Serve the Dashboard:**
    -   Add a new route `/dashboard` that renders the `dashboard.html` template.
    -   Add a link to the dashboard in the navigation bar in `templates/base.html`.

4.  **Create JavaScript for the Dashboard:**
    -   In `static/js/app.js` (or a new dedicated JS file), add JavaScript code to:
        -   Fetch data from the new API endpoints when the dashboard page loads.
        -   Use Chart.js to create and populate the bar chart for top entities and the line chart for daily frequencies.
        -   Populate the HTML table with the trending entities data.
        -   Implement the date range selector functionality to refetch data when the date changes.
