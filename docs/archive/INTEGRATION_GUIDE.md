# Atlas Integration Guide: Advanced Features from Similar Projects

This guide provides detailed implementation instructions for integrating advanced features from leading knowledge management and content processing projects into Atlas.

## Overview

Based on comprehensive research of projects like Unstructured, HPI, ArchiveBox, Whisper, Meilisearch, FAISS, and others, this guide outlines how to enhance Atlas with cutting-edge capabilities while maintaining its local-first, privacy-focused philosophy.

## Quick Start Integration Checklist

### Phase 1: Core Enhancements (Immediate Impact)
- [ ] **Unstructured Integration** - Multi-format document processing
- [ ] **Enhanced Deduplication** - Jaccard similarity scoring
- [ ] **Meilisearch Integration** - Full-text search capabilities
- [ ] **Enhanced Retry Logic** - Exponential backoff and circuit breakers

### Phase 2: Advanced Features (High Value)
- [ ] **Whisper Integration** - Local audio transcription
- [ ] **FAISS Vector Search** - Semantic similarity and recommendations
- [ ] **ArchiveBox Integration** - Multi-format content preservation
- [ ] **APScheduler Integration** - Automated periodic ingestion

### Phase 3: Intelligence & Insights (Future)
- [ ] **Entity Graph Building** - Knowledge graph construction
- [ ] **HPI Integration** - Personal data import expansion
- [ ] **ActivityWatch Integration** - Personal activity insights
- [ ] **Plugin System** - Extensible architecture

## Detailed Implementation Instructions

### 1. Document Processing Expansion (Unstructured)

**Objective**: Expand Atlas beyond web content to support PDFs, Word documents, and 20+ file formats.

**Implementation Location**: `ingest_pipeline/document_extraction.py`

```python
# LOCATION: ingest_pipeline/document_extraction.py
# DESCRIPTION: Extract clean text and metadata from documents using Unstructured

from unstructured.partition.auto import partition
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def extract_text_with_unstructured(filepath: str) -> dict:
    """
    Extracts text and metadata from a document using Unstructured.
    Supports PDF, Word, HTML, and 20+ document types.

    Args:
        filepath: Path to the document file

    Returns:
        dict: Contains 'text', 'metadata', and optionally 'error'
    """
    try:
        elements = partition(filename=filepath)

        # Extract text from elements
        text_content = []
        for element in elements:
            if element.text:
                text_content.append(element.text)

        text = "\n".join(text_content)

        # Build metadata
        metadata = {
            "element_count": len(elements),
            "source_file": Path(filepath).name,
            "file_size": Path(filepath).stat().st_size,
            "extraction_method": "unstructured",
            "element_types": list(set(type(el).__name__ for el in elements))
        }

        logger.info(f"Successfully extracted {len(text)} characters from {filepath}")
        return {"text": text, "metadata": metadata}

    except Exception as e:
        logger.error(f"Failed to extract text from {filepath}: {e}")
        return {
            "error": str(e),
            "metadata": {
                "source_file": Path(filepath).name,
                "extraction_method": "unstructured",
                "failed": True
            }
        }
```

**Dependencies to Add**:
```bash
pip install unstructured python-docx pdfminer.six
```

**Integration Steps**:
1. Create `ingest_pipeline/document_extraction.py` with the above code
2. Update `helpers/article_fetcher.py` to detect file uploads and route to document extraction
3. Modify `ingest/link_dispatcher.py` to handle file:// URLs
4. Add document processing to the main ingestion workflow

### 2. Enhanced Deduplication System

**Objective**: Implement multi-level duplicate detection using Jaccard similarity scoring.

**Implementation Location**: `utils/deduplication.py`

