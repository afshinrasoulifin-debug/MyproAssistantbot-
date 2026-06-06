
from __future__ import annotations
"""
Victor Memory — SQLite Backend
Replaces JSON file persistence with proper SQLite.

Benefits:
  - Atomic writes (no corruption on crash)
  - Concurrent access safe
  - Query performance (indexed)
  - No full-file rewrite on every save

Integration:
  Replace MemoryStore._save_memories() / _load() with these methods.
  Or use VictorDB as a drop-in backend.
"""

import sqlite3
import json
import time
import os
import threading
from typing import List, Dict, Optional, Any
from pathlib import Path
from contextlib import contextmanager


class VictorDB:
    """SQLite backend for Victor's memory system."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> Any:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    topic TEXT NOT NULL DEFAULT '',
                    memory_type TEXT NOT NULL DEFAULT 'fact',
                    source TEXT NOT NULL DEFAULT 'user',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    importance REAL NOT NULL DEFAULT 0.5,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    relation TEXT NOT NULL DEFAULT 'related',
                    weight REAL NOT NULL DEFAULT 1.0,
                    UNIQUE(from_node, to_node, relation)
                );

                CREATE TABLE IF NOT EXISTS inference_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    condition_topic TEXT NOT NULL,
                    condition_keywords TEXT NOT NULL,
                    conclusion TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.8,
                    use_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wrong_response TEXT NOT NULL,
                    correct_response TEXT NOT NULL,
                    context TEXT DEFAULT '',
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interaction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_input TEXT NOT NULL,
                    response TEXT NOT NULL,
                    intent TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.0,
                    action TEXT DEFAULT 'chat',
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_memories_topic ON memories(topic);
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS idx_memories_confidence ON memories(confidence);
                CREATE INDEX IF NOT EXISTS idx_graph_from ON graph_edges(from_node);
                CREATE INDEX IF NOT EXISTS idx_graph_to ON graph_edges(to_node);
                CREATE INDEX IF NOT EXISTS idx_corrections_created ON corrections(created_at);
                CREATE INDEX IF NOT EXISTS idx_log_created ON interaction_log(created_at);
            """)

    @contextmanager
    def _conn(self) -> Any:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Memory CRUD ──

    def store_memory(self, mid: str, content: str, topic: str = "",
                     memory_type: str = "fact", source: str = "user",
                     confidence: float = 1.0, importance: float = 0.5,
                     tags: List[str] = None, metadata: Dict = None) -> None:
        now = time.time()
        with self._lock, self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO memories 
                   (id, content, topic, memory_type, source, confidence, importance,
                    access_count, created_at, last_accessed, tags, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
                (mid, content, topic, memory_type, source, confidence, importance,
                 now, now, json.dumps(tags or []), json.dumps(metadata or {}))
            )

    def get_all_memories(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM memories ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_memory(self, mid: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (mid,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                    (time.time(), mid)
                )
                return dict(row)
            return None

    def search_memories(self, query: str, limit: int = 10) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? OR topic LIKE ? ORDER BY confidence DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_memories_by_topic(self, topic: str) -> int:
        with self._lock, self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE topic LIKE ?",
                (f"%{topic}%",)
            )
            return cursor.rowcount

    def reinforce_memory(self, mid: str, amount: float = 0.5) -> Any:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE memories SET confidence = MIN(5.0, confidence + ?) WHERE id = ?",
                (amount, mid)
            )

    def weaken_memory(self, mid: str, amount: float = 0.3) -> Any:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE memories SET confidence = MAX(0.0, confidence - ?) WHERE id = ?",
                (amount, mid)
            )

    # ── Graph ──

    def add_edge(self, from_node: str, to_node: str, relation: str = "related",
                 weight: float = 1.0) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO graph_edges (from_node, to_node, relation, weight)
                   VALUES (?, ?, ?, ?)""",
                (from_node, to_node, relation, weight)
            )

    def get_edges_from(self, node: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM graph_edges WHERE from_node = ? OR to_node = ?",
                (node, node)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Corrections ──

    def add_correction(self, wrong: str, correct: str, context: str = "") -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO corrections (wrong_response, correct_response, context, created_at) VALUES (?, ?, ?, ?)",
                (wrong, correct, context, time.time())
            )

    def get_corrections(self, limit: int = 50) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM corrections ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Interaction Log ──

    def log_interaction(self, user_input: str, response: str,
                        intent: str = "", confidence: float = 0.0,
                        action: str = "chat") -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """INSERT INTO interaction_log 
                   (user_input, response, intent, confidence, action, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_input, response, intent, confidence, action, time.time())
            )

    def get_interaction_stats(self) -> Dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM interaction_log").fetchone()[0]
            today = conn.execute(
                "SELECT COUNT(*) FROM interaction_log WHERE created_at > ?",
                (time.time() - 86400,)
            ).fetchone()[0]
            avg_conf = conn.execute(
                "SELECT AVG(confidence) FROM interaction_log WHERE confidence > 0"
            ).fetchone()[0] or 0.0

            return {
                "total_interactions": total,
                "today_interactions": today,
                "avg_confidence": round(avg_conf, 3),
            }

    # ── Maintenance ──

    def backup(self, backup_path: str) -> Any:
        import shutil
        with self._lock:
            with self._conn() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            shutil.copy2(self.db_path, backup_path)

    def vacuum(self) -> Any:
        with self._lock, self._conn() as conn:
            conn.execute("VACUUM")

    def get_db_stats(self) -> Dict:
        with self._conn() as conn:
            memories = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            edges = conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
            rules = conn.execute("SELECT COUNT(*) FROM inference_rules").fetchone()[0]
            corrections = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
            interactions = conn.execute("SELECT COUNT(*) FROM interaction_log").fetchone()[0]

        size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        return {
            "memories": memories,
            "graph_edges": edges,
            "inference_rules": rules,
            "corrections": corrections,
            "interactions": interactions,
            "db_size_bytes": size,
            "db_size_mb": round(size / (1024 * 1024), 2),
        }


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Database Features
# ══════════════════════════════════════════════════════════════

class VictorDBAnalytics:
    """Analytics overlay for VictorDB."""

    def __init__(self, db: "VictorDB") -> None:
        self._db = db
        self._query_count = 0
        self._write_count = 0
        self._cache_hits = 0

    def on_query(self) -> None:
        self._query_count += 1

    def on_write(self) -> None:
        self._write_count += 1

    def on_cache_hit(self) -> None:
        self._cache_hits += 1

    def report(self) -> dict:
        db_stats = self._db.get_db_stats()
        return {
            **db_stats,
            "queries": self._query_count,
            "writes": self._write_count,
            "cache_hits": self._cache_hits,
            "cache_ratio": (
                self._cache_hits / max(self._query_count, 1)
            ),
        }


class AutoVacuum:
    """Scheduled vacuum + optimization for SQLite."""

    def __init__(self, db: "VictorDB", interval_hours: float = 24.0) -> None:
        self._db = db
        self._interval = interval_hours * 3600
        self._last_vacuum = 0.0

    def should_vacuum(self) -> bool:
        import time
        return (time.time() - self._last_vacuum) > self._interval

    def run(self) -> dict:
        import time
        start = time.time()
        self._db.vacuum()
        self._last_vacuum = time.time()
        return {
            "vacuumed": True,
            "duration_ms": round((time.time() - start) * 1000, 1),
        }


class MemoryDecay:
    """Gradually decay old, unused memories to keep the DB lean."""

    def __init__(self, db: "VictorDB", decay_rate: float = 0.01) -> None:
        self._db = db
        self._decay_rate = decay_rate

    def decay_pass(self, min_age_days: float = 30.0) -> int:
        """Weaken old, rarely-accessed memories."""
        import time
        cutoff = time.time() - (min_age_days * 86400)
        memories = self._db.get_all_memories()
        decayed = 0
        for m in memories:
            if m.get("last_accessed", 0) < cutoff and m.get("importance", 1.0) > 0.1:
                self._db.weaken_memory(m["id"], self._decay_rate)
                decayed += 1
        return decayed


