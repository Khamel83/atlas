#!/usr/bin/env python3
"""
Task 1.1: Diagnose Document Content Extraction Failure

This script diagnoses the root cause of 18,575 document processing failures
by analyzing the document processing pipeline and identifying failure points.
"""

import logging
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.config import load_config
from helpers.document_processor import (
    AtlasDocumentProcessor,
    is_document_processing_available
)
from helpers.document_ingestor import DocumentIngestor

# Configure logging
os.makedirs('logs', exist_ok=True)
log_file = f"logs/document_extraction_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required dependencies are available."""
    logger.info("=== CHECKING DEPENDENCIES ===")

    # Check unstructured library
    try:
        from unstructured.partition.auto import partition
        logger.info("✅ Unstructured library is available")
        return True
    except ImportError as e:
        logger.error(f"❌ Unstructured library not available: {e}")
        return False

def find_sample_documents() -> List[str]:
    """Find sample documents to test processing."""
    logger.info("=== FINDING SAMPLE DOCUMENTS ===")

    sample_docs = []
    search_paths = [
        "inputs",
        "inputs/PROCESSED/Docs",
        "output",
        "."
    ]

    supported_extensions = ['.html', '.pdf', '.txt', '.md', '.docx', '.doc']

    for search_path in search_paths:
        if os.path.exists(search_path):
            logger.info(f"Searching in: {search_path}")

            for ext in supported_extensions:
                pattern = f"**/*{ext}"
                found_files = list(Path(search_path).glob(pattern))

                for file_path in found_files[:3]:  # Limit to 3 per extension
                    if file_path.is_file() and file_path.stat().st_size > 0:
                        sample_docs.append(str(file_path))
                        logger.info(f"Found sample: {file_path} ({file_path.stat().st_size} bytes)")

    logger.info(f"Found {len(sample_docs)} sample documents")
    return sample_docs

def test_document_processor_directly(sample_files: List[str]) -> Dict[str, Any]:
    """Test AtlasDocumentProcessor directly on sample files."""
    logger.info("=== TESTING DOCUMENT PROCESSOR DIRECTLY ===")

    results = {
        "tested_files": 0,
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    try:
        config = load_config()
        processor = AtlasDocumentProcessor(config)

        for file_path in sample_files[:5]:  # Test first 5 files
            logger.info(f"Testing direct processing of: {file_path}")
            results["tested_files"] += 1

            try:
                # Test if file format is supported
                if not processor.is_supported_format(file_path):
                    logger.warning(f"File format not supported: {file_path}")
                    results["errors"].append({
                        "file": file_path,
                        "error": "Unsupported format",
                        "step": "format_check"
                    })
                    continue

                # Try to process the document
                result = processor.process_document(file_path)

                if result["processing_status"] == "completed":
                    logger.info(f"✅ Successfully processed: {file_path}")
                    logger.info(f"   Content length: {len(result['content'])}")
                    logger.info(f"   Elements: {len(result['structured_content'])}")
                    results["successful"] += 1
                else:
                    logger.error(f"❌ Processing failed: {file_path}")
                    logger.error(f"   Error: {result.get('error', 'Unknown')}")
                    results["failed"] += 1
                    results["errors"].append({
                        "file": file_path,
                        "error": result.get("error", "Unknown processing error"),
                        "step": "document_processing"
                    })

            except Exception as e:
                logger.error(f"❌ Exception processing {file_path}: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "file": file_path,
                    "error": str(e),
                    "step": "exception"
                })

    except Exception as e:
        logger.error(f"❌ Failed to initialize document processor: {e}")
        results["errors"].append({
            "error": f"Processor initialization failed: {e}",
            "step": "initialization"
        })

    return results

def test_document_ingestor(sample_files: List[str]) -> Dict[str, Any]:
    """Test DocumentIngestor on sample files."""
    logger.info("=== TESTING DOCUMENT INGESTOR ===")

    results = {
        "tested_files": 0,
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    try:
        config = load_config()
        ingestor = DocumentIngestor(config)

        for file_path in sample_files[:5]:  # Test first 5 files
            logger.info(f"Testing ingestor processing of: {file_path}")
            results["tested_files"] += 1

            try:
                # Check if source is supported
                if not ingestor.is_supported_source(file_path):
                    logger.warning(f"Source not supported by ingestor: {file_path}")
                    results["errors"].append({
                        "file": file_path,
                        "error": "Source not supported by ingestor",
                        "step": "source_check"
                    })
                    continue

                # Try to ingest the document
                result = ingestor.ingest_content(file_path)

                if result.success:
                    logger.info(f"✅ Successfully ingested: {file_path}")
                    logger.info(f"   Metadata: {result.metadata.uid if result.metadata else 'None'}")
                    results["successful"] += 1
                else:
                    logger.error(f"❌ Ingestion failed: {file_path}")
                    logger.error(f"   Error: {result.error}")
                    results["failed"] += 1
                    results["errors"].append({
                        "file": file_path,
                        "error": result.error or "Unknown ingestion error",
                        "step": "document_ingestion"
                    })

            except Exception as e:
                logger.error(f"❌ Exception during ingestion {file_path}: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "file": file_path,
                    "error": str(e),
                    "step": "ingestion_exception"
                })

    except Exception as e:
        logger.error(f"❌ Failed to initialize document ingestor: {e}")
        results["errors"].append({
            "error": f"Ingestor initialization failed: {e}",
            "step": "initialization"
        })

    return results

