# 1Password setup

## Create the item
1. Open 1Password (Mac or Web).
2. Vault: **Private** (or choose another and adjust `OP_VAULT`).
3. New Item → **Secure Note** (or "Login" with custom field).
4. Add a **custom field** named **env** (type: **Text**).
5. Paste your KEY=VALUE lines (see `docs/ENV_TEMPLATE.md`).

> ✅ Each line must be exactly `KEY=value` (no trailing text).
> ❌ Do not paste shell errors like `: No such file or directory`.

## CLI sign-in (each shell)
```bash
eval "$(op signin)"
op whoami
op item get "bootstrap-env" --vault "Private" --fields env | head
```

## Sync into a project
```bash
op item get "bootstrap-env" --vault "Private" --fields env > .env
sed -i 's/\r$//' .env
```