```python
# LOCATION: utils/deduplication.py
# DESCRIPTION: Detect near-duplicate content using advanced similarity scoring

import hashlib
import re
from typing import List, Tuple, Set
from dataclasses import dataclass

@dataclass
class DuplicateScore:
    """Container for duplicate detection results."""
    url_similarity: float
    content_similarity: float
    title_similarity: float
    overall_score: float
    is_duplicate: bool

def normalize_url(url: str) -> str:
    """Normalize URL by removing tracking parameters and fragments."""
    # Remove common tracking parameters
    tracking_params = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
        'fbclid', 'gclid', 'ref', 'source', 'campaign'
    ]

    # Basic URL normalization
    normalized = url.lower().strip()

    # Remove tracking parameters (simplified)
    for param in tracking_params:
        normalized = re.sub(f'[?&]{param}=[^&]*', '', normalized)

    # Remove fragments
    normalized = normalized.split('#')[0]

    # Remove trailing slash and query separators
    normalized = normalized.rstrip('/?&')

    return normalized

def jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two text strings."""
    if not text1 or not text2:
        return 0.0

    # Convert to word sets
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    # Calculate Jaccard similarity
    intersection = words1 & words2
    union = words1 | words2

    if not union:
        return 0.0

    return len(intersection) / len(union)

def content_hash(text: str) -> str:
    """Generate a hash for content comparison."""
    # Normalize text for hashing
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.md5(normalized.encode()).hexdigest()

def detect_duplicate(doc_a: dict, doc_b: dict,
                    url_threshold: float = 0.9,
                    content_threshold: float = 0.8,
                    title_threshold: float = 0.7) -> DuplicateScore:
    """
    Detect if two documents are duplicates using multiple similarity metrics.

    Args:
        doc_a, doc_b: Documents with 'url', 'title', and 'content' keys
        url_threshold: Threshold for URL similarity
        content_threshold: Threshold for content similarity
        title_threshold: Threshold for title similarity

    Returns:
        DuplicateScore with similarity metrics and duplicate determination
    """
    # URL similarity
    url_sim = jaccard_similarity(
        normalize_url(doc_a.get('url', '')),
        normalize_url(doc_b.get('url', ''))
    )

    # Content similarity
    content_sim = jaccard_similarity(
        doc_a.get('content', ''),
        doc_b.get('content', '')
    )

    # Title similarity
    title_sim = jaccard_similarity(
        doc_a.get('title', ''),
        doc_b.get('title', '')
    )

    # Calculate overall score (weighted average)
    overall_score = (url_sim * 0.3 + content_sim * 0.5 + title_sim * 0.2)

    # Determine if duplicate
    is_duplicate = (
        url_sim >= url_threshold or
        content_sim >= content_threshold or
        title_sim >= title_threshold or
        overall_score >= 0.7
    )

    return DuplicateScore(
        url_similarity=url_sim,
        content_similarity=content_sim,
        title_similarity=title_sim,
        overall_score=overall_score,
        is_duplicate=is_duplicate
    )

def find_duplicates_in_batch(documents: List[dict]) -> List[Tuple[int, int, DuplicateScore]]:
    """
    Find all duplicate pairs in a batch of documents.

    Args:
        documents: List of documents with 'url', 'title', and 'content'

    Returns:
        List of tuples (index_a, index_b, duplicate_score) for duplicate pairs
    """
    duplicates = []

    for i in range(len(documents)):
        for j in range(i + 1, len(documents)):
            score = detect_duplicate(documents[i], documents[j])
            if score.is_duplicate:
                duplicates.append((i, j, score))

    return duplicates
```

**Integration Steps**:
1. Create `utils/deduplication.py` with the above code
2. Update `helpers/article_fetcher.py` to check for duplicates before processing
3. Modify metadata storage to include duplicate detection results
4. Add duplicate management to the processing queue

### 3. Full-Text Search (Meilisearch)

**Objective**: Add fast, typo-tolerant full-text search across all content.

**Implementation Location**: `indexing/fulltext.py`

