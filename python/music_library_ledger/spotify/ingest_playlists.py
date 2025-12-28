from __future__ import annotations

import sqlite3
from typing import Any, Optional

from music_library_ledger.db.tracks import TrackInput, upsert_track
from music_library_ledger.db.artists import ArtistInput, get_or_create_artist, attach_artist_to_track
from music_library_ledger.db.collections import CollectionInput, get_or_create_collection, add_track_to_collection
from music_library_ledger.db.platform import upsert_platform_track, upsert_platform_artist, upsert_platform_collection
from music_library_ledger.spotify.client import get_spotify_client


def _spotify_url(obj: dict) -> Optional[str]:
    ext = obj.get("external_urls") or {}
    return ext.get("spotify")


def _as_dict(x: Any) -> Optional[dict]:
    return x if isinstance(x, dict) else None


def ingest_playlists(
    conn: sqlite3.Connection,
    *,
    include_private: bool = True,
    limit_playlists: Optional[int] = None,
) -> None:
    """
    Ingest all user-visible playlists (public + private + collaborative, depending on scopes)
    and store:
      - collections row (canonical)
      - platform_collections mapping (spotify playlist id -> collection_uid)
      - playlist items as collection_items with stable position + added_at
      - tracks/artists + platform mappings as needed
    """
    sp = get_spotify_client()

    playlist_page_limit = 50
    playlist_offset = 0
    ingested_playlists = 0

    while True:
        page = sp.current_user_playlists(limit=playlist_page_limit, offset=playlist_offset)
        playlists = page.get("items", []) or []
        if not playlists:
            break

        for pl in playlists:
            if limit_playlists is not None and ingested_playlists >= limit_playlists:
                return

            playlist_id = pl.get("id")
            if not playlist_id:
                continue

            # Private playlist filtering is messy because "public" can be None.
            # We'll only skip if explicitly False and you asked to exclude private.
            is_public = pl.get("public")
            if not include_private and is_public is False:
                continue

            playlist_name = (pl.get("name") or "").strip() or f"Unnamed Playlist ({playlist_id})"
            playlist_desc = pl.get("description")
            playlist_url = _spotify_url(pl)

            # Create/resolve canonical collection
            with conn:
                collection_uid = get_or_create_collection(
                    conn,
                    CollectionInput(
                        name=playlist_name,
                        collection_type="playlist",
                        description=playlist_desc,
                    ),
                )

                upsert_platform_collection(
                    conn,
                    platform="spotify",
                    platform_collection_id=playlist_id,
                    collection_uid=collection_uid,
                    playlist_url=playlist_url,
                    raw_json=_as_dict(pl),
                )

            # Ingest items for this playlist
            _ingest_playlist_items(
                conn,
                playlist_id=playlist_id,
                collection_uid=collection_uid,
            )

            ingested_playlists += 1

        playlist_offset += playlist_page_limit


def _ingest_playlist_items(
    conn: sqlite3.Connection,
    *,
    playlist_id: str,
    collection_uid: str,
) -> None:
    # Clear existing items for idempotency
    conn.execute("DELETE FROM collection_items WHERE collection_uid = ?;", (collection_uid,))

    sp = get_spotify_client()

    item_limit = 100
    item_offset = 0
    position = 0

    while True:
        page = sp.playlist_items(
            playlist_id,
            limit=item_limit,
            offset=item_offset,
            additional_types=("track",),
        )
        items = page.get("items", []) or []
        if not items:
            break

        with conn:
            for item in items:
                added_at = item.get("added_at")

                t = item.get("track") or {}
                if not isinstance(t, dict) or not t:
                    continue

                # Spotify sometimes returns local/unavailable items without an id
                spotify_track_id = t.get("id")
                if not spotify_track_id:
                    continue

                track_name = t.get("name") or "UNKNOWN TITLE"

                track_uid = upsert_track(
                    conn,
                    TrackInput(
                        title=track_name,
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
                    raw_json=_as_dict(t),
                    match_confidence=1.0,
                    match_method="spotify_id",
                )

                # Artists in order
                artists = t.get("artists") or []
                for idx, a in enumerate(artists):
                    if not isinstance(a, dict):
                        continue
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
                            raw_json=_as_dict(a),
                        )

                # Add to collection with ordering
                add_track_to_collection(
                    conn,
                    collection_uid=collection_uid,
                    track_uid=track_uid,
                    position=position,
                    added_at=added_at,
                )
                position += 1

        item_offset += item_limit


def main() -> None:
    from music_library_ledger.db.connection import get_connection

    conn = get_connection()
    ingest_playlists(conn)
    print("Done: ingested Spotify playlists.")


if __name__ == "__main__":
    main()
