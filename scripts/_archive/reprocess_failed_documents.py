#!/usr/bin/env python3
"""
Task 1.3: Re-process Failed Documents

This script identifies and re-processes the documents that previously failed content extraction,
using the fixed document processing pipeline from Tasks 1.1 and 1.2.

Based on our diagnosis, the root cause was missing config parameters in summarize_content() calls.
This has been fixed in helpers/document_ingestor.py and helpers/skyvern_enhanced_ingestor.py.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from helpers.document_ingestor import DocumentIngestor
    from helpers.simple_database import SimpleDatabase
    from helpers.config import load_config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the Atlas root directory")
    sys.exit(1)


class FailedDocumentReprocessor:
    """Reprocesses documents that previously failed content extraction."""

    def __init__(self):
        self.config = load_config()
        self.db = SimpleDatabase()
        self.document_ingestor = DocumentIngestor(self.config)
        self.failed_documents = []
        self.processed_count = 0
        self.success_count = 0
        self.failure_count = 0

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup comprehensive logging for reprocessing."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"reprocess_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info("Starting failed document reprocessing")
        self.logger.info(f"Log file: {log_file}")

    def identify_failed_documents(self) -> List[Dict[str, Any]]:
        """Identify documents that have no content or failed processing."""
        self.logger.info("🔍 Identifying failed documents...")

        # Check database for documents without content
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # First check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        self.logger.info(f"Available tables: {tables}")

        # Use 'content' table if 'documents' doesn't exist
        table_name = 'documents' if 'documents' in tables else 'content'

        # Query for documents with empty or null content
        if table_name == 'content':
            query = """
            SELECT id, title, url, content, metadata
            FROM content
            WHERE content IS NULL
               OR content = ''
               OR LENGTH(TRIM(content)) = 0
               OR content = 'Failed to extract content'
            """
        else:
            query = """
            SELECT uid, title, source_url, file_path, metadata
            FROM documents
            WHERE content IS NULL
               OR content = ''
               OR LENGTH(TRIM(content)) = 0
               OR content = 'Failed to extract content'
            """

        cursor.execute(query)
        failed_docs = cursor.fetchall()

        failed_documents = []
        for doc in failed_docs:
            if table_name == 'content':
                doc_id, title, url, content, metadata = doc
                # For content table, we need to find corresponding files
                failed_documents.append({
                    'uid': str(doc_id),
                    'title': title or 'Untitled',
                    'source_url': url,
                    'file_path': None,  # We'll need to find this differently
                    'metadata': json.loads(metadata) if metadata else {}
                })
            else:
                uid, title, source_url, file_path, metadata = doc
                failed_documents.append({
                    'uid': uid,
                    'title': title or 'Untitled',
                    'source_url': source_url,
                    'file_path': file_path,
                    'metadata': json.loads(metadata) if isinstance(metadata, str) else metadata or {}
                })

        cursor.close()
        conn.close()

        self.logger.info(f"📊 Found {len(failed_documents)} failed documents in '{table_name}' table to reprocess")
        return failed_documents

    def reprocess_single_document(self, doc: Dict[str, Any]) -> bool:
        """Reprocess a single failed document."""
        try:
            file_path = doc.get('file_path')
            if not file_path or not Path(file_path).exists():
                self.logger.warning(f"⚠️ File not found for UID {doc['uid']}: {file_path}")
                return False

            self.logger.info(f"🔄 Reprocessing: {doc['title'][:50]}... (UID: {doc['uid']})")

            # Use the fixed document ingestor to reprocess
            result = self.document_ingestor.process_file(Path(file_path))

            if result and hasattr(result, 'content') and result.content:
                # Update database with new content
                conn = self.db.get_connection()
                cursor = conn.cursor()

                # Check table structure again for update
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                table_name = 'documents' if 'documents' in tables else 'content'

                if table_name == 'content':
                    update_query = """
                    UPDATE content
                    SET content = ?,
                        metadata = ?,
                        updated_at = ?
                    WHERE id = ?
                    """
                else:
                    update_query = """
                    UPDATE documents
                    SET content = ?,
                        metadata = ?,
                        updated_at = ?
                    WHERE uid = ?
                    """

                # Merge existing metadata with new metadata
                existing_metadata = doc.get('metadata', {})
                if hasattr(result, 'metadata') and result.metadata:
                    existing_metadata.update(result.metadata)

                cursor.execute(update_query, (
                    result.content,
                    json.dumps(existing_metadata),
                    datetime.now().isoformat(),
                    doc['uid']
                ))

                conn.commit()
                cursor.close()
                conn.close()

                self.logger.info(f"✅ Successfully reprocessed UID {doc['uid']}")
                return True
            else:
                self.logger.warning(f"❌ Reprocessing failed for UID {doc['uid']} - no content extracted")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error reprocessing UID {doc['uid']}: {str(e)}")
            return False

    def run_batch_reprocessing(self, batch_size: int = 10) -> None:
        """Run reprocessing in batches with progress reporting."""
        self.failed_documents = self.identify_failed_documents()
        total_docs = len(self.failed_documents)

        if total_docs == 0:
            self.logger.info("✅ No failed documents found to reprocess!")
            return

        self.logger.info(f"🚀 Starting batch reprocessing of {total_docs} documents")
        self.logger.info(f"📦 Batch size: {batch_size}")

        start_time = time.time()

        for i in range(0, total_docs, batch_size):
            batch = self.failed_documents[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_docs + batch_size - 1) // batch_size

            self.logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")

            # Process batch
            for doc in batch:
                success = self.reprocess_single_document(doc)
                self.processed_count += 1

                if success:
                    self.success_count += 1
                else:
                    self.failure_count += 1

                # Progress update every 10 documents
                if self.processed_count % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = self.processed_count / elapsed if elapsed > 0 else 0

                    self.logger.info(
                        f"📊 Progress: {self.processed_count}/{total_docs} "
                        f"({(self.processed_count/total_docs)*100:.1f}%) "
                        f"| Success: {self.success_count} | Failed: {self.failure_count} "
                        f"| Rate: {rate:.1f} docs/sec"
                    )

                # Small delay to prevent overwhelming the system
                time.sleep(0.1)

            # Batch completion summary
            batch_success_rate = (self.success_count / self.processed_count) * 100 if self.processed_count > 0 else 0
            self.logger.info(f"✅ Batch {batch_num} completed. Overall success rate: {batch_success_rate:.1f}%")

            # Brief pause between batches
            time.sleep(1)

        self.generate_final_report(start_time)

    def generate_final_report(self, start_time: float) -> None:
        """Generate final processing report."""
        elapsed_time = time.time() - start_time
        success_rate = (self.success_count / self.processed_count) * 100 if self.processed_count > 0 else 0

        report = f"""
