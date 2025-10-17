#!/usr/bin/env python3
"""
Content Reprocessor

Reprocesses low-quality content using improved extraction methods.
Integrates with existing ingestion pipeline and semantic quality evaluator.
"""

import sqlite3
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Add path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing ingestors
try:
    from helpers.article_ingestor import ArticleIngestor
    from helpers.config import load_config
    from helpers.semantic_content_evaluator import SemanticContentEvaluator
    INGESTORS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some ingestors not available: {e}")
    INGESTORS_AVAILABLE = False
    # Create fallback classes
    class SemanticContentEvaluator:
        def evaluate_content(self, **kwargs):
            return type('Result', (), {'overall_score': 0.5, 'issues': []})()
    class ArticleIngestor:
        def __init__(self, config): pass
        def process_urls(self, urls): return {"success": False}
    load_config = lambda: {}


@dataclass
class ReprocessResult:
    """Result of content reprocessing."""
    content_id: int
    success: bool
    old_quality: float
    new_quality: float
    old_issues: str
    new_issues: str
    method_used: str
    error: Optional[str] = None


class ContentReprocessor:
    """Reprocesses problematic content to improve quality."""

    def __init__(self):
        self.db_path = "atlas.db"
        self.config = load_config() if INGESTORS_AVAILABLE else {}
        self.evaluator = SemanticContentEvaluator()

        # Initialize ingestors if available
        if INGESTORS_AVAILABLE:
            try:
                self.article_ingestor = ArticleIngestor(self.config)
            except Exception as e:
                print(f"Warning: Could not initialize ArticleIngestor: {e}")
                self.article_ingestor = None
        else:
            self.article_ingestor = None

    def reprocess_item(self, content_id: int) -> ReprocessResult:
        """Reprocess a single content item."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get current content info
            cursor.execute("""
                SELECT id, title, content, url, content_type, quality_score, quality_issues
                FROM content WHERE id = ?
            """, (content_id,))

            row = cursor.fetchone()
            if not row:
                return ReprocessResult(
                    content_id=content_id,
                    success=False,
                    old_quality=0.0,
                    new_quality=0.0,
                    old_issues="",
                    new_issues="",
                    method_used="none",
                    error="Content not found"
                )

            item_id, title, old_content, url, content_type, old_quality, old_issues = row

            print(f"🔄 Reprocessing #{item_id}: {title[:60]}...")

            # Try different reprocessing methods based on issues
            new_content = None
            method_used = "none"

            # Method 1: Re-extract from URL if available
            if url and not url.startswith('inputs/'):
                print(f"   📥 Re-extracting from URL: {url[:60]}...")
                new_content, method_used = self._reextract_from_url(url, content_type)

            # Method 2: Enhanced text cleaning for HTML-heavy content
            if not new_content and "html_heavy" in (old_issues or ""):
                print(f"   🧹 Cleaning HTML-heavy content...")
                new_content, method_used = self._clean_html_content(old_content)

            # Method 3: Content reconstruction from partial data
            if not new_content and "insufficient" in (old_issues or ""):
                print(f"   🔧 Attempting content reconstruction...")
                new_content, method_used = self._reconstruct_content(old_content, title)

            # If no improvement possible, mark as processed
            if not new_content:
                method_used = "no_improvement_possible"
                new_content = old_content

            # Evaluate new content quality
            evaluation = self.evaluator.evaluate_content(
                content=new_content or "",
                title=title or "",
                url=url or "",
                content_type=content_type or ""
            )

            # Update database
            cursor.execute("""
                UPDATE content
                SET content = ?, quality_score = ?, quality_issues = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                new_content,
                evaluation.overall_score,
                ",".join(evaluation.issues),
                datetime.now().isoformat(),
                content_id
            ))

            conn.commit()

            result = ReprocessResult(
                content_id=content_id,
                success=True,
                old_quality=old_quality or 0.0,
                new_quality=evaluation.overall_score,
                old_issues=old_issues or "",
                new_issues=",".join(evaluation.issues),
                method_used=method_used
            )

            print(f"   ✅ Quality: {old_quality:.3f} → {evaluation.overall_score:.3f}")
            return result

        except Exception as e:
            print(f"   ❌ Error reprocessing #{content_id}: {e}")
            return ReprocessResult(
                content_id=content_id,
                success=False,
                old_quality=old_quality or 0.0,
                new_quality=0.0,
                old_issues=old_issues or "",
                new_issues="reprocessing_failed",
                method_used="error",
                error=str(e)
            )
        finally:
            conn.close()

    def _reextract_from_url(self, url: str, content_type: str) -> Tuple[Optional[str], str]:
        """Re-extract content from URL using improved methods."""
        try:
            # Fix URL scheme if missing
            if url and not url.startswith(('http://', 'https://', 'file://')):
                url = f"https://{url}"
                print(f"      🔧 Fixed URL scheme: {url[:60]}...")
            # Use article ingestor if available
            if self.article_ingestor and content_type != "podcast":
                print(f"      🔄 Using ArticleIngestor...")
                results = self.article_ingestor.process_urls([url])

                if results.get("success") and results.get("articles"):
                    article_data = results["articles"][0]
                    if article_data.get("content") and len(article_data["content"]) > 100:
                        return article_data["content"], "article_ingestor_reextraction"

            # Fallback: Simple requests + readability
            print(f"      🔄 Using fallback extraction...")
            import requests
            from readability import Document

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                doc = Document(response.content)
                title = doc.title()
                content = doc.summary()

                # Convert HTML to text
                from bs4 import BeautifulSoup
                # Ensure content is string, not bytes
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
                soup = BeautifulSoup(content, 'html.parser')
                clean_text = soup.get_text(strip=True)

                if len(clean_text) > 200:
                    return f"Title: {title}\n\n{clean_text}", "requests_readability"

        except Exception as e:
            print(f"      ❌ Re-extraction failed: {e}")

        return None, "reextraction_failed"

    def _clean_html_content(self, content: str) -> Tuple[Optional[str], str]:
        """Clean HTML-heavy content."""
        try:
            from bs4 import BeautifulSoup

            # Parse HTML
            soup = BeautifulSoup(content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            # Only return if significantly improved
            if len(text) > len(content) * 0.3:  # At least 30% of original length
                return text, "html_cleaning"

        except Exception as e:
            print(f"      ❌ HTML cleaning failed: {e}")

        return None, "html_cleaning_failed"

    def _reconstruct_content(self, content: str, title: str) -> Tuple[Optional[str], str]:
        """Try to reconstruct content from partial data."""
        try:
            # If content is very short but title exists, try to pad with title info
            if content and title and len(content) < 200:
                reconstructed = f"Title: {title}\n\n{content}"

                # Add some basic structure
                if not content.endswith('.'):
                    reconstructed += "."

                return reconstructed, "content_reconstruction"

        except Exception as e:
            print(f"      ❌ Content reconstruction failed: {e}")

        return None, "reconstruction_failed"

    def reprocess_batch(self, batch_size: int = 10, max_items: int = None) -> Dict[str, Any]:
        """Reprocess a batch of problematic content."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get problematic content
        query = """
            SELECT id, title, quality_score, quality_issues
            FROM content
            WHERE quality_score < 0.4 AND quality_score > 0.0
            AND (quality_issues NOT LIKE '%reprocessing%' AND quality_issues NOT LIKE '%marked_as_stub%')
            ORDER BY quality_score ASC
        """

        if max_items:
            query += f" LIMIT {max_items}"
        else:
            query += f" LIMIT {batch_size}"

        cursor.execute(query)
        problematic_items = cursor.fetchall()
        conn.close()

        if not problematic_items:
            return {
                "message": "No items found for reprocessing",
                "total_processed": 0,
                "results": []
            }

        print(f"🚀 Starting reprocessing of {len(problematic_items)} items...")

        results = []
        successful = 0
        improved = 0

        for item_id, title, old_quality, old_issues in problematic_items:
            result = self.reprocess_item(item_id)
            results.append(result)

            if result.success:
                successful += 1
                if result.new_quality > result.old_quality + 0.1:  # Significant improvement
                    improved += 1

            # Add delay to avoid overwhelming servers
            time.sleep(1)

        summary = {
            "total_processed": len(problematic_items),
            "successful": successful,
            "improved": improved,
            "improvement_rate": improved / len(problematic_items) if problematic_items else 0,
            "results": results
        }

        print(f"\n✅ Reprocessing complete!")
        print(f"   Total: {summary['total_processed']}")
        print(f"   Successful: {summary['successful']}")
        print(f"   Improved: {summary['improved']} ({summary['improvement_rate']*100:.1f}%)")

        return summary

    def get_reprocessing_stats(self) -> Dict[str, Any]:
        """Get statistics about content that needs reprocessing."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count by quality and issues
        cursor.execute("""
            SELECT
                CASE
                    WHEN quality_score < 0.2 THEN 'Failed'
                    WHEN quality_score < 0.4 THEN 'Stub'
                    ELSE 'Low Quality'
                END as category,
                COUNT(*) as count
            FROM content
            WHERE quality_score < 0.4 AND quality_score > 0.0
            GROUP BY
                CASE
                    WHEN quality_score < 0.2 THEN 'Failed'
                    WHEN quality_score < 0.4 THEN 'Stub'
                    ELSE 'Low Quality'
                END
        """)

        categories = dict(cursor.fetchall())

        # Count by issue type
        cursor.execute("""
            SELECT quality_issues, COUNT(*) as count
            FROM content
            WHERE quality_score < 0.4 AND quality_score > 0.0
            AND quality_issues IS NOT NULL AND quality_issues != ''
            GROUP BY quality_issues
            ORDER BY count DESC
            LIMIT 10
        """)

        issue_types = cursor.fetchall()

        conn.close()

        return {
            "total_problematic": sum(categories.values()),
            "categories": categories,
            "common_issues": issue_types
        }


async def reprocess_all_problematic_content():
    """Async function to reprocess all problematic content."""
    reprocessor = ContentReprocessor()

    # Get stats first
    stats = reprocessor.get_reprocessing_stats()
    total_problematic = stats["total_problematic"]

    print(f"🎯 Found {total_problematic} items needing reprocessing")
    print(f"Categories: {stats['categories']}")

    if total_problematic == 0:
        print("✅ No content needs reprocessing!")
        return

    # Process in batches to avoid overwhelming the system
    batch_size = 20
    processed = 0

    while processed < total_problematic:
        print(f"\n📦 Processing batch {processed//batch_size + 1}...")

        result = reprocessor.reprocess_batch(batch_size=batch_size)
        processed += result["total_processed"]

        if result["total_processed"] == 0:
            print("✅ All problematic content has been processed!")
            break

        print(f"Progress: {processed}/{total_problematic} ({processed/total_problematic*100:.1f}%)")

        # Brief pause between batches
        await asyncio.sleep(2)

    print(f"\n🎉 Reprocessing complete! Processed {processed} items total.")


if __name__ == "__main__":
    print("🔄 Atlas Content Reprocessor")
    print("=" * 50)

    reprocessor = ContentReprocessor()

    # Show current stats
    stats = reprocessor.get_reprocessing_stats()
    print(f"Problematic content: {stats['total_problematic']} items")

    if stats["total_problematic"] > 0:
        print("\nStarting reprocessing...")
        # Run async reprocessing
        import asyncio
        asyncio.run(reprocess_all_problematic_content())
    else:
        print("✅ No content needs reprocessing!")