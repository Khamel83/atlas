#!/bin/bash

# Navigate to your project root (e.g., Atlas)
cd "$(dirname "$0")"

echo "📁 Creating folder structure..."

mkdir -p \
  inputs \
  output/articles/html \
  output/articles/markdown \
  output/youtube/transcripts \
  output/youtube/videos \
  output/podcasts/audio \
  output/podcasts/transcripts \
  config \
  helpers

echo "✅ Folders created."

# ----------------------------
# 🧪 1. Add test article URLs
# ----------------------------
echo "https://arstechnica.com/information-technology/2024/12/the-rise-of-agentic-ai-systems/" > inputs/articles.txt
echo "https://blog.langchain.com/the-rise-of-context-engineering/" >> inputs/articles.txt

# ----------------------------
# 🧪 2. Add test YouTube video IDs
# ----------------------------
echo "dQw4w9WgXcQ" > inputs/youtube.txt  # Rickroll classic

# ----------------------------
# 🧪 3. Add test OPML file for podcasts
# ----------------------------
cat <<EOF > inputs/podcasts.opml
<opml version="1.0">
  <head>
    <title>Test Podcast Subscriptions</title>
  </head>
  <body>
    <outline text="Planet Money" title="Planet Money" type="rss" xmlUrl="https://www.npr.org/rss/podcast.php?id=510289"/>
  </body>
</opml>
EOF

# ----------------------------
# 🧪 4. Add sample .env config
# ----------------------------
cat <<EOF > config/.env
# OpenRouter
OPENROUTER_API_KEY=sk-fake-openrouter-key
MODEL=google/gemini-2.0-flash-lite-001

# YouTube
YOUTUBE_API_KEY=fake_youtube_api_key

# Podcast Ingestion
OVERCAST_OPML_PATH=$(pwd)/inputs/podcasts.opml

# Optional (for Google Takeout automation)
GOOGLE_DRIVE_FOLDER_ID=fake_drive_id
EOF

echo "🧪 Test data and .env file written."

echo "✅ All set. Now run one of the fetchers to validate:"
echo "   python helpers/article_fetcher.py"
echo "   python helpers/youtube_ingestor.py"
echo "   python helpers/podcast_ingestor.py"
