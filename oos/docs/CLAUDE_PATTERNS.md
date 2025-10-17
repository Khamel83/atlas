# Claude Code Intelligence Patterns

## Auto-Detection Patterns for Efficient Responses

### Repository Update Requests

**Trigger Phrases:**
- "update oos"
- "sync oos"
- "get latest oos"
- "update from github"
- "pull latest changes"

**Auto-Response Pattern:**
When user mentions updating OOS in any form, immediately:

1. **Context Detection:**
   - Check if current directory has `oos/` subdirectory
   - Detect if we're in a parent project with OOS as dependency
   - Check git remotes to understand repository structure

2. **Intelligent Update:**
   - If OOS subdirectory exists: Navigate and smart update
   - If no OOS: Clone fresh from GitHub
   - Auto-backup existing if needed

3. **Auto-Integration:**
   - Run integration script automatically
   - Copy slash commands to parent `.claude/`
   - Make all OOS capabilities available

4. **Verification:**
   - Single status check
   - Confirm commands are available
   - Report success

**Example Implementation:**
```bash
# User says: "update our oos from github"
# Assistant automatically runs:
cd oos && git pull origin master && ./bin/integrate_to_parent.sh
# No discovery commands needed
```

### Anti-Pattern Prevention

**Never Do:**
- Multiple `git remote -v` checks
- Manual `ls` exploration
- Ask user to clarify obvious requests
- Require user to run specific commands

**Always Do:**
- Use intelligent defaults
- Handle integration automatically
- Provide single confirmation
- Apply learned efficiency patterns

### Learning Integration

When handling repository updates:
1. Check for `bin/archon_learning.sh` and use smart-update if available
2. Auto-run integration scripts without asking
3. Log the pattern for future learning
4. Optimize the response for next time

This makes OOS truly intelligent - it learns from inefficient patterns and prevents repeating them.