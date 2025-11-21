#!/usr/bin/env python3
"""
Atlas Interface
Universal interface for you to provide ANY data source
"""

from atlas_universal_bookmarker import AtlasUniversalBookmarker
import json
from datetime import datetime

class AtlasInterface:
    """Your personal Atlas data interface"""

    def __init__(self):
        self.bookmarker = AtlasUniversalBookmarker()
        print("🚀 ATLAS UNIVERSAL INTERFACE READY!")
        print("=" * 60)
        print("📚 Ready to bookmark ANY data source you provide")
        print("🔗 Universal deduplication (SHA-256)")
        print("🏷️  Full search and tagging support")
        print("📊 Real-time statistics")
        print()

    def show_status(self):
        """Show current Atlas status"""
        stats = self.bookmarker.get_stats()
        print(f"📊 ATLAS STATUS: {stats['total_bookmarks']:,} total bookmarks")

        if stats['by_content_type']:
            print(f"📋 By Type: {dict(list(stats['by_content_type'].items())[:5])}")

        if stats['by_source']:
            print(f"📂 By Source: {dict(list(stats['by_source'].items())[:3])}")

        print()

    def bookmark_url(self, url: str, title: str = "", tags: str = ""):
        """Bookmark a URL"""
        print(f"🔗 Bookmarking URL: {url[:60]}...")
        bookmark_id = self.bookmarker.bookmark_url(url, title, tags)
        if bookmark_id:
            print(f"   ✅ SUCCESS! Bookmark ID: {bookmark_id}")
        else:
            print(f"   ❌ Failed to bookmark (may be duplicate)")
        return bookmark_id

    def bookmark_file(self, file_path: str, tags: str = ""):
        """Bookmark a file"""
        print(f"📁 Bookmarking file: {file_path}")
        bookmark_id = self.bookmarker.bookmark_file(file_path, tags)
        if bookmark_id:
            print(f"   ✅ SUCCESS! Bookmark ID: {bookmark_id}")
        else:
            print(f"   ❌ Failed to bookmark")
        return bookmark_id

    def bookmark_text(self, text: str, title: str = "", tags: str = ""):
        """Bookmark text content"""
        print(f"📝 Bookmarking text: {title[:50]}...")
        bookmark_id = self.bookmarker.bookmark_text(text, title, tags)
        if bookmark_id:
            print(f"   ✅ SUCCESS! Bookmark ID: {bookmark_id}")
        else:
            print(f"   ❌ Failed to bookmark")
        return bookmark_id

    def import_directory(self, directory_path: str, pattern: str = "*"):
        """Import all files from a directory"""
        print(f"📂 Importing directory: {directory_path}")
        imported = self.bookmarker.import_directory(directory_path, pattern)
        print(f"   ✅ Imported {imported} files")
        return imported

    def search(self, query: str):
        """Search your bookmarks"""
        print(f"🔍 Searching for: {query}")
        results = self.bookmarker.search_bookmarks(query)
        print(f"   📊 Found {len(results)} results:")

        for i, result in enumerate(results[:10], 1):
            print(f"   {i}. {result['title'][:50]}...")
            print(f"      Type: {result['content_type']} | Source: {result['source']}")
            print(f"      Added: {result['added_date']}")

        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more results")

        return results

    def menu(self):
        """Interactive menu"""
        while True:
            print("\n" + "=" * 50)
            print("🎯 ATLAS UNIVERSAL INTERFACE MENU")
            print("=" * 50)
            print("1. 📊 Show Status")
            print("2. 🔗 Bookmark URL")
            print("3. 📁 Bookmark File")
            print("4. 📝 Bookmark Text")
            print("5. 📂 Import Directory")
            print("6. 🔍 Search Bookmarks")
            print("7. 📋 Bulk Import Existing Data")
            print("8. ❌ Exit")
            print()

            choice = input("Choose option (1-8): ").strip()

            if choice == '1':
                self.show_status()
            elif choice == '2':
                url = input("Enter URL: ").strip()
                title = input("Enter title (optional): ").strip()
                tags = input("Enter tags (optional): ").strip()
                self.bookmark_url(url, title, tags)
            elif choice == '3':
                file_path = input("Enter file path: ").strip()
                tags = input("Enter tags (optional): ").strip()
                self.bookmark_file(file_path, tags)
            elif choice == '4':
                print("Paste your text (end with empty line):")
                lines = []
                while True:
                    line = input()
                    if not line:
                        break
                    lines.append(line)
                text = '\n'.join(lines)
                title = input("Enter title (optional): ").strip()
                tags = input("Enter tags (optional): ").strip()
                self.bookmark_text(text, title, tags)
            elif choice == '5':
                directory = input("Enter directory path: ").strip()
                pattern = input("Enter file pattern (default: *): ").strip() or "*"
                self.import_directory(directory, pattern)
            elif choice == '6':
                query = input("Enter search query: ").strip()
                self.search(query)
            elif choice == '7':
                self.bulk_import_existing()
            elif choice == '8':
                print("👋 Thanks for using Atlas!")
                break
            else:
                print("❌ Invalid choice. Try again.")

            input("\nPress Enter to continue...")

    def bulk_import_existing(self):
        """Import all existing Atlas data"""
        from atlas_bulk_importer import AtlasBulkImporter
        print("🚀 STARTING BULK IMPORT OF ALL EXISTING ATLAS DATA")
        print("=" * 60)

        importer = AtlasBulkImporter()
        total_imported = importer.run_complete_import()

        print(f"\n🎉 BULK IMPORT COMPLETE!")
        print(f"📊 Total imported this session: {total_imported:,}")
        self.show_status()

# Quick interface
if __name__ == "__main__":
    interface = AtlasInterface()

    # Show initial status
    interface.show_status()

    # Start interactive menu
    interface.menu()