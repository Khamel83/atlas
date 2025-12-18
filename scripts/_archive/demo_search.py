#!/usr/bin/env python3
"""
Demo script for Atlas Search System
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def demo_enhanced_search():
    """Demo the enhanced search engine"""
    print("🔍 Atlas Enhanced Search Engine Demo")
    print("=" * 45)

    try:
        from search.enhanced_search import EnhancedSearchEngine

        # Create search engine
        search_engine = EnhancedSearchEngine()

        # Sample documents
        documents = [
            {
                'id': 'python_guide',
                'content': 'Python is a high-level programming language with dynamic semantics. It is used for web development, data science, and automation. Python has a simple syntax similar to English.',
                'metadata': {
                    'title': 'Complete Python Programming Guide',
                    'type': 'article',
                    'category': 'programming',
                    'author': 'John Doe',
                    'tags': ['python', 'programming', 'beginner']
                }
            },
            {
                'id': 'ml_basics',
                'content': 'Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn and improve from experience. It focuses on the development of computer programs that can access data and use it to learn for themselves.',
                'metadata': {
                    'title': 'Machine Learning Basics',
                    'type': 'article',
                    'category': 'ai',
                    'author': 'Jane Smith',
                    'tags': ['machine-learning', 'ai', 'data-science']
                }
            },
            {
                'id': 'data_science_intro',
                'content': 'Data science combines statistics, mathematics, and computer science to extract insights from data. It involves data cleaning, data analysis, and data visualization. Popular tools include Python, R, and SQL.',
                'metadata': {
                    'title': 'Introduction to Data Science',
                    'type': 'article',
                    'category': 'data-science',
                    'author': 'Bob Johnson',
                    'tags': ['data-science', 'statistics', 'analytics']
                }
            }
        ]

        # Build index
        print("Building search index...")
        search_engine.build_index(documents)
        print("✅ Index built successfully!")

        # Perform search
        print("\nSearching for 'python programming'...")
        results = search_engine.search('python programming')
        print(f"Found {len(results)} results:")
        for result in results:
            print(f"  - {result['doc_id']}: Score {result['score']:.4f}")
            print(f"    Content: {result['content'][:100]}...")

        # Perform semantic search
        print("\nPerforming semantic search for 'artificial intelligence'...")
        semantic_results = search_engine.semantic_search('artificial intelligence')
        print(f"Found {len(semantic_results)} semantic search results:")
        for result in semantic_results:
            print(f"  - {result['doc_id']}: Score {result['score']:.4f}")

        # Perform filtered search
        print("\nPerforming filtered search for 'data' in 'data-science' category...")
        filtered_results = search_engine.filter_search(
            'data',
            filters={'category': 'data-science'}
        )
        print(f"Found {len(filtered_results)} filtered results:")
        for result in filtered_results:
            print(f"  - {result['doc_id']}: Score {result['score']:.4f}")

        # Get index stats
        stats = search_engine.get_index_stats()
        print(f"\nIndex Statistics:")
        print(f"  Documents: {stats['document_count']}")
        print(f"  Terms: {stats['term_count']}")
        print(f"  Average Document Length: {stats['avg_document_length']:.2f}")

        print("\n✅ Enhanced Search Engine demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Enhanced Search Engine demo failed: {e}")
        return False

def demo_indexing_system():
    """Demo the indexing system"""
    print("\n📚 Atlas Search Indexing System Demo")
    print("=" * 45)

    try:
        from search.indexing_system import SearchIndexer
        import os

        # Create indexer with temporary database
        db_path = "/tmp/demo_search_index.db"
        if os.path.exists(db_path):
            os.remove(db_path)

        indexer = SearchIndexer(db_path)

        # Sample documents
        documents = [
            {
                'id': 'demo_doc_1',
                'title': 'Demo Document 1',
                'content': 'This is the first demo document for the Atlas search indexing system.',
                'type': 'article',
                'author': 'Demo User',
                'created_at': '2023-05-01T10:00:00Z',
                'updated_at': '2023-05-01T10:00:00Z',
                'metadata': {
                    'category': 'demo',
                    'tags': ['demo', 'testing']
                }
            },
            {
                'id': 'demo_doc_2',
                'title': 'Demo Document 2',
                'content': 'This is the second demo document showcasing the Atlas search indexing capabilities.',
                'type': 'article',
                'author': 'Demo User',
                'created_at': '2023-05-01T11:00:00Z',
                'updated_at': '2023-05-01T11:00:00Z',
                'metadata': {
                    'category': 'demo',
                    'tags': ['demo', 'indexing']
                }
            }
        ]

        # Index documents
        print("Indexing demo documents...")
        for doc in documents:
            indexer.index_document(doc)
        print("✅ Documents indexed successfully!")

        # Retrieve a document
        print("\nRetrieving document 'demo_doc_1'...")
        doc = indexer.get_document('demo_doc_1')
        if doc:
            print(f"Retrieved document: {doc['title']}")
            print(f"Content: {doc['content']}")
            print(f"Author: {doc['author']}")
        else:
            print("Document not found")

        # Update a document
        print("\nUpdating document 'demo_doc_1'...")
        indexer.update_document('demo_doc_1', {
            'content': 'This is the UPDATED first demo document for the Atlas search indexing system.',
            'metadata': {
                'category': 'demo',
                'tags': ['demo', 'testing', 'updated']
            }
        })
        print("✅ Document updated successfully!")

        # Get index stats
        stats = indexer.get_index_stats()
        print(f"\nIndex Statistics:")
        print(f"  Documents: {stats['document_count']}")
        print(f"  Terms: {stats['term_count']}")
        print(f"  Document-Term Associations: {stats['document_term_count']}")

        # Close and cleanup
        indexer.close()
        if os.path.exists(db_path):
            os.remove(db_path)

        print("\n✅ Search Indexing System demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Search Indexing System demo failed: {e}")
        return False

def demo_search_api():
    """Demo the search API endpoints"""
    print("\n🌐 Atlas Search API Demo")
    print("=" * 45)

    try:
        from api.search_api import search_bp, initialize_search_system

        # Initialize search system
        print("Initializing search system...")
        initialize_search_system()
        print("✅ Search system initialized!")

        # Show available endpoints
        print("\nAvailable API Endpoints:")
        print("  GET /api/search/query?q=<query>")
        print("  GET /api/search/semantic?q=<query>")
        print("  GET /api/search/filter?q=<query>&filters=<json>")
        print("  POST /api/search/documents")
        print("  GET /api/search/documents/<doc_id>")
        print("  PUT /api/search/documents/<doc_id>")
        print("  DELETE /api/search/documents/<doc_id>")
        print("  GET /api/search/stats")
        print("  GET /api/search/health")

        print("\n✅ Search API demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Search API demo failed: {e}")
        return False

def main():
    """Run all demos"""
    print("🚀 Atlas Search System Demo")
    print("=" * 50)

    demos = [
        demo_enhanced_search,
        demo_indexing_system,
        demo_search_api
    ]

    passed = 0
    failed = 0

    for demo in demos:
        if demo():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 50)
    print(f"Demo Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All demos completed successfully!")
        print("\n🎯 Atlas Search System is ready for use!")
        return True
    else:
        print("⚠️  Some demos failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)