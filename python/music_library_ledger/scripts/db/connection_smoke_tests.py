from music_library_ledger.db.connection import get_connection

conn = get_connection()
rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()

print("Tables:")
for r in rows:
    print(" -", r["name"])
