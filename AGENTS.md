# ONE_SHOT

**The $0 AI Build System.** Single curl. Skills included. Builds anything.

```bash
curl -sL https://raw.githubusercontent.com/Khamel83/oneshot/master/oneshot.sh | bash
```

Then tell Claude Code: **"utilize agents.md"**

---

## What This Is

A single curl that drops everything into your project:
- **AGENTS.md** - orchestration rules
- **22 skills** - predetermined workflows for Claude Code
- **SOPS config** - encrypted secrets (bring your own Age key)

Your AI agent reads it and knows how to:
- Ask the right questions upfront (5 min of your time)
- Generate a PRD you approve
- Build autonomously for hours while you walk away
- Resume from checkpoints across sessions

**Cost**: $0 infrastructure (homelab/OCI free tier) + ~$0.30/million tokens

## What This Isn't

- Not a framework to install
- Not a SaaS to sign up for
- Not a CLI tool to configure
- Just files your AI reads

---

## Prerequisites

**Age key** (one-time setup):
```bash
# Install age
sudo apt install age  # or: brew install age

# Generate key
mkdir -p ~/.age
age-keygen -o ~/.age/key.txt

# Save public key to 1Password (backup)
```

---

## After Installation

Your project now has:
```
project/
├── AGENTS.md              # Skeleton key orchestrator
├── .claude/skills/        # 22 skills for Claude Code
├── .sops.yaml             # Secrets encryption config
├── .env.example           # Secrets template
└── .gitignore             # Updated for secrets
```

**Reset anytime**: Say `(ONE_SHOT)` to re-anchor to first principles.

---

<!-- ONE_SHOT_CONTRACT v4.0 -->

## YAML CONFIG (Always Parsed by Agent)

```yaml
oneshot:
  version: 4.0

  prime_directive: |
    USER TIME IS PRECIOUS. AGENT COMPUTE IS CHEAP.
    Ask ALL questions UPFRONT. Get ALL info BEFORE coding.
    User walks away after: "PRD approved. Execute autonomous build."

  infrastructure:
    priority: ["homelab ($0)", "OCI free tier ($0)", "GitHub Actions ($0)"]
    oci_dev:
      ip: "100.126.13.70"
      limits: "4 OCPU, 24GB RAM, 200GB disk (Always Free ARM)"

  modes:
    micro: { trigger: "'micro mode' OR <100 lines", questions: [Q1, Q11] }
    tiny: { trigger: "Single CLI, no services" }
    normal: { trigger: "CLI or simple web/API" }
    heavy: { trigger: "Multi-service, AI agents" }

  hard_stops:
    - "Storage upgrade (files->SQLite->Postgres)"
    - "Auth method changes"
    - "Production deployment"
    action: "STOP -> Present -> Wait for approval"

  build_loop: |
    for each task in PRD:
      implement -> test -> commit -> update TODO.md

  required_files: [TODO.md, README.md, LLM-OVERVIEW.md, PRD.md]
```

---

## TRIAGE (First 30 Seconds)

| Intent | Signals | Skill |
|--------|---------|-------|
| **build_new** | "new project", "build me" | `oneshot-core` |
| **fix_existing** | "broken", "bug", "error" | `debugger` |
| **continue_work** | "resume", "checkpoint" | `oneshot-resume` |
| **add_feature** | "add feature", "extend" | `feature-planner` |
| **deploy** | "deploy", "push to cloud" | `push-to-cloud` |
| **stuck** | "looping", "confused" | `failure-recovery` |

---

## CORE QUESTIONS

| ID | Key | Required |
|----|-----|----------|
| **Q0** | Mode (micro/tiny/normal/heavy) | Yes |
| **Q1** | What are you building? | Yes |
| **Q2** | What problem does this solve? | Yes |
| **Q4** | Features (3-7 items) | Yes |
| **Q6** | Project type (CLI/Web/API) | Yes |
| **Q12** | Done criteria / v1 scope | Yes |

Full details in `oneshot-core` skill.

---

## AVAILABLE SKILLS (22)

**Core**: `oneshot-core`, `oneshot-resume`, `failure-recovery`

**Planning**: `project-initializer`, `feature-planner`, `api-designer`, `designer`

**Development**: `debugger`, `test-runner`, `code-reviewer`, `refactorer`, `database-migrator`, `performance-optimizer`

**Operations**: `git-workflow`, `ci-cd-setup`, `docker-composer`, `push-to-cloud`, `dependency-manager`

**Docs & Secrets**: `documentation-generator`, `secrets-vault-manager`

**Meta**: `skill-creator`, `marketplace-browser`

---

## QUICK REFERENCES

### Storage Progression
| Tier | When | Upgrade Trigger |
|------|------|-----------------|
| Files | Default | Need querying |
| SQLite | Most projects | Multi-user |
| PostgreSQL | Only when needed | Explicit approval |

### Project Invariants
- `README.md` - one-line description, quick start
- `TODO.md` - task tracking (kanban)
- `LLM-OVERVIEW.md` - project context
- `PRD.md` - approved requirements
- `scripts/` - setup, start, stop, status
- `/health` endpoint (if service)

---

## SECRETS

```bash
# Decrypt from secrets-vault
sops -d ~/github/secrets-vault/secrets.env.encrypted > .env

# Create project secrets
cp .env.example .env
# Fill in values
sops -e .env > .env.encrypted && rm .env
```

---

## CORE ETHOS

- **$0 Infrastructure**: Homelab, OCI Free Tier, no lock-in
- **Simplicity First**: Files → SQLite → Postgres only when needed
- **Skills Over Scripts**: Predetermined workflows, not reinvention
- **User Time is Precious**: 5 min questions → autonomous build → done

---

**Version**: 4.0 | **Skills**: 22 | **Cost**: $0

Compatible: Claude Code, Cursor, Aider, Gemini CLI
