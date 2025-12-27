from music_library_ledger.db.connection import get_connection
from music_library_ledger.db.tracks import TrackInput, upsert_track, get_track_by_uid

conn = get_connection()
with conn:
    uid = upsert_track(conn, TrackInput(title="Nights", album="Blonde", duration_ms=300000, media_type="song"))
    row = get_track_by_uid(conn, uid)
    print(dict(row))
