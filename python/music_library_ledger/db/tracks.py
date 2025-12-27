from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class TrackInput:
    title: str
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    explicit: Optional[bool] = None
    media_type: str = "song"                 # 'song' or 'video'
    source_url: Optional[str] = None
    canonical_platform: Optional[str] = None # 'spotify','ytm','youtube','local'


def _bool_to_int(v: Optional[bool]) -> Optional[int]:
    if v is None:
        return None
    return 1 if v else 0


def create_track_uid() -> str:
    return str(uuid.uuid4())


def get_track_by_uid(
    conn: sqlite3.Connection,
    track_uid: str,
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM tracks WHERE track_uid = ?;",
        (track_uid,),
    ).fetchone()


def get_track_by_isrc(
    conn: sqlite3.Connection,
    isrc: str,
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM tracks WHERE isrc = ?;",
        (isrc,),
    ).fetchone()


def upsert_track(
    conn: sqlite3.Connection,
    track: TrackInput,
    *,
    track_uid: Optional[str] = None,
) -> str:
    if not track.title or not track.title.strip():
        raise ValueError("Track title is required")

    existing_uid: Optional[str] = None
    if track.isrc:
        row = get_track_by_isrc(conn, track.isrc)
        if row:
            existing_uid = row["track_uid"]

    uid = existing_uid or track_uid or create_track_uid()

    if existing_uid:
        conn.execute(
            """
            UPDATE tracks
            SET title = ?,
                album = ?,
                duration_ms = ?,
                explicit = ?,
                media_type = ?,
                source_url = ?,
                canonical_platform = ?,
                updated_at = datetime('now')
            WHERE track_uid = ?;
            """,
            (
                track.title.strip(),
                track.album,
                track.duration_ms,
                _bool_to_int(track.explicit),
                track.media_type,
                track.source_url,
                track.canonical_platform,
                uid,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO tracks (
                track_uid,
                title,
                album,
                duration_ms,
                isrc,
                explicit,
                media_type,
                source_url,
                canonical_platform,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'));
            """,
            (
                uid,
                track.title.strip(),
                track.album,
                track.duration_ms,
                track.isrc,
                _bool_to_int(track.explicit),
                track.media_type,
                track.source_url,
                track.canonical_platform,
            ),
        )

    return uid


def list_tracks_missing_platform_mapping(
    conn: sqlite3.Connection,
    platform: str,
    *,
    media_type: Optional[str] = None,
    limit: int = 500,
) -> Sequence[sqlite3.Row]:
    if limit <= 0:
        raise ValueError("limit must be > 0")

    params = [platform]
    media_filter_sql = ""
    if media_type is not None:
        media_filter_sql = "AND t.media_type = ?"
        params.append(media_type)

    params.append(limit)

    return conn.execute(
        f"""
        SELECT t.*
        FROM tracks t
        WHERE NOT EXISTS (
            SELECT 1
            FROM platform_tracks pt
            WHERE pt.track_uid = t.track_uid
                AND pt.platform = ?
        )
        {media_filter_sql}
        ORDER BY t.created_at ASC
        LIMIT ?;
        """,
        tuple(params),
    ).fetchall()
