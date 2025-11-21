# Preferred Stack (OOS, free-first)

**Goals:** free, simple, local-first, auditable, human-in-the-loop.

## Data
- **SoT:** SQLite (WAL). No routine human edits.
- **Mirrors:** Google Sheets tabs: `Pending_Approvals`, `Runs`, `Errors_Hotlist`, `KPIs`.
- **Search:** SQLite FTS5 now; swap later if needed.
- **Blobs:** `$OOS_DATA_ROOT` on VM block volume. Optional weekly cold export to OCI Object Storage.

## Ops
- **Scheduler:** systemd timers (hourly exports/writebacks; nightly backups).
- **Observability:** JSONL logs + logrotate; daily heartbeat (Uptime-Kuma/Telegram).
- **Read UI:** Datasette (`--immutable`).
- **Write UI (rare):** sqlite-web via SSH/Tailscale (localhost bind).

## Security
- **Network:** Services bind to 127.0.0.1 only; access via SSH tunnels or Tailscale.
- **Auth:** SSH key authentication only; no passwords in URLs.
- **Secrets:** sops + age encryption for .env files; commit .env.template only.
- **Disk:** Full-disk encryption enabled at OS install (recommended).

## Human Loop
- Sheets is **not** SoT. Allowed inbound fields: `approved`, `notes`.
- Sync: DB→Sheets hourly (curated views); Sheets→DB hourly (whitelist).
- Conflict: DB wins except whitelisted fields.

## Safety
- Pause workers before schema/data edits.
- Snapshot before edits.
- Single editor at a time.
- `admin_changes` table for audit.

## Reliability
- SQLite settings: WAL mode, busy_timeout=5000.
- Weekly VACUUM + ANALYZE operations.
- Nightly backups (7-day retention) + weekly cold exports.
- Quarterly restore drills.

## Scale-up triggers
- >2 concurrent writers, remote collaborators, or external API clients → migrate SoT to Postgres (keep same mirror pattern).