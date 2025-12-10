---
name: skill-creator
description: "Design and scaffold new Claude Code skills for recurring workflows. Creates properly structured SKILL.md files with YAML frontmatter. Use when user says 'create skill', 'new skill', 'make this a skill', or 'automate workflow'."
allowed-tools: Read, Write, Glob
---

# Skill Creator

You are an expert at creating reusable Claude Code skills.

## When To Use

- You identify a workflow you repeat across repos
- User says "Make this a reusable skill"
- User says "I keep doing X; make a skill for it"
- User wants to automate a recurring pattern

## Inputs

- Description of workflow
- One or two concrete examples

## Outputs

- New skill directory under `.claude/skills/<skill-name>/`:
  - `SKILL.md` with YAML frontmatter
  - Optional templates or helper files
  - Optional `references/` directory

## Workflow

### 1. Abstract Workflow

Identify:
- Invariants (always true)
- Inputs (what user provides)
- Outputs (what skill produces)
- Variable parts (customizable)

### 2. Define Clear Trigger

"When the user says..." or "When repository has pattern..."

The description field is CRITICAL for skill discovery.

### 3. Write SKILL.md

Use the canonical template below.

### 4. Self-Test

Run through the skill manually on a small example.

## SKILL.md Template

```yaml
---
name: skill-name
description: "Brief description of what this skill does. When to use it. Specific trigger phrases like 'X', 'Y', or 'Z'."
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Skill Name

You are an expert at [domain].

## When To Use

- Trigger condition 1
- Trigger condition 2
- User says "[phrase]"

## Inputs

- [What user/repo provides]

## Outputs

- [What skill produces]

## Workflow

1. Step 1
2. Step 2
3. Step 3

## Output Format

[Expected output format or template]

## Anti-Patterns

- What NOT to do
- Common mistakes

## Keywords

keyword1, keyword2, keyword3
```

## Best Practices

### Description Field (Critical for Discovery)

- Write in **third person** ("Processes files" not "I process files")
- Include **what it does AND when to use it**
- Be specific with trigger phrases
- Stay under 1024 characters

**Good:**
```
"Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when user mentions PDFs, forms, or document extraction."
```

**Bad:**
```
"Helps with documents"
```

### Content Organization

- SKILL.md body under 500 lines
- Use `references/` for detailed content
- Keep one capability per skill
- Use gerund form for naming (e.g., `processing-pdfs`)

### Naming Conventions

- Lowercase, alphanumeric, hyphens only
- Max 64 characters
- Avoid vague terms like "helper" or "utils"
- Avoid reserved words like "anthropic" or "claude"

## Directory Structure

```
my-skill/
├── SKILL.md           # Required
├── references/        # Optional - detailed docs
│   └── detailed.md
├── templates/         # Optional - output templates
│   └── template.md
└── scripts/           # Optional - helper scripts
    └── helper.py
```

## Anti-Patterns

- Skills that are too vague: "do useful things with git"
- Skills that bake in project-specific paths or constants
- Skills that do multiple unrelated things
- Over-explaining concepts Claude already knows
- Including all tools in `allowed-tools` (use minimum needed)

## Keywords

create skill, new skill, automate workflow, make skill, reusable, template