```python
# LOCATION: indexing/fulltext.py
# DESCRIPTION: Index content in Meilisearch for local full-text search

import os
import json
import logging
from typing import List, Dict, Any, Optional
from meilisearch import Client
from meilisearch.errors import MeilisearchError

logger = logging.getLogger(__name__)

class AtlasSearchIndex:
    """Atlas-specific Meilisearch integration."""

    def __init__(self, url: str = "http://127.0.0.1:7700",
                 master_key: Optional[str] = None,
                 index_name: str = "atlas_documents"):
        """
        Initialize Meilisearch client.

        Args:
            url: Meilisearch server URL
            master_key: Master key for authentication
            index_name: Name of the search index
        """
        self.client = Client(url, master_key)
        self.index_name = index_name
        self.index = self.client.index(index_name)
        self._setup_index()

    def _setup_index(self):
        """Configure the search index with appropriate settings."""
        try:
            # Create index if it doesn't exist
            self.client.create_index(self.index_name, {'primaryKey': 'id'})
        except MeilisearchError as e:
            if "already exists" not in str(e):
                logger.error(f"Failed to create index: {e}")
                raise

        # Configure searchable attributes
        self.index.update_searchable_attributes([
            'title',
            'content',
            'summary',
            'tags',
            'entities'
        ])

        # Configure filterable attributes
        self.index.update_filterable_attributes([
            'source',
            'category',
            'date',
            'content_type',
            'tags'
        ])

        # Configure sortable attributes
        self.index.update_sortable_attributes([
            'date',
            'title'
        ])

        logger.info(f"Search index '{self.index_name}' configured successfully")

    def index_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Index a single document with text and metadata.

        Args:
            doc_id: Unique document identifier
            content: Document text content
            metadata: Document metadata (title, source, etc.)

        Returns:
            bool: True if indexing succeeded
        """
        try:
            # Prepare document for indexing
            document = {
                "id": doc_id,
                "content": content,
                "title": metadata.get("title", ""),
                "source": metadata.get("source", ""),
                "date": metadata.get("date", ""),
                "category": metadata.get("category", ""),
                "content_type": metadata.get("content_type", ""),
                "tags": metadata.get("tags", []),
                "entities": metadata.get("entities", []),
                "summary": metadata.get("summary", ""),
                "word_count": len(content.split()) if content else 0
            }

            # Add to index
            self.index.add_documents([document])
            logger.info(f"Successfully indexed document {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to index document {doc_id}: {e}")
            return False

    def search(self, query: str, limit: int = 20,
               filters: Optional[str] = None,
               sort: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Search the index for documents matching the query.

        Args:
            query: Search query string
            limit: Maximum number of results
            filters: Filter expression (e.g., "category = 'tech'")
            sort: Sort criteria (e.g., ['date:desc'])

        Returns:
            dict: Search results with hits and metadata
        """
        try:
            search_params = {
                'limit': limit,
                'attributesToHighlight': ['title', 'content', 'summary'],
                'attributesToCrop': ['content'],
                'cropLength': 200
            }

            if filters:
                search_params['filter'] = filters

            if sort:
                search_params['sort'] = sort

            results = self.index.search(query, search_params)

            logger.info(f"Search for '{query}' returned {len(results['hits'])} results")
            return results

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return {"hits": [], "query": query, "error": str(e)}

    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing document in the index.

        Args:
            doc_id: Document identifier
            updates: Fields to update

        Returns:
            bool: True if update succeeded
        """
        try:
            updates['id'] = doc_id
            self.index.update_documents([updates])
            logger.info(f"Successfully updated document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the index.

        Args:
            doc_id: Document identifier

        Returns:
            bool: True if deletion succeeded
        """
        try:
            self.index.delete_document(doc_id)
            logger.info(f"Successfully deleted document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        try:
            stats = self.index.get_stats()
            return {
                "total_documents": stats.get("numberOfDocuments", 0),
                "index_size": stats.get("databaseSize", 0),
                "last_update": stats.get("lastUpdate", ""),
                "is_indexing": stats.get("isIndexing", False)
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}

# Convenience functions for integration
def initialize_search_index(config: Dict[str, Any]) -> AtlasSearchIndex:
    """Initialize search index with configuration."""
    return AtlasSearchIndex(
        url=config.get("MEILISEARCH_URL", "http://127.0.0.1:7700"),
        master_key=config.get("MEILISEARCH_KEY"),
        index_name=config.get("SEARCH_INDEX_NAME", "atlas_documents")
    )

def index_processed_content(search_index: AtlasSearchIndex,
                          content_path: str, metadata_path: str) -> bool:
    """
    Index processed content from Atlas output files.

    Args:
        search_index: Configured search index
        content_path: Path to content file (.md)
        metadata_path: Path to metadata file (.json)

    Returns:
        bool: True if indexing succeeded
    """
    try:
        # Read content
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Read metadata
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # Generate document ID from file path
        doc_id = os.path.basename(content_path).replace('.md', '')

        return search_index.index_document(doc_id, content, metadata)

    except Exception as e:
        logger.error(f"Failed to index content from {content_path}: {e}")
        return False
```

