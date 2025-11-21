# Maintenance Runbook (Edit DB safely)

## Routine Ops
1) Keep workers running; use Datasette for read-only browsing.

## Direct Edit (rare)
1) Pause writers (stop ingest worker/cron).
2) Snapshot DB:
   - `cp "$OOS_DB" "$OOS_BACKUP_DIR/oos_$(date +%F_%H%M).db"`
3) Start editor (localhost only):
   - `sqlite_web "$OOS_DB" -H 127.0.0.1 -p 8080`
   - SSH tunnel from Mac: `ssh -N -L 8080:127.0.0.1:8080 ubuntu@<vm>`
   - Edit at http://localhost:8080
4) Record changes in `admin_changes` (who/what/why).
5) Stop editor, close tunnel.
6) Resume workers.

## Security Protocol
- **Network Access:** All services bind to 127.0.0.1 only
- **SSH Tunneling:** `ssh -L local_port:127.0.0.1:remote_port user@host`
- **Authentication:** SSH key auth only; no password authentication
- **Audit Trail:** All admin changes logged with actor, timestamp, reason

## Emergency Procedures
### Database Corruption
1. Stop all services immediately
2. Check integrity: `sqlite3 "$OOS_DB" "PRAGMA integrity_check;"`
3. If corrupted, restore from latest backup
4. Verify restoration, then resume services

### Service Outages
1. Check systemd status: `systemctl status oos-*`
2. Review logs: `journalctl -u service-name -n 50`
3. Restart if needed: `systemctl restart service-name`
4. Update monitoring after resolution

## Restore Drill (quarterly)
- Copy latest backup to temp path; run Datasette (`--immutable`) and verify views.
- Test complete restore process in isolated environment.
- Document any issues found and update procedures.