CREATE TABLE IF NOT EXISTS tracks (
  track_uid          TEXT PRIMARY KEY,
  title              TEXT NOT NULL,
  album              TEXT,
  duration_ms        INTEGER,
  isrc               TEXT,
  explicit           INTEGER,

  -- Allow YouTube-video-style entries
  media_type         TEXT NOT NULL DEFAULT 'song',      -- 'song' or 'video'
  source_url         TEXT,                              -- e.g., youtube link (optional)
  canonical_platform TEXT,                              -- 'spotify','ytm','youtube','local' (optional)

  created_at         TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at         TEXT NOT NULL DEFAULT (datetime('now'))
);
