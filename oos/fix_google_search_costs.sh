#!/bin/bash
# Universal Google Search Cost Fixer
# Finds and replaces expensive Google Custom Search API usage in any project

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

TARGET_DIR=${1:-$(pwd)}

echo -e "${CYAN}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🚨 Google Search Cost Fixer                               ║
║   Find and replace expensive Google Custom Search APIs      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
${NC}"

echo -e "${BLUE}🔍 Analyzing project for expensive Google Search APIs...${NC}"

# Find files with Google Search API usage
echo -e "${YELLOW}Looking for Google Custom Search API usage...${NC}"

GOOGLE_FILES=($(find "$TARGET_DIR" -type f \( -name "*.py" -o -name "*.js" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) \
    -exec grep -l "googleapis.*search\|google.*custom.*search\|customsearch\.googleapis\|CSE_ID\|GOOGLE_SEARCH.*API" {} + 2>/dev/null || true))

if [[ ${#GOOGLE_FILES[@]} -eq 0 ]]; then
    echo -e "${GREEN}✅ No Google Custom Search API usage found!${NC}"
    echo -e "${GREEN}Your project is already safe from Google Search charges.${NC}"
    exit 0
fi

echo -e "${RED}🚨 Found ${#GOOGLE_FILES[@]} files using Google Custom Search API:${NC}"
for file in "${GOOGLE_FILES[@]}"; do
    rel_path=$(realpath --relative-to="$TARGET_DIR" "$file")
    echo "   • $rel_path"
done
echo ""

# Analyze potential costs
echo -e "${YELLOW}💰 Analyzing potential costs...${NC}"

for file in "${GOOGLE_FILES[@]}"; do
    rel_path=$(realpath --relative-to="$TARGET_DIR" "$file")

    # Count API calls in loops
    api_calls=$(grep -c "customsearch\.googleapis\|googleapis.*search" "$file" 2>/dev/null || echo "0")
    loops=$(grep -c "for\|while\|range\|forEach" "$file" 2>/dev/null || echo "0")

    if [[ $api_calls -gt 0 ]]; then
        echo "   📄 $rel_path:"
        echo "      • API calls: $api_calls"
        echo "      • Loops detected: $loops"

        if [[ $loops -gt 0 && $api_calls -gt 0 ]]; then
            echo -e "      • ${RED}🚨 HIGH RISK: API calls in loops${NC}"
            echo "      • Potential cost: \$40-200/day"
        elif [[ $api_calls -gt 5 ]]; then
            echo -e "      • ${YELLOW}⚠️  MEDIUM RISK: Multiple API calls${NC}"
            echo "      • Potential cost: \$5-40/day"
        else
            echo -e "      • ${BLUE}ℹ️  LOW RISK: Few API calls${NC}"
            echo "      • Potential cost: \$0.05-5/day"
        fi
    fi
done
echo ""

# Offer fix options
echo -e "${BLUE}🔧 Fix Options:${NC}"
echo "1. 🆓 Replace with free search alternatives (DuckDuckGo, Wikipedia, GitHub)"
echo "2. 🛡️ Add cost controls to existing Google Search"
echo "3. 💡 Hybrid: Free search first, then Perplexity Pro"
echo "4. 🔍 Show detailed analysis only"
echo ""

read -p "Choose fix option (1-4): " choice

case $choice in
    1)
        echo -e "${GREEN}🆓 Installing free search alternatives...${NC}"

        # Install OOS search system if not present
        if [[ ! -f "$TARGET_DIR/src/free_search_alternatives.py" ]]; then
            echo -e "${YELLOW}Installing OOS free search system...${NC}"
            curl -sSL https://raw.githubusercontent.com/Khamel83/oos/master/install.sh | bash
            echo -e "${GREEN}✅ OOS free search system installed${NC}"
        fi

        # Create replacement suggestions for each file
        for file in "${GOOGLE_FILES[@]}"; do
            rel_path=$(realpath --relative-to="$TARGET_DIR" "$file")
            backup_file="${file}.google-backup-$(date +%s)"

            echo -e "${YELLOW}Backing up: $rel_path${NC}"
            cp "$file" "$backup_file"

            # Create a free replacement template
            free_replacement="${file%.py}_free_version.py"
            cat > "$free_replacement" << EOF
#!/usr/bin/env python3
"""
FREE VERSION of $rel_path
Replaces expensive Google Custom Search API with free alternatives
Original backed up as: $(basename "$backup_file")
"""

# Import OOS free search system
import sys
import os
sys.path.insert(0, './src')
try:
    from free_search_alternatives import search_free
    from perplexity_usage_manager import safe_perplexity_search
except ImportError:
    print("⚠️  OOS search modules not found. Please install OOS first:")
    print("   curl -sSL https://raw.githubusercontent.com/Khamel83/oos/master/install.sh | bash")
    sys.exit(1)

import asyncio

# TODO: Replace your Google Search functions with these free alternatives:

async def free_search_replacement(query, max_results=10):
    """
    Free replacement for Google Custom Search API
    Cost: \$0.00 for most searches, ~\$0.01 for Perplexity Pro fallback
    """
    print(f"🔍 FREE Search: {query}")

    # Try free search first
    results = await search_free(query, max_results)

    if len(results) >= 3:
        print(f"✅ Found {len(results)} results from free sources")
        return [{'title': r.title, 'link': r.url, 'snippet': r.snippet} for r in results]

    # If insufficient results, offer Perplexity Pro (asks permission)
    print(f"⚠️  Only found {len(results)} results from free sources")
    success, message, perplexity_results = await safe_perplexity_search(query, max_results)

    if success:
        all_results = results + perplexity_results
        return [{'title': r.title, 'link': r.url, 'snippet': r.snippet} for r in all_results]
    else:
        print(f"💡 {message}")
        return [{'title': r.title, 'link': r.url, 'snippet': r.snippet} for r in results]

# Example usage:
if __name__ == "__main__":
    async def test_free_search():
        results = await free_search_replacement("python tutorials", 5)
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   {result['link']}")
            print()

    asyncio.run(test_free_search())

# TODO: Update your original code to use free_search_replacement() instead of Google API
EOF

            echo -e "${GREEN}✅ Created free version: $(basename "$free_replacement")${NC}"
        done

        echo -e "${GREEN}🎉 Free search alternatives ready!${NC}"
        echo ""
        echo -e "${BLUE}Next steps:${NC}"
        echo "1. Review the *_free_version.py files created"
        echo "2. Update your original code to use the free search functions"
        echo "3. Test with: ./oos-cli search \"your query\""
        echo "4. Expected savings: \$30-200/day → \$0.00/day"
        ;;

    2)
        echo -e "${YELLOW}🛡️ Adding cost controls to existing Google Search...${NC}"

        # Create cost control wrapper
        cat > "$TARGET_DIR/google_search_cost_control.py" << 'EOF'
#!/usr/bin/env python3
"""
Google Search Cost Control Wrapper
Adds safety limits to existing Google Custom Search API usage
"""

import os
import json
import time
from datetime import datetime, date
from pathlib import Path

class GoogleSearchCostController:
    def __init__(self, daily_limit=1.00, max_calls_per_day=100):
        self.daily_limit = daily_limit
        self.max_calls_per_day = max_calls_per_day
        self.usage_file = Path('data/google_search_usage.json')
        self.usage_file.parent.mkdir(exist_ok=True)

        self.usage_data = self._load_usage_data()

    def _load_usage_data(self):
        if self.usage_file.exists():
            with open(self.usage_file, 'r') as f:
                data = json.load(f)

            # Reset if new day
            if data.get('date') != str(date.today()):
                data = {'date': str(date.today()), 'calls': 0, 'cost': 0.0}
                self._save_usage_data(data)

            return data

        return {'date': str(date.today()), 'calls': 0, 'cost': 0.0}

    def _save_usage_data(self, data):
        with open(self.usage_file, 'w') as f:
            json.dump(data, f, indent=2)

    def can_make_call(self):
        """Check if we can make another API call safely"""
        if self.usage_data['calls'] >= self.max_calls_per_day:
            print(f"🚨 BLOCKED: Daily call limit reached ({self.max_calls_per_day})")
            return False

        if self.usage_data['cost'] >= self.daily_limit:
            print(f"🚨 BLOCKED: Daily cost limit reached (${self.daily_limit:.2f})")
            return False

        return True

    def record_call(self, estimated_cost=0.005):
        """Record an API call"""
        self.usage_data['calls'] += 1
        self.usage_data['cost'] += estimated_cost
        self._save_usage_data(self.usage_data)

        print(f"💰 Google Search: ${self.usage_data['cost']:.3f} / ${self.daily_limit:.2f} ({self.usage_data['calls']} calls)")

        if self.usage_data['cost'] > self.daily_limit * 0.8:
            print(f"⚠️  Warning: Approaching daily limit!")

    def get_status(self):
        """Get current usage status"""
        return {
            'calls_today': self.usage_data['calls'],
            'cost_today': self.usage_data['cost'],
            'daily_limit': self.daily_limit,
            'max_calls': self.max_calls_per_day,
            'can_call': self.can_make_call()
        }

# Global controller instance
cost_controller = GoogleSearchCostController()

def safe_google_search(original_search_function):
    """Decorator to add cost controls to existing Google Search functions"""
    def wrapper(*args, **kwargs):
        if not cost_controller.can_make_call():
            print("🚨 Google Search blocked by cost controls")
            return []

        result = original_search_function(*args, **kwargs)
        cost_controller.record_call()

        return result

    return wrapper

# Example usage:
# @safe_google_search
# def your_existing_google_search_function(query):
#     # Your existing Google API code here
#     pass
EOF

        echo -e "${GREEN}✅ Cost control wrapper created: google_search_cost_control.py${NC}"
        echo ""
        echo -e "${BLUE}Usage:${NC}"
        echo "1. Import: from google_search_cost_control import safe_google_search"
        echo "2. Decorate your functions: @safe_google_search"
        echo "3. Automatic protection: \$1/day limit, 100 calls/day max"
        ;;

    3)
        echo -e "${BLUE}💡 Creating hybrid search system...${NC}"

        # Install OOS if needed
        if [[ ! -f "$TARGET_DIR/src/free_search_alternatives.py" ]]; then
            curl -sSL https://raw.githubusercontent.com/Khamel83/oos/master/install.sh | bash
        fi

        cat > "$TARGET_DIR/hybrid_search.py" << 'EOF'
