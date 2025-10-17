#!/bin/bash
# Simple Diagnose - 5 lines instead of 781

echo "🔍 OOS Health Check"
python3 --version >/dev/null && echo "✅ Python" || echo "❌ Python missing"
git --version >/dev/null && echo "✅ Git" || echo "❌ Git missing"
[ -f ".claude/slash_commands.json" ] && echo "✅ Slash commands" || echo "❌ Slash commands missing"
[ -d "src" ] && echo "✅ OOS structure" || echo "❌ OOS structure missing"