# Mirror Contract (Sheets ↔ DB)

## Tabs & Columns
### Pending_Approvals (bi-directional: whitelist only)
- item_id (ro), source (ro), title (ro), reason (ro), proposed_action (ro)
- approved (rw: BOOLEAN), notes (rw: TEXT), approved_by (ro|system), approved_at (ro|system)

### Runs (read-only)
- run_id, status, started_at, finished_at, items_processed, errors

### Errors_Hotlist (read-only)
- error_id, item_id, stage, message, retry_count, next_action

### KPIs (read-only)
- date, items_ingested, items_indexed, errors, success_rate

## Rules
- Only `approved`, `notes` are written **from** Sheets to DB.
- All IDs are deterministic and never reused.
- Sync cadence: hourly; DB authoritative on conflicts except whitelist above.

## State Machine
Each item follows this state progression:
```
queued → fetching → extracted → indexed → exported → error(retryable|fatal)
```

All state transitions include:
- Timestamps for each transition
- Attempt counters
- Error details where applicable

## Data Integrity
- **Deterministic IDs:** source_id, item_id, run_id never reused
- **Append-only logs:** events/runs_log as JSONL for audit trail
- **Atomic operations:** All multi-step operations use transactions
- **Validation:** Schema validation on all data flows