#!/usr/bin/env python3
"""
Test Block 4: Content Export Framework
Tests content export with actual Atlas processed documents
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from helpers.content_exporter import ContentExporter


class AtlasContentExporter(ContentExporter):
    """Custom content exporter for Atlas processed documents"""

    def __init__(self, atlas_output_dir: str = None):
        self.atlas_output_dir = Path(atlas_output_dir or "output")
        self.documents_dir = self.atlas_output_dir / "documents"
        # Skip podcast database init
        pass

    def _get_atlas_content(self, limit: int = 10) -> list:
        """Get processed Atlas documents"""
        content_data = []

        # Find document metadata files
        metadata_files = list(self.documents_dir.glob("*_metadata.json"))[:limit]

        for metadata_file in metadata_files:
            try:
                # Load metadata
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

                # Load content
                content_file = metadata_file.parent / f"{metadata['uid']}.md"
                content = ""
                if content_file.exists():
                    with open(content_file, 'r') as f:
                        content = f.read()

                # Convert to export format
                content_item = {
                    "id": metadata["uid"],
                    "title": metadata.get("source_file", "Unknown").split("/")[-1],
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "created_at": metadata.get("created_at", datetime.now().isoformat()),
                    "content": content,
                    "content_type": metadata.get("content_type", "document"),
                    "source_url": metadata.get("source_file", ""),
                    "word_count": metadata.get("word_count", 0),
                    "file_size": metadata.get("file_size", 0),
                    "language": metadata.get("language", "eng")
                }

                content_data.append(content_item)

            except Exception as e:
                print(f"Error processing {metadata_file}: {e}")
                continue

        return content_data

    def export_atlas_content(self, format_type: str = "markdown", output_path: str = None, limit: int = 10):
        """Export Atlas processed content"""
        content_data = self._get_atlas_content(limit)

        if not content_data:
            return {"status": "error", "message": "No Atlas content found"}

        # Use parent class formatting
        formatted_content = self._format_content(content_data, format_type)

        # Write output
        if output_path:
            output_files = self._write_export(formatted_content, format_type, output_path)
            return {
                "status": "success",
                "content_count": len(content_data),
                "files": output_files,
                "format": format_type
            }
        else:
            return {
                "status": "success",
                "content_count": len(content_data),
                "data": formatted_content,
                "format": format_type
            }


def test_all_export_formats():
    """Test all export formats with Atlas content"""
    print("🧪 Testing Block 4: Content Export Framework")
    print("=" * 50)

    exporter = AtlasContentExporter()
    test_output_dir = Path("test_exports")
    test_output_dir.mkdir(exist_ok=True)

    formats_to_test = ["markdown", "json", "csv", "obsidian", "notion", "anki"]
    results = {}

    for fmt in formats_to_test:
        print(f"\n📄 Testing {fmt.upper()} export...")
        try:
            result = exporter.export_atlas_content(
                format_type=fmt,
                output_path=str(test_output_dir / fmt),
                limit=5
            )

            if result["status"] == "success":
                print(f"✅ {fmt} export successful:")
                print(f"   - Content items: {result['content_count']}")
                print(f"   - Files created: {len(result['files'])}")
                for file_path in result['files']:
                    file_size = os.path.getsize(file_path)
                    print(f"   - {Path(file_path).name}: {file_size} bytes")
                results[fmt] = "✅ SUCCESS"
            else:
                print(f"❌ {fmt} export failed: {result['message']}")
                results[fmt] = f"❌ FAILED: {result['message']}"

        except Exception as e:
            print(f"❌ {fmt} export error: {str(e)}")
            results[fmt] = f"❌ ERROR: {str(e)}"

    # Summary
    print(f"\n📊 BLOCK 4 EXPORT TEST SUMMARY")
    print("=" * 50)
    for fmt, status in results.items():
        print(f"{fmt.ljust(10)}: {status}")

    successful = len([r for r in results.values() if "SUCCESS" in r])
    total = len(results)

    if successful == total:
        print(f"\n🎉 BLOCK 4 COMPLETE: All {total}/{total} export formats working!")
        return True
    else:
        print(f"\n⚠️  BLOCK 4 PARTIAL: {successful}/{total} export formats working")
        return False


def test_export_content_sampling():
    """Test content sampling and validation"""
    print(f"\n🔍 Testing Atlas content sampling...")

    exporter = AtlasContentExporter()

    # Check available documents
    total_docs = len(list(exporter.documents_dir.glob("*_metadata.json")))
    print(f"📚 Total processed documents: {total_docs}")

    if total_docs == 0:
        print("❌ No processed documents found in output/documents/")
        return False

    # Sample content
    content_data = exporter._get_atlas_content(limit=3)
    print(f"📄 Sampled {len(content_data)} documents for testing")

    for i, item in enumerate(content_data):
        print(f"\n📄 Document {i+1}:")
        print(f"   ID: {item['id']}")
        print(f"   Title: {item['title'][:50]}...")
        print(f"   Content Type: {item['content_type']}")
        print(f"   Word Count: {item['word_count']}")
        print(f"   Content Length: {len(item['content'])} chars")

    return True


if __name__ == "__main__":
    print("🚀 Starting Block 4: Content Export Framework Test")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Working Directory: {os.getcwd()}")

    # Test content sampling first
    if not test_export_content_sampling():
        print("❌ Content sampling failed - cannot proceed with export tests")
        sys.exit(1)

    # Test all export formats
    success = test_all_export_formats()

    if success:
        print(f"\n🎉 BLOCK 4: CONTENT EXPORT FRAMEWORK - COMPLETE!")
        print("✅ All export formats tested and working")
        print("✅ Framework validated with real Atlas data")
        sys.exit(0)
    else:
        print(f"\n⚠️  BLOCK 4: Partial success - some formats need debugging")
        sys.exit(1)