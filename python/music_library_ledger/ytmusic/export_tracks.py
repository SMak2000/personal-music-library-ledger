from __future__ import annotations

import argparse
import logging
from pathlib import Path
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable, Optional

from ytmusicapi.models.content.enums import LikeStatus

from music_library_ledger.db.artists import get_artists_for_track
from music_library_ledger.db.connection import get_connection
from music_library_ledger.db.platform import upsert_platform_track
from music_library_ledger.db.tracks import list_tracks_missing_platform_mapping
from music_library_ledger.ytmusic.client import get_ytmusic_client
from ytmusicapi import YTMusic

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrackInfo:
    track_uid: str
    title: str
    album: Optional[str]
    duration_ms: Optional[int]
    artists: list[str]


@dataclass(frozen=True)
class MatchCandidate:
    video_id: str
    title: str
    artists: list[str]
    duration_ms: Optional[int]
    raw: dict[str, Any]
    score: float


def _normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalize_text(a), _normalize_text(b)).ratio()


def _duration_str_to_ms(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    parts = value.split(":")
    if not parts or any(not p.isdigit() for p in parts):
        return None
    total_seconds = 0
    for part in parts:
        total_seconds = total_seconds * 60 + int(part)
    return total_seconds * 1000


def _duration_score(expected_ms: Optional[int], candidate_ms: Optional[int]) -> float:
    if expected_ms is None or candidate_ms is None:
        return 0.0
    delta = abs(expected_ms - candidate_ms)
    if delta <= 2500:
        return 1.0
    if delta <= 5000:
        return 0.5
    if delta <= 10000:
        return 0.2
    return 0.0


def _best_artist_ratio(track_artists: list[str], candidate_artists: list[str]) -> float:
    if not track_artists or not candidate_artists:
        return 0.0
    return max(_ratio(track_artist, cand_artist) for track_artist in track_artists for cand_artist in candidate_artists)


def _pick_best_match(
    track: TrackInfo,
    candidates: Iterable[dict[str, Any]],
    *,
    min_score: float,
) -> Optional[MatchCandidate]:
    best: Optional[MatchCandidate] = None

    for cand in candidates:
        video_id = cand.get("videoId")
        if not video_id:
            continue

        title = cand.get("title") or ""
        artists = [a.get("name") for a in (cand.get("artists") or []) if isinstance(a, dict) and a.get("name")]
        duration_ms = _duration_str_to_ms(cand.get("duration"))

        title_ratio = _ratio(track.title, title)
        artist_ratio = _best_artist_ratio(track.artists, artists)
        duration_ratio = _duration_score(track.duration_ms, duration_ms)

        score = 0.65 * title_ratio + 0.25 * artist_ratio + 0.10 * duration_ratio
        if title_ratio < 0.6:
            continue

        candidate = MatchCandidate(
            video_id=video_id,
            title=title,
            artists=artists,
            duration_ms=duration_ms,
            raw=cand,
            score=score,
        )

        if best is None or candidate.score > best.score:
            best = candidate

    if best and best.score >= min_score:
        return best
    return None


def _track_from_row(conn, row) -> TrackInfo:
    artists = [artist["name"] for artist in get_artists_for_track(conn, row["track_uid"])]
    title = (row["title"] or "").strip() or "UNKNOWN TITLE"
    return TrackInfo(
        track_uid=row["track_uid"],
        title=title,
        album=row["album"],
        duration_ms=row["duration_ms"],
        artists=artists,
    )


def _search_candidates(ytm: YTMusic, query: str, *, limit: int) -> list[dict[str, Any]]:
    results = ytm.search(query, filter="songs", limit=limit) or []
    if results:
        return results
    return ytm.search(query, filter="videos", limit=limit) or []


def export_tracks_to_ytmusic(
    *,
    limit: int = 5000,
    media_type: Optional[str] = "song",
    search_limit: int = 5,
    min_score: float = 0.65,
    dry_run: bool = False,
) -> None:
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if search_limit <= 0:
        raise ValueError("search_limit must be > 0")

    conn = get_connection()
    ytm = get_ytmusic_client()

    tracks = list_tracks_missing_platform_mapping(
        conn,
        platform="ytm",
        media_type=media_type,
        limit=limit,
    )

    LOGGER.info("Found %s tracks missing YT Music mapping", len(tracks))

    for row in tracks:
        track = _track_from_row(conn, row)
        artist_hint = track.artists[0] if track.artists else ""
        query = f"{track.title} {artist_hint}".strip()

        try:
            candidates = _search_candidates(ytm, query, limit=search_limit)
        except Exception:
            LOGGER.exception("Search failed for track_uid=%s title=%s", track.track_uid, track.title)
            continue

        match = _pick_best_match(track, candidates, min_score=min_score)
        if not match:
            LOGGER.warning(
                "No YT Music match for track_uid=%s title=%s artists=%s",
                track.track_uid,
                track.title,
                ", ".join(track.artists) or "UNKNOWN",
            )
            continue

        if dry_run:
            LOGGER.info(
                "DRY RUN match track_uid=%s -> %s (%s) score=%.2f",
                track.track_uid,
                match.title,
                ", ".join(match.artists) or "UNKNOWN",
                match.score,
            )
            continue

        try:
            ytm.rate_song(match.video_id, rating=LikeStatus.LIKE)
        except Exception:
            LOGGER.exception(
                "Failed to add to YT Music library track_uid=%s title=%s video_id=%s",
                track.track_uid,
                track.title,
                match.video_id,
            )
            continue

        with conn:
            upsert_platform_track(
                conn,
                platform="ytm",
                platform_track_id=match.video_id,
                track_uid=track.track_uid,
                song_url=f"https://music.youtube.com/watch?v={match.video_id}",
                raw_json=match.raw,
                match_confidence=match.score,
                match_method="ytmusic_search",
            )

        LOGGER.info(
            "Added track_uid=%s -> %s (%s) score=%.2f",
            track.track_uid,
            match.title,
            ", ".join(match.artists) or "UNKNOWN",
            match.score,
        )


def _configure_logging(verbose: bool, log_path: Optional[str]) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_path:
        path = Path(log_path).expanduser()
        handlers.append(logging.FileHandler(path))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export tracks from SQLite to YouTube Music.")
    parser.add_argument("--limit", type=int, default=50000, help="Max tracks to export per run.")
    parser.add_argument("--media-type", default="song", help="Filter by media_type or pass empty for all.")
    parser.add_argument("--search-limit", type=int, default=5, help="Candidates per search call.")
    parser.add_argument("--min-score", type=float, default=0.65, help="Minimum match score.")
    parser.add_argument("--dry-run", action="store_true", help="Match only, do not add to YT Music.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument("--log-path", help="Optional file path for logs.")
    args = parser.parse_args()

    media_type = args.media_type.strip() if args.media_type else None
    _configure_logging(args.verbose, args.log_path)

    export_tracks_to_ytmusic(
        limit=args.limit,
        media_type=media_type,
        search_limit=args.search_limit,
        min_score=args.min_score,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