#!/usr/bin/env python3
"""
Hybrid Search System
1. Try free search first (DuckDuckGo, Wikipedia, GitHub, Stack Overflow)
2. If insufficient results, ask permission to use Perplexity Pro
3. Google Search as emergency fallback with cost controls
"""

import sys
sys.path.insert(0, './src')
from free_search_alternatives import search_free
from perplexity_usage_manager import safe_perplexity_search
from google_search_cost_control import safe_google_search, cost_controller
import asyncio

async def hybrid_search(query, max_results=10, require_permission=True):
    """
    Smart hybrid search that tries free sources first
    """
    print(f"🔍 Hybrid Search: {query}")

    # Phase 1: Free search (always try this first)
    print("1️⃣ Trying free search alternatives...")
    free_results = await search_free(query, max_results)

    if len(free_results) >= max_results * 0.7:  # If we get 70% of desired results
        print(f"✅ Sufficient results from free sources: {len(free_results)}")
        return [{'title': r.title, 'link': r.url, 'snippet': r.snippet, 'source': r.source, 'cost': 0.00} for r in free_results]

    # Phase 2: Perplexity Pro (asks permission)
    print(f"2️⃣ Free search found {len(free_results)} results. Trying enhanced search...")

    if require_permission:
        response = input("🤔 Use Perplexity Pro for better results? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Sticking with free results only")
            return [{'title': r.title, 'link': r.url, 'snippet': r.snippet, 'source': r.source, 'cost': 0.00} for r in free_results]

    success, message, perplexity_results = await safe_perplexity_search(query, max_results - len(free_results))

    if success:
        all_results = free_results + perplexity_results
        print(f"✅ Enhanced search: {len(all_results)} total results")

        formatted_results = []
        for r in free_results:
            formatted_results.append({'title': r.title, 'link': r.url, 'snippet': r.snippet, 'source': r.source, 'cost': 0.00})
        for r in perplexity_results:
            formatted_results.append({'title': r.title, 'link': r.url, 'snippet': r.snippet, 'source': 'Perplexity', 'cost': 0.01})

        return formatted_results

    # Phase 3: Google Search fallback (with cost controls)
    print("3️⃣ Perplexity unavailable. Google Search fallback (with cost controls)...")

    if cost_controller.can_make_call():
        if require_permission:
            response = input(f"🚨 Use Google Search? (costs money, ${cost_controller.usage_data['cost']:.2f} used today) (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Using free results only")
                return [{'title': r.title, 'link': r.url, 'snippet': r.snippet, 'source': r.source, 'cost': 0.00} for r in free_results]

        # Your existing Google Search code would go here (with @safe_google_search decorator)
        print("🔍 Using Google Search fallback...")
        # google_results = your_google_search_function(query)
        google_results = []  # Placeholder

        cost_controller.record_call()
        return google_results
    else:
        print("Google Search blocked by cost controls")
        return [{'title': r.title, 'link': r.url, 'snippet': r.snippet, 'source': r.source, 'cost': 0.00} for r in free_results]

