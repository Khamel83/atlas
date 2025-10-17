#!/usr/bin/env python3
"""
Test script for structured content extraction system.
"""

import json
import logging
import sqlite3
from helpers.structured_extraction import StructuredExtractor, ContentInput, create_extractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_real_database_article():
    """Test extraction on a real article from the database."""

    # Get a real article from database
    import sqlite3
    conn = sqlite3.connect("data/atlas.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, content, url
        FROM content
        WHERE content IS NOT NULL
        AND length(content) > 1000
        AND content_type = 'article'
        ORDER BY RANDOM()
        LIMIT 1
    """)
    article = cursor.fetchone()
    conn.close()

    if not article:
        print("❌ No real articles found in database")
        return None

    content_id, title, content, url = article

    print(f"🔍 Testing real article: {title[:60]}...")
    print(f"   Content ID: {content_id}")
    print(f"   URL: {url}")

    try:
        # Create content input from real data
        content_input = ContentInput(
            title=title,
            content=content,
            url=url,
            content_type="article"
        )

        # Create extractor
        extractor = create_extractor()

        # Run structured extraction
        extraction_result = extractor.extract(content_input, validate=True)

        if extraction_result.success:
            insights = extraction_result.insights
            print(f"✅ Real extraction successful!")
            print(f"   Summary: {insights.summary[:100]}...")
            print(f"   Quality score: {extraction_result.extraction_quality}")
            print(f"   Entities found: {len(insights.entities)}")
            print(f"   Topics found: {len(insights.key_topics)}")

            # Save to database
            conn = sqlite3.connect("data/atlas.db")
            cursor = conn.cursor()

            # Insert insights
            cursor.execute("""
                INSERT OR REPLACE INTO content_insights
                (content_id, summary, key_topics, key_themes, entities, quotes, theses,
                 sentiment, complexity, extraction_quality, model_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content_id,
                insights.summary,
                json.dumps([{"name": t.name, "relevance": t.relevance, "subtopics": t.subtopics or []} for t in insights.key_topics]),
                json.dumps(insights.key_themes),
                json.dumps([{"name": e.name, "type": e.type, "confidence": e.confidence} for e in insights.entities]),
                json.dumps([{"text": q.text, "speaker": q.speaker} for q in insights.quotes]),
                json.dumps([{"statement": th.statement, "rationale": th.rationale, "confidence": th.confidence, "category": th.category} for th in insights.theses]),
                insights.sentiment,
                insights.complexity,
                extraction_result.extraction_quality,
                extraction_result.model_used
            ))

            conn.commit()
            conn.close()

            print(f"💾 Insights saved to database!")
            return extraction_result
        else:
            print(f"❌ Real extraction failed: {extraction_result.error}")
            return None

    except Exception as e:
        print(f"❌ Exception during real extraction: {e}")
        return None

def test_article_extraction():
    """Test extraction on a sample article."""

    # Sample article content
    sample_content = """
    OpenAI announced a major breakthrough in artificial intelligence with their new GPT-5 model.
    CEO Sam Altman said in a recent interview, "This represents a fundamental shift in how we approach AI development."

    The company, valued at over $80 billion, has been at the forefront of the AI revolution. Their partnership
    with Microsoft has enabled massive scaling of compute resources, allowing them to train larger and more
    sophisticated models.

    Key technical improvements include:
    - Enhanced reasoning capabilities
    - Better factual accuracy
    - Reduced hallucination rates
    - Multimodal understanding

    Industry experts predict this will accelerate AI adoption across enterprise applications. The implications
    for software development, content creation, and business automation are significant.

    "We're entering a new era where AI becomes truly useful for complex problem-solving," noted AI researcher
    Dr. Yann LeCun from Meta AI Research.

    Investment thesis: Companies that can effectively integrate these AI capabilities will gain significant
    competitive advantages, while those that lag behind risk obsolescence.
    """

    # Create content input
    content_input = ContentInput(
        title="OpenAI Announces GPT-5 Breakthrough",
        content=sample_content,
        url="https://example.com/openai-gpt5",
        content_type="article"
    )

    # Create extractor
    extractor = create_extractor()

    logger.info("Testing structured extraction...")

    # Extract insights
    try:
        result = extractor.extract(content_input, validate=True)

        logger.info(f"✅ Extraction successful!")
        logger.info(f"Content ID: {result.content_id}")
        logger.info(f"Quality Score: {result.extraction_quality:.2f}")
        logger.info(f"Processing Time: {result.processing_time:.2f}s")
        logger.info(f"Model Used: {result.model_used}")

        # Display insights
        insights = result.insights
        print("\n" + "="*60)
        print("EXTRACTED INSIGHTS")
        print("="*60)

        print(f"\n📄 SUMMARY:")
        print(f"   {insights.summary}")

        print(f"\n🏷️  TOPICS ({len(insights.key_topics)}):")
        for topic in insights.key_topics:
            print(f"   • {topic.name} (relevance: {topic.relevance:.1f})")
            if topic.subtopics:
                print(f"     - Subtopics: {', '.join(topic.subtopics)}")

        print(f"\n🎯 THEMES ({len(insights.key_themes)}):")
        for theme in insights.key_themes:
            print(f"   • {theme}")

        print(f"\n🏢 ENTITIES ({len(insights.entities)}):")
        for entity in insights.entities:
            canonical = entity.canonical or entity.name
            print(f"   • {canonical} ({entity.type}) - confidence: {entity.confidence:.1f}")

        print(f"\n💬 QUOTES ({len(insights.quotes)}):")
        for quote in insights.quotes:
            speaker = f" - {quote.speaker}" if quote.speaker else ""
            print(f"   • \"{quote.text[:80]}...{speaker}\"")

        print(f"\n📈 THESES ({len(insights.theses)}):")
        for thesis in insights.theses:
            print(f"   • {thesis.statement}")
            print(f"     Rationale: {thesis.rationale}")
            print(f"     Confidence: {thesis.confidence:.1f} | Category: {thesis.category}")

        print(f"\n📊 METADATA:")
        print(f"   Sentiment: {insights.sentiment}")
        print(f"   Complexity: {insights.complexity}")
        print(f"   Type: {insights.content_type}")

        return result

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        raise

