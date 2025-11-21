#!/usr/bin/env python3
"""
Test the enhanced content processor with idempotent processing.
"""

import logging
import os
from datetime import datetime
from helpers.content_processor_enhanced import create_enhanced_processor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_idempotent_processing():
    """Test that content is not reprocessed unnecessarily."""

    # Create processor
    processor = create_enhanced_processor({
        'processed_content_db': 'data/test_processed_content.db',
        'output_dir': 'output/test'
    })

    # Sample content
    content = """
    Apple Inc. announced record quarterly earnings driven by strong iPhone sales.
    CEO Tim Cook stated, "We're seeing unprecedented demand across all product lines."

    The company's services revenue grew 16% year-over-year, reaching $22.3 billion.
    Key growth drivers include the App Store, iCloud, and Apple Music subscriptions.

    Investment thesis: Apple's ecosystem creates strong customer lock-in, leading to
    consistent revenue streams and pricing power in premium market segments.
    """

    print("🔄 Testing Idempotent Processing")
    print("=" * 50)

    # First processing
    print("\n1️⃣ First processing attempt...")

    # Debug: Check content ID generation
    test_id = processor.generate_content_id(
        title="Apple Reports Record Quarterly Earnings",
        url="https://example.com/apple-earnings",
        content=content
    )
    print(f"   Expected content ID: {test_id}")

    result1 = processor.process_content(
        title="Apple Reports Record Quarterly Earnings",
        content=content,
        url="https://example.com/apple-earnings",
        content_type="article"
    )

    print(f"✅ First result: {result1['status']}")
    print(f"   Content ID: {result1['content_id']}")
    print(f"   Quality: {result1.get('extraction_quality', 'N/A')}")

    # Second processing (should skip)
    print("\n2️⃣ Second processing attempt (should skip)...")
    result2 = processor.process_content(
        title="Apple Reports Record Quarterly Earnings",
        content=content,
        url="https://example.com/apple-earnings",
        content_type="article"
    )

    print(f"✅ Second result: {result2['status']}")
    print(f"   Same content ID: {result1['content_id'] == result2['content_id']}")

    # Verify insights were stored
    if result1['status'] == 'processed':
        insights = result1['insights']['insights']
        print(f"\n📊 Extracted Insights:")
        print(f"   Entities: {len(insights['entities'])}")
        print(f"   Quotes: {len(insights['quotes'])}")
        print(f"   Theses: {len(insights['theses'])}")
        print(f"   Sentiment: {insights['sentiment']}")

        # Show some entities
        for entity in insights['entities'][:3]:
            print(f"   • {entity['canonical']} ({entity['type']}) - {entity['confidence']:.1f}")

    return result1['content_id']

def test_different_content():
    """Test processing different content."""

    processor = create_enhanced_processor({
        'processed_content_db': 'data/test_processed_content.db',
        'output_dir': 'output/test'
    })

    print("\n🔄 Testing Different Content Types")
    print("=" * 50)

    # Article content
    article_result = processor.process_content(
        title="Microsoft Acquires OpenAI Partnership",
        content="Microsoft announced a deeper partnership with OpenAI, investing $10 billion to integrate AI capabilities across its product suite.",
        content_type="article"
    )

    # Podcast content
    podcast_result = processor.process_content(
        title="Tech Leaders Discuss AI Future",
        content="HOST: Today we're joined by Satya Nadella. SATYA: AI will transform how we work and live.",
        content_type="podcast"
    )

    print(f"✅ Article processed: {article_result['content_id']}")
    print(f"✅ Podcast processed: {podcast_result['content_id']}")
    print(f"   Different IDs: {article_result['content_id'] != podcast_result['content_id']}")

def test_search_functionality():
    """Test searching processed content."""

    processor = create_enhanced_processor({
        'processed_content_db': 'data/test_processed_content.db',
        'output_dir': 'output/test'
    })

    print("\n🔍 Testing Search Functionality")
    print("=" * 50)

    # Search for Apple-related content
    results = processor.search_insights("Apple", limit=5)
    print(f"Found {len(results)} results for 'Apple'")

    for result in results:
        print(f"• {result['title'][:50]}...")
        print(f"  Quality: {result['extraction_quality']:.2f} | Type: {result['content_type']}")

def test_processing_stats():
    """Test processing statistics."""

    processor = create_enhanced_processor({
        'processed_content_db': 'data/test_processed_content.db',
        'output_dir': 'output/test'
    })

    print("\n📊 Processing Statistics")
    print("=" * 50)

    stats = processor.get_processing_stats()

    print(f"Total Processed: {stats['total_processed']}")
    print(f"Successful: {stats['successful']}")
    print(f"Errors: {stats['errors']}")
    avg_quality = stats['avg_quality']
    quality_str = f"{avg_quality:.2f}" if avg_quality else "N/A"
    print(f"Average Quality: {quality_str}")
    print(f"Content Types: {stats['content_types']}")

    if stats['content_type_breakdown']:
        print("\nContent Type Breakdown:")
        for content_type, count in stats['content_type_breakdown'].items():
            print(f"  {content_type}: {count}")

if __name__ == "__main__":
    print("🚀 Testing Enhanced Content Processor")
    print("=" * 60)

    # Clean up test database
    test_db = 'data/test_processed_content.db'
    if os.path.exists(test_db):
        os.remove(test_db)

    try:
        # Test idempotent processing
        content_id = test_idempotent_processing()

        # Test different content types
        test_different_content()

        # Test search
        test_search_functionality()

        # Test stats
        test_processing_stats()

        print(f"\n✅ All tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise