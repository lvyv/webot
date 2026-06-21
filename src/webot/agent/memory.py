import json
import os
from datetime import datetime

from ..utils import get_logger

logger = get_logger(__name__)


class MemoryBackend:
    def save_message(self, chat_name, role, content, metadata=None):
        raise NotImplementedError

    def get_history(self, chat_name, limit=30):
        raise NotImplementedError

    def search(self, query, chat_name=None):
        raise NotImplementedError

    def get_all_chats(self):
        raise NotImplementedError


class JsonLinesBackend(MemoryBackend):
    def __init__(self, path="memory.jsonl"):
        self.path = path

    def save_message(self, chat_name, role, content, metadata=None):
        entry = {
            "chat_name": chat_name,
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            entry["metadata"] = metadata
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_history(self, chat_name, limit=30):
        if not os.path.exists(self.path):
            return []
        result = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("chat_name") == chat_name:
                    result.append(entry)
        return result[-limit:]

    def search(self, query, chat_name=None):
        if not os.path.exists(self.path):
            return []
        result = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if chat_name and entry.get("chat_name") != chat_name:
                    continue
                if query.lower() in entry.get("content", "").lower():
                    result.append(entry)
        return result

    def get_all_chats(self):
        if not os.path.exists(self.path):
            return []
        chats = set()
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                cn = entry.get("chat_name")
                if cn:
                    chats.add(cn)
        return sorted(chats)


class SqliteBackend(MemoryBackend):
    def __init__(self, path="memory.db"):
        self.path = path
        self._conn = None
        self._ensure_table()

    def _get_conn(self):
        if self._conn is None:
            import sqlite3
            self._conn = sqlite3.connect(self.path)
        return self._conn

    def _ensure_table(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_name TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_name ON messages(chat_name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)
        """)
        conn.commit()

    def save_message(self, chat_name, role, content, metadata=None):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO messages (chat_name, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            (chat_name, role, content, datetime.now().isoformat(),
             json.dumps(metadata, ensure_ascii=False) if metadata else None),
        )
        conn.commit()

    def get_history(self, chat_name, limit=30):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT chat_name, role, content, timestamp, metadata FROM messages WHERE chat_name=? ORDER BY id DESC LIMIT ?",
            (chat_name, limit),
        ).fetchall()
        result = []
        for row in reversed(rows):
            entry = {"chat_name": row[0], "role": row[1], "content": row[2], "timestamp": row[3]}
            if row[4]:
                entry["metadata"] = json.loads(row[4])
            result.append(entry)
        return result

    def search(self, query, chat_name=None):
        conn = self._get_conn()
        like = f"%{query}%"
        if chat_name:
            rows = conn.execute(
                "SELECT chat_name, role, content, timestamp, metadata FROM messages WHERE chat_name=? AND content LIKE ? ORDER BY id DESC LIMIT 100",
                (chat_name, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT chat_name, role, content, timestamp, metadata FROM messages WHERE content LIKE ? ORDER BY id DESC LIMIT 100",
                (like,),
            ).fetchall()
        result = []
        for row in reversed(rows):
            entry = {"chat_name": row[0], "role": row[1], "content": row[2], "timestamp": row[3]}
            if row[4]:
                entry["metadata"] = json.loads(row[4])
            result.append(entry)
        return result

    def get_all_chats(self):
        conn = self._get_conn()
        rows = conn.execute("SELECT DISTINCT chat_name FROM messages ORDER BY chat_name").fetchall()
        return [r[0] for r in rows]


class Memory:
    def __init__(self, backend=None):
        if backend is None:
            backend = JsonLinesBackend()
        self._backend = backend
        logger.info(f"Memory 后端: {type(backend).__name__} ({getattr(backend, 'path', '')})")

    @property
    def backend(self):
        return self._backend

    def save_message(self, chat_name, role, content, metadata=None):
        self._backend.save_message(chat_name, role, content, metadata)

    def get_history(self, chat_name, limit=30):
        return self._backend.get_history(chat_name, limit)

    def search(self, query, chat_name=None):
        return self._backend.search(query, chat_name)

    def get_all_chats(self):
        return self._backend.get_all_chats()
