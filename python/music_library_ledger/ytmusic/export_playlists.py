from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from music_library_ledger.db.connection import get_connection
from music_library_ledger.db.platform import upsert_platform_collection
from music_library_ledger.ytmusic.client import get_ytmusic_client

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlaylistTrack:
    track_uid: str
    title: str
    platform_track_id: Optional[str]


def _chunked(values: list[str], size: int) -> Iterable[list[str]]:
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]


def _get_collection_tracks(conn, collection_uid: str) -> list[PlaylistTrack]:
    rows = conn.execute(
        """
        SELECT t.track_uid, t.title, pt.platform_track_id
        FROM collection_items ci
        JOIN tracks t ON t.track_uid = ci.track_uid
        LEFT JOIN platform_tracks pt
            ON pt.track_uid = t.track_uid AND pt.platform = 'ytm'
        WHERE ci.collection_uid = ?
        ORDER BY ci.position ASC;
        """,
        (collection_uid,),
    ).fetchall()

    return [
        PlaylistTrack(
            track_uid=row["track_uid"],
            title=row["title"],
            platform_track_id=row["platform_track_id"],
        )
        for row in rows
    ]


def export_playlists_to_ytmusic(
    *,
    limit: int = 100,
    collection_type: str = "playlist",
    chunk_size: int = 50,
    dry_run: bool = False,
    force_new: bool = False,
) -> None:
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")

    conn = get_connection()
    ytm = get_ytmusic_client()

    collections = conn.execute(
        """
        SELECT *
        FROM collections
        WHERE collection_type = ?
        ORDER BY updated_at DESC
        LIMIT ?;
        """,
        (collection_type.strip(), limit),
    ).fetchall()

    LOGGER.info("Found %s collections of type=%s", len(collections), collection_type)

    for collection in collections:
        collection_uid = collection["collection_uid"]
        name = collection["name"]
        description = collection["description"]

        try:
            tracks = _get_collection_tracks(conn, collection_uid)
            if not tracks:
                LOGGER.warning("No tracks for collection_uid=%s name=%s", collection_uid, name)
                continue

            mapped_ids = [t.platform_track_id for t in tracks if t.platform_track_id]
            missing = [t for t in tracks if not t.platform_track_id]
            if missing:
                LOGGER.warning(
                    "Missing YT Music mappings for %s tracks in collection_uid=%s name=%s",
                    len(missing),
                    collection_uid,
                    name,
                )

            if not mapped_ids:
                LOGGER.warning("No mapped YT Music tracks for collection_uid=%s name=%s", collection_uid, name)
                continue

            existing = conn.execute(
                """
                SELECT *
                FROM platform_collections
                WHERE platform = 'ytm' AND collection_uid = ?;
                """,
                (collection_uid,),
            ).fetchone()

            if dry_run:
                LOGGER.info(
                    "DRY RUN playlist=%s tracks=%s existing=%s",
                    name,
                    len(mapped_ids),
                    bool(existing),
                )
                continue

            if existing and not force_new:
                playlist_id = existing["platform_collection_id"]
            else:
                playlist_id = ytm.create_playlist(
                    name,
                    description or "",
                    privacy_status="PRIVATE",
                )

                with conn:
                    upsert_platform_collection(
                        conn,
                        platform="ytm",
                        platform_collection_id=playlist_id,
                        collection_uid=collection_uid,
                        playlist_url=f"https://music.youtube.com/playlist?list={playlist_id}",
                        raw_json={
                            "name": name,
                            "description": description,
                            "source": "ledger_export",
                        },
                    )

            for chunk in _chunked(mapped_ids, chunk_size):
                ytm.add_playlist_items(playlist_id, chunk)

            LOGGER.info(
                "Exported playlist name=%s tracks=%s playlist_id=%s",
                name,
                len(mapped_ids),
                playlist_id,
            )
        except Exception:
            LOGGER.exception("Failed exporting collection_uid=%s name=%s", collection_uid, name)


def _configure_logging(verbose: bool, log_path: Optional[str]) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_path:
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export playlists from SQLite to YouTube Music.")
    parser.add_argument("--limit", type=int, default=100, help="Max playlists to export per run.")
    parser.add_argument("--collection-type", default="playlist", help="Collection type to export.")
    parser.add_argument("--chunk-size", type=int, default=50, help="Batch size for YT Music API calls.")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, do not create playlists.")
    parser.add_argument("--force-new", action="store_true", help="Always create a new YT Music playlist.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument("--log-path", help="Optional file path for logs.")
    args = parser.parse_args()

    _configure_logging(args.verbose, args.log_path)

    export_playlists_to_ytmusic(
        limit=args.limit,
        collection_type=args.collection_type,
        chunk_size=args.chunk_size,
        dry_run=args.dry_run,
        force_new=args.force_new,
    )


if __name__ == "__main__":
    main()