def analyze_existing_output():
    """Analyze existing output directory for processing patterns."""
    logger.info("=== ANALYZING EXISTING OUTPUT ===")

    analysis = {
        "total_files": 0,
        "with_content": 0,
        "empty_content": 0,
        "content_stats": {
            "min_length": float('inf'),
            "max_length": 0,
            "avg_length": 0
        }
    }

    output_dir = "output/documents"
    if not os.path.exists(output_dir):
        logger.warning(f"Output directory doesn't exist: {output_dir}")
        return analysis

    content_lengths = []

    for file_path in Path(output_dir).glob("*.md"):
        analysis["total_files"] += 1

        try:
            content = file_path.read_text(encoding='utf-8')
            content_length = len(content.strip())

            if content_length > 0:
                analysis["with_content"] += 1
                content_lengths.append(content_length)
            else:
                analysis["empty_content"] += 1

        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")

    if content_lengths:
        analysis["content_stats"] = {
            "min_length": min(content_lengths),
            "max_length": max(content_lengths),
            "avg_length": sum(content_lengths) // len(content_lengths)
        }

    logger.info(f"Output analysis: {analysis['total_files']} total files")
    logger.info(f"  - {analysis['with_content']} with content")
    logger.info(f"  - {analysis['empty_content']} with empty content")

    return analysis

def main():
    """Main diagnostic function."""
    logger.info("=== DOCUMENT PROCESSING DIAGNOSIS STARTED ===")

    diagnostic_results = {
        "timestamp": datetime.now().isoformat(),
        "log_file": log_file,
        "dependencies_check": None,
        "sample_files": [],
        "processor_test": None,
        "ingestor_test": None,
        "output_analysis": None,
        "root_cause": None,
        "recommendations": []
    }

    # Step 1: Check dependencies
    dependencies_ok = check_dependencies()
    diagnostic_results["dependencies_check"] = dependencies_ok

    if not dependencies_ok:
        diagnostic_results["root_cause"] = "Missing required dependencies (unstructured library)"
        diagnostic_results["recommendations"].append("Install unstructured library: pip install 'unstructured[all-docs]'")

    # Step 2: Find sample documents
    sample_files = find_sample_documents()
    diagnostic_results["sample_files"] = sample_files

    if not sample_files:
        diagnostic_results["recommendations"].append("No sample documents found for testing")

    # Step 3: Test document processor directly
    if dependencies_ok and sample_files:
        processor_results = test_document_processor_directly(sample_files)
        diagnostic_results["processor_test"] = processor_results

    # Step 4: Test document ingestor
    if dependencies_ok and sample_files:
        ingestor_results = test_document_ingestor(sample_files)
        diagnostic_results["ingestor_test"] = ingestor_results

    # Step 5: Analyze existing output
    output_analysis = analyze_existing_output()
    diagnostic_results["output_analysis"] = output_analysis

    # Determine root cause
    if not dependencies_ok:
        diagnostic_results["root_cause"] = "Missing unstructured library dependency"
    elif not sample_files:
        diagnostic_results["root_cause"] = "No documents available for processing"
    elif diagnostic_results.get("processor_test", {}).get("failed", 0) > 0:
        diagnostic_results["root_cause"] = "Document processor failures"
    elif diagnostic_results.get("ingestor_test", {}).get("failed", 0) > 0:
        diagnostic_results["root_cause"] = "Document ingestor failures"
    else:
        diagnostic_results["root_cause"] = "Unknown - further investigation needed"

    # Save results
    results_file = f"logs/diagnosis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(diagnostic_results, f, indent=2)

    logger.info("=== DIAGNOSIS COMPLETE ===")
    logger.info(f"Root cause: {diagnostic_results['root_cause']}")
    logger.info(f"Full results saved to: {results_file}")
    logger.info(f"Detailed logs saved to: {log_file}")

    return diagnostic_results

if __name__ == "__main__":
    main()