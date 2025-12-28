CREATE TABLE IF NOT EXISTS platform_tracks (
  platform           TEXT NOT NULL,
  platform_track_id  TEXT NOT NULL,
  track_uid          TEXT NOT NULL,

  match_confidence   REAL,
  match_method       TEXT,
  raw_json           TEXT,
  created_at         TEXT NOT NULL DEFAULT (datetime('now')),
  last_verified_at   TEXT,
  song_url           TEXT,
  updated_at         TEXT NOT NULL DEFAULT (datetime('now')),

  PRIMARY KEY (platform, platform_track_id),
  FOREIGN KEY (track_uid) REFERENCES tracks(track_uid) ON DELETE CASCADE
);
