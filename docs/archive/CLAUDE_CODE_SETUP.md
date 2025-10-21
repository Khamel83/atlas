# OOS for Claude Code - Simple Setup

## 🎯 **When users ask for OOS, they want DEVELOPMENT HELP**

**Common user requests:**
- "Integrate OOS"
- "Add OOS to my project"
- "Setup OOS for development"
- "Use OOS middleware"

**Claude Code should respond:**

```
I can help you integrate OOS (Operational Intelligence System) to assist with your development workflow.

OOS will help you:
• Optimize your code and reduce complexity
• Save money on API costs (40-60% token reduction)
• Generate smart commit messages
• Provide development guidance when you're stuck

This is for YOUR development workflow - it won't add features to your actual product.

Should I proceed with setting up OOS for development assistance?
```

**If user says yes, proceed with these steps:**

## 🚀 **Simple 3-Step Setup**

### Step 1: Download OOS Dev Tools
```bash
curl -o oos-dev-tools.js https://raw.githubusercontent.com/Khamel83/oos/master/oos-dev-tools.js
chmod +x oos-dev-tools.js
```

### Step 2: Add to Package.json Scripts
```json
{
  "scripts": {
    "oos:analyze": "node oos-dev-tools.js analyze",
    "oos:optimize": "node oos-dev-tools.js optimize",
    "oos:commit": "node oos-dev-tools.js commit",
    "oos:help": "node oos-dev-tools.js help"
  }
}
```

### Step 3: Add Token Optimization to API Routes
```javascript
// Add to your main API route (like pages/api/ask.ts)
const OOSDevTools = require('./oos-dev-tools');
const oos = new OOSDevTools();

// Optimize conversation history
const optimization = oos.optimizeConversationHistory(conversationHistory, question);
const optimizedHistory = optimization.optimizedHistory;
```

### Step 4: Test It Works
```bash
# Test the tools
npm run oos:analyze src/pages/index.tsx
npm run oos:optimize
```

## 🎉 **Final Message**

```
✅ OOS Development Assistant Integrated!

Now you can use:
• npm run oos:analyze <file> - Code complexity analysis
• npm run oos:optimize - Performance optimization tips
• npm run oos:commit - Smart commit messages
• npm run oos:help <topic> - Development guidance

OOS is now optimizing your API tokens and ready to help with development! 🚀
```

---

**IMPORTANT:** OOS is for development assistance, NOT product features. Always clarify this with users.