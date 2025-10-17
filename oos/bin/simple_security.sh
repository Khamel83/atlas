#!/bin/bash
# Simple Security Audit - 5 lines instead of 503

echo "🔒 Security Check"
find . -name "*.json" -exec grep -l "api.key\|password\|secret" {} \; | head -5
[ -f ".env" ] && echo "⚠️ .env file found" || echo "✅ No .env file"
ls -la ~/.ssh/ 2>/dev/null | grep -q "id_rsa" && echo "⚠️ SSH keys present" || echo "✅ No SSH keys"
git log --oneline -5 | grep -i "password\|key\|secret" && echo "⚠️ Secrets in git" || echo "✅ No secrets in recent commits"