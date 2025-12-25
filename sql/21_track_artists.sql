CREATE TABLE IF NOT EXISTS track_artists (
  track_uid     TEXT NOT NULL,
  artist_uid    TEXT NOT NULL,
  artist_order  INTEGER NOT NULL,
  role          TEXT NOT NULL DEFAULT 'primary',

  PRIMARY KEY (track_uid, artist_uid),
  UNIQUE (track_uid, artist_order),

  FOREIGN KEY (track_uid) REFERENCES tracks(track_uid) ON DELETE CASCADE,
  FOREIGN KEY (artist_uid) REFERENCES artists(artist_uid) ON DELETE CASCADE
);
