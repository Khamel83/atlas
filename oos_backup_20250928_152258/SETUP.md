# OOS Setup for Claude Code

## 🎯 **When user asks for OOS:**

```bash
# User says any of these:
"integrate OOS"
"add OOS to project"
"setup OOS for development"
"use OOS middleware"

# Claude Code responds:
I can help you integrate OOS (Operational Intelligence System) for development assistance.

OOS will help you:
• Optimize code and reduce complexity
• Save 40-60% on API token costs
• Generate smart commit messages
• Provide development guidance

This is for YOUR development workflow - not product features.

Should I proceed? [WAIT FOR YES]

# If yes, do these 3 steps:
1. Download tools: curl -o oos-dev-tools.js https://raw.githubusercontent.com/Khamel83/oos/master/oos-dev-tools.js
2. Add package.json scripts (oos:analyze, oos:optimize, oos:commit, oos:help)
3. Add token optimization to API routes
4. Test with: npm run oos:analyze src/pages/index.tsx

# Final message:
✅ OOS Development Assistant ready! Use npm run oos:analyze <file> to start.
```

## 🚨 **CRITICAL: This is DEVELOPMENT ASSISTANCE, not product features**

OOS helps developers build better code. It does NOT add features to the user's product.