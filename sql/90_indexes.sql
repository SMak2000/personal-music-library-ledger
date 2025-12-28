-- tracks
CREATE INDEX IF NOT EXISTS idx_tracks_isrc ON tracks(isrc);
CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
CREATE INDEX IF NOT EXISTS idx_tracks_media_type ON tracks(media_type);
CREATE UNIQUE INDEX IF NOT EXISTS uq_tracks_isrc ON tracks(isrc) WHERE isrc IS NOT NULL;

-- artists
CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name);

-- track_artists
CREATE INDEX IF NOT EXISTS idx_track_artists_track
  ON track_artists(track_uid, artist_order);
CREATE INDEX IF NOT EXISTS idx_track_artists_artist
  ON track_artists(artist_uid);

-- collections
CREATE INDEX IF NOT EXISTS idx_collections_type ON collections(collection_type);

-- collection_items
CREATE INDEX IF NOT EXISTS idx_collection_items_collection_pos
  ON collection_items(collection_uid, position);

-- platform mappings
CREATE INDEX IF NOT EXISTS idx_platform_tracks_track_uid
  ON platform_tracks(track_uid);
CREATE INDEX IF NOT EXISTS idx_platform_artists_artist_uid
  ON platform_artists(artist_uid);
CREATE INDEX IF NOT EXISTS idx_platform_collections_collection_uid
  ON platform_collections(collection_uid);
