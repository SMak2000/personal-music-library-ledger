from __future__ import annotations

import sqlite3
from typing import Optional

from music_library_ledger.db.tracks import TrackInput, upsert_track
from music_library_ledger.db.artists import ArtistInput, clear_artists_for_track, get_or_create_artist, attach_artist_to_track
from music_library_ledger.db.collections import CollectionInput, get_or_create_collection, add_track_to_collection
from music_library_ledger.db.platform import upsert_platform_track, upsert_platform_artist, upsert_platform_collection
from music_library_ledger.spotify.client import get_spotify_client


def _spotify_url(obj: dict) -> Optional[str]:
    ext = obj.get("external_urls") or {}
    return ext.get("spotify")


def ingest_saved_tracks(conn: sqlite3.Connection) -> None:
    sp = get_spotify_client()

    # Canonical "Liked Songs" collection
    liked_uid = get_or_create_collection(
        conn,
        CollectionInput(
            name="Liked Songs",
            collection_type="liked",
            description="Imported from Spotify saved tracks",
        ),
    )
    upsert_platform_collection(
        conn,
        platform="spotify",
        platform_collection_id="me:tracks",
        collection_uid=liked_uid,
        playlist_url=None,
        raw_json={"kind": "saved_tracks"},
    )

    limit = 30
    offset = 0
    position = 0  # stable ordering in our DB

    while True:
        page = sp.current_user_saved_tracks(limit=limit, offset=offset)
        items = page.get("items", [])
        if not items:
            break

        with conn:  # commit each page
            for item in items:
                added_at = item.get("added_at")  # ISO8601 UTC Z :contentReference[oaicite:6]{index=6}
                t = item.get("track") or {}
                if not t:
                    continue

                # Some tracks can be unavailable; skip if needed
                spotify_track_id = t.get("id")
                if not spotify_track_id:
                    continue

                track_uid = upsert_track(
                    conn,
                    TrackInput(
                        title=t.get("name") or "UMKNOWN TITLE",
                        album=(t.get("album") or {}).get("name"),
                        duration_ms=t.get("duration_ms"),
                        isrc=((t.get("external_ids") or {}).get("isrc")),
                        explicit=t.get("explicit"),
                        media_type="song",
                        source_url=_spotify_url(t),
                        canonical_platform="spotify",
                    ),
                )

                upsert_platform_track(
                    conn,
                    platform="spotify",
                    platform_track_id=spotify_track_id,
                    track_uid=track_uid,
                    song_url=_spotify_url(t),
                    raw_json=t,
                    match_confidence=1.0,
                    match_method="spotify_id",
                )

                # Artists (ordered)
                artists = t.get("artists") or []
                clear_artists_for_track(conn, track_uid)

                for idx, a in enumerate(artists):
                    artist_uid = get_or_create_artist(conn, ArtistInput(name=a.get("name") or ""))
                    attach_artist_to_track(
                        conn,
                        track_uid=track_uid,
                        artist_uid=artist_uid,
                        artist_order=idx,
                        role="primary" if idx == 0 else "artist",
                    )
                    if a.get("id"):
                        upsert_platform_artist(
                            conn,
                            platform="spotify",
                            platform_artist_id=a["id"],
                            artist_uid=artist_uid,
                            raw_json=a,
                        )

                # Add to "Liked Songs"
                add_track_to_collection(
                    conn,
                    collection_uid=liked_uid,
                    track_uid=track_uid,
                    position=position,
                    added_at=added_at,
                )
                position += 1

        offset += limit


def main() -> None:
    from music_library_ledger.db.connection import get_connection

    conn = get_connection()
    ingest_saved_tracks(conn)
    print("Done: ingested Spotify saved tracks.")


if __name__ == "__main__":
    main()
