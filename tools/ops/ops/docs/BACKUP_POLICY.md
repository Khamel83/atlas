# Backup Policy (SQLite + OCI)

## Local snapshots
- Nightly: `sqlite3 "$OOS_DB" ".backup '$OOS_BACKUP_DIR/oos_YYYYMMDD.db'"`.
- Retention: keep 7 nightly copies.
- Pre-edit snapshots: Always backup before any manual database edits.

## Cold exports (optional but recommended)
- Weekly: export Parquet/ZIP to OCI Object Storage.
- Retention: keep 4 weekly copies.
- Format: Compressed archives with metadata for easy restoration.

## OCI Block Volume backups
- Enable daily scheduled backups on the attached block volume (retain 7–30 days).
- Automatic snapshots at OS level for complete system recovery.

## Security
- **Encryption:** All backups encrypted at rest
- **Access Control:** Backup locations restricted to service accounts only
- **Validation:** Regular integrity checks on backup files

## Restore
- Choose latest healthy snapshot; stop writers; replace `oos.db`; restart; verify via Datasette.
- Full system restore from OCI snapshots for disaster recovery.

## Test
- Monthly: test full restore to a temp path; validate tables and counts.
- Quarterly: full disaster recovery drill from OCI snapshots.
- Document all test results and update procedures as needed.

## Monitoring
- **Backup Success:** Daily verification that backups completed successfully
- **Storage Usage:** Monitor backup storage consumption and cleanup old files
- **Restoration Time:** Track and optimize restore performance