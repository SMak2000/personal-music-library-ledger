import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

def get_connection() -> sqlite3.Connection:
    db_path = os.environ["SQLITE_DB_PATH"]

    db_path = Path(db_path).expanduser().resolve()
    conn = sqlite3.connect(db_path)

    # Always enforce foreign keys (SQLite gotcha)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Safer writes for Drive / synced filesystems
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = FULL;")

    # Rows as dict-like objects
    conn.row_factory = sqlite3.Row

    return conn
