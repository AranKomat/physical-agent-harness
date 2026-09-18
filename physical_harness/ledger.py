"""Episode-scoped task predicates backed by current observational beliefs."""

from dataclasses import dataclass

from .state import WorldState, _text


@dataclass(frozen=True)
class TaskPredicate:
    id: str
    expression: str
    dependencies: tuple[str, ...] = ()
    # Explicit bindings avoid guessing a domain predicate grammar.
    bindings: tuple[tuple[str, str, str], ...] = ()
    status: str = "planned"
    evidence: tuple[str, ...] = ()


class TaskLedger:
    def __init__(self, state: WorldState):
        self.state = state

    def add(self, task: TaskPredicate) -> None:
        if task.status != "planned" or task.evidence:
            raise ValueError("New tasks must be planned without completion evidence")
        deps = tuple(dict.fromkeys(task.dependencies))
        for dependency in deps:
            if dependency == task.id or self.get(dependency) is None:
                raise ValueError("Dependencies must be existing, distinct tasks")
        for binding in task.bindings:
            if len(binding) != 3:
                raise ValueError("Bindings must be subject, predicate, object triples")
            for value in binding:
                _text(value, "binding", 1024)
        with self.state.db:
            self.state.db.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?)",
                (
                    self.state.episode,
                    _text(task.id, "task id", 256),
                    _text(task.expression, "expression"),
                    "planned",
                    None,
                ),
            )
            self.state.db.executemany(
                "INSERT INTO task_dependencies VALUES(?,?,?)",
                [(self.state.episode, task.id, dep) for dep in deps],
            )
            self.state.db.executemany(
                "INSERT INTO task_bindings VALUES(?,?,?,?,?)",
                [(self.state.episode, task.id, *b) for b in task.bindings],
            )

    def get(self, identifier: str) -> TaskPredicate | None:
        db, episode = self.state.db, self.state.episode
        row = db.execute(
            "SELECT * FROM tasks WHERE episode=? AND id=?", (episode, identifier)
        ).fetchone()
        if row is None:
            return None
        deps = tuple(
            r[0]
            for r in db.execute(
                "SELECT dependency FROM task_dependencies WHERE episode=? AND task_id=? ORDER BY dependency",
                (episode, identifier),
            )
        )
        bindings = tuple(
            tuple(r)
            for r in db.execute(
                "SELECT subject,predicate,object FROM task_bindings WHERE episode=? AND task_id=? ORDER BY subject,predicate",
                (episode, identifier),
            )
        )
        evidence = tuple(
            r[0]
            for r in db.execute(
                "SELECT DISTINCT evidence_id FROM task_support WHERE episode=? AND task_id=? ORDER BY evidence_id",
                (episode, identifier),
            )
        )
        return TaskPredicate(identifier, row["goal"], deps, bindings, row["status"], evidence)

    def set_status(
        self,
        identifier: str,
        status: str,
        evidence_id: str | None = None,
        *,
        now: float | None = None,
        max_evidence_age: float = 5.0,
    ) -> None:
        self.state.set_task_status(
            identifier, status, evidence_id, now=now, max_evidence_age=max_evidence_age
        )

    def pending(self) -> tuple[TaskPredicate, ...]:
        return tuple(
            self.get(r[0])
            for r in self.state.db.execute(
                "SELECT id FROM tasks WHERE episode=? AND status!='observed_complete' ORDER BY id",
                (self.state.episode,),
            )
        )
