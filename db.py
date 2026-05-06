"""SQLite 데이터베이스: 콘텐츠 큐 + 중복 방지"""
import hashlib
import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / 'xauto.db'


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posted_hashes (
            hash TEXT PRIMARY KEY,
            content_snippet TEXT,
            posted_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niche TEXT NOT NULL,
            tweet_text TEXT NOT NULL,
            source_title TEXT,
            source_link TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posted_source_ids (
            source_id TEXT PRIMARY KEY,
            posted_at TEXT
        )
    """)
    conn.commit()
    return conn


def content_hash(tweet_text: str) -> str:
    return hashlib.md5(tweet_text.encode()).hexdigest()


def is_content_duplicate(tweet_text: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM posted_hashes WHERE hash=?", (content_hash(tweet_text),)
    ).fetchone()
    conn.close()
    return row is not None


def enqueue_tweet(niche: str, tweet_text: str, source_title: str, source_link: str) -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO content_queue (niche, tweet_text, source_title, source_link, created_at, status) VALUES (?,?,?,?,?,?)",
        (niche, tweet_text, source_title, source_link, datetime.datetime.now().isoformat(), 'pending')
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_pending_tweets(limit: int = 5, preferred_niche: str = None) -> list[dict]:
    conn = get_db()
    if preferred_niche:
        rows = conn.execute(
            "SELECT * FROM content_queue WHERE status='pending' AND niche=? ORDER BY created_at ASC LIMIT ?",
            (preferred_niche, limit)
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT * FROM content_queue WHERE status='pending' ORDER BY created_at ASC LIMIT ?",
                (limit,)
            ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM content_queue WHERE status='pending' ORDER BY created_at ASC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_content_posted(tweet_text: str):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO posted_hashes (hash, content_snippet, posted_at) VALUES (?,?,?)",
        (content_hash(tweet_text), tweet_text[:80], datetime.datetime.now().isoformat())
    )
    conn.execute(
        "UPDATE content_queue SET status='posted' WHERE tweet_text=? AND status='pending'",
        (tweet_text,)
    )
    conn.commit()
    conn.close()


def mark_queue_status(row_id: int, status: str):
    conn = get_db()
    conn.execute("UPDATE content_queue SET status=? WHERE id=?", (status, row_id))
    conn.commit()
    conn.close()


def queue_depth() -> int:
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM content_queue WHERE status='pending'").fetchone()[0]
    conn.close()
    return count


def is_source_posted(source_id: str) -> bool:
    conn = get_db()
    row = conn.execute("SELECT 1 FROM posted_source_ids WHERE source_id=?", (source_id,)).fetchone()
    conn.close()
    return row is not None


def mark_source_posted(source_id: str):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO posted_source_ids (source_id, posted_at) VALUES (?,?)",
        (source_id, datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def monthly_post_count() -> int:
    first_of_month = datetime.date.today().replace(day=1).isoformat()
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM posted_hashes WHERE posted_at >= ?", (first_of_month,)
    ).fetchone()[0]
    conn.close()
    return count