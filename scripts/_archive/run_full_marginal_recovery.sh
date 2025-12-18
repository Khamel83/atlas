#!/bin/bash
# Full Marginal Recovery Pipeline
# Run with: nohup ./scripts/run_full_marginal_recovery.sh > /tmp/full_recovery.log 2>&1 &

set -e
cd /home/khamel83/github/atlas

LOG="/tmp/full_recovery.log"
VENV="./venv/bin/python"

echo "========================================"
echo "FULL MARGINAL RECOVERY PIPELINE"
echo "Started: $(date)"
echo "========================================"

# Step 1: Tier 1 - High priority articles (content/article, clean/article, stratechery)
echo ""
echo "[STEP 1/4] Running Tier 1 recovery (high priority articles)..."
echo "Estimated time: ~25 minutes for 289 files"
$VENV scripts/recover_marginal_tiered.py --tier 1

# Step 2: Tier 2 - Major news sites (washingtonpost, nytimes, bloomberg, etc.)
echo ""
echo "[STEP 2/4] Running Tier 2 recovery (major news sites)..."
$VENV scripts/recover_marginal_tiered.py --tier 2

# Step 3: Re-verify everything with updated content
echo ""
echo "[STEP 3/4] Re-verifying all content..."
$VENV scripts/verify_content.py --report

# Step 4: Generate final summary
echo ""
echo "[STEP 4/4] Generating final report..."
echo ""
echo "========================================"
echo "FINAL RECOVERY SUMMARY"
echo "========================================"

# Get stats from recovery DB
echo ""
echo "Recovery Database Stats:"
sqlite3 data/quality/marginal_recovery.db "
SELECT
  'Tier ' || tier as tier,
  status,
  COUNT(*) as count
FROM marginal_recovery
GROUP BY tier, status
ORDER BY tier, status
"

# Get final verification stats
echo ""
echo "Final Verification Stats:"
sqlite3 data/quality/verification.db "
SELECT quality, COUNT(*) as count
FROM verifications
GROUP BY quality
"

echo ""
echo "========================================"
echo "COMPLETED: $(date)"
echo "========================================"
echo ""
echo "Full report saved to: data/reports/quality_$(date +%Y-%m-%d).md"
