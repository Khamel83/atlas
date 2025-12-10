---
name: oneshot-resume
description: "Resume ONE_SHOT sessions from checkpoints. Handles TODO.md loading, session handoffs, and context recovery. Use when user says 'resume', 'continue', 'pick up where we left off', or 'checkpoint'."
allowed-tools: Read, Write, Glob
---

# ONE_SHOT Resume

You are resuming a ONE_SHOT build session from a checkpoint.

## When To Use

- User says "continue", "resume", "pick up where we left off"
- User says "what's the status?" or "where were we?"
- TRIAGE intent = continue_work
- Session restart after context window exhaustion

## Resume Protocol

**Agent MUST**:
1. Read `TODO.md`
2. Read `LLM-OVERVIEW.md`
3. Read `PRD.md`
4. Summarize state to user
5. Confirm next action before proceeding

## Resume Output Format

```markdown
## Session Resume

**Project**: [name]
**Last updated**: [date from TODO.md header]

**Done** (from Done ✓ section):
- [x] Task 1
- [x] Task 2

**In Progress** (from In Progress section):
- [ ] Task 3 (status from sub-tasks)

**Next Action**: First item from In Progress, or first Backlog item if none in progress

Ready to continue?
```

## TODO.md Format

Based on [todomd/todo.md](https://github.com/todomd/todo.md):

```markdown
# TODO - project-name

> Project tasks. Updated: YYYY-MM-DD

### Backlog
- [ ] Task description ~estimate #tag @assignee

### In Progress
- [ ] Current task ~2h #feature

### Done ✓
- [x] Completed task 2024-12-09
```

**Metadata syntax** (optional, at end of line):
- `~3d` or `~2h` - time estimate
- `#tag` - category/type
- `@name` - assignee
- `YYYY-MM-DD` - due date or completion date

## When to Update TODO.md

- After completing any task → move to Done ✓
- When starting a task → move to In Progress
- Before context window reaches 70%
- When switching phases
- At end of any session

**CRITICAL**: Before ANY handoff or session end, agent MUST:
1. Update TODO.md to reflect current state
2. Ensure "In Progress" section shows actual current work
3. Move completed items to "Done ✓" with date

## Session Handoff Protocol

When ending session or switching contexts:

```markdown
## HANDOFF STATE
**Project**: [project-name]
**Timestamp**: [ISO timestamp]
**Agent**: [Claude Code / Cursor / etc.]

### Last Completed
- [Phase X, Task Y - description]

### Currently Blocked On (if any)
- [Issue]
- [What was tried]
- [Why it failed]

### Next Action (BE SPECIFIC)
1. Open file: `[exact path]`
2. Find function: `[function name]`
3. Do: [exact change needed]

### Files Changed This Session
- `src/storage.py` - Added CRUD operations

### Decisions Made This Session
- Chose X over Y because Z

### Context the Next Agent Needs
- [Important detail 1]
- [Important detail 2]
```

## Handoff Triggers

Generate handoff when:
- User says "handoff", "switch agent", "take a break"
- Context window exceeds 80%
- Agent is looping or stuck
- Before any session end

## Receiving a Handoff

**Agent MUST**:
1. Read handoff document
2. Read `LLM-OVERVIEW.md`
3. Read PRD
4. Verify "Next Action" is still valid
5. Confirm understanding before proceeding

## Context Window Exhaustion Recovery

```yaml
prevention:
  - "Use TODO.md for state"
  - "Keep LLM-OVERVIEW.md updated"
  - "Don't paste entire files"

recovery:
  1_handoff: "Generate HANDOFF STATE document"
  2_new_session: |
    New session. Read in order:
    1. LLM-OVERVIEW.md
    2. TODO.md
    3. [handoff document]
    Confirm understanding.
```

## Anti-Patterns

- Starting work without reading TODO.md
- Not updating TODO.md at session end
- Making multiple sessions of progress without checkpoint
- Ignoring existing In Progress items

## Keywords

resume, continue, checkpoint, pick up, status, handoff, where were we, session