**Dependencies to Add**:
```bash
pip install meilisearch-python
```

**System Setup**:
```bash
# Install Meilisearch
brew install meilisearch

# Start Meilisearch server
meilisearch --master-key=your_master_key_here
```

**Integration Steps**:
1. Create `indexing/fulltext.py` with the above code
2. Add search indexing to the content processing pipeline
3. Update `process/evaluate.py` to index processed content
4. Create search CLI commands or web interface

### 4. Local Audio Transcription (Whisper)

**Objective**: Replace external transcription APIs with local Whisper processing.

**Implementation Location**: `ingest_pipeline/transcription.py`

```python
# LOCATION: ingest_pipeline/transcription.py
# DESCRIPTION: Transcribe audio using OpenAI Whisper locally

import os
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
import whisper
from whisper.utils import get_writer

logger = logging.getLogger(__name__)

class WhisperTranscriber:
    """Local audio transcription using OpenAI Whisper."""

    def __init__(self, model_size: str = "base", device: str = "auto"):
        """
        Initialize Whisper transcriber.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to use (auto, cpu, cuda)
        """
        self.model_size = model_size
        self.device = device
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the Whisper model."""
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = whisper.load_model(self.model_size, device=self.device)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe_audio(self, filepath: str,
                        language: Optional[str] = None,
                        task: str = "transcribe") -> Dict[str, Any]:
        """
        Transcribe audio file using Whisper.

        Args:
            filepath: Path to audio file
            language: Language code (e.g., 'en', 'es') or None for auto-detection
            task: 'transcribe' or 'translate'

        Returns:
            dict: Transcription results with text, segments, and metadata
        """
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Audio file not found: {filepath}")

            logger.info(f"Transcribing audio file: {filepath}")

            # Transcribe audio
            options = {
                "task": task,
                "fp16": False,  # Use fp32 for better compatibility
            }

            if language:
                options["language"] = language

            result = self.model.transcribe(filepath, **options)

            # Process results
            transcription_data = {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": self._process_segments(result.get("segments", [])),
                "metadata": {
                    "model_size": self.model_size,
                    "file_path": filepath,
                    "file_size": os.path.getsize(filepath),
                    "duration": self._get_audio_duration(result),
                    "task": task,
                    "word_count": len(result["text"].split())
                }
            }

            logger.info(f"Transcription completed: {len(transcription_data['text'])} characters")
            return transcription_data

        except Exception as e:
            logger.error(f"Transcription failed for {filepath}: {e}")
            return {
                "error": str(e),
                "metadata": {
                    "file_path": filepath,
                    "failed": True,
                    "model_size": self.model_size
                }
            }

    def _process_segments(self, segments: List[Dict]) -> List[Dict]:
        """Process and clean transcription segments."""
        processed_segments = []

        for segment in segments:
            processed_segment = {
                "id": segment.get("id", 0),
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
                "text": segment.get("text", "").strip(),
                "confidence": segment.get("avg_logprob", 0.0)
            }

            # Add word-level timestamps if available
            if "words" in segment:
                processed_segment["words"] = [
                    {
                        "word": word.get("word", ""),
                        "start": word.get("start", 0.0),
                        "end": word.get("end", 0.0),
                        "confidence": word.get("probability", 0.0)
                    }
                    for word in segment["words"]
                ]

            processed_segments.append(processed_segment)

        return processed_segments

    def _get_audio_duration(self, result: Dict) -> float:
        """Extract audio duration from transcription result."""
        segments = result.get("segments", [])
        if segments:
            return segments[-1].get("end", 0.0)
        return 0.0

    def transcribe_with_timestamps(self, filepath: str,
                                 output_format: str = "srt") -> Dict[str, Any]:
        """
        Transcribe audio with timestamp formatting.

        Args:
            filepath: Path to audio file
            output_format: Output format (srt, vtt, txt, json)

        Returns:
            dict: Transcription with formatted timestamps
        """
        try:
            # Get basic transcription
            result = self.transcribe_audio(filepath)

            if "error" in result:
                return result

            # Create temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write formatted output
                writer = get_writer(output_format, temp_dir)

                # Reconstruct whisper result format for writer
                whisper_result = {
                    "text": result["text"],
                    "segments": result["segments"],
                    "language": result["language"]
                }

                output_file = os.path.join(temp_dir, f"transcript.{output_format}")
                writer(whisper_result, output_file)

                # Read formatted output
                with open(output_file, 'r', encoding='utf-8') as f:
                    formatted_content = f.read()

                result["formatted_transcript"] = formatted_content
                result["format"] = output_format

                return result

        except Exception as e:
            logger.error(f"Timestamp transcription failed for {filepath}: {e}")
            return {"error": str(e), "metadata": {"file_path": filepath, "failed": True}}

# Convenience functions for integration
def create_transcriber(config: Dict[str, Any]) -> WhisperTranscriber:
    """Create transcriber with configuration."""
    return WhisperTranscriber(
        model_size=config.get("WHISPER_MODEL_SIZE", "base"),
        device=config.get("WHISPER_DEVICE", "auto")
    )

def transcribe_podcast_episode(audio_path: str,
                             output_dir: str,
                             transcriber: WhisperTranscriber) -> Dict[str, Any]:
    """
    Transcribe a podcast episode and save results.

    Args:
        audio_path: Path to audio file
        output_dir: Directory to save transcription
        transcriber: Configured transcriber

    Returns:
        dict: Transcription results and file paths
    """
    try:
        # Transcribe audio
        result = transcriber.transcribe_audio(audio_path)

        if "error" in result:
            return result

        # Generate output paths
        base_name = Path(audio_path).stem
        transcript_path = os.path.join(output_dir, f"{base_name}_transcript.txt")
        metadata_path = os.path.join(output_dir, f"{base_name}_transcript_metadata.json")

        # Save transcript
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(result["text"])

        # Save metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(result["metadata"], f, indent=2)

        result["transcript_path"] = transcript_path
        result["metadata_path"] = metadata_path

        logger.info(f"Transcription saved to {transcript_path}")
        return result

    except Exception as e:
        logger.error(f"Failed to transcribe podcast episode {audio_path}: {e}")
        return {"error": str(e), "audio_path": audio_path}
```

