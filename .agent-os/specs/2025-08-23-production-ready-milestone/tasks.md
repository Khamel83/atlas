# Tasks: Production-Ready Milestone (v2)

**Date**: 2025-08-23

**Status**: Proposed

## Phase 1: Critical Fixes & Core Functionality Validation

### Task 1.1: Diagnose Document Content Extraction Failure

*   **Depends On:** None
*   **Context:** The `audit_atlas_reality.py` script revealed that 18,575 documents have no content. This task is to diagnose the root cause of this failure.
*   **Steps:**
    1.  Read the code for the document processing pipeline, located in `run.py` and any related modules.
    2.  Identify the specific function responsible for content extraction from documents.
    3.  Add detailed logging to this function to trace its execution and identify the point of failure.
    4.  Run the document processing pipeline on a single, sample document that is known to be failing.
    5.  Analyze the logs to determine the exact cause of the failure.
*   **Success Criteria:** The root cause of the document content extraction failure is identified and documented.
*   **Failure Criteria:** The root cause of the failure cannot be identified after 4 hours of investigation.

### Task 1.2: Fix Document Content Extraction

*   **Depends On:** Task 1.1
*   **Context:** Now that the root cause of the document content extraction failure is known, this task is to fix it.
*   **Steps:**
    1.  Based on the findings from Task 1.1, develop a fix for the content extraction logic.
    2.  Write a unit test to verify that the fix works as expected.
    3.  Run the unit test and ensure that it passes.
*   **Success Criteria:** The unit test for the fix passes.
*   **Failure Criteria:** The unit test does not pass after 3 attempts.

### Task 1.3: Re-process Failed Documents

*   **Depends On:** Task 1.2
*   **Context:** Now that the document content extraction logic is fixed, this task is to re-process the 18,575 documents that previously failed.
*   **Steps:**
    1.  Create a script to identify and re-process the 18,575 failed documents.
    2.  Run the script in a screen session to ensure it continues to run in the background.
    3.  Monitor the script's progress and ensure that it is running without errors.
*   **Success Criteria:** The script successfully re-processes all 18,575 failed documents, and the `check_all_content.py` script shows that at least 90% of them now have content.
*   **Failure Criteria:** The script fails to re-process the documents, or the success rate is less than 90%.

### Task 1.4: Analyze Article Fetching Failures

*   **Depends On:** None
*   **Context:** The article success rate is only 50%. This task is to analyze the `retry_log` to identify the most common reasons for failure.
*   **Steps:**
    1.  Read the `retry_log` file.
    2.  Write a script to parse the log file and identify the most common error messages and failure patterns.
    3.  Categorize the failures (e.g., paywalls, Cloudflare, 404s, etc.).
*   **Success Criteria:** A report is generated that details the most common reasons for article fetching failures.
*   **Failure Criteria:** The script fails to parse the log file, or the report is not generated.

### Task 1.5: Enhance Article Fetching Pipeline

*   **Depends On:** Task 1.4
*   **Context:** Now that the most common reasons for article fetching failures are known, this task is to enhance the pipeline to address them.
*   **Steps:**
    1.  Based on the findings from Task 1.4, implement new strategies for handling paywalls and other common issues.
    2.  Integrate a proxy rotation service to avoid being blocked.
    3.  Add a more sophisticated user-agent rotation mechanism.
    4.  Test the enhanced pipeline on a sample of 100 failed articles.
*   **Success Criteria:** The success rate on the sample of 100 failed articles is at least 85%.
*   **Failure Criteria:** The success criteria is not met after 3 attempts.

### Task 1.6: Implement Instapaper Processing

*   **Depends On:** Task 1.5
*   **Context:** The Instapaper processing pipeline is currently missing.
*   **Steps:**
    1.  Design and implement a pipeline to process Instapaper exports.
    2.  The pipeline should be able to parse the Instapaper CSV format, extract the article URLs, and process them using the enhanced article fetching pipeline.
    3.  Test the pipeline on a sample Instapaper export.
*   **Success Criteria:** All articles from the sample Instapaper export are successfully processed and stored in the database.
*   **Failure Criteria:** The success criteria is not met after 2 attempts.

### Task 1.7: Create End-to-End Core Functionality Test Suite

*   **Depends On:** Tasks 1.3, 1.5, 1.6
*   **Context:** A comprehensive end-to-end test suite is needed to validate the core functionality.
*   **Steps:**
    1.  Create a test suite that covers the entire lifecycle of an article, podcast, document, and Instapaper item, from ingestion to storage and retrieval.
    2.  The test suite should be automated and run as part of the CI/CD pipeline.
*   **Success Criteria:** The test suite passes without any errors.
*   **Failure Criteria:** The test suite does not pass after 3 attempts.

## Phase 2: Comprehensive Testing & Hardening

...
(The rest of the tasks will be similarly detailed)