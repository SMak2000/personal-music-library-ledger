import json
import sqlite3
from typing import Any, Optional


def _to_json(raw: Optional[dict[str, Any]]) -> Optional[str]:
    if raw is None:
        return None
    return json.dumps(raw, ensure_ascii=False, separators=(",", ":"))


def upsert_platform_track(
    conn: sqlite3.Connection,
    *,
    platform: str,
    platform_track_id: str,
    track_uid: str,
    song_url: Optional[str] = None,
    raw_json: Optional[dict[str, Any]] = None,
    match_confidence: Optional[float] = None,
    match_method: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO platform_tracks (
            platform,
            platform_track_id,
            track_uid,
            match_confidence,
            match_method,
            raw_json,
            created_at,
            last_verified_at,
            song_url,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?, datetime('now'))
        ON CONFLICT(platform, platform_track_id) DO UPDATE SET
            track_uid = excluded.track_uid,
            match_confidence = COALESCE(excluded.match_confidence, platform_tracks.match_confidence),
            match_method = COALESCE(excluded.match_method, platform_tracks.match_method),
            raw_json = COALESCE(excluded.raw_json, platform_tracks.raw_json),
            song_url = COALESCE(excluded.song_url, platform_tracks.song_url),
            last_verified_at = datetime('now'),
            updated_at = datetime('now');
        """,
        (
            platform,
            platform_track_id,
            track_uid,
            match_confidence,
            match_method,
            _to_json(raw_json),
            song_url,
        ),
    )


def attach_artist_to_track(
    conn: sqlite3.Connection,
    *,
    track_uid: str,
    artist_uid: str,
    artist_order: int,
    role: str = "primary",
) -> None:
    if artist_order < 0:
        raise ValueError("artist_order must be >= 0")
    if not role or not role.strip():
        raise ValueError("role is required")

    role_clean = role.strip()

    # 1) Ensure this artist is not already attached to the track at a different order.
    # If it is, remove it so we don't violate PRIMARY KEY(track_uid, artist_uid) on reinsert.
    conn.execute(
        """
        DELETE FROM track_artists
        WHERE track_uid = ? AND artist_uid = ?;
        """,
        (track_uid, artist_uid),
    )

    # 2) Upsert by (track_uid, artist_order)
    # If that slot is already occupied by another artist, overwrite it.
    conn.execute(
        """
        INSERT INTO track_artists (
            track_uid,
            artist_uid,
            artist_order,
            role
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(track_uid, artist_order) DO UPDATE SET
            artist_uid = excluded.artist_uid,
            role = excluded.role;
        """,
        (track_uid, artist_uid, artist_order, role_clean),
    )

def upsert_platform_artist(
    conn: sqlite3.Connection,
    *,
    platform: str,
    platform_artist_id: str,
    artist_uid: str,
    raw_json: Optional[dict[str, Any]] = None,
) -> None:
    # Matches your platform_artists DDL: no url, no updated_at
    conn.execute(
        """
        INSERT INTO platform_artists (
            platform,
            platform_artist_id,
            artist_uid,
            raw_json,
            created_at
        )
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(platform, platform_artist_id) DO UPDATE SET
            artist_uid = excluded.artist_uid,
            raw_json = COALESCE(excluded.raw_json, platform_artists.raw_json);
        """,
        (platform, platform_artist_id, artist_uid, _to_json(raw_json)),
    )


def upsert_platform_collection(
    conn: sqlite3.Connection,
    *,
    platform: str,
    platform_collection_id: str,
    collection_uid: str,
    playlist_url: Optional[str] = None,
    raw_json: Optional[dict[str, Any]] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO platform_collections (
            platform,
            platform_collection_id,
            collection_uid,
            raw_json,
            created_at,
            last_verified_at,
            playlist_url,
            updated_at
        )
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), ?, datetime('now'))
        ON CONFLICT(platform, platform_collection_id) DO UPDATE SET
            collection_uid = excluded.collection_uid,
            raw_json = COALESCE(excluded.raw_json, platform_collections.raw_json),
            playlist_url = COALESCE(excluded.playlist_url, platform_collections.playlist_url),
            last_verified_at = datetime('now'),
            updated_at = datetime('now');
        """,
        (
            platform,
            platform_collection_id,
            collection_uid,
            _to_json(raw_json),
            playlist_url,
        ),
    )
