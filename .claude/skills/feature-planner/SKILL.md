---
name: feature-planner
description: "Turn feature requests into concrete, ordered implementation plans. Breaks down features into tasks with dependencies. Use when user says 'plan feature', 'break this down', 'create a plan for', or 'how should I implement'."
allowed-tools: Read, Write, Glob
---

# Feature Planner

You are an expert at breaking down features into actionable implementation plans.

## When To Use

- User says "Plan this feature", "Break this down"
- User says "Can you create a plan for X?"
- TRIAGE intent = modify_existing or build_new with specific feature
- Scope = small, medium, or large (not micro)

## Inputs

- Natural language feature request from user
- Existing: `PRD.md`, `LLM-OVERVIEW.md`, relevant code in `src/`

## Outputs

- Markdown feature plan in either:
  - `docs/features/[feature-name].md`, or
  - `## Feature Plan: [Feature Name]` section in `PRD.md`
- Contains: Overview, components, ordered tasks, dependencies, risks, tests, success criteria

## Workflow

### 1. Parse Request

Extract:
- User persona
- Problem being solved
- Expected behavior
- Constraints

### 2. Check PRD

Confirm feature fits existing scope. If it expands scope materially, update PRD first.

### 3. Decompose Feature

**Components**: API, storage, UI, background jobs, etc.
**Tasks**: Break down into 0.5-2 hour chunks.

### 4. Order by Dependencies

```
Data model → Storage → Core logic → Interface → Tests → Docs
```

### 5. Risk + Testing

- Identify risks (security, data migration)
- Define test strategy

### 6. Write Plan

Use the template below.

## Output Template

```markdown
# Feature Plan: [Feature Name]

## Overview
[What this feature does and why]

## Components
1. [Component 1]
2. [Component 2]

## Tasks (ordered)
- [ ] Task 1 (prerequisite for 2, 3) ~1h
- [ ] Task 2 (depends on 1) ~2h
- [ ] Task 3 (depends on 1) ~1h

## Dependencies
- External: [APIs, libraries]
- Internal: [Other features, services]

## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk 1] | [High/Medium/Low] | [How to handle] |

## Testing Strategy
- Unit tests for [X]
- Integration tests for [Y]
- Manual testing for [Z]

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

## Data-First Order

Always follow this implementation order:
1. Define data models
2. Define storage schema
3. Implement storage layer (CRUD)
4. Build processing logic
5. Create interface (CLI/API/UI)
6. Write tests
7. Update docs

## Anti-Patterns

- Turning planning into implementation (plan first, then implement)
- Skipping PRD update when feature crosses boundaries (e.g., adding auth)
- Tasks that are too large (>2 hours)
- Tasks with unclear completion criteria

## Keywords

plan feature, break down, create plan, implement, design, architect, tasks
