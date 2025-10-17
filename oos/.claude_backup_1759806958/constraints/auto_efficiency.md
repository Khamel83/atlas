# MANDATORY Auto-Efficiency Constraint

## IMMEDIATE PATTERN RECOGNITION - NO EXCEPTIONS

When user mentions ANY of these phrases, **IMMEDIATELY** run `/oos-update` without any discovery:

**Trigger Phrases:**
- "update oos"
- "update our oos"
- "sync oos"
- "get latest oos"
- "update from github"
- "pull latest changes"

## MANDATORY RESPONSE PATTERN:

```
User: "update oos from github"
Assistant: I'll use the efficient OOS update pattern to avoid the discovery waste from previous flows.

[RUNS /oos-update IMMEDIATELY]
```

## FORBIDDEN ACTIONS:
- ❌ ANY `git remote -v` checks
- ❌ ANY `ls -la` exploration
- ❌ ANY directory navigation discovery
- ❌ Asking user to clarify obvious requests
- ❌ Manual step-by-step process

## REQUIRED ACTIONS:
- ✅ **IMMEDIATELY** run `/oos-update` slash command
- ✅ Let the script handle ALL context detection
- ✅ Let the script handle ALL integration
- ✅ Tell user exactly what to do after completion

## LEARNING ENFORCEMENT:
This constraint PREVENTS repeating the 15+ command inefficiency from atlas update flow. The assistant MUST apply this learning automatically.

**CRITICAL:** If assistant starts doing discovery commands instead of `/oos-update`, it has FAILED to apply the learning.