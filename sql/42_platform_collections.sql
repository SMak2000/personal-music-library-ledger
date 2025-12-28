CREATE TABLE IF NOT EXISTS platform_collections (
  platform                TEXT NOT NULL,
  platform_collection_id  TEXT NOT NULL,
  collection_uid          TEXT NOT NULL,

  raw_json                TEXT,
  created_at              TEXT NOT NULL DEFAULT (datetime('now')),
  last_verified_at        TEXT,
  playlist_url            TEXT,
  updated_at              TEXT NOT NULL DEFAULT (datetime('now')),

  PRIMARY KEY (platform, platform_collection_id),
  FOREIGN KEY (collection_uid) REFERENCES collections(collection_uid) ON DELETE CASCADE
);
