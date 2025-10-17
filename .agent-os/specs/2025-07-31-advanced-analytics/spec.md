# Spec: Advanced Analytics

**Project:** TrojanHorse
**Date:** 2025-07-31
**Author:** Gemini Agent

## 1. Overview

This specification details the development of an **Advanced Analytics** feature for the TrojanHorse system. The current system provides search and analysis on individual transcripts. This feature will introduce a new layer of analysis that operates across multiple transcripts to identify trends, patterns, and recurring themes over time.

The goal is to provide the user with a high-level overview of their captured audio data, moving from a document-retrieval system to a personal knowledge-discovery platform.

This will be achieved by:
1.  Creating a new **Analytics Engine** that can process transcripts in batches.
2.  Identifying and extracting key entities (people, places, topics) from all transcripts.
3.  Performing trend analysis on these entities.
4.  Visualizing the results in a new **"Analytics Dashboard"** section of the web interface.

## 2. Detailed Requirements

### 2.1. Analytics Engine

A new module, `src/analytics_engine.py`, will be created. This engine will be responsible for all cross-transcript analysis.

**Requirements:**
-   The engine will have a main function `run_analysis(date_range)` that can operate on all transcripts within a given period.
-   It will use the existing `search_engine.py` to retrieve the raw text of transcripts.
-   It must be designed to be extensible, allowing new types of analysis to be added in the future.
-   The results of the analysis will be stored in a new set of tables in the `trojan_search.db` database.

### 2.2. Entity Extraction and Aggregation

The first type of analysis to be implemented is entity extraction.

**Requirements:**
-   The analytics engine will process the text of each transcript and use a Named Entity Recognition (NER) model to identify entities such as People (PER), Organizations (ORG), and Locations (LOC).
-   A simple, efficient, non-LLM-based NER model (e.g., from the `spaCy` library) should be used for this task to ensure performance.
-   The extracted entities will be stored in a new database table, `analytics_entities`, with columns for `entity_text`, `entity_type`, `transcript_id`, and `timestamp`.
-   The engine will then aggregate this data to calculate the frequency of each entity over time.

### 2.3. Trend Analysis

Once entities are aggregated, the system will perform trend analysis.

**Requirements:**
-   The engine will calculate the daily and weekly frequency of the most common entities.
-   It will identify "trending" entities by comparing their frequency in the last 7 days to the previous period.
-   The results of this trend analysis will be stored in another new table, `analytics_trends`.

### 2.4. Analytics Dashboard

A new section will be added to the web interface (`src/web_interface.py` and new templates) to display the results of the advanced analysis.

**Requirements:**
-   A new page, accessible via a `/dashboard` URL, will be created.
-   This page will feature several data visualizations, created using Chart.js:
    -   A bar chart showing the **Top 10 Most Frequent People, Organizations, and Locations** over the last 30 days.
    -   A line chart showing the **daily frequency** of the top 5 entities over the last 30 days.
    -   A table displaying the **Top 5 Trending Entities** for the current week.
-   The dashboard will have a date range selector to allow the user to customize the analysis period.
-   The data for these charts will be served by new API endpoints in `src/web_interface.py` (e.g., `/api/analytics/top_entities`, `/api/analytics/trends`).

## 3. Success Criteria

-   The user can run the analytics engine via a new command.
-   The system successfully identifies and stores entities from transcripts.
-   The new "Analytics Dashboard" in the web interface displays meaningful and accurate visualizations of trends and entity frequencies.
-   The analysis process is reasonably performant and can be run on a daily or weekly basis without significant system impact.
