from music_library_ledger.db.connection import get_connection
from music_library_ledger.db.tracks import TrackInput, upsert_track
from music_library_ledger.db.artists import (
    ArtistInput,
    get_or_create_artist,
    attach_artist_to_track,
    get_artists_for_track,
)


def main() -> None:
    conn = get_connection()

    with conn:
        track_uid = upsert_track(
            conn,
            TrackInput(
                title="Nights",
                album="Blonde",
                duration_ms=300000,
                media_type="song",
                canonical_platform="spotify",
            ),
        )

        frank_uid = get_or_create_artist(conn, ArtistInput(name="Frank Ocean"))
        beyonce_uid = get_or_create_artist(conn, ArtistInput(name="Beyoncé"))

        # Attach with explicit ordering
        attach_artist_to_track(
            conn,
            track_uid=track_uid,
            artist_uid=frank_uid,
            artist_order=0,
            role="primary",
        )
        attach_artist_to_track(
            conn,
            track_uid=track_uid,
            artist_uid=beyonce_uid,
            artist_order=1,
            role="featured",
        )

        rows = get_artists_for_track(conn, track_uid)

    print("Track UID:", track_uid)
    print("Artists (ordered):")
    for r in rows:
        print(f"  {r['artist_order']}: {r['name']} ({r['role']})")

    # Basic assertions
    assert len(rows) == 2
    assert rows[0]["name"] == "Frank Ocean"
    assert rows[0]["artist_order"] == 0
    assert rows[1]["artist_order"] == 1


if __name__ == "__main__":
    main()
