#!/usr/bin/env python3
"""
Search Indexing System for Atlas

This module implements a search indexing system that automatically indexes
content as it's processed by Atlas.
"""

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

class SearchIndexer:
    """Search indexing system for Atlas content"""

    def __init__(self, db_path: str = "search_index.db"):
        """
        Initialize the search indexer

        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.init_database()

    def init_database(self):
        """Initialize the SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()

            # Create documents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    content_type TEXT,
                    author TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    word_count INTEGER,
                    metadata TEXT
                )
            ''')

            # Create terms table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS terms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT UNIQUE
                )
            ''')

            # Create document_terms table (many-to-many relationship)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS document_terms (
                    document_id TEXT,
                    term_id INTEGER,
                    frequency INTEGER,
                    FOREIGN KEY (document_id) REFERENCES documents (id),
                    FOREIGN KEY (term_id) REFERENCES terms (id)
                )
            ''')

            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_doc_type ON documents (content_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_doc_author ON documents (author)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_term_text ON terms (term)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_doc_terms ON document_terms (document_id, term_id)')

            self.conn.commit()
            print("Search indexing database initialized successfully")

        except Exception as e:
            print(f"Error initializing search indexing database: {e}")
            raise

    def index_document(self, document: Dict[str, Any]):
        """
        Index a document in the search system

        Args:
            document (Dict[str, Any]): Document to index
        """
        try:
            cursor = self.conn.cursor()

            # Extract document fields
            doc_id = document.get('id', str(hash(document.get('content', ''))))
            title = document.get('title', '')
            content = document.get('content', '')
            content_type = document.get('type', 'unknown')
            author = document.get('author', 'unknown')
            created_at = document.get('created_at', datetime.now().isoformat())
            updated_at = document.get('updated_at', datetime.now().isoformat())
            word_count = len(content.split()) if content else 0
            metadata = json.dumps(document.get('metadata', {}))

            # Insert or update document
            cursor.execute('''
                INSERT OR REPLACE INTO documents
                (id, title, content, content_type, author, created_at, updated_at, word_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (doc_id, title, content, content_type, author, created_at, updated_at, word_count, metadata))

            # Remove existing term associations for this document
            cursor.execute('DELETE FROM document_terms WHERE document_id = ?', (doc_id,))

            # Extract and index terms
            terms = self._extract_terms(content)
            for term, frequency in terms.items():
                # Get or create term ID
                cursor.execute('SELECT id FROM terms WHERE term = ?', (term,))
                result = cursor.fetchone()

                if result:
                    term_id = result[0]
                else:
                    # Insert new term
                    cursor.execute('INSERT INTO terms (term) VALUES (?)', (term,))
                    term_id = cursor.lastrowid

                # Associate term with document
                cursor.execute('''
                    INSERT INTO document_terms (document_id, term_id, frequency)
                    VALUES (?, ?, ?)
                ''', (doc_id, term_id, frequency))

            self.conn.commit()
            print(f"Document {doc_id} indexed successfully")

        except Exception as e:
            print(f"Error indexing document {document.get('id', 'unknown')}: {e}")
            self.conn.rollback()

    def _extract_terms(self, text: str) -> Dict[str, int]:
        """
        Extract terms from text with frequency counts

        Args:
            text (str): Text to extract terms from

        Returns:
            Dict[str, int]: Dictionary of terms and their frequencies
        """
        # Simple term extraction (in a real implementation, this would be more sophisticated)
        import re

        # Convert to lowercase and remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text.lower())

        # Split into words
        words = text.split()

        # Remove stop words and short words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }

        terms = {}
        for word in words:
            if len(word) > 2 and word not in stop_words:
                terms[word] = terms.get(word, 0) + 1

        return terms

    def remove_document(self, doc_id: str):
        """
        Remove a document from the index

        Args:
            doc_id (str): Document ID to remove
        """
        try:
            cursor = self.conn.cursor()

            # Remove term associations
            cursor.execute('DELETE FROM document_terms WHERE document_id = ?', (doc_id,))

            # Remove document
            cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))

            self.conn.commit()
            print(f"Document {doc_id} removed from index")

        except Exception as e:
            print(f"Error removing document {doc_id}: {e}")
            self.conn.rollback()

    def update_document(self, doc_id: str, updates: Dict[str, Any]):
        """
        Update a document in the index

        Args:
            doc_id (str): Document ID to update
            updates (Dict[str, Any]): Fields to update
        """
        try:
            cursor = self.conn.cursor()

            # Build update query dynamically
            fields = []
            values = []

            for key, value in updates.items():
                if key in ['title', 'content', 'content_type', 'author', 'metadata']:
                    fields.append(f"{key} = ?")
                    if key == 'metadata':
                        values.append(json.dumps(value))
                    else:
                        values.append(value)

            if fields:
                values.append(doc_id)
                query = f"UPDATE documents SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
                values.append(datetime.now().isoformat())

                cursor.execute(query, values)
                self.conn.commit()
                print(f"Document {doc_id} updated successfully")

                # Re-index terms if content was updated
                if 'content' in updates:
                    # Remove existing term associations
                    cursor.execute('DELETE FROM document_terms WHERE document_id = ?', (doc_id,))

                    # Extract and index new terms
                    terms = self._extract_terms(updates['content'])
                    for term, frequency in terms.items():
                        # Get or create term ID
                        cursor.execute('SELECT id FROM terms WHERE term = ?', (term,))
                        result = cursor.fetchone()

                        if result:
                            term_id = result[0]
                        else:
                            # Insert new term
                            cursor.execute('INSERT INTO terms (term) VALUES (?)', (term,))
                            term_id = cursor.lastrowid

                        # Associate term with document
                        cursor.execute('''
                            INSERT INTO document_terms (document_id, term_id, frequency)
                            VALUES (?, ?, ?)
                        ''', (doc_id, term_id, frequency))

                    self.conn.commit()

        except Exception as e:
            print(f"Error updating document {doc_id}: {e}")
            self.conn.rollback()

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from the index

        Args:
            doc_id (str): Document ID to retrieve

        Returns:
            Optional[Dict[str, Any]]: Document data or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
            row = cursor.fetchone()

            if row:
                return {
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'content_type': row[3],
                    'author': row[4],
                    'created_at': row[5],
                    'updated_at': row[6],
                    'word_count': row[7],
                    'metadata': json.loads(row[8]) if row[8] else {}
                }

            return None

        except Exception as e:
            print(f"Error retrieving document {doc_id}: {e}")
            return None

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get index statistics

        Returns:
            Dict[str, Any]: Index statistics
        """
        try:
            cursor = self.conn.cursor()

            # Get document count
            cursor.execute('SELECT COUNT(*) FROM documents')
            doc_count = cursor.fetchone()[0]

            # Get term count
            cursor.execute('SELECT COUNT(*) FROM terms')
            term_count = cursor.fetchone()[0]

            # Get document-terms count
            cursor.execute('SELECT COUNT(*) FROM document_terms')
            doc_term_count = cursor.fetchone()[0]

            return {
                'document_count': doc_count,
                'term_count': term_count,
                'document_term_count': doc_term_count,
                'db_path': self.db_path
            }

        except Exception as e:
            print(f"Error getting index stats: {e}")
            return {}

    def rebuild_index(self, documents: List[Dict[str, Any]]):
        """
        Rebuild the entire index from scratch

        Args:
            documents (List[Dict[str, Any]]): List of documents to index
        """
        try:
            print(f"Rebuilding index with {len(documents)} documents...")

            # Clear existing index
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM document_terms')
            cursor.execute('DELETE FROM terms')
            cursor.execute('DELETE FROM documents')
            self.conn.commit()

            # Index all documents
            for doc in documents:
                self.index_document(doc)

            print("Index rebuilt successfully")

        except Exception as e:
            print(f"Error rebuilding index: {e}")
            self.conn.rollback()

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            print("Search indexing database closed")

def main():
    """Example usage of SearchIndexer"""
    # Create indexer
    indexer = SearchIndexer()

    # Sample documents
    documents = [
        {
            'id': 'doc1',
            'title': 'Introduction to Python Programming',
            'content': 'Python is a high-level programming language with dynamic semantics. It is used for web development, data science, and automation.',
            'type': 'article',
            'author': 'John Doe',
            'created_at': '2023-05-01T10:00:00Z',
            'updated_at': '2023-05-01T10:00:00Z',
            'metadata': {
                'category': 'programming',
                'tags': ['python', 'programming', 'beginner'],
                'source': 'atlas'
            }
        },
        {
            'id': 'doc2',
            'title': 'Machine Learning Basics',
            'content': 'Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn and improve from experience.',
            'type': 'article',
            'author': 'Jane Smith',
            'created_at': '2023-05-02T11:00:00Z',
            'updated_at': '2023-05-02T11:00:00Z',
            'metadata': {
                'category': 'ai',
                'tags': ['machine-learning', 'ai', 'data-science'],
                'source': 'atlas'
            }
        }
    ]

    # Index documents
    for doc in documents:
        indexer.index_document(doc)

    # Get index stats
    stats = indexer.get_index_stats()
    print(f"Index Stats: {stats}")

    # Retrieve a document
    doc = indexer.get_document('doc1')
    if doc:
        print(f"Retrieved document: {doc['title']}")

    # Close indexer
    indexer.close()

if __name__ == "__main__":
    main()