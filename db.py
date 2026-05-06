"""SQLite 데이터베이스: 콘텐츠 큐 + 중복 방지 (스레드 JSON 지원)"""
import hashlib
import json
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


def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _dedup_key(tweet_text: str) -> str:
    """스레드(JSON 배열)면 첫 트윗, 단일이면 전체를 해시 키로 사용"""
    try:
        parsed = json.loads(tweet_text)
        if isinstance(parsed, list) and parsed:
            return parsed[0]
    except (json.JSONDecodeError, ValueError):
        pass
    return tweet_text


def is_content_duplicate(tweet_text: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM posted_hashes WHERE hash=?",
        (content_hash(_dedup_key(tweet_text)),)
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

    result = []
    for r in rows:
        d = dict(r)
        # 스레드(JSON 배열) 여부 판별
        try:
            parsed = json.loads(d['tweet_text'])
            if isinstance(parsed, list) and len(parsed) > 1:
                d['is_thread'] = True
                d['thread_tweets'] = parsed
            else:
                d['is_thread'] = False
        except (json.JSONDecodeError, ValueError):
            d['is_thread'] = False
        result.append(d)
    return result


def mark_content_posted(tweet_text: str):
    key = _dedup_key(tweet_text)
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO posted_hashes (hash, content_snippet, posted_at) VALUES (?,?,?)",
        (content_hash(key), key[:80], datetime.datetime.now().isoformat())
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


def clear_pending_queue():
    """기존 pending 트윗 전체 삭제 (품질 개선 후 재생성용)"""
    conn = get_db()
    deleted = conn.execute("DELETE FROM content_queue WHERE status='pending'").rowcount
    conn.commit()
    conn.close()
    return deleted


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