**Dependencies to Add**:
```bash
pip install openai-whisper ffmpeg-python
```

**System Setup**:
```bash
# Install FFmpeg
brew install ffmpeg
```

**Integration Steps**:
1. Create `ingest_pipeline/transcription.py` with the above code
2. Update `helpers/podcast_ingestor.py` to use local transcription
3. Update `helpers/youtube_ingestor.py` to use Whisper as fallback
4. Add transcription quality assessment and model selection

## Configuration Updates

### Environment Variables
Add these to your `.env` file:

```bash
# Meilisearch Configuration
MEILISEARCH_URL=http://127.0.0.1:7700
MEILISEARCH_KEY=your_master_key_here
SEARCH_INDEX_NAME=atlas_documents

# Whisper Configuration
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=auto

# Reddit Integration (for HPI)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password

# ActivityWatch Integration
ACTIVITYWATCH_URL=http://localhost:5600
```

### Requirements Updates
Add these to `requirements.txt`:

```bash
# Document Processing
unstructured
python-docx
pdfminer.six

# Audio Processing
openai-whisper
ffmpeg-python

# Search & Discovery
meilisearch-python
faiss-cpu
numpy

# Personal Data Import
praw

# Automation
apscheduler

# NLP & Entity Processing
spacy
en_core_web_sm

# Enhanced Reliability
tenacity
```

