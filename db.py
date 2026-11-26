from pathlib import Path
import sqlite3
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "clipper.db"

def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db(conn):
    """Create the clips table if it doesn't exist yet"""
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS clips (
            id          TEXT PRIMARY KEY,
            creator     TEXT,
            title       TEXT,
            view_count  INTEGER,
            duration    REAL,
            video_id    TEXT,
            vod_offset  INTEGER,
            url         TEXT,
            created_at  TEXT,
            first_seen  TEXT,
            last_seen   TEXT
        )
    """

    conn.execute(create_table_sql)
    conn.commit()


def save_clips(conn, creator, clips):
    """Add new clips, or update views for clips already saved.
    Returns how many were new."""
    now = datetime.now(timezone.utc).isoformat()
    new_count = 0

    insert_table_sql = """
        INSERT INTO clips (id, creator, title, view_count, duration,
                            video_id, vod_offset, url, created_at,
                            first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            view_count = excluded.view_count,
            last_seen  = excluded.last_seen
    """

    for clip in clips:
        exists = conn.execute("SELECT 1 FROM clips WHERE id = ?", (clip["id"],)).fetchone()
        if not exists:
            new_count += 1

        conn.execute(insert_table_sql, (
            clip["id"], creator, clip["title"], clip["view_count"],
            clip["duration"], clip["video_id"], clip["vod_offset"],
            clip["url"], clip["created_at"],
            now, now,
        ))

    conn.commit()
    return new_count
    