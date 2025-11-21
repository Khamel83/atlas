# Design Doc: Advanced Archival & Paywall Bypassing Strategy

*This document contains the user-provided research and plan for creating a robust, multi-layered fallback system for the article ingestor.*

---

### 🛠️ Paywall Bypass & Archive Fallback Options

1.  **12ft.io / 12ft Ladder**
    *   **Usage**: Prepend `https://12ft.io/` in front of the original URL to retrieve a cleaner, paywall-free version.
    *   **How it works**: Disables JavaScript and fetches a Google-cached or “text-only” version of the page.

2.  **Internet Archive (Wayback Machine)**
    *   **API availability**: Includes public endpoints like Availability, SavePageNow, and CDX to check or archive pages. We primarily use the [Wayback Availability JSON API](https://archive.org/help/wayback_api.php).
    *   **Use cases**: Good fallback when paywalls persist or pages are removed.

3.  **Archive.today (aka archive.is)**
    *   **Functionality**: Creates snapshots with unique, persistent URLs. Commonly used in investigative archiving.

4.  **Memento Protocol / Other Archives**
    *   **Scope**: Exposes time-based URIs across multiple archives (e.g., web, Wikipedia). Useful for retrieving historical versions.

5.  **Browser-based ‘print-friendly’ services**
    *   **Examples**: `txtify.it`, `PrintFriendly`, Bardeen‑style browser plugins.
    *   **Effect**: Provide a stripped-down, text‑only version bypassing paywall overlays—but less reliable universally.

---

### 🧠 Integration Plan for Atlas Ingest

1.  Attempt direct fetch of the page.
2.  If content appears truncated or paywalled (via a new `is_truncated()` helper):
    *   Retry using `12ft.io`.
    *   If still failing, use `Archive.today` API to snapshot or retrieve.
    *   Then check `Wayback Machine` availability.
3.  Once a valid version is obtained, proceed to parse and archive.
4.  Log every fallback action with metadata, including:
    *   `fallback_source`: `direct` | `12ft` | `archive.today` | `wayback`
    *   `successful`: `true`/`false`
    *   `timestamp`, etc.

---

### ✅ Implementation Sub-Tasks

*   Structure directory layout for `raw`/`collateral`/`parsed`.
*   Write the `is_truncated()` helper (e.g., check word count or compare `<title>` and text length).
*   Create logging for fallback attempts.
*   Wire fallback chain into `article_fetcher` flow.
*   Add tests simulating paywalled URLs and ensuring correct fallback.