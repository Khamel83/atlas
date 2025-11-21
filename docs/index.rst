Atlas Documentation
===================

**Atlas** is a comprehensive local-first content ingestion platform that processes articles, podcasts, YouTube videos, and documents with advanced recovery strategies and continuous background operation.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting-started/index
   api-reference/index
   user-guide/index
   developer-guide/index
   testing/index

Quick Start
-----------

Atlas provides a unified system for content ingestion and processing:

.. code-block:: bash

   # Start Atlas background service
   ./start_work.sh

   # Process content from URLs
   python run.py --articles inputs/articles.txt

   # Check system status
   python atlas_status.py

Key Features
------------

✅ **Core Content Processing**
   - Article ingestion with 6-strategy fallback system
   - YouTube transcript extraction and metadata processing
   - Podcast system with 190 registered shows
   - Background service with auto-restart and monitoring

✅ **Advanced Recovery**
   - Enhanced Wayback Machine with multi-timeframe attempts
   - Paywall authentication for premium content
   - Skyvern AI-powered content extraction
   - Comprehensive retry mechanisms

✅ **Metadata Intelligence**
   - YouTube history analysis and processing
   - GitHub repository detection from content
   - Email integration with full IMAP support
   - Comprehensive metadata preservation

✅ **Search and Analytics**
   - Full-text search with ranking
   - Content processing statistics
   - Basic dashboard structure
   - Performance monitoring

Architecture Overview
---------------------

.. code-block:: text

   Atlas System Architecture:
   
   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
   │  Content Input  │────│   Processors    │────│     Output      │
   │                 │    │                 │    │                 │
   │ • Articles      │    │ • Ingestors     │    │ • Markdown      │
   │ • Podcasts      │    │ • Metadata Mgr  │    │ • JSON          │
   │ • YouTube       │    │ • Deduplication │    │ • Search Index  │
   │ • Documents     │    │ • Classification│    │ • Analytics     │
   └─────────────────┘    └─────────────────┘    └─────────────────┘
                                   │
                          ┌─────────────────┐
                          │ Background Svc  │
                          │ • Auto-restart  │
                          │ • Health checks │
                          │ • Retry queues  │
                          └─────────────────┘

Installation
------------

1. Clone the repository and install dependencies:

   .. code-block:: bash

      git clone https://github.com/atlas/atlas.git
      cd atlas
      pip install -r requirements.txt

2. Configure environment variables:

   .. code-block:: bash

      cp config/.env.template config/.env
      # Edit .env with your API keys and settings

3. Initialize the system:

   .. code-block:: bash

      python -c "from helpers.config import load_config; print('✅ Configuration loaded')"

API Reference
-------------

The Atlas API is organized into several key modules:

.. autosummary::
   :toctree: api-reference/
   :template: module.rst

   helpers.article_ingestor
   helpers.podcast_ingestor
   helpers.youtube_ingestor
   helpers.metadata_manager
   helpers.search_engine
   helpers.utils
   process.evaluate
   ask.insights.pattern_detector

Implementation Status
--------------------

Current implementation status by feature block:

.. list-table::
   :header-rows: 1
   :widths: 15 25 15 45

   * - Block
     - Feature
     - Status
     - Notes
   * - 1-3
     - Core Platform
     - ✅ Complete
     - 3,495+ articles processed
   * - 8
     - Analytics Dashboard
     - 🔧 Basic
     - Structure exists, needs data integration
   * - 9
     - Enhanced Search
     - 🔧 Basic
     - Full-text search working, needs ranking
   * - 10
     - Content Processing
     - 🔧 Basic
     - Summarizer and classifier implemented
   * - 15
     - Metadata Discovery
     - ✅ Complete
     - YouTube history, GitHub detection
   * - 16
     - Email Integration
     - ✅ Complete
     - Full IMAP pipeline with authentication

Contributing
------------

See the :doc:`developer-guide/index` for information on:

- Setting up development environment
- Code standards and documentation
- Testing requirements
- Contribution process

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`