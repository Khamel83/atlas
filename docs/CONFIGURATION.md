# Atlas Configuration Guide

**Last Updated**: 2025-12-04

## Environment Variables

Copy `.env.template` to `.env` and configure:

### Required
- `GMAIL_USERNAME` - Gmail account for email ingestion
- `GMAIL_APP_PASSWORD` - Gmail app password (from [Google](https://myaccount.google.com/apppasswords))
- `DATABASE_PATH` - SQLite database path (default: `data/atlas_vos.db`)
- `ATLAS_API_KEY` - API authentication key (change from default!)

### Optional
- `LOG_LEVEL` - Logging level (default: `info`)
- `PROCESSOR_SLEEP_SECONDS` - Loop delay (default: `60`)
- `ATLAS_API_PORT` - API port (default: `7444`)

## YAML Configuration Files

- `config/feeds.yaml` - RSS feed definitions
- `config/categories.yaml` - Content categorization
- `config/podcast_sources.json` - Transcript source mappings

## Security

**Generate secure API key**:
```bash
openssl rand -hex 32
```

**Never commit `.env` to git** - it contains secrets.

## SOPS Secrets Management (Teams)

For encrypted secrets management:

```bash
# Clone secrets vault
git clone git@github.com:YOUR_ORG/secrets-vault.git ~/github/secrets-vault

# Decrypt secrets
sops --decrypt ~/github/secrets-vault/secrets.env.encrypted > .env
```

See `.env.template` for details.

---

See `docs/SETUP.md` for initial setup.
