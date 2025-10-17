API Reference
=============

This section contains the complete API reference for Atlas modules, classes, and functions.

Core Modules
------------

Content Ingestors
~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: ingestors/
   :template: module.rst

   helpers.article_ingestor
   helpers.podcast_ingestor
   helpers.youtube_ingestor
   helpers.document_ingestor
   helpers.base_ingestor

Utility Modules
~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: utilities/
   :template: module.rst

   helpers.utils
   helpers.metadata_manager
   helpers.path_manager
   helpers.config
   helpers.dedupe
   helpers.enhanced_dedupe

Processing Modules
~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: processing/
   :template: module.rst

   process.evaluate
   helpers.search_engine
   helpers.content_classifier

Error Handling & Recovery
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: recovery/
   :template: module.rst

   helpers.error_handler
   helpers.retry_queue
   helpers.article_strategies

Email Integration
~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: email/
   :template: module.rst

   helpers.email_ingestor
   helpers.email_auth_manager
   helpers.email_to_html_converter

Cognitive Features
~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: cognitive/
   :template: module.rst

   ask.insights.pattern_detector
   ask.recall.recall_engine
   ask.temporal.temporal_engine

Podcast System
~~~~~~~~~~~~~~

.. autosummary::
   :toctree: podcast/
   :template: module.rst

   helpers.podcast_transcript_ingestor
   helpers.atp_transcript_scraper
   helpers.network_transcript_scrapers
   modules.podcasts.cli

Classes and Functions
---------------------

Base Classes
~~~~~~~~~~~~

.. autoclass:: helpers.base_ingestor.BaseIngestor
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: helpers.base_ingestor.IngestorResult
   :members:
   :undoc-members:

Content Types and Metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: helpers.metadata_manager.ContentType
   :members:
   :undoc-members:

.. autoclass:: helpers.metadata_manager.ContentMetadata
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: helpers.metadata_manager.ProcessingStatus
   :members:
   :undoc-members:

Error Handling
~~~~~~~~~~~~~~

.. autoclass:: helpers.error_handler.ErrorCategory
   :members:
   :undoc-members:

.. autoclass:: helpers.error_handler.ErrorSeverity
   :members:
   :undoc-members:

.. autoclass:: helpers.error_handler.ErrorContext
   :members:
   :undoc-members:

Constants and Configuration
---------------------------

.. autodata:: helpers.config.CONFIG_DIR
   :annotation: str

.. autodata:: helpers.config.DOTENV_PATH
   :annotation: str

.. autodata:: helpers.config.CATEGORIES_PATH
   :annotation: str

.. autofunction:: helpers.config.load_config

.. autofunction:: helpers.config.load_categories

Common Patterns
---------------

Ingestor Usage Pattern
~~~~~~~~~~~~~~~~~~~~~~

All content ingestors follow a common pattern:

.. code-block:: python

   from helpers.article_ingestor import ArticleIngestor
   from helpers.config import load_config

   # Load configuration
   config = load_config()

   # Initialize ingestor
   ingestor = ArticleIngestor(config)

   # Process content
   urls = ["https://example.com/article1", "https://example.com/article2"]
   result = ingestor.process_urls(urls)

   print(f"Processed {result['success_count']} articles successfully")

Error Handling Pattern
~~~~~~~~~~~~~~~~~~~~~~

Atlas uses consistent error handling across all modules:

.. code-block:: python

   from helpers.error_handler import create_error_handler, ErrorSeverity

   # Create error handler
   error_handler = create_error_handler(config)

   try:
       # Your processing code here
       process_content()
   except Exception as e:
       error_handler.handle_error(
           error=e,
           context="Content processing failed",
           severity=ErrorSeverity.HIGH,
           metadata={"url": url, "attempt": attempt_count}
       )

Metadata Management Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Consistent metadata handling across all content types:

.. code-block:: python

   from helpers.metadata_manager import create_metadata_manager, ContentType

   # Create metadata manager
   metadata_manager = create_metadata_manager(config)

   # Create metadata for processed content
   metadata = metadata_manager.create_metadata(
       content_type=ContentType.ARTICLE,
       source_url="https://example.com/article",
       title="Article Title",
       additional_data={"author": "John Doe", "publish_date": "2024-01-01"}
   )

   # Save metadata
   metadata_manager.save_metadata(metadata)