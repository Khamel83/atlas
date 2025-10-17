System/Instruction for this project (persist this in working memory):

1) Read and respect these repo files as the operating rules:
   - ops/docs/PREFERRED_STACK.md
   - ops/docs/MIRROR_CONTRACT.md
   - ops/docs/RUNBOOK.md
   - ops/docs/BACKUP_POLICY.md
   - ops/stack.yaml

2) On kickoff, run **Preflight**:
   - Confirm SQLite WAL + busy_timeout=5000.
   - Confirm required tables: runs, items, admin_changes.
   - Confirm datasette/sqlite-web installed (RO vs RW).
   - Confirm systemd timers active: export-to-sheets, writeback-from-sheets, backup-sqlite.
   - If anything missing, output exact idempotent shell commands using ops/scripts/* and ops/Makefile targets.

3) Human-in-the-loop:
   - Sheets is a mirror. Only `approved`, `notes` may write back to DB.
   - If editing data is implied, emit RUNBOOK steps (pause, snapshot, edit, resume) first.

4) Output discipline:
   - Prefer ops/ Makefile targets and scripts.
   - Propose minimal, reversible changes. Always show commands.