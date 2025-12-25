CREATE TABLE IF NOT EXISTS collection_items (
  collection_uid  TEXT NOT NULL,
  track_uid       TEXT NOT NULL,
  position        INTEGER,
  added_at        TEXT NOT NULL DEFAULT (datetime('now')),
  source          TEXT,

  PRIMARY KEY (collection_uid, track_uid),
  FOREIGN KEY (collection_uid) REFERENCES collections(collection_uid) ON DELETE CASCADE,
  FOREIGN KEY (track_uid) REFERENCES tracks(track_uid) ON DELETE CASCADE
);