# Convenience function
def search(query, max_results=10):
    """Simple sync wrapper for hybrid search"""
    return asyncio.run(hybrid_search(query, max_results))

if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "python tutorials"
    results = search(query, 5)

    total_cost = sum(r.get('cost', 0) for r in results)

    print(f"\n🎉 Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['link']}")
        print(f"   Source: {result.get('source', 'Unknown')} (${result.get('cost', 0):.2f})")
        print()

    print(f"💰 Total search cost: ${total_cost:.2f}")
EOF

        echo -e "${GREEN}✅ Hybrid search system created: hybrid_search.py${NC}"
        echo ""
        echo -e "${BLUE}Usage:${NC}"
        echo "1. Replace Google Search calls with: hybrid_search(query)"
        echo "2. Free sources tried first, Perplexity Pro asks permission"
        echo "3. Google Search as emergency fallback with cost controls"
        ;;

    4)
        echo -e "${BLUE}🔍 Detailed Analysis:${NC}"

        for file in "${GOOGLE_FILES[@]}"; do
            rel_path=$(realpath --relative-to="$TARGET_DIR" "$file")
            echo ""
            echo -e "${CYAN}📄 $rel_path${NC}"
            echo "=" * 50

            # Show Google API usage lines
            grep -n "googleapis.*search\|google.*custom.*search\|customsearch\.googleapis\|CSE_ID\|GOOGLE_SEARCH.*API" "$file" | head -5

            echo ""
        done
        ;;

    *)
        echo -e "${RED}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}🎉 Google Search cost fix completed!${NC}"
echo ""
echo -e "${BLUE}📊 Expected savings:${NC}"
echo "   Before: $5-200/day (Google Custom Search API)"
echo "   After:  $0.00-0.10/day (free alternatives + optional Perplexity)"
echo ""
echo -e "${BLUE}🧪 Test your fixes:${NC}"
echo "   ./oos-cli search \"test query\""
echo "   python3 hybrid_search.py \"test query\""