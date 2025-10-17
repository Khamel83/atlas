# Third-Party Projects, Libraries & Resources for Atlas

Below is a low-level inventory of every external dependency that Atlas may pull in.
For each entry you’ll find:

* **Name & purpose**
* **Repository URL**
* **License**
* **Key considerations / notes**

> This table was provided by the project owner on *2025-07-11* and is copied here verbatim to keep the information in-repo for easy reference.

---

* **karakeep**
  *Purpose*: Self-hosted Instapaper-style read-it-later service you originally referenced.
  *Repo*: <https://github.com/karakeep-app/karakeep>
  *License*: AGPL-3.0 (strong copyleft)
  *Notes*: All code must remain open if redistributed.

* **Monolith**
  *Purpose*: CLI tool to convert web pages into single HTML files (useful for raw HTML archiving).
  *Repo*: <https://github.com/Y2Z/monolith>
  *License*: CC0-1.0 (“public domain”)
  *Notes*: No attribution required.

* **youtube-dl**
  *Purpose*: Download videos (and metadata) from YouTube and hundreds of other sites.
  *Repo*: <https://github.com/ytdl-org/youtube-dl>
  *License*: Unlicense / Public Domain
  *Notes*: Can grab video blobs if you choose.

* **whisper.cpp**
  *Purpose*: Local transcription via OpenAI’s Whisper model in C++ (suitable for RPi).
  *Repo*: <https://github.com/ggerganov/whisper.cpp>
  *License*: MIT
  *Notes*: Very low-resource; ideal for on-device transcription.

* **MeiliSearch**
  *Purpose*: Lightweight, typo-tolerant search engine for indexing everything you ingest.
  *Repo*: <https://github.com/meilisearch/MeiliSearch>
  *License*: MIT
  *Notes*: Use for the future “Atlas Ask” search index.

* **feedparser**
  *Purpose*: Parse RSS/Atom feeds (for podcast OPML ingestion).
  *Repo*: <https://github.com/kurtmckee/feedparser>
  *License*: BSD-2-Clause
  *Notes*: Battle-tested and pure Python.

* **BeautifulSoup4**
  *Purpose*: HTML parsing/cleanup (used alongside readability).
  *Repo*: <https://www.crummy.com/software/BeautifulSoup/> (PyPI: `beautifulsoup4`)
  *License*: MIT

* **readability-lxml**
  *Purpose*: Extract the main article text from HTML.
  *Repo*: <https://github.com/buriy/python-readability>
  *License*: MIT
  *Notes*: Removes boilerplate (ads, nav) automatically.

* **youtube-transcript-api**
  *Purpose*: Pull YouTube transcripts without a headless browser.
  *Repo*: <https://github.com/jdepoix/youtube-transcript-api>
  *License*: MIT

* **python-dotenv**
  *Purpose*: Load `.env` config into the Python process.
  *Repo*: <https://github.com/theskumar/python-dotenv>
  *License*: BSD-3-Clause
  *Notes*: Follows 12-factor app style.

* **requests**
  *Purpose*: HTTP client for fetching pages, feeds, blobs.
  *Repo*: <https://github.com/psf/requests>
  *License*: Apache-2.0
  *Notes*: “HTTP for Humans”.

---

The above list is now part of the repo so Cursor (and future contributors) can reference licensing details and integration pointers when scaffolding features, pinning versions, or preparing Docker/CI configs.