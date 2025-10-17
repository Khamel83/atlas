#!/bin/bash
# Quick Atlas Production Continuation

cd /home/ubuntu/dev/atlas
source atlas_venv/bin/activate

echo "🚀 Atlas Quick Production Continuation"
echo "======================================"

# Show current status
echo "📊 Current Status:"
ARTICLES=$(ls output/articles/markdown/ 2>/dev/null | wc -l)
echo "📄 Articles processed: $ARTICLES"

FAILED=$(wc -l < retries/queue.jsonl 2>/dev/null || echo "unknown")
echo "❌ Failed articles remaining: $FAILED"

echo ""
echo "🎯 Choose what to start:"
echo "1) Start web dashboard"
echo "2) Continue AI recovery"
echo "3) Run cognitive processing"
echo "4) Start all (dashboard + recovery + cognitive)"
echo "5) Just show status and exit"
echo ""

read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo "🌐 Starting web dashboard..."
        cd web
        nohup uvicorn app:app --host 0.0.0.0 --port 8000 --reload > ../dashboard.log 2>&1 &
        DASH_PID=$!
        echo "✅ Dashboard started (PID: $DASH_PID)"
        echo "🌐 Access at: http://localhost:8000"
        echo "📋 Monitor: tail -f dashboard.log"
        ;;
    2)
        echo "🤖 Starting AI recovery..."
        nohup python retry_failed_articles.py --use-skyvern > recovery_continue.log 2>&1 &
        RECOVERY_PID=$!
        echo "✅ AI recovery started (PID: $RECOVERY_PID)"
        echo "📋 Monitor: tail -f recovery_continue.log"
        ;;
    3)
        echo "🧠 Running cognitive processing batch..."
        python -c "
from cognitive_engine import CognitiveEngine
import glob, json, os
from datetime import datetime

engine = CognitiveEngine()
articles = glob.glob('output/articles/markdown/*.md')[:100]
print(f'Processing {len(articles)} articles...')

results = []
for i, article in enumerate(articles, 1):
    if i % 10 == 0:
        print(f'  [{i}/{len(articles)}] Processing...')
    try:
        analysis = engine.analyze_article(article)
        if analysis:
            results.append({
                'file': os.path.basename(article),
                'word_count': analysis.get('word_count', 0),
                'insights_count': len(analysis.get('insights', {}).get('insights', [])),
                'connections_count': len(analysis.get('connections', []))
            })
    except Exception as e:
        print(f'Error: {e}')

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
with open(f'cognitive_results_{timestamp}.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f'✅ Processed {len(results)} articles')
print(f'📊 Results saved to cognitive_results_{timestamp}.json')
"
        ;;
    4)
        echo "🚀 Starting full production..."

        echo "🌐 Starting dashboard..."
        cd web
        nohup uvicorn app:app --host 0.0.0.0 --port 8000 --reload > ../dashboard_full.log 2>&1 &
        DASH_PID=$!
        echo "✅ Dashboard started (PID: $DASH_PID)"

        cd ..
        echo "🤖 Starting AI recovery..."
        nohup python retry_failed_articles.py --use-skyvern > recovery_full.log 2>&1 &
        RECOVERY_PID=$!
        echo "✅ AI recovery started (PID: $RECOVERY_PID)"

        echo "🧠 Running cognitive processing..."
        nohup python -c "
from cognitive_engine import CognitiveEngine
import glob, json, os
from datetime import datetime

engine = CognitiveEngine()
articles = glob.glob('output/articles/markdown/*.md')[:200]
print(f'Processing {len(articles)} articles...')

results = []
for i, article in enumerate(articles, 1):
    if i % 20 == 0:
        print(f'  [{i}/{len(articles)}] Processing...')
    try:
        analysis = engine.analyze_article(article)
        if analysis:
            results.append({
                'file': os.path.basename(article),
                'word_count': analysis.get('word_count', 0),
                'insights_count': len(analysis.get('insights', {}).get('insights', [])),
                'connections_count': len(analysis.get('connections', []))
            })
    except Exception as e:
        pass

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
with open(f'cognitive_batch_{timestamp}.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f'✅ Processed {len(results)} articles')
print(f'📊 Results saved to cognitive_batch_{timestamp}.json')
" > cognitive_full.log 2>&1 &
        COGNITIVE_PID=$!
        echo "✅ Cognitive processing started (PID: $COGNITIVE_PID)"

        echo ""
        echo "🎉 Full production mode active!"
        echo "🌐 Dashboard: http://localhost:8000"
        echo "📋 Monitor with:"
        echo "   tail -f dashboard_full.log"
        echo "   tail -f recovery_full.log"
        echo "   tail -f cognitive_full.log"
        echo ""
        echo "PIDs: Dashboard=$DASH_PID, Recovery=$RECOVERY_PID, Cognitive=$COGNITIVE_PID"
        ;;
    5)
        echo "📊 Status only - nothing started"
        echo "✅ Ready for production continuation"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Done! Atlas production continuation complete."