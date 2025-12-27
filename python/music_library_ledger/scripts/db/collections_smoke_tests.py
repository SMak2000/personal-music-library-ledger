from music_library_ledger.db.connection import get_connection
from music_library_ledger.db.tracks import TrackInput, upsert_track
from music_library_ledger.db.collections import (
    CollectionInput,
    get_or_create_collection,
    add_track_to_collection,
    get_collection_tracks,
    list_collections,
    remove_track_from_collection,
)


def main() -> None:
    conn = get_connection()

    with conn:
        t1 = upsert_track(conn, TrackInput(title="Nights", album="Blonde", duration_ms=300000))
        t2 = upsert_track(conn, TrackInput(title="Ivy", album="Blonde", duration_ms=250000))
        t3 = upsert_track(conn, TrackInput(title="Pink + White", album="Blonde", duration_ms=230000))

        col_uid = get_or_create_collection(
            conn,
            CollectionInput(
                name="Test Playlist - Blonde",
                collection_type="playlist",
                description="Smoke test playlist",
            ),
        )

        # Add tracks with explicit ordering
        add_track_to_collection(conn, collection_uid=col_uid, track_uid=t1, position=0)
        add_track_to_collection(conn, collection_uid=col_uid, track_uid=t2, position=1)
        add_track_to_collection(conn, collection_uid=col_uid, track_uid=t3, position=2)

        # Re-add one track to confirm idempotent update
        add_track_to_collection(conn, collection_uid=col_uid, track_uid=t2, position=5)

        rows = get_collection_tracks(conn, col_uid)
        cols = list_collections(conn, collection_type="playlist", limit=50)

        # Remove one
        remove_track_from_collection(conn, collection_uid=col_uid, track_uid=t1)
        rows_after_remove = get_collection_tracks(conn, col_uid)

    print("Collection UID:", col_uid)
    print("Tracks (ordered):")
    for r in rows:
        print(f"  pos={r['position']}: {r['title']}")

    print("\nCollections found (playlist):", len(cols))

    # Assertions
    assert len(rows) == 3
    # After updating position, Ivy should be at pos=5 (end if you sort ASC, but still present)
    ivy = [r for r in rows if r["title"] == "Ivy"][0]
    assert ivy["position"] == 5

    assert len(rows_after_remove) == 2
    assert all(r["title"] != "Nights" for r in rows_after_remove)


if __name__ == "__main__":
    main()
