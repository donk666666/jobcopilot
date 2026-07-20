"""SQLite 会话持久化层，替代内存 dict"""

import sqlite3
import json
import os
import threading
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sessions.db")


def _now() -> str:
    return datetime.now().isoformat()


class SessionStore:
    def __init__(self, db_path: str = DB_PATH):
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self._migrate()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    session_id TEXT PRIMARY KEY,
                    summary_text TEXT NOT NULL DEFAULT '',
                    last_message_idx INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)")

    def _migrate(self):
        """处理表结构变更（如新增字段）"""
        pass

    # ---- 会话 CRUD ----

    def create_session(self, session_id: str, title: str = "") -> dict:
        with self._lock, self._get_conn() as conn:
            now = _now()
            conn.execute(
                "INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title or "新对话", now, now),
            )
            return {"id": session_id, "title": title or "新对话", "created_at": now, "updated_at": now}

    def ensure_session(self, session_id: str) -> None:
        """如果会话不存在则自动创建"""
        with self._lock, self._get_conn() as conn:
            now = _now()
            conn.execute(
                "INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, "新对话", now, now),
            )

    def list_sessions(self, limit: int = 50, include_archived: bool = False) -> list[dict]:
        with self._get_conn() as conn:
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            if include_archived:
                rows = conn.execute(
                    "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, title, created_at, updated_at FROM sessions WHERE updated_at >= ? ORDER BY updated_at DESC LIMIT ?",
                    (cutoff, limit),
                ).fetchall()
            return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]

    def get_session(self, session_id: str) -> dict | None:
        with self._get_conn() as conn:
            r = conn.execute("SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if not r:
                return None
            return {"id": r["id"], "title": r["title"], "created_at": r["created_at"], "updated_at": r["updated_at"]}

    def update_title(self, session_id: str, title: str):
        with self._lock, self._get_conn() as conn:
            conn.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, _now(), session_id))

    def touch(self, session_id: str):
        with self._lock, self._get_conn() as conn:
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (_now(), session_id))

    def delete_session(self, session_id: str):
        with self._lock, self._get_conn() as conn:
            conn.execute("DELETE FROM summaries WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    # ---- 消息 CRUD ----

    def add_message(self, session_id: str, role: str, content: str) -> int:
        self.ensure_session(session_id)
        with self._lock, self._get_conn() as conn:
            now = _now()
            cur = conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
            return cur.lastrowid

    def get_history(self, session_id: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [{"id": r["id"], "role": r["role"], "content": r["content"]} for r in rows]

    def get_last_message_idx(self, session_id: str) -> int:
        with self._get_conn() as conn:
            r = conn.execute("SELECT MAX(id) as max_id FROM messages WHERE session_id = ?", (session_id,)).fetchone()
            return r["max_id"] or 0

    def get_message_count(self, session_id: str) -> int:
        with self._get_conn() as conn:
            r = conn.execute("SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?", (session_id,)).fetchone()
            return r["cnt"]

    # ---- 摘要 CRUD ----

    def get_summary(self, session_id: str) -> str | None:
        with self._get_conn() as conn:
            r = conn.execute("SELECT summary_text FROM summaries WHERE session_id = ?", (session_id,)).fetchone()
            return r["summary_text"] if r else None

    def save_summary(self, session_id: str, summary_text: str, last_message_idx: int):
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """INSERT INTO summaries (session_id, summary_text, last_message_idx, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET
                   summary_text = excluded.summary_text,
                   last_message_idx = excluded.last_message_idx,
                   updated_at = excluded.updated_at""",
                (session_id, summary_text, last_message_idx, _now()),
            )

    def get_summary_last_idx(self, session_id: str) -> int:
        with self._get_conn() as conn:
            r = conn.execute("SELECT last_message_idx FROM summaries WHERE session_id = ?", (session_id,)).fetchone()
            return r["last_message_idx"] if r else 0

    # ---- 归档 ----

    def archive_old_sessions(self, days: int = 30):
        """标记超过 N 天未活动的会话为归档（摘要保留，消息历史可通过 include_archived 查询）"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute("UPDATE sessions SET updated_at = updated_at WHERE updated_at < ?", (cutoff,))
