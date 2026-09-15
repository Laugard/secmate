CREATE TABLE IF NOT EXISTS guild_settings (
  guild_id TEXT PRIMARY KEY,
  timezone TEXT NOT NULL DEFAULT 'Europe/Copenhagen',
  digest_channel_id TEXT,
  digest_time_local TEXT NOT NULL,
  news_time_local TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  guild_id TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  expires_at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_guild_expiry ON memories(guild_id, expires_at_utc);
CREATE TABLE IF NOT EXISTS deadlines (
  id TEXT PRIMARY KEY,
  guild_id TEXT NOT NULL,
  title TEXT NOT NULL,
  due_at_utc TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','completed')),
  created_at_utc TEXT NOT NULL,
  completed_at_utc TEXT
);
CREATE INDEX IF NOT EXISTS idx_deadlines_guild_status_due ON deadlines(guild_id,status,due_at_utc);
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  relative_path TEXT NOT NULL UNIQUE,
  sha256 TEXT NOT NULL,
  file_type TEXT NOT NULL,
  page_count INTEGER,
  embed_model TEXT NOT NULL,
  indexed_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS document_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  page_start INTEGER,
  page_end INTEGER,
  content TEXT NOT NULL,
  embedding BLOB NOT NULL,
  embedding_dimensions INTEGER NOT NULL,
  embed_model TEXT NOT NULL,
  UNIQUE(document_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);
CREATE TABLE IF NOT EXISTS news_items (
  id TEXT PRIMARY KEY,
  dedupe_key TEXT NOT NULL UNIQUE,
  source_name TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  published_at_utc TEXT,
  fetched_at_utc TEXT NOT NULL,
  category TEXT NOT NULL CHECK(category IN ('sårbarheder','cyberangreb','ai-security','lovgivning','andet')),
  summary_da TEXT NOT NULL,
  study_relevance_da TEXT NOT NULL,
  confidence REAL CHECK(confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  posted_at_utc TEXT,
  expires_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_runs (
  id TEXT PRIMARY KEY,
  job_name TEXT NOT NULL,
  guild_id TEXT NOT NULL,
  local_date TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('claimed','succeeded','failed')),
  attempts INTEGER NOT NULL DEFAULT 0,
  claimed_at_utc TEXT NOT NULL,
  finished_at_utc TEXT,
  last_error_code TEXT,
  UNIQUE(job_name, guild_id, local_date)
);

