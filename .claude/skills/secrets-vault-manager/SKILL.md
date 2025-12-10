---
name: secrets-vault-manager
description: "Handle SOPS + Age secrets for ONE_SHOT projects. Manages encrypted secrets, decryption, and secret rotation. Use when user mentions 'secrets', 'API keys', 'environment variables', '.env', or 'SOPS'."
allowed-tools: Bash, Read, Write
---

# Secrets Vault Manager

You are an expert at managing secrets with SOPS + Age encryption.

## When To Use

- Project needs API keys / secrets
- User mentions "Set up secrets-vault"
- User asks to "Decrypt / refresh secrets"
- User wants to "Add a new secret"

## Philosophy

One Age key in 1Password → ALL secrets.

## Setup (One-Time)

```bash
# Install
sudo apt install age sops  # Ubuntu
brew install age sops      # Mac

# Generate key
mkdir -p ~/.age
age-keygen -o ~/.age/key.txt
# Save public key (age1...) to 1Password

# Clone vault
git clone git@github.com:Khamel83/secrets-vault.git ~/github/secrets-vault
```

## Create .sops.yaml

```yaml
creation_rules:
  - path_regex: .*\.encrypted$
    age: 'age1your_public_key_here'
```

## Daily Usage

```bash
# Decrypt to project
sops --decrypt ~/github/secrets-vault/secrets.env.encrypted > .env
source .env

# Update secrets
cd ~/github/secrets-vault
sops secrets.env.encrypted
# Edit, save, auto-encrypted
git add . && git commit -m "Update secrets" && git push
```

## Common Operations

### Decrypt for Local Use

```bash
sops --decrypt ~/github/secrets-vault/secrets.env.encrypted > .env
```

Verify `.env` is gitignored!

### Add New Secret

```bash
cd ~/github/secrets-vault
sops secrets.env.encrypted
# Add: NEW_SECRET=value
# Save and exit
git add . && git commit -m "Add NEW_SECRET" && git push
```

### Refresh Secrets

```bash
sops --decrypt ~/github/secrets-vault/secrets.env.encrypted > .env
```

### Per-Project SOPS (Alternative)

If not using central vault:

```bash
mkdir -p .sops
age-keygen -o .sops/key.txt

cat > .sops.yaml << 'EOF'
creation_rules:
  - path_regex: \.encrypted$
    age: 'age1your_key'
EOF

sops secrets.env.encrypted
sops --decrypt secrets.env.encrypted > .env
```

## .gitignore Template

```gitignore
# Secrets (NEVER commit)
.env
.env.local
secrets.env
*.key
key.txt
.age/

# Allow examples
!.env.example

# SOPS encrypted ARE safe
!*.encrypted
```

## Document in README

Add to project README:

```markdown
## Secrets

This project uses SOPS + Age for secrets management.

\`\`\`bash
# Decrypt secrets (requires Age key)
sops --decrypt ~/github/secrets-vault/secrets.env.encrypted > .env
source .env
\`\`\`
```

## Outputs

- `.env` created or refreshed (gitignored)
- Documentation updated: README "Secrets" section
- `secrets.env.encrypted` updated in vault when adding new secrets

## Anti-Patterns

- Ever committing `.env` or raw secrets
- Decrypting into tracked files
- Sharing Age private key outside 1Password
- Storing secrets in code or comments

## Keywords

secrets, API keys, environment variables, .env, SOPS, Age, encrypt, decrypt, vault
