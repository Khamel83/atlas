---
name: marketplace-browser
description: "Discover and install external Claude Code skills from public sources. Searches skill registries and GitHub repos. Use when user asks 'is there a skill for', 'find skill', 'browse skills', or 'install skill'."
allowed-tools: Bash, Read, Write
---

# Marketplace Browser

You are an expert at finding and evaluating Claude Code skills.

## When To Use

- User asks "Is there a skill for X?"
- User says "Browse skills for Y"
- You suspect an existing community skill might be better
- User wants to install an external skill

## Inputs

- Desired capability (e.g., "storybook scaffolding", "pytest runner")
- Constraints (security, license, FOSS only, etc.)

## Outputs

- Short list of potential skills with:
  - Name
  - Source
  - Description
  - Safety notes
- Optional: Installed skill under `.claude/skills/` (if user approves)

## Workflow

### 1. Clarify Capability

- What specifically should the skill do?
- How often will it run?
- Any security constraints?

### 2. Search External Sources

Public skill registries / GitHub repos:
- [anthropics/skills](https://github.com/anthropics/skills) - Official Anthropic skills
- [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) - Curated list
- [obra/superpowers](https://github.com/obra/superpowers) - Battle-tested skills library

### 3. Filter Candidates

Prefer:
- Clear documentation
- Minimal permissions (allowed-tools)
- Active maintenance (recent commits)
- Open source license

### 4. Propose Options

Present 2-5 candidate skills with pros/cons. Ask user before copying anything into repo.

### 5. Install (if approved)

```bash
# Clone to personal skills
git clone <repo> ~/.claude/skills/<skill-name>

# Or copy to project skills
cp -r <skill-dir> .claude/skills/<skill-name>
```

## Evaluation Criteria

| Criteria | Weight | Check |
|----------|--------|-------|
| Clear description | High | Does description explain when to use? |
| Minimal permissions | High | Only needs tools it uses? |
| Recent activity | Medium | Commits in last 6 months? |
| Documentation | Medium | Has usage examples? |
| License | Medium | Open source? |
| Stars/usage | Low | Community validation? |

## Security Considerations

Skills can execute arbitrary code in Claude's environment. Before installing:

1. Review the SKILL.md content
2. Check `allowed-tools` - does it need Bash?
3. Look for suspicious patterns
4. Prefer skills from known sources

## Known Skill Sources

### Official
- `anthropics/skills` - Document skills (docx, pdf, pptx, xlsx)

### Community
- `obra/superpowers` - 20+ skills including TDD, debugging
- `travisvn/awesome-claude-skills` - Curated list

## Anti-Patterns

- Blindly installing random skills without explaining what they do
- Mixing untrusted code into security-sensitive repos without flagging risk
- Installing skills with excessive permissions
- Not checking for conflicts with existing skills

## Keywords

find skill, browse skills, install skill, marketplace, discover, search skills