## Testing Integration

### Unit Tests
Create test files for each new module:

```bash
tests/unit/test_document_extraction.py
tests/unit/test_deduplication.py
tests/unit/test_fulltext_search.py
tests/unit/test_whisper_transcription.py
```

### Integration Tests
Create integration tests that verify the entire pipeline:

```bash
tests/integration/test_document_processing_pipeline.py
tests/integration/test_search_indexing.py
tests/integration/test_transcription_pipeline.py
```

## Performance Considerations

### Whisper Model Selection
- **tiny**: Fastest, least accurate (~39 MB)
- **base**: Good balance (~74 MB) - **Recommended for most users**
- **small**: Better accuracy (~244 MB)
- **medium**: High accuracy (~769 MB)
- **large**: Best accuracy (~1550 MB)

### Meilisearch Optimization
- Configure appropriate RAM allocation
- Use SSD storage for index files
- Monitor index size and performance
- Consider distributed setup for large datasets

### Deduplication Performance
- Implement batch processing for large document sets
- Use content hashing for exact duplicates
- Consider approximate algorithms for very large datasets

## Monitoring and Maintenance

### Health Checks
Add health checks for new services:

```python
def check_meilisearch_health():
    """Check if Meilisearch is running and accessible."""

def check_whisper_models():
    """Verify Whisper models are available."""

def check_integration_dependencies():
    """Verify all integration dependencies are installed."""
```

### Logging
Ensure comprehensive logging for all new integrations:

```python
import logging

# Configure logging for integrations
logging.getLogger('meilisearch').setLevel(logging.INFO)
logging.getLogger('whisper').setLevel(logging.INFO)
logging.getLogger('unstructured').setLevel(logging.INFO)
```

## Troubleshooting Common Issues

### Meilisearch Issues
- **Connection refused**: Check if Meilisearch server is running
- **Index errors**: Verify master key and permissions
- **Performance issues**: Check RAM allocation and index size

### Whisper Issues
- **CUDA errors**: Set device to "cpu" if GPU issues occur
- **Memory errors**: Use smaller model size
- **Audio format issues**: Ensure FFmpeg is installed correctly

### Unstructured Issues
- **PDF parsing errors**: Check if file is corrupted or password-protected
- **Memory issues**: Process large documents in chunks
- **Dependency conflicts**: Ensure all required packages are installed

## Future Enhancements

### Planned Integrations
1. **FAISS Vector Search** - Semantic similarity and recommendations
2. **Entity Graph Building** - Knowledge graph construction
3. **ActivityWatch Integration** - Personal activity insights
4. **Plugin System** - Extensible architecture

### Community Contributions
- Plugin development framework
- Custom extraction rules
- Language-specific processing
- Performance optimizations

---

This integration guide provides a comprehensive roadmap for enhancing Atlas with cutting-edge capabilities while maintaining its core principles of local-first processing and privacy preservation.