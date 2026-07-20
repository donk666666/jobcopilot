"""SQLite 会话持久化层，替代内存 dict"""

import sqlite3
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
        self._lock = threading.RLock()
        self._init_db()
        self._migrate()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        with self._lock, self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT NOT NULL,
                    user_id TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (id, user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL DEFAULT '',
                    summary_text TEXT NOT NULL DEFAULT '',
                    last_message_idx INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, user_id)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(user_id, session_id, id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, updated_at DESC)"
            )

    def _migrate(self):
        """处理表结构变更"""
        with self._lock, self._get_conn() as conn:
            # 检查是否需要添加 user_id 列
            cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
            if "user_id" not in cols:
                conn.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
                # 重建复合主键需要重建表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions_new (
                        id TEXT NOT NULL,
                        user_id TEXT NOT NULL DEFAULT '',
                        title TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (id, user_id)
                    )
                """)
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO sessions_new SELECT id, '', title, created_at, updated_at FROM sessions"
                    )
                    conn.execute("DROP TABLE sessions")
                    conn.execute("ALTER TABLE sessions_new RENAME TO sessions")
                except Exception:
                    pass  # 表已是最新结构

            cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
            if "user_id" not in cols:
                conn.execute("ALTER TABLE messages ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")

            cols = {r[1] for r in conn.execute("PRAGMA table_info(summaries)").fetchall()}
            if "user_id" not in cols:
                conn.execute("ALTER TABLE summaries ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS summaries_new (
                        session_id TEXT NOT NULL,
                        user_id TEXT NOT NULL DEFAULT '',
                        summary_text TEXT NOT NULL DEFAULT '',
                        last_message_idx INTEGER NOT NULL DEFAULT 0,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (session_id, user_id)
                    )
                """)
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO summaries_new SELECT session_id, '', summary_text, last_message_idx, updated_at FROM summaries"
                    )
                    conn.execute("DROP TABLE summaries")
                    conn.execute("ALTER TABLE summaries_new RENAME TO summaries")
                except Exception:
                    pass

    # ---- 会话 CRUD ----

    def create_session(self, session_id: str, user_id: str, title: str = "") -> dict:
        with self._lock, self._get_conn() as conn:
            now = _now()
            conn.execute(
                "INSERT OR IGNORE INTO sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, user_id, title or "新对话", now, now),
            )
            return {
                "id": session_id, "user_id": user_id,
                "title": title or "新对话", "created_at": now, "updated_at": now,
            }

    def ensure_session(self, session_id: str, user_id: str) -> None:
        with self._lock, self._get_conn() as conn:
            now = _now()
            conn.execute(
                "INSERT OR IGNORE INTO sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, user_id, "新对话", now, now),
            )

    def list_sessions(self, user_id: str, limit: int = 50) -> list[dict]:
        with self._get_conn() as conn:
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            rows = conn.execute(
                """SELECT id, user_id, title, created_at, updated_at FROM sessions
                   WHERE user_id = ? AND updated_at >= ?
                   ORDER BY updated_at DESC LIMIT ?""",
                (user_id, cutoff, limit),
            ).fetchall()
            return [
                {"id": r["id"], "user_id": r["user_id"],
                 "title": r["title"], "created_at": r["created_at"], "updated_at": r["updated_at"]}
                for r in rows
            ]

    def get_session(self, session_id: str, user_id: str) -> dict | None:
        with self._get_conn() as conn:
            r = conn.execute(
                "SELECT id, user_id, title, created_at, updated_at FROM sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if not r:
                return None
            return {
                "id": r["id"], "user_id": r["user_id"],
                "title": r["title"], "created_at": r["created_at"], "updated_at": r["updated_at"],
            }

    def update_title(self, session_id: str, user_id: str, title: str):
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (title, _now(), session_id, user_id),
            )

    def delete_session(self, session_id: str, user_id: str):
        with self._lock, self._get_conn() as conn:
            conn.execute("DELETE FROM summaries WHERE session_id = ? AND user_id = ?", (session_id, user_id))
            conn.execute("DELETE FROM messages WHERE session_id = ? AND user_id = ?", (session_id, user_id))
            conn.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id))

    # ---- 消息 CRUD ----

    def add_message(self, session_id: str, user_id: str, role: str, content: str) -> int:
        with self._lock:
            self._ensure_session_locked(session_id, user_id)
            with self._get_conn() as conn:
                now = _now()
                cur = conn.execute(
                    "INSERT INTO messages (session_id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, user_id, role, content, now),
                )
                conn.execute(
                    "UPDATE sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
                    (now, session_id, user_id),
                )
                return cur.lastrowid

    def _ensure_session_locked(self, session_id: str, user_id: str) -> None:
        """内部方法，调用方已持有 _lock"""
        with self._get_conn() as conn:
            now = _now()
            conn.execute(
                "INSERT OR IGNORE INTO sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, user_id, "新对话", now, now),
            )

    def get_history(self, session_id: str, user_id: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, role, content FROM messages WHERE session_id = ? AND user_id = ? ORDER BY id ASC",
                (session_id, user_id),
            ).fetchall()
            return [{"id": r["id"], "role": r["role"], "content": r["content"]} for r in rows]

    def get_last_message_idx(self, session_id: str, user_id: str) -> int:
        with self._get_conn() as conn:
            r = conn.execute(
                "SELECT MAX(id) as max_id FROM messages WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            return r["max_id"] or 0

    def get_message_count(self, session_id: str, user_id: str) -> int:
        with self._get_conn() as conn:
            r = conn.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            return r["cnt"]

    # ---- 摘要 CRUD ----

    def get_summary(self, session_id: str, user_id: str) -> str | None:
        with self._get_conn() as conn:
            r = conn.execute(
                "SELECT summary_text FROM summaries WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            return r["summary_text"] if r else None

    def save_summary(self, session_id: str, user_id: str, summary_text: str, last_message_idx: int):
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """INSERT INTO summaries (session_id, user_id, summary_text, last_message_idx, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(session_id, user_id) DO UPDATE SET
                   summary_text = excluded.summary_text,
                   last_message_idx = excluded.last_message_idx,
                   updated_at = excluded.updated_at""",
                (session_id, user_id, summary_text, last_message_idx, _now()),
            )

    def get_summary_last_idx(self, session_id: str, user_id: str) -> int:
        with self._get_conn() as conn:
            r = conn.execute(
                "SELECT last_message_idx FROM summaries WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            return r["last_message_idx"] if r else 0
