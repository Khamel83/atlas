---
name: dependency-manager
description: "Update, audit, and manage project dependencies. Handles security audits and version updates. Use when user says 'update deps', 'dependencies', 'outdated', 'security audit', or 'npm audit'."
allowed-tools: Bash, Read, Write
---

# Dependency Manager

You are an expert at managing project dependencies safely.

## When To Use

- User says "Update dependencies", "Security audit"
- User asks "Check for outdated packages"
- Dependabot/Renovate alerts
- Before major releases

## Inputs

- Package manifest (package.json, requirements.txt, Cargo.toml, etc.)
- Security requirements
- Update scope (patch/minor/major)

## Outputs

- Updated lock file
- Security audit report
- Breaking change notes

## Workflow

### 1. Check Current State

```bash
# Node
npm outdated
npm audit

# Python
pip list --outdated
pip-audit

# Rust
cargo outdated
cargo audit
```

### 2. Categorize Updates

| Type | Action |
|------|--------|
| Security fixes | Update immediately |
| Patch versions | Safe to update |
| Minor versions | Review changelog |
| Major versions | Requires migration plan |

### 3. Update Carefully

```bash
# Node - update one at a time
npm update <package>

# Python
pip install --upgrade <package>

# Rust
cargo update -p <package>
```

### 4. Test After Each Update

- Run test suite
- Check for deprecation warnings

### 5. Document

- Note major version changes in CHANGELOG
- Update compatibility notes

## Commands by Ecosystem

### Node (npm)

```bash
# Check outdated
npm outdated

# Security audit
npm audit

# Update all patch versions
npm update

# Update specific package
npm install <package>@latest

# Update to specific version
npm install <package>@1.2.3
```

### Python (pip)

```bash
# Check outdated
pip list --outdated

# Security audit
pip-audit

# Update package
pip install --upgrade <package>

# Update all
pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U
```

### Rust (cargo)

```bash
# Check outdated
cargo outdated

# Security audit
cargo audit

# Update
cargo update
```

## Security Audit Process

1. Run audit command
2. Review vulnerabilities by severity
3. Update affected packages
4. If no fix available:
   - Check if vulnerability applies to your usage
   - Consider alternatives
   - Document accepted risk

## Version Pinning Strategy

| Environment | Strategy |
|-------------|----------|
| App | Pin exact versions |
| Library | Use ranges (^, ~) |
| Dev deps | Can be more flexible |

```json
// package.json
{
  "dependencies": {
    "express": "4.18.2",      // Exact - production app
    "lodash": "^4.17.0"       // Range - library
  }
}
```

## Handling Major Updates

1. Read CHANGELOG/migration guide
2. Create branch
3. Update one major at a time
4. Run tests
5. Fix breaking changes
6. Document changes
7. PR review

## Anti-Patterns

- Updating all deps at once
- Ignoring security alerts
- Pinning to exact versions without reason
- Not reading changelogs for major updates
- Updating production without testing

## Keywords

dependencies, update deps, outdated, security audit, npm audit, pip, packages
