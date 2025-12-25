CREATE TABLE IF NOT EXISTS artists (
  artist_uid   TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (name)
);
