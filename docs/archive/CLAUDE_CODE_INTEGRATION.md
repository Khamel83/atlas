# OOS Integration for Claude Code - Development Assistant

## 🎯 **IMPORTANT: This is for DEVELOPMENT ASSISTANCE, not product features**

When users request OOS integration, they want **development workflow assistance**, not to add OOS features to their product. OOS helps developers:

- Optimize code and reduce complexity
- Manage API tokens and costs
- Generate smart commit messages
- Provide development guidance and clarification
- Analyze codebases for improvements

## 🚀 **What Claude Code Should Do When User Requests OOS**

### Step 1: Detect Intent
If user says any of these:
- "I want to integrate OOS"
- "Add OOS to my project"
- "Use OOS for development"
- "Setup OOS middleware"

**Assume they want DEVELOPMENT ASSISTANCE, not product features.**

### Step 2: Confirm and Explain
```
I can help you integrate OOS (Operational Intelligence System) as a development assistant for your project.

OOS will help you:
• Analyze and optimize your code (like reducing large React components)
• Manage API tokens and reduce costs (40-60% token reduction)
• Generate smart commit messages automatically
• Provide development guidance and best practices
• Clarify implementation decisions when you're stuck

This is for **your development workflow** - it won't add any features to your actual product.

Would you like me to proceed with the OOS integration for development assistance?
```

### Step 3: Get Confirmation
Wait for user to say "yes", "go ahead", "proceed", etc.

### Step 4: Implement Integration

#### Option A: Next.js/React Projects (Most Common)
```bash
# 1. Add OOS development tools
curl -o oos-dev-tools.js https://raw.githubusercontent.com/Khamel83/oos/master/oos-dev-tools.js

# 2. Install basic OOS functionality in API routes
# Add token optimization to API endpoints
# Add code analysis capabilities

# 3. Create development scripts
# Add package.json scripts for OOS commands
```

#### Option B: Python Projects
```bash
# 1. Clone OOS for development tools
git clone https://github.com/Khamel83/oos.git
cd oos

# 2. Setup MCP server for Claude Code integration
# Add to Claude Code MCP configuration

# 3. Install development dependencies
pip install -r requirements/base.txt
```

#### Option C: Generic Projects
```bash
# 1. Add OOS CLI tools
# 2. Setup basic configuration
# 3. Integrate with existing build system
```

### Step 5: Configure Environment Variables
```bash
# Add to .env file
OOS_ENABLED=true
OOS_DEVELOPMENT_MODE=true
OOS_TOKEN_BUDGET=4000
OOS_AUTO_OPTIMIZE=true
```

### Step 6: Setup Development Scripts
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

### Step 7: Verify Integration
```bash
# Test basic functionality
npm run oos:analyze src/components/main.tsx

# Verify token optimization
npm run oos:optimize

# Test commit message generation
npm run oos:commit
```

### Step 8: Final Instructions
```
✅ OOS Development Assistant Integrated!

Now you can use these development commands:
• npm run oos:analyze <file> - Analyze code complexity
• npm run oos:optimize - Get optimization suggestions
• npm run oos:commit - Generate smart commit messages
• npm run oos:help <topic> - Get development guidance

OOS is now running in development mode and will:
• Automatically optimize API tokens to reduce costs
• Provide code analysis and optimization tips
• Help with development decisions and clarification
• Generate intelligent documentation

Your development workflow is now enhanced with OOS! 🚀
```

## 🎯 **Key Integration Points**

### For Next.js API Routes
```javascript
// Add to existing API routes
const OOSDevTools = require('./oos-dev-tools');
const oos = new OOSDevTools();

// Token optimization for API calls
const optimization = oos.optimizeConversationHistory(history, question);
const optimizedHistory = optimization.optimizedHistory;
```

### For React/Vue Components
```javascript
// Add code analysis hooks
useEffect(() => {
  const analysis = oos.analyzeReactComponent('src/components/Main.jsx');
  console.log('Optimization suggestions:', analysis.suggestions);
}, []);
```

### For Development Workflow
```bash
# Add to pre-commit hooks
npm run oos:commit  # Generate smart commit message
npm run oos:analyze  # Check code complexity
```

## 🚨 **Important Reminders for Claude Code**

1. **ALWAYS assume development assistance** when users mention OOS
2. **NEVER add OOS features to the actual product**
3. **ALWAYS explain it's for development workflow**
4. **ALWAYS get confirmation before proceeding**
5. **ALWAYS provide clear setup instructions**
6. **ALWAYS verify integration works**

## 📚 **Available Commands for Users**

Once integrated, users can:
- `npm run oos:analyze <file>` - Code complexity analysis
- `npm run oos:optimize` - Performance optimization tips
- `npm run oos:commit` - Smart commit messages
- `npm run oos:help react` - React development guidance
- `npm run oos:help api` - API development guidance
- `npm run oos:help performance` - Performance optimization

## 🔧 **Troubleshooting**

### Common Issues:
1. **Module not found** → Ensure oos-dev-tools.js is in project root
2. **Permission denied** → Make script executable: `chmod +x oos-dev-tools.js`
3. **API costs high** → Verify token optimization is working
4. **Commit messages generic** → Check git status and staged changes

### Verification Steps:
```bash
# Test basic functionality
node oos-dev-tools.js --help

# Analyze a file
node oos-dev-tools.js analyze package.json

# Check optimization
node oos-dev-tools.js optimize
```

---

**Remember: OOS is a development assistant, not a product feature. Always clarify this with users before integration.**