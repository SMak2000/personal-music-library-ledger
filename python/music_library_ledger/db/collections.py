import sqlite3
import uuid
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class CollectionInput:
    name: str
    collection_type: str = "playlist"  # maps to SQL column: collections.collection_type
    description: Optional[str] = None


def create_collection_uid() -> str:
    return str(uuid.uuid4())


def get_collection_by_uid(
    conn: sqlite3.Connection,
    collection_uid: str,
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM collections WHERE collection_uid = ?;",
        (collection_uid,),
    ).fetchone()


def get_collection_by_name_and_type(
    conn: sqlite3.Connection,
    name: str,
    collection_type: str,
) -> Optional[sqlite3.Row]:
    return conn.execute(
        """
        SELECT *
        FROM collections
        WHERE name = ? AND collection_type = ?;
        """,
        (name.strip(), collection_type.strip()),
    ).fetchone()


def get_or_create_collection(
    conn: sqlite3.Connection,
    collection: CollectionInput,
    *,
    collection_uid: Optional[str] = None,
) -> str:
    if not collection.name or not collection.name.strip():
        raise ValueError("Collection name is required")
    if not collection.collection_type or not collection.collection_type.strip():
        raise ValueError("collection_type is required")

    name = collection.name.strip()
    ctype = collection.collection_type.strip()

    existing = get_collection_by_name_and_type(conn, name, ctype)
    if existing:
        if collection.description is not None:
            conn.execute(
                """
                UPDATE collections
                SET description = ?,
                    updated_at = datetime('now')
                WHERE collection_uid = ?;
                """,
                (collection.description, existing["collection_uid"]),
            )
        return existing["collection_uid"]

    uid = collection_uid or create_collection_uid()

    conn.execute(
        """
        INSERT INTO collections (
            collection_uid,
            name,
            collection_type,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'));
        """,
        (uid, name, ctype, collection.description),
    )

    return uid


def add_track_to_collection(
    conn: sqlite3.Connection,
    *,
    collection_uid: str,
    track_uid: str,
    position: int,
    added_at: Optional[str] = None,
) -> None:
    if position < 0:
        raise ValueError("position must be >= 0")

    existing = conn.execute(
        """
        SELECT position
        FROM collection_items
        WHERE collection_uid = ? AND track_uid = ?;
        """,
        (collection_uid, track_uid),
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE collection_items
            SET position = ?,
                added_at = COALESCE(?, added_at)
            WHERE collection_uid = ? AND track_uid = ?;
            """,
            (position, added_at, collection_uid, track_uid),
        )
        return

    if added_at is None:
        conn.execute(
            """
            INSERT INTO collection_items (
                collection_uid,
                track_uid,
                position,
                added_at
            )
            VALUES (?, ?, ?, datetime('now'));
            """,
            (collection_uid, track_uid, position),
        )
    else:
        conn.execute(
            """
            INSERT INTO collection_items (
                collection_uid,
                track_uid,
                position,
                added_at
            )
            VALUES (?, ?, ?, ?);
            """,
            (collection_uid, track_uid, position, added_at),
        )



def remove_track_from_collection(
    conn: sqlite3.Connection,
    *,
    collection_uid: str,
    track_uid: str,
) -> None:
    conn.execute(
        """
        DELETE FROM collection_items
        WHERE collection_uid = ? AND track_uid = ?;
        """,
        (collection_uid, track_uid),
    )


def get_collection_tracks(
    conn: sqlite3.Connection,
    collection_uid: str,
) -> Sequence[sqlite3.Row]:
    return conn.execute(
        """
        SELECT t.*, ci.position, ci.added_at
        FROM collection_items ci
        JOIN tracks t ON t.track_uid = ci.track_uid
        WHERE ci.collection_uid = ?
        ORDER BY ci.position ASC;
        """,
        (collection_uid,),
    ).fetchall()


def list_collections(
    conn: sqlite3.Connection,
    *,
    collection_type: Optional[str] = None,
    limit: int = 500,
) -> Sequence[sqlite3.Row]:
    if limit <= 0:
        raise ValueError("limit must be > 0")

    params = []
    where_sql = ""
    if collection_type is not None:
        where_sql = "WHERE collection_type = ?"
        params.append(collection_type.strip())

    params.append(limit)

    return conn.execute(
        f"""
        SELECT *
        FROM collections
        {where_sql}
        ORDER BY updated_at DESC
        LIMIT ?;
        """,
        tuple(params),
    ).fetchall()