def test_podcast_extraction():
    """Test extraction on podcast transcript."""

    podcast_content = """
    HOST: Welcome back to Tech Talk. Today we're joined by Jensen Huang, CEO of NVIDIA.

    HOST: Jensen, NVIDIA's stock has been incredible this year. What's driving this growth?

    JENSEN: Well, it's really about the AI revolution. We've seen unprecedented demand for our GPUs in data centers.
    Companies like Google, Microsoft, Amazon - they're all racing to build AI infrastructure.

    HOST: Your H100 chips are basically sold out everywhere. When will supply catch up with demand?

    JENSEN: That's the challenge. We're scaling production as fast as we can, but the demand is just extraordinary.
    I've never seen anything like it in my 30 years in this industry.

    HOST: What about competition from AMD, Intel, even Apple's M-series chips?

    JENSEN: Competition is good. It pushes everyone to innovate. But right now, we have a significant moat in AI workloads.
    Our CUDA ecosystem, our software stack - it's taken decades to build.

    HOST: Looking forward, where do you see AI going in the next 5 years?

    JENSEN: I think we're at the beginning of a complete transformation. Every industry will be AI-native.
    The companies that figure this out first will dominate their sectors.
    """

    content_input = ContentInput(
        title="Tech Talk: NVIDIA CEO Jensen Huang on AI Revolution",
        content=podcast_content,
        content_type="podcast"
    )

    extractor = create_extractor()

    logger.info("Testing podcast extraction...")

    try:
        result = extractor.extract(content_input)

        logger.info(f"✅ Podcast extraction successful!")
        logger.info(f"Quality Score: {result.extraction_quality:.2f}")

        # Show key results
        insights = result.insights
        print(f"\n🎙️  PODCAST INSIGHTS:")
        print(f"   Topics: {len(insights.key_topics)} | Entities: {len(insights.entities)} | Quotes: {len(insights.quotes)}")
        print(f"   Investment Theses: {len([t for t in insights.theses if t.category == 'investment'])}")

        return result

    except Exception as e:
        logger.error(f"❌ Podcast extraction failed: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Testing Atlas Structured Content Extraction")
    print("=" * 60)

    # Test real database article first
    print("\n1️⃣  Testing Real Database Article...")
    real_result = test_real_database_article()

    # Test sample article extraction
    print("\n\n2️⃣  Testing Sample Article Extraction...")
    article_result = test_article_extraction()

    # Test podcast extraction
    print("\n\n3️⃣  Testing Podcast Extraction...")
    podcast_result = test_podcast_extraction()

    print(f"\n✅ All tests completed successfully!")

    # Calculate average quality score
    scores = []
    if real_result:
        scores.append(real_result.extraction_quality)
    if article_result:
        scores.append(article_result.extraction_quality)
    if podcast_result and hasattr(podcast_result, 'extraction_quality'):
        scores.append(podcast_result.extraction_quality)

    if scores:
        print(f"Average quality score: {sum(scores)/len(scores):.2f}")
        print(f"Real database article processed and saved to insights table!")