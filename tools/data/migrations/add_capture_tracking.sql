-- Migration: Add capture tracking for Apple device integration
-- Supports tracking content captured from iOS/macOS devices

-- Track content captured from devices
CREATE TABLE IF NOT EXISTS capture_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_id TEXT UNIQUE NOT NULL,
    content_type TEXT NOT NULL, -- url, text, voice
    content TEXT NOT NULL,
    metadata TEXT, -- JSON metadata (notes, source device, etc.)
    source_device TEXT,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    status TEXT DEFAULT 'queued', -- queued, processing, completed, failed
    error_message TEXT,
    atlas_content_id TEXT -- Link to processed content in main content table
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_capture_queue_status ON capture_queue(status);
CREATE INDEX IF NOT EXISTS idx_capture_queue_captured_at ON capture_queue(captured_at);
CREATE INDEX IF NOT EXISTS idx_capture_queue_content_type ON capture_queue(content_type);
CREATE INDEX IF NOT EXISTS idx_capture_queue_source_device ON capture_queue(source_device);

-- Track export history for audit and optimization
CREATE TABLE IF NOT EXISTS export_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    export_type TEXT NOT NULL, -- obsidian, notion, anki, markdown, json, csv
    content_count INTEGER NOT NULL,
    filters TEXT, -- JSON representation of filters used
    output_path TEXT,
    export_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    file_count INTEGER, -- Number of files created
    total_size_bytes INTEGER -- Total size of exported content
);

-- Create indexes for export tracking
CREATE INDEX IF NOT EXISTS idx_export_history_type ON export_history(export_type);
CREATE INDEX IF NOT EXISTS idx_export_history_timestamp ON export_history(export_timestamp);
CREATE INDEX IF NOT EXISTS idx_export_history_success ON export_history(success);

-- Note: content table doesn't exist in podcast database
-- Export tracking will be handled separately when needed