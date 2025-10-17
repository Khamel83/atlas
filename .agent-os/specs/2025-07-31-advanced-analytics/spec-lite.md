# Spec-Lite: Advanced Analytics

**Objective:** Create a system for cross-transcript analysis to identify trends and patterns in the user's audio data.

**Key Components:**

1.  **Analytics Engine (`src/analytics_engine.py`):**
    -   A new module to run batch analysis on transcripts within a date range.
    -   Will use a non-LLM NER model (e.g., `spaCy`) for efficient entity extraction (People, Orgs, Locations).
    -   Analysis results will be stored in new database tables.

2.  **Entity Extraction & Trending:**
    -   Extract and store entities from all transcripts.
    -   Aggregate entity data to calculate daily/weekly frequency.
    -   Identify "trending" entities by comparing frequency over time.

3.  **Analytics Dashboard (`/dashboard` in web interface):**
    -   A new page to visualize analytics.
    -   Will use Chart.js to display:
        -   Top 10 most frequent entities (bar chart).
        -   Daily frequency of top 5 entities (line chart).
        -   Top 5 trending entities (table).
    -   Will have a date range selector for the analysis period.
    -   Data will be served by new API endpoints (e.g., `/api/analytics/top_entities`).
