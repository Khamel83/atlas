-- OOS Agent-OS Database Schema
-- Designed for SQLite WAL mode with human-in-the-loop workflows

-- Enable optimal SQLite settings
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA cache_size=10000;
PRAGMA synchronous=NORMAL;

-- Core operational tables
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'success', 'failed', 'cancelled')),
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at TEXT,
  items_processed INTEGER DEFAULT 0,
  errors INTEGER DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS items (
  item_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  title TEXT,
  status TEXT NOT NULL CHECK (status IN ('queued', 'fetching', 'extracted', 'indexed', 'exported', 'error_retryable', 'error_fatal')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  attempts INTEGER DEFAULT 0,
  last_error TEXT,
  metadata JSON
);

-- Admin audit trail (append-only)
CREATE TABLE IF NOT EXISTS admin_changes (
  change_id TEXT PRIMARY KEY,
  changed_at TEXT NOT NULL DEFAULT (datetime('now')),
  actor TEXT NOT NULL,
  table_name TEXT NOT NULL,
  record_key TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT,
  reason TEXT NOT NULL,
  session_id TEXT
);

-- Human approval workflow
CREATE TABLE IF NOT EXISTS approvals (
  approval_id TEXT PRIMARY KEY,
  item_type TEXT NOT NULL,
  item_id TEXT NOT NULL,
  action TEXT NOT NULL,
  payload JSON NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  requested_at TEXT NOT NULL DEFAULT (datetime('now')),
  reviewed_at TEXT,
  reviewed_by TEXT,
  notes TEXT,
  approved_by TEXT,
  approved_at TEXT
);

-- Error tracking and resolution
CREATE TABLE IF NOT EXISTS errors (
  error_id TEXT PRIMARY KEY,
  item_id TEXT,
  run_id TEXT,
  stage TEXT NOT NULL,
  message TEXT NOT NULL,
  stack_trace TEXT,
  retry_count INTEGER DEFAULT 0,
  next_action TEXT,
  severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  resolved BOOLEAN DEFAULT FALSE,
  resolution TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  resolved_at TEXT,
  FOREIGN KEY (item_id) REFERENCES items(item_id),
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- KPI tracking
CREATE TABLE IF NOT EXISTS daily_kpis (
  date TEXT PRIMARY KEY,
  items_ingested INTEGER DEFAULT 0,
  items_indexed INTEGER DEFAULT 0,
  errors INTEGER DEFAULT 0,
  success_rate REAL DEFAULT 0.0,
  processing_time_avg REAL DEFAULT 0.0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Append-only event log (JSONL-style in database)
CREATE TABLE IF NOT EXISTS events_log (
  event_id TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL DEFAULT (datetime('now')),
  event_type TEXT NOT NULL,
  actor TEXT,
  resource_type TEXT,
  resource_id TEXT,
  details JSON,
  trace_id TEXT
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);
CREATE INDEX IF NOT EXISTS idx_items_updated_at ON items(updated_at);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
CREATE INDEX IF NOT EXISTS idx_approvals_requested_at ON approvals(requested_at);
CREATE INDEX IF NOT EXISTS idx_errors_resolved ON errors(resolved);
CREATE INDEX IF NOT EXISTS idx_errors_severity ON errors(severity);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON events_log(event_type);

-- Full-text search on items
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
  item_id UNINDEXED,
  title,
  source,
  content='items',
  content_rowid='rowid'
);

-- Triggers for FTS updates
CREATE TRIGGER IF NOT EXISTS items_fts_insert AFTER INSERT ON items BEGIN
  INSERT INTO items_fts(rowid, item_id, title, source) VALUES (new.rowid, new.item_id, new.title, new.source);
END;

CREATE TRIGGER IF NOT EXISTS items_fts_update AFTER UPDATE ON items BEGIN
  UPDATE items_fts SET title = new.title, source = new.source WHERE rowid = new.rowid;
END;

CREATE TRIGGER IF NOT EXISTS items_fts_delete AFTER DELETE ON items BEGIN
  DELETE FROM items_fts WHERE rowid = old.rowid;
END;

-- Update timestamp triggers
CREATE TRIGGER IF NOT EXISTS runs_updated_at AFTER UPDATE ON runs BEGIN
  UPDATE runs SET updated_at = datetime('now') WHERE run_id = NEW.run_id;
END;

CREATE TRIGGER IF NOT EXISTS items_updated_at AFTER UPDATE ON items BEGIN
  UPDATE items SET updated_at = datetime('now') WHERE item_id = NEW.item_id;
END;

-- Seed data for testing
INSERT OR IGNORE INTO runs (run_id, status, started_at) VALUES
('run-001', 'success', datetime('now', '-1 hour'));

INSERT OR IGNORE INTO items (item_id, source, title, status) VALUES
('item-001', 'test', 'Test Item', 'indexed');

INSERT OR IGNORE INTO daily_kpis (date, items_ingested, items_indexed, success_rate) VALUES
(date('now'), 1, 1, 1.0);