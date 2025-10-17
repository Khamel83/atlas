-- Atlas Transcript Segments Database Schema
-- Adds support for parsed transcript content with speaker attribution and topic clustering

-- Create transcript segments table
CREATE TABLE IF NOT EXISTS transcript_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER,
    content_uid TEXT NOT NULL,
    speaker TEXT,
    content TEXT NOT NULL,
    segment_id INTEGER NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    start_timestamp TEXT,
    end_timestamp TEXT,
    word_count INTEGER,
    segment_type TEXT, -- question, answer, transition, discussion
    topic_tags TEXT, -- JSON array of topic keywords
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create topic clusters table
CREATE TABLE IF NOT EXISTS topic_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_name TEXT UNIQUE NOT NULL,
    keywords TEXT, -- JSON array of keywords
    related_segments TEXT, -- JSON array of segment IDs
    episode_count INTEGER DEFAULT 0,
    content_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create speaker index table
CREATE TABLE IF NOT EXISTS transcript_speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    speaker_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    episode_count INTEGER DEFAULT 0,
    segment_count INTEGER DEFAULT 0,
    total_word_count INTEGER DEFAULT 0,
    first_appearance TIMESTAMP,
    last_appearance TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(normalized_name)
);

-- Create indexes for search performance
CREATE INDEX IF NOT EXISTS idx_transcript_segments_speaker ON transcript_segments(speaker);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_episode ON transcript_segments(episode_id);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_content_uid ON transcript_segments(content_uid);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_content ON transcript_segments(content);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_type ON transcript_segments(segment_type);
CREATE INDEX IF NOT EXISTS idx_topic_clusters_name ON topic_clusters(topic_name);
CREATE INDEX IF NOT EXISTS idx_transcript_speakers_name ON transcript_speakers(normalized_name);
CREATE INDEX IF NOT EXISTS idx_transcript_speakers_speaker ON transcript_speakers(speaker_name);

-- Create full-text search indexes for content
CREATE VIRTUAL TABLE IF NOT EXISTS transcript_segments_fts USING fts5(
    content,
    speaker,
    segment_type,
    topic_tags,
    content='transcript_segments',
    content_rowid='id'
);

-- Triggers to keep FTS table in sync
CREATE TRIGGER IF NOT EXISTS transcript_segments_ai AFTER INSERT ON transcript_segments BEGIN
    INSERT INTO transcript_segments_fts(rowid, content, speaker, segment_type, topic_tags)
    VALUES (new.id, new.content, new.speaker, new.segment_type, new.topic_tags);
END;

CREATE TRIGGER IF NOT EXISTS transcript_segments_ad AFTER DELETE ON transcript_segments BEGIN
    INSERT INTO transcript_segments_fts(transcript_segments_fts, rowid, content, speaker, segment_type, topic_tags)
    VALUES ('delete', old.id, old.content, old.speaker, old.segment_type, old.topic_tags);
END;

CREATE TRIGGER IF NOT EXISTS transcript_segments_au AFTER UPDATE ON transcript_segments BEGIN
    INSERT INTO transcript_segments_fts(transcript_segments_fts, rowid, content, speaker, segment_type, topic_tags)
    VALUES ('delete', old.id, old.content, old.speaker, old.segment_type, old.topic_tags);
    INSERT INTO transcript_segments_fts(rowid, content, speaker, segment_type, topic_tags)
    VALUES (new.id, new.content, new.speaker, new.segment_type, new.topic_tags);
END;