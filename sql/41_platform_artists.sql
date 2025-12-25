CREATE TABLE IF NOT EXISTS platform_artists (
  platform           TEXT NOT NULL,
  platform_artist_id TEXT NOT NULL,
  artist_uid         TEXT NOT NULL,

  raw_json           TEXT,
  created_at         TEXT NOT NULL DEFAULT (datetime('now')),

  PRIMARY KEY (platform, platform_artist_id),
  FOREIGN KEY (artist_uid) REFERENCES artists(artist_uid) ON DELETE CASCADE
);
