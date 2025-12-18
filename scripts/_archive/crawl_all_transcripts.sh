#!/bin/bash
# Bulk Transcript Crawler - Crawl all configured podcast transcript sites
#
# Usage:
#   ./scripts/crawl_all_transcripts.sh          # Crawl all sites
#   ./scripts/crawl_all_transcripts.sh --list   # List available sites
#   ./scripts/crawl_all_transcripts.sh --dry-run # Show what would be crawled

set -e
cd "$(dirname "$0")/.."

VENV_PYTHON="./venv/bin/python3"
CRAWLER_MODULE="modules.podcasts.resolvers.bulk_crawler"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "============================================================"
echo "  ATLAS BULK TRANSCRIPT CRAWLER"
echo "============================================================"
echo ""

# Handle flags
if [[ "$1" == "--list" || "$1" == "-l" ]]; then
    $VENV_PYTHON -m $CRAWLER_MODULE --list
    exit 0
fi

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    $VENV_PYTHON -m $CRAWLER_MODULE --help
    exit 0
fi

# Sites to crawl (in priority order)
# Already done: catatp.fm, conversationswithtyler.com
SITES_TO_CRAWL=(
    "lexfridman.com"
    "econtalk.org"
    "dwarkesh.com"
    "freakonomics.com"
    "tim.blog"
    "darknetdiaries.com"
    "hubermantranscripts.com"
    "preposterousuniverse.com"
    "macrovoices.com"
    "alieward.com"
    "hiddenbrain.org"
    "thisamericanlife.org"
)

if [[ "$1" == "--dry-run" ]]; then
    echo "DRY RUN - Would crawl these sites:"
    echo ""
    for site in "${SITES_TO_CRAWL[@]}"; do
        echo "  - $site"
    done
    echo ""
    echo "Already completed:"
    echo "  - catatp.fm (677 transcripts)"
    echo "  - conversationswithtyler.com (273 transcripts)"
    echo ""
    exit 0
fi

# Crawl each site
TOTAL_SAVED=0
FAILED_SITES=()

for site in "${SITES_TO_CRAWL[@]}"; do
    echo ""
    echo -e "${YELLOW}Starting: $site${NC}"
    echo "============================================================"

    if $VENV_PYTHON -m $CRAWLER_MODULE "$site"; then
        echo -e "${GREEN}✓ Completed: $site${NC}"
    else
        echo -e "${RED}✗ Failed: $site${NC}"
        FAILED_SITES+=("$site")
    fi

    # Rate limit between sites
    echo "Waiting 5 seconds before next site..."
    sleep 5
done

echo ""
echo "============================================================"
echo "  CRAWL COMPLETE"
echo "============================================================"
echo ""

if [ ${#FAILED_SITES[@]} -gt 0 ]; then
    echo -e "${RED}Failed sites:${NC}"
    for site in "${FAILED_SITES[@]}"; do
        echo "  - $site"
    done
fi

echo ""
echo "Transcripts saved to: data/podcasts/*/transcripts/"
echo "Check each folder for the crawled content."
echo ""
