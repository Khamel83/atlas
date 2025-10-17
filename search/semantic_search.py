#!/usr/bin/env python3
"""
Semantic Search for Atlas

This module implements semantic search capabilities for Atlas using vector embeddings.
"""

import re
import math
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np

class SemanticSearchEngine:
    """Semantic search engine using vector embeddings"""

    def __init__(self):
        """Initialize the semantic search engine"""
        self.documents = {}
        self.embeddings = {}
        self.document_count = 0
        self.embedding_dimension = 300  # Default embedding dimension

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        """
        Add a document to the semantic search index

        Args:
            doc_id (str): Unique identifier for the document
            content (str): Document content
            metadata (Dict[str, Any], optional): Additional document metadata
        """
        # Store document
        self.documents[doc_id] = {
            'id': doc_id,
            'content': content,
            'metadata': metadata or {},
            'embedding': None  # Will be calculated later
        }

        # Generate embedding for document
        embedding = self._generate_embedding(content)
        self.documents[doc_id]['embedding'] = embedding
        self.embeddings[doc_id] = embedding

        # Update document count
        self.document_count += 1

        print(f"Document {doc_id} added to semantic search index")

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text (placeholder implementation)

        Args:
            text (str): Text to embed

        Returns:
            List[float]: Generated embedding
        """
        # In a real implementation, this would use a transformer model or similar
        # For now, we'll generate a random embedding as a placeholder
        # In a real implementation, you would use:
        # 1. Pre-trained models like BERT, RoBERTa, or Sentence-BERT
        # 2. Or a service like OpenAI embeddings API

        # Generate a deterministic pseudo-random embedding based on text
        # This ensures the same text always produces the same embedding
        import hashlib

        # Create a hash of the text
        text_hash = hashlib.md5(text.encode()).hexdigest()

        # Convert hash to a list of floats
        embedding = []
        for i in range(0, min(len(text_hash), self.embedding_dimension * 2), 2):
            # Convert hex pairs to float values between -1 and 1
            hex_pair = text_hash[i:i+2]
            float_val = (int(hex_pair, 16) / 255.0) * 2 - 1
            embedding.append(float_val)

        # Pad or truncate to correct dimension
        if len(embedding) < self.embedding_dimension:
            # Pad with zeros
            embedding.extend([0.0] * (self.embedding_dimension - len(embedding)))
        elif len(embedding) > self.embedding_dimension:
            # Truncate
            embedding = embedding[:self.embedding_dimension]

        return embedding

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search

        Args:
            query (str): Search query
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: Search results
        """
        if not self.documents:
            return []

        # Generate embedding for query
        query_embedding = self._generate_embedding(query)

        # Calculate similarity scores for all documents
        similarities = {}

        for doc_id, doc_embedding in self.embeddings.items():
            if doc_embedding is not None:
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                similarities[doc_id] = similarity

        # Sort by similarity (descending)
        sorted_docs = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

        # Prepare results
        results = []
        for doc_id, similarity in sorted_docs[:limit]:
            if doc_id in self.documents:
                doc = self.documents[doc_id]
                results.append({
                    'doc_id': doc_id,
                    'similarity': similarity,
                    'content': doc['content'][:200] + '...' if len(doc['content']) > 200 else doc['content'],
                    'metadata': doc['metadata']
                })

        return results

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1 (List[float]): First vector
            vec2 (List[float]): Second vector

        Returns:
            float: Cosine similarity (0-1)
        """
        # Convert to numpy arrays for easier computation
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        # Calculate dot product
        dot_product = np.dot(vec1, vec2)

        # Calculate magnitudes
        magnitude1 = np.linalg.norm(vec1)
        magnitude2 = np.linalg.norm(vec2)

        # Calculate cosine similarity
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def semantic_filter(self, query: str, filters: Dict[str, Any] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search with filters

        Args:
            query (str): Search query
            filters (Dict[str, Any], optional): Search filters
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: Filtered search results
        """
        # First perform semantic search
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
        Build semantic search index from a list of documents

        Args:
            documents (List[Dict[str, Any]]): List of documents to index
        """
        print(f"Building semantic search index for {len(documents)} documents...")

        for doc in documents:
            doc_id = doc.get('id', str(hash(doc.get('content', ''))))
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})

            self.add_document(doc_id, content, metadata)

        print(f"Semantic search index built with {self.document_count} documents")

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get semantic search index statistics

        Returns:
            Dict[str, Any]: Index statistics
        """
        return {
            'document_count': self.document_count,
            'embedding_dimension': self.embedding_dimension,
            'indexed_documents': list(self.documents.keys())[:10]  # First 10 document IDs
        }

def main():
    """Example usage of SemanticSearchEngine"""
    # Create search engine
    search_engine = SemanticSearchEngine()

    # Sample documents
    documents = [
        {
            'id': 'doc1',
            'content': 'Python is a high-level programming language with dynamic semantics. It is used for web development, data science, and automation.',
            'metadata': {
                'type': 'article',
                'category': 'programming',
                'author': 'John Doe',
                'year': 2023
            }
        },
        {
            'id': 'doc2',
            'content': 'Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn and improve from experience.',
            'metadata': {
                'type': 'article',
                'category': 'ai',
                'author': 'Jane Smith',
                'year': 2023
            }
        },
        {
            'id': 'doc3',
            'content': 'Data science combines statistics, mathematics, and computer science to extract insights from data. It involves data cleaning, data analysis, and data visualization.',
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

    # Perform semantic search
    print("Performing semantic search for 'python programming'...")
    results = search_engine.search('python programming')
    print(f"Found {len(results)} results:")
    for result in results:
        print(f"  - {result['doc_id']}: Similarity {result['similarity']:.4f}")
        print(f"    Content: {result['content'][:100]}...")

    # Perform filtered semantic search
    print("\nPerforming filtered semantic search for 'data' with category filter...")
    filtered_results = search_engine.semantic_filter(
        'data',
        filters={'category': 'data-science'}
    )
    print(f"Found {len(filtered_results)} filtered results:")
    for result in filtered_results:
        print(f"  - {result['doc_id']}: Similarity {result['similarity']:.4f}")
        print(f"    Content: {result['content'][:100]}...")

    # Get index stats
    stats = search_engine.get_index_stats()
    print(f"\nIndex Statistics:")
    print(f"  Documents: {stats['document_count']}")
    print(f"  Embedding Dimension: {stats['embedding_dimension']}")
    print(f"  Indexed Documents: {', '.join(stats['indexed_documents'])}")

if __name__ == "__main__":
    main()