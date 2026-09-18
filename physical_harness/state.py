"""Evidence-backed memory with episode isolation and bounded context projection.

This module does NOT detect objects, estimate pose, solve data association, or
certify outcomes. A perception adapter must supply those estimates. 'observed'
means observation-supported, not oracle truth. Model-generated text remains
'inferred'. Full benchmark scores never enter this policy-facing store.
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Iterable


class ContextBudgetExceeded(ValueError):
    pass


def _time(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("Timestamp must be finite, nonnegative simulator time")
    return float(value)


def _text(value: str, name: str, max_length: int = 8192) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"{name} must be nonempty bounded text")
    return value


class WorldState:
    """One writer connection. Use one episode namespace per independent rollout."""

    def __init__(self, database: str | Path, episode: str):
        self.episode = _text(episode, "episode", 256)
        self.db = sqlite3.connect(str(database))
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS evidence(
            episode TEXT NOT NULL, id TEXT NOT NULL, sim_time REAL NOT NULL,
            kind TEXT NOT NULL, uri TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(episode,id));
          CREATE TABLE IF NOT EXISTS events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, episode TEXT NOT NULL,
            sim_time REAL NOT NULL, type TEXT NOT NULL, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS beliefs(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, episode TEXT NOT NULL,
            subject TEXT NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL,
            sim_time REAL NOT NULL, valid_until REAL, evidence_id TEXT NOT NULL,
            epistemic TEXT NOT NULL,
            FOREIGN KEY(episode,evidence_id) REFERENCES evidence(episode,id));
          CREATE TABLE IF NOT EXISTS tasks(
            episode TEXT NOT NULL, id TEXT NOT NULL, goal TEXT NOT NULL,
            status TEXT NOT NULL, evidence_id TEXT, PRIMARY KEY(episode,id));
          CREATE TABLE IF NOT EXISTS task_dependencies(
            episode TEXT NOT NULL, task_id TEXT NOT NULL, dependency TEXT NOT NULL,
            PRIMARY KEY(episode,task_id,dependency));
          CREATE TABLE IF NOT EXISTS task_bindings(
            episode TEXT NOT NULL, task_id TEXT NOT NULL, subject TEXT NOT NULL,
            predicate TEXT NOT NULL, object TEXT NOT NULL,
            PRIMARY KEY(episode,task_id,subject,predicate));
          CREATE TABLE IF NOT EXISTS task_support(
            episode TEXT NOT NULL, task_id TEXT NOT NULL, subject TEXT NOT NULL,
            predicate TEXT NOT NULL, object TEXT NOT NULL, evidence_id TEXT NOT NULL,
            PRIMARY KEY(episode,task_id,subject,predicate));
        """)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "WorldState":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _event(self, kind: str, sim_time: float, payload: dict[str, Any]) -> None:
        self.db.execute(
            "INSERT INTO events(episode,sim_time,type,payload) VALUES(?,?,?,?)",
            (self.episode, sim_time, kind, json.dumps(payload, sort_keys=True, allow_nan=False)),
        )

    def add_evidence(
        self,
        identifier: str,
        sim_time: float,
        kind: str,
        uri: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Immutable evidence. Runtime adapters must enforce the sensor allowlist."""
        _text(identifier, "evidence id", 256)
        sim_time = _time(sim_time)
        if kind not in {"perception", "telemetry", "inference"}:
            raise ValueError(
                "Only legal observation-derived evidence is accepted; no scorer/oracle/command evidence"
            )
        _text(uri, "evidence URI")
        encoded = json.dumps(payload or {}, allow_nan=False, sort_keys=True)
        with self.db:
            self.db.execute(
                "INSERT INTO evidence VALUES(?,?,?,?,?,?)",
                (self.episode, identifier, sim_time, kind, uri, encoded),
            )
            self._event("evidence", sim_time, {"id": identifier, "kind": kind})

    def _evidence(self, identifier: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT * FROM evidence WHERE episode=? AND id=?", (self.episode, identifier)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown evidence in this episode")
        return dict(row)

    def record_command(self, identifier: str, sim_time: float, intended: dict[str, Any]) -> None:
        """A requested action has no effect on believed object locations."""
        with self.db:
            self._event(
                "command_requested",
                _time(sim_time),
                {"id": _text(identifier, "command id"), "intended": intended},
            )

    def belief(self, subject: str, predicate: str) -> dict[str, Any] | None:
        row = self.db.execute(
            """SELECT * FROM beliefs WHERE episode=? AND subject=?
                 AND predicate=? AND valid_until IS NULL ORDER BY seq DESC LIMIT 1""",
            (self.episode, subject, predicate),
        ).fetchone()
        return dict(row) if row else None

    def update(
        self,
        subject: str,
        predicate: str,
        object_value: str,
        evidence_id: str,
        epistemic: str = "observed",
    ) -> bool:
        """Update a single-valued belief (location, visibility, open_state, etc.).

        Generic multi-valued scene edges should use distinct predicates/keys in
        an adapter. Same-time conflicting observations are logged, not resolved
        arbitrarily. A missing detection must not delete a location.
        """
        for value, name in [
            (subject, "subject"),
            (predicate, "predicate"),
            (object_value, "object"),
        ]:
            _text(value, name, 1024)
        if epistemic not in {"observed", "inferred"}:
            raise ValueError("Invalid epistemic status")
        evidence = self._evidence(evidence_id)
        if epistemic == "observed" and evidence["kind"] == "inference":
            raise ValueError("Reasoner inference cannot masquerade as observation")
        previous = self.belief(subject, predicate)
        with self.db:
            if previous and evidence["sim_time"] < previous["sim_time"]:
                self._event(
                    "stale_belief_rejected",
                    evidence["sim_time"],
                    {"subject": subject, "predicate": predicate, "evidence": evidence_id},
                )
                return False
            if previous and evidence["sim_time"] == previous["sim_time"]:
                if previous["object"] == object_value:
                    return False
                self._event(
                    "belief_conflict",
                    evidence["sim_time"],
                    {
                        "subject": subject,
                        "predicate": predicate,
                        "old": previous["object"],
                        "new": object_value,
                        "evidence": evidence_id,
                    },
                )
                self._invalidate_tasks(subject, predicate, object_value, evidence["sim_time"])
                return False
            if previous:
                self.db.execute(
                    "UPDATE beliefs SET valid_until=? WHERE seq=?",
                    (evidence["sim_time"], previous["seq"]),
                )
            self.db.execute(
                """INSERT INTO beliefs(episode,subject,predicate,object,sim_time,evidence_id,epistemic)
                             VALUES(?,?,?,?,?,?,?)""",
                (
                    self.episode,
                    subject,
                    predicate,
                    object_value,
                    evidence["sim_time"],
                    evidence_id,
                    epistemic,
                ),
            )
            self._event(
                "belief_updated",
                evidence["sim_time"],
                {
                    "subject": subject,
                    "predicate": predicate,
                    "object": object_value,
                    "evidence": evidence_id,
                    "epistemic": epistemic,
                },
            )
            self._invalidate_tasks(subject, predicate, object_value, evidence["sim_time"])
        return True

    def _invalidate_tasks(self, subject: str, predicate: str, value: str, time: float) -> None:
        rows = self.db.execute(
            """SELECT task_id FROM task_support WHERE episode=?
            AND subject=? AND predicate=? AND object!=?""",
            (self.episode, subject, predicate, value),
        ).fetchall()
        for row in rows:
            changed = self.db.execute(
                "UPDATE tasks SET status='invalidated' WHERE episode=? AND id=? AND status='observed_complete'",
                (self.episode, row["task_id"]),
            ).rowcount
            if changed:
                self._event("task_status", time, {"id": row["task_id"], "status": "invalidated"})
        self._invalidate_dependents(time)

    def _invalidate_dependents(self, time: float) -> None:
        while True:
            rows = self.db.execute(
                """SELECT DISTINCT t.id FROM tasks t
                JOIN task_dependencies d ON d.episode=t.episode AND d.task_id=t.id
                JOIN tasks p ON p.episode=d.episode AND p.id=d.dependency
                WHERE t.episode=? AND t.status='observed_complete'
                AND p.status!='observed_complete' """,
                (self.episode,),
            ).fetchall()
            if not rows:
                return
            for row in rows:
                self.db.execute(
                    "UPDATE tasks SET status='invalidated' WHERE episode=? AND id=?",
                    (self.episode, row["id"]),
                )
                self._event("task_status", time, {"id": row["id"], "status": "invalidated"})

    def history(self, subject: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM beliefs WHERE episode=? AND subject=? ORDER BY seq",
            (self.episode, subject),
        )
        return [dict(row) for row in rows]

    def add_task(
        self,
        identifier: str,
        goal: str,
        *,
        dependencies: tuple[str, ...] = (),
        bindings: tuple[tuple[str, str, str], ...] = (),
    ) -> None:
        if dependencies or bindings:
            from .ledger import TaskLedger, TaskPredicate

            TaskLedger(self).add(TaskPredicate(identifier, goal, dependencies, bindings))
            return
        with self.db:
            self.db.execute(
                "INSERT INTO tasks(episode,id,goal,status) VALUES(?,?,?,?)",
                (self.episode, _text(identifier, "task id", 256), _text(goal, "goal"), "planned"),
            )

    def set_task_status(
        self,
        identifier: str,
        status: str,
        evidence_id: str | None = None,
        *,
        now: float | None = None,
        max_evidence_age: float = 5.0,
    ) -> None:
        if status not in {
            "planned",
            "running",
            "needs_verification",
            "observed_complete",
            "invalidated",
        }:
            raise ValueError("Unknown task state")
        if not self.db.execute(
            "SELECT 1 FROM tasks WHERE episode=? AND id=?", (self.episode, identifier)
        ).fetchone():
            raise ValueError("Unknown task")
        time = 0.0
        if evidence_id:
            e = self._evidence(evidence_id)
            time = e["sim_time"]
            if status == "observed_complete":
                if e["kind"] == "inference":
                    raise ValueError(
                        "Completion requires observational evidence, not reasoner assertion"
                    )
                if now is None or _time(max_evidence_age) < 0:
                    raise ValueError("Completion requires an explicit current simulator time")
                age = _time(now) - e["sim_time"]
                if age < 0 or age > max_evidence_age:
                    raise ValueError("Completion evidence is stale or from the future")
        elif status == "observed_complete":
            raise ValueError("Completion requires evidence")
        support = []
        if status in {"running", "observed_complete"}:
            dependencies = self.db.execute(
                """SELECT t.status FROM task_dependencies d
                JOIN tasks t ON t.episode=d.episode AND t.id=d.dependency
                WHERE d.episode=? AND d.task_id=?""",
                (self.episode, identifier),
            )
            if any(row["status"] != "observed_complete" for row in dependencies):
                raise ValueError("Task dependencies are not complete")
        if status == "observed_complete":
            bindings = self.db.execute(
                "SELECT * FROM task_bindings WHERE episode=? AND task_id=?",
                (self.episode, identifier),
            ).fetchall()
            if not bindings:
                raise ValueError(
                    "Completion requires explicit task bindings; freeform goals are not predicates"
                )
            support = [self.belief(row["subject"], row["predicate"]) for row in bindings]
            if any(b is None or b["object"] != row["object"] for b, row in zip(support, bindings)):
                raise ValueError("Current beliefs do not support task predicates")
            if not support or not any(b["evidence_id"] == evidence_id for b in support):
                raise ValueError("Completion evidence must support a current task belief")
            for b in support:
                age = _time(now) - b["sim_time"]
                if b["epistemic"] != "observed" or not 0 <= age <= max_evidence_age:
                    raise ValueError("Task support must be fresh observational evidence")
                conflicts = self.db.execute(
                    "SELECT payload FROM events WHERE episode=? AND type='belief_conflict' AND sim_time>=?",
                    (self.episode, b["sim_time"]),
                )
                if any(
                    (p.get("subject"), p.get("predicate")) == (b["subject"], b["predicate"])
                    for p in (json.loads(row["payload"]) for row in conflicts)
                ):
                    raise ValueError("Task support has unresolved conflicting evidence")
        with self.db:
            if status == "observed_complete":
                self.db.execute(
                    "DELETE FROM task_support WHERE episode=? AND task_id=?",
                    (self.episode, identifier),
                )
                self.db.executemany(
                    "INSERT INTO task_support VALUES(?,?,?,?,?,?)",
                    [
                        (
                            self.episode,
                            identifier,
                            b["subject"],
                            b["predicate"],
                            b["object"],
                            b["evidence_id"],
                        )
                        for b in support
                    ],
                )
            self.db.execute(
                "UPDATE tasks SET status=?,evidence_id=? WHERE episode=? AND id=?",
                (status, evidence_id, self.episode, identifier),
            )
            self._event(
                "task_status", time, {"id": identifier, "status": status, "evidence": evidence_id}
            )
            self._invalidate_dependents(time)

    def project(
        self,
        goal: str,
        subjects: Iterable[str],
        image_evidence: list[str],
        *,
        max_images: int = 4,
        max_events: int = 5,
        max_bytes: int = 12000,
    ) -> dict[str, Any]:
        """Return a bounded policy context; never equate bytes with tokens.

        The caller chooses relevant subjects. No implicit semantic retrieval is
        claimed. Provider-side token counting must additionally enforce the
        actual text+vision budget. Exceeding the budget fails visibly.
        """
        _text(goal, "goal")
        if any(
            isinstance(v, bool) or not isinstance(v, int) or v < 0
            for v in [max_images, max_events, max_bytes]
        ):
            raise ValueError("Budgets must be nonnegative integers")
        if len(image_evidence) > max_images:
            raise ContextBudgetExceeded("Too many image references; select evidence explicitly")
        subject_list = list(dict.fromkeys(subjects))
        rows = []
        for subject in subject_list:
            for row in self.db.execute(
                "SELECT subject,predicate,object,sim_time,evidence_id,epistemic FROM beliefs WHERE episode=? AND subject=? AND valid_until IS NULL ORDER BY predicate",
                (self.episode, subject),
            ):
                rows.append(dict(row))
        refs = []
        for identifier in image_evidence:
            e = self._evidence(identifier)
            if e["kind"] != "perception":
                raise ValueError("Image reference must point to perception evidence")
            refs.append({"id": identifier, "uri": e["uri"], "sim_time": e["sim_time"]})
        tasks = [
            dict(row)
            for row in self.db.execute(
                "SELECT id,goal,status,evidence_id FROM tasks WHERE episode=? ORDER BY id",
                (self.episode,),
            )
        ]
        for task in tasks:
            task["dependencies"] = [
                row[0]
                for row in self.db.execute(
                    "SELECT dependency FROM task_dependencies WHERE episode=? AND task_id=? ORDER BY dependency",
                    (self.episode, task["id"]),
                )
            ]
            task["evidence"] = [
                row[0]
                for row in self.db.execute(
                    "SELECT DISTINCT evidence_id FROM task_support WHERE episode=? AND task_id=? ORDER BY evidence_id",
                    (self.episode, task["id"]),
                )
            ]
        events = [
            {"seq": row["seq"], "sim_time": row["sim_time"], "type": row["type"]}
            for row in self.db.execute(
                "SELECT * FROM events WHERE episode=? ORDER BY seq DESC LIMIT ?",
                (self.episode, max_events),
            )
        ][::-1]
        payload = {
            "episode": self.episode,
            "goal": goal,
            "beliefs": rows,
            "task_ledger": tasks,
            "images": refs,
            "recent_events": events,
            "memory_notice": "Beliefs are fallible. Objects absent from view are not necessarily absent. Full trace is external.",
        }
        size = len(json.dumps(payload, allow_nan=False, sort_keys=True).encode("utf-8"))
        if size > max_bytes:
            raise ContextBudgetExceeded(
                f"Context metadata uses {size} bytes; budget {max_bytes}. Retrieve a smaller explicit slice."
            )
        return payload
