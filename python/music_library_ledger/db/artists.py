import sqlite3
import uuid
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class ArtistInput:
  name: str


def create_artist_uid() -> str:
  return str(uuid.uuid4())


def get_artist_by_uid(
  conn: sqlite3.Connection,
  artist_uid: str,
) -> Optional[sqlite3.Row]:
  return conn.execute(
    "SELECT * FROM artists WHERE artist_uid = ?;",
    (artist_uid,),
  ).fetchone()


def get_artist_by_name(
  conn: sqlite3.Connection,
  name: str,
) -> Optional[sqlite3.Row]:
  return conn.execute(
    "SELECT * FROM artists WHERE name = ?;",
    (name.strip(),),
  ).fetchone()


def get_or_create_artist(
  conn: sqlite3.Connection,
  artist: ArtistInput,
  *,
  artist_uid: Optional[str] = None,
) -> str:
  if not artist.name or not artist.name.strip():
    raise ValueError("Artist name is required")

  name = artist.name.strip()

  existing = get_artist_by_name(conn, name)
  if existing:
    return existing["artist_uid"]

  uid = artist_uid or create_artist_uid()

  conn.execute(
    """
    INSERT INTO artists (
      artist_uid,
      name,
      created_at
    )
    VALUES (?, ?, datetime('now'));
    """,
    (uid, name),
  )

  return uid


def attach_artist_to_track(
  conn: sqlite3.Connection,
  *,
  track_uid: str,
  artist_uid: str,
  artist_order: int,
  role: str = "primary",
) -> None:
  if artist_order < 0:
    raise ValueError("artist_order must be >= 0")
  if not role or not role.strip():
    raise ValueError("role is required")

  # Idempotent insert: if the (track_uid, artist_uid) already exists, we update its order/role.
  # Note: table has UNIQUE(track_uid, artist_order) so you can't assign two artists the same order.
  existing = conn.execute(
    """
    SELECT artist_order, role
    FROM track_artists
    WHERE track_uid = ? AND artist_uid = ?;
    """,
    (track_uid, artist_uid),
  ).fetchone()

  if existing:
    conn.execute(
      """
      UPDATE track_artists
      SET artist_order = ?,
          role = ?
      WHERE track_uid = ? AND artist_uid = ?;
      """,
      (artist_order, role.strip(), track_uid, artist_uid),
    )
    return

  conn.execute(
    """
    INSERT INTO track_artists (
      track_uid,
      artist_uid,
      artist_order,
      role
    )
    VALUES (?, ?, ?, ?);
    """,
    (track_uid, artist_uid, artist_order, role.strip()),
  )


def get_artists_for_track(
  conn: sqlite3.Connection,
  track_uid: str,
) -> Sequence[sqlite3.Row]:
  return conn.execute(
    """
    SELECT a.*, ta.artist_order, ta.role
    FROM track_artists ta
    JOIN artists a ON a.artist_uid = ta.artist_uid
    WHERE ta.track_uid = ?
    ORDER BY ta.artist_order ASC;
    """,
    (track_uid,),
  ).fetchall()
