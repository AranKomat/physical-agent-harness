"""Durable reservations and request records. A timeout never refunds unknown spend."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from physical_harness.integrations.experiment.validation import digest, dumps, integer, loads, text


class BudgetExceeded(RuntimeError):
    pass


class DuplicateCall(RuntimeError):
    pass


class Journal:
    def __init__(self, path: str | Path, episode: str, *, max_microusd: int, max_calls: int):
        self.episode = text(episode, "episode", 256)
        integer(max_microusd)
        integer(max_calls, minimum=1)
        self.max_microusd, self.max_calls = max_microusd, max_calls
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY, body TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS calls(
            id TEXT PRIMARY KEY, role TEXT NOT NULL, request_hash TEXT NOT NULL,
            reserved INTEGER NOT NULL, actual INTEGER, status TEXT NOT NULL,
            request TEXT NOT NULL, response TEXT, error TEXT);
          CREATE TABLE IF NOT EXISTS records(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
            id TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(kind,id));
        """)
        settings = dumps(dict(episode=episode, max_microusd=max_microusd,
                              max_calls=max_calls)).decode()
        with self.db:
            old = self.db.execute("SELECT body FROM settings WHERE id=1").fetchone()
            if old and old[0] != settings:
                self.db.close()
                raise ValueError("Journal episode/budget changed; use a new run")
            self.db.execute("INSERT OR IGNORE INTO settings VALUES(1,?)", (settings,))

    def reserve(self, call_id: str, role: str, request: dict, upper_microusd: int) -> None:
        text(call_id, "call id", 256)
        text(role, "role", 64)
        integer(upper_microusd)
        with self.lock, self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if self.db.execute("SELECT 1 FROM calls WHERE id=?", (call_id,)).fetchone():
                raise DuplicateCall("Call ID already reserved; never implicitly resubmit")
            count, exposure = self.db.execute(
                "SELECT COUNT(*),COALESCE(SUM(COALESCE(actual,reserved)),0) FROM calls"
            ).fetchone()
            if count >= self.max_calls or exposure + upper_microusd > self.max_microusd:
                raise BudgetExceeded("Call count or maximum estimated spend would exceed budget")
            self.db.execute("INSERT INTO calls VALUES(?,?,?,?,?,?,?,?,?)", (
                call_id, role, digest(request), upper_microusd, None, "reserved",
                dumps(request).decode(), None, None))

    def complete(self, call_id: str, response: dict, actual_microusd: int) -> None:
        integer(actual_microusd)
        with self.lock, self.db:
            row = self.db.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
            if row is None or row["status"] != "reserved":
                raise ValueError("Only reserved calls can be completed")
            self.db.execute("UPDATE calls SET actual=?,status=?,response=? WHERE id=?", (
                actual_microusd, "overrun" if actual_microusd > row["reserved"] else "completed",
                dumps(response).decode(), call_id))
        if actual_microusd > row["reserved"]:
            raise BudgetExceeded("Provider usage exceeded the declared bound; run must stop")

    def fail(self, call_id: str, error: str) -> None:
        # Only a type/code is recorded; exception text can contain URLs or secrets.
        with self.lock, self.db:
            self.db.execute("UPDATE calls SET status='ambiguous',error=? "
                            "WHERE id=? AND status='reserved'", (text(error, maximum=256), call_id))

    def put(self, kind: str, identifier: str, body: dict) -> None:
        data = dumps(body).decode()
        with self.lock, self.db:
            old = self.db.execute("SELECT body FROM records WHERE kind=? AND id=?",
                                  (kind, identifier)).fetchone()
            if old:
                if old[0] != data:
                    raise ValueError("Immutable run record changed")
                return
            self.db.execute("INSERT INTO records(kind,id,body) VALUES(?,?,?)",
                            (text(kind), text(identifier), data))

    def get(self, kind: str, identifier: str) -> dict:
        with self.lock:
            row = self.db.execute("SELECT body FROM records WHERE kind=? AND id=?",
                                  (kind, identifier)).fetchone()
        if row is None:
            raise ValueError("Unknown run record")
        return loads(row[0])

    def records(self, kind: str) -> list[dict]:
        with self.lock:
            return [dict(id=r["id"], **loads(r["body"])) for r in self.db.execute(
                "SELECT id,body FROM records WHERE kind=? ORDER BY seq", (kind,))]

    def report(self) -> dict[str, Any]:
        with self.lock:
            rows = self.db.execute(
                "SELECT role,COUNT(*) AS calls,SUM(COALESCE(actual,reserved)) AS exposure,"
                "SUM(COALESCE(actual,0)) AS accounted,"
                "SUM(CASE WHEN actual IS NULL THEN 1 ELSE 0 END) AS unresolved "
                "FROM calls GROUP BY role ORDER BY role").fetchall()
        return {"episode": self.episode, "roles": [dict(r) for r in rows],
                "currency": "USD", "unit": "microdollars", "includes_gpu_rental": False}

    def close(self):
        with self.lock:
            self.db.close()