=====================================
FAILED DOCUMENT REPROCESSING REPORT
=====================================

Execution Time: {elapsed_time/60:.1f} minutes ({elapsed_time:.1f} seconds)
Total Documents Processed: {self.processed_count}
Successfully Reprocessed: {self.success_count}
Still Failed: {self.failure_count}
Success Rate: {success_rate:.1f}%

Processing Rate: {self.processed_count/elapsed_time:.1f} documents per second

SUCCESS CRITERIA CHECK:
Target: 90% success rate
Actual: {success_rate:.1f}%
Status: {'✅ PASSED' if success_rate >= 90 else '❌ FAILED'}

Next Steps:
{'- Task 1.3 completed successfully!' if success_rate >= 90 else f'- Investigation needed for remaining {self.failure_count} failed documents'}
- Run check_all_content.py to verify final state
- Consider Task 1.5 enhancements if needed
"""

        # Log the report
        self.logger.info(report)

        # Save report to file
        report_file = Path("reports") / f"reprocess_documents_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.parent.mkdir(exist_ok=True)
        report_file.write_text(report)

        self.logger.info(f"📄 Final report saved to: {report_file}")

        # Print conclusion
        if success_rate >= 90:
            print("\n🎉 Task 1.3 SUCCESS: Failed document reprocessing completed!")
            print(f"✅ {success_rate:.1f}% success rate achieved (target: 90%)")
        else:
            print(f"\n⚠️ Task 1.3 PARTIAL SUCCESS: {success_rate:.1f}% success rate")
            print("💡 Consider investigating remaining failures or proceeding with current improvements")


def main():
    """Main function to run failed document reprocessing."""
    print("🚀 Atlas Failed Document Reprocessor - Task 1.3")
    print("=" * 60)
    print("This script will reprocess documents that previously failed content extraction")
    print("using the fixes applied in Tasks 1.1 and 1.2.")
    print()

    # Auto-confirm in agent mode or check for --auto flag
    auto_mode = len(sys.argv) > 1 and '--auto' in sys.argv
    if not auto_mode:
        try:
            confirm = input("Do you want to proceed with reprocessing? (y/N): ")
            if confirm.lower() != 'y':
                print("Reprocessing cancelled.")
                return
        except EOFError:
            # Running in agent mode without TTY - proceed automatically
            print("Running in agent mode - proceeding with reprocessing...")
            auto_mode = True

    # Create reprocessor and run
    reprocessor = FailedDocumentReprocessor()

    try:
        reprocessor.run_batch_reprocessing(batch_size=10)
    except KeyboardInterrupt:
        print("\n⚠️ Reprocessing interrupted by user")
        reprocessor.logger.info("Reprocessing interrupted by user")
        reprocessor.generate_final_report(time.time())
    except Exception as e:
        print(f"\n❌ Reprocessing failed with error: {e}")
        reprocessor.logger.error(f"Reprocessing failed with error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)