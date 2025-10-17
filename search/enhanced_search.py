#!/usr/bin/env python3
"""
Enhanced Search Engine for Atlas

This module implements an enhanced search engine with full-text search,
semantic search, and advanced filtering capabilities.
"""

import re
import math
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import json

class EnhancedSearchEngine:
    """Enhanced search engine with full-text and semantic search capabilities"""

    def __init__(self):
        """Initialize the enhanced search engine"""
        self.index = defaultdict(list)  # Inverted index for full-text search
        self.documents = {}  # Document storage
        self.document_count = 0
        self.avg_document_length = 0

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        """
        Add a document to the search index

        Args:
            doc_id (str): Unique identifier for the document
            content (str): Document content
            metadata (Dict[str, Any], optional): Additional document metadata
        """
        # Store document
        self.documents[doc_id] = {
            'content': content,
            'metadata': metadata or {},
            'length': len(content.split())
        }

        # Update document count
        self.document_count += 1

        # Update average document length
        total_length = sum(doc['length'] for doc in self.documents.values())
        self.avg_document_length = total_length / self.document_count if self.document_count > 0 else 0

        # Tokenize content
        tokens = self._tokenize(content)

        # Update inverted index
        term_freq = defaultdict(int)
        for token in tokens:
            term_freq[token] += 1

        # Add terms to index
        for term, freq in term_freq.items():
            self.index[term].append({
                'doc_id': doc_id,
                'frequency': freq
            })

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into terms

        Args:
            text (str): Text to tokenize

        Returns:
            List[str]: List of tokens
        """
        # Simple tokenization - lowercase and remove punctuation
        text = re.sub(r'[^\\w\\s]', '', text.lower())
        tokens = text.split()

        # Remove stop words (simplified)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        tokens = [token for token in tokens if token not in stop_words and len(token) > 2]

        return tokens

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform a full-text search

        Args:
            query (str): Search query
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: Search results
        """
        # Tokenize query
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        # Calculate document scores using TF-IDF
        doc_scores = defaultdict(float)

        for term in query_tokens:
            # Get documents containing this term
            term_documents = self.index.get(term, [])

            # Calculate IDF for this term
            idf = math.log(self.document_count / len(term_documents)) if term_documents and self.document_count > 0 else 0

            # Calculate TF-IDF for each document
            for doc_info in term_documents:
                doc_id = doc_info['doc_id']
                tf = doc_info['frequency']

                # Get document length
                doc_length = self.documents[doc_id]['length']

                # Calculate normalized TF
                normalized_tf = tf / doc_length if doc_length > 0 else 0

                # Calculate TF-IDF score
                tfidf = normalized_tf * idf

                # Add to document score
                doc_scores[doc_id] += tfidf

        # Sort documents by score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # Prepare results
        results = []
        for doc_id, score in sorted_docs[:limit]:
            if doc_id in self.documents:
                doc = self.documents[doc_id]
                results.append({
                    'doc_id': doc_id,
                    'score': score,
                    'content': doc['content'][:200] + '...' if len(doc['content']) > 200 else doc['content'],
                    'metadata': doc['metadata']
                })

        return results

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search (placeholder implementation)

        Args:
            query (str): Search query
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: Search results
        """
        # In a real implementation, this would use embeddings and cosine similarity
        # For now, we'll just do a simple keyword-based search
        return self.search(query, limit)

    def filter_search(self, query: str, filters: Dict[str, Any] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform filtered search

        Args:
            query (str): Search query
            filters (Dict[str, Any], optional): Search filters
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: Filtered search results
        """
        # First perform regular search
        results = self.search(query, limit * 2)  # Get more results to filter

        # Apply filters if provided
        if filters:
            filtered_results = []
            for result in results:
                doc_metadata = result['metadata']
                match = True

                # Check each filter
                for key, value in filters.items():
                    if key in doc_metadata:
                        if isinstance(value, list):
                            # Check if any of the filter values match
                            if doc_metadata[key] not in value:
                                match = False
                                break
                        else:
                            # Check if filter value matches
                            if doc_metadata[key] != value:
                                match = False
                                break
                    else:
                        # Filter key not in metadata
                        match = False
                        break

                if match:
                    filtered_results.append(result)

                # Stop when we have enough results
                if len(filtered_results) >= limit:
                    break

            return filtered_results[:limit]

        return results[:limit]

    def build_index(self, documents: List[Dict[str, Any]]):
        """
        Build search index from a list of documents

        Args:
            documents (List[Dict[str, Any]]): List of documents to index
        """
        print(f"Building search index for {len(documents)} documents...")

        for doc in documents:
            doc_id = doc.get('id', str(hash(doc.get('content', ''))))
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})

            self.add_document(doc_id, content, metadata)

        print(f"Search index built with {self.document_count} documents")

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get search index statistics

        Returns:
            Dict[str, Any]: Index statistics
        """
        return {
            'document_count': self.document_count,
            'term_count': len(self.index),
            'avg_document_length': self.avg_document_length
        }

def main():
    """Example usage of EnhancedSearchEngine"""
    # Create search engine
    search_engine = EnhancedSearchEngine()

    # Sample documents
    documents = [
        {
            'id': 'doc1',
            'content': 'Python is a high-level programming language with dynamic semantics.',
            'metadata': {
                'type': 'article',
                'category': 'programming',
                'author': 'John Doe',
                'year': 2023
            }
        },
        {
            'id': 'doc2',
            'content': 'Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn.',
            'metadata': {
                'type': 'article',
                'category': 'ai',
                'author': 'Jane Smith',
                'year': 2023
            }
        },
        {
            'id': 'doc3',
            'content': 'Data science combines statistics, mathematics, and computer science to extract insights from data.',
            'metadata': {
                'type': 'article',
                'category': 'data-science',
                'author': 'Bob Johnson',
                'year': 2022
            }
        }
    ]

    # Build index
    search_engine.build_index(documents)

    # Perform search
    print("Searching for 'python programming'...")
    results = search_engine.search('python programming')
    print(f"Found {len(results)} results:")
    for result in results:
        print(f"  - {result['doc_id']}: {result['content'][:50]}...")

    # Perform filtered search
    print("\nSearching for 'data' with category filter...")
    filtered_results = search_engine.filter_search(
        'data',
        filters={'category': 'data-science'}
    )
    print(f"Found {len(filtered_results)} filtered results:")
    for result in filtered_results:
        print(f"  - {result['doc_id']}: {result['content'][:50]}...")

    # Get index stats
    stats = search_engine.get_index_stats()
    print(f"\nIndex Statistics:")
    print(f"  Documents: {stats['document_count']}")
    print(f"  Terms: {stats['term_count']}")
    print(f"  Average Document Length: {stats['avg_document_length']:.2f}")

if __name__ == "__main__":
    main()