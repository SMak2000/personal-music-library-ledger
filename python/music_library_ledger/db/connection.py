import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

def get_connection() -> sqlite3.Connection:
    db_path = os.environ["SQLITE_DB_PATH"]
    db_path = Path(db_path).expanduser().resolve()

    print("DB_PATH =", db_path)
    print("Exists:", db_path.exists())
    print("Is file:", db_path.is_file())
    print("Parent exists:", db_path.parent.exists())
    conn = sqlite3.connect(db_path)

    # Always enforce foreign keys (SQLite gotcha)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Safer writes for Drive / synced filesystems
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = FULL;")

    # Rows as dict-like objects
    conn.row_factory = sqlite3.Row

    return conn
