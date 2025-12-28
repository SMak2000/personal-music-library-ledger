import sqlite3
from typing import Optional


def upsert_platform_track(
    conn: sqlite3.Connection,
    *,
    platform: str,
    platform_track_id: str,
    track_uid: str,
    url: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO platform_tracks (platform, platform_track_id, track_uid, song_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(platform, platform_track_id) DO UPDATE SET
            track_uid = excluded.track_uid,
            song_url = COALESCE(excluded.song_url, platform_tracks.song_url),
            updated_at = datetime('now');
        """,
        (platform, platform_track_id, track_uid, url),
    )


def upsert_platform_artist(
    conn: sqlite3.Connection,
    *,
    platform: str,
    platform_artist_id: str,
    artist_uid: str,
    url: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO platform_artists (platform, platform_artist_id, artist_uid, song_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(platform, platform_artist_id) DO UPDATE SET
            artist_uid = excluded.artist_uid,
            song_url = COALESCE(excluded.song_url, platform_artists.song_url),
            updated_at = datetime('now');
        """,
        (platform, platform_artist_id, artist_uid, url),
    )


def upsert_platform_collection(
    conn: sqlite3.Connection,
    *,
    platform: str,
    platform_collection_id: str,
    collection_uid: str,
    url: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO platform_collections (platform, platform_collection_id, collection_uid, song_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(platform, platform_collection_id) DO UPDATE SET
            collection_uid = excluded.collection_uid,
            song_url = COALESCE(excluded.song_url, platform_collections.song_url),
            updated_at = datetime('now');
        """,
        (platform, platform_collection_id, collection_uid, url),
    )
