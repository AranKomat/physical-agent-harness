import sqlite3

import pytest

from physical_harness.ledger import TaskLedger, TaskPredicate
from physical_harness.state import WorldState


@pytest.fixture
def state():
    with WorldState(":memory:", "ep") as state:
        yield state


def observe(state, identifier="e1", time=1, value="cabinet", kind="perception"):
    state.add_evidence(identifier, time, kind, "frames/" + identifier)
    state.update(
        "cup",
        "location",
        value,
        identifier,
        epistemic="inferred" if kind == "inference" else "observed",
    )


def test_episode_isolation_and_immutable_evidence(tmp_path):
    path = tmp_path / "state.db"
    with WorldState(path, "a") as a, WorldState(path, "b") as b:
        observe(a)
        with pytest.raises(sqlite3.IntegrityError):
            observe(a)
        assert b.belief("cup", "location") is None
        b.add_task("task", "put cup away")
        with pytest.raises(ValueError, match="Unknown evidence"):
            b.set_task_status("task", "observed_complete", "e1", now=1)


def test_commands_are_not_beliefs_and_stale_updates_rejected(state):
    observe(state, time=5)
    state.record_command("cmd", 6, {"cup": "floor"})
    assert state.belief("cup", "location")["object"] == "cabinet"
    state.add_evidence("old", 2, "perception", "old.png")
    assert not state.update("cup", "location", "floor", "old")
    assert state.belief("cup", "location")["object"] == "cabinet"


@pytest.mark.parametrize("now,age", [(10, 5), (0, 5), (1, float("nan"))])
def test_completion_requires_fresh_evidence(state, now, age):
    observe(state)
    state.add_task("t", "cup in cabinet", bindings=(("cup", "location", "cabinet"),))
    with pytest.raises(ValueError):
        state.set_task_status("t", "observed_complete", "e1", now=now, max_evidence_age=age)


def test_completion_requires_observational_support(state):
    state.add_task("t", "cup in cabinet", bindings=(("cup", "location", "cabinet"),))
    for kind in ("perception", "inference"):
        state.add_evidence(kind, 1, kind, kind)
        with pytest.raises(ValueError):
            state.set_task_status("t", "observed_complete", kind, now=1)
    with pytest.raises(ValueError):
        state.set_task_status("t", "observed_complete", now=1)


def test_dependencies_and_contradiction_cascade(state):
    ledger = TaskLedger(state)
    binding = (("cup", "location", "cabinet"),)
    ledger.add(TaskPredicate("a", "cup in cabinet", bindings=binding))
    ledger.add(TaskPredicate("b", "finish", ("a",), binding))
    observe(state)
    with pytest.raises(ValueError, match="dependencies"):
        ledger.set_status("b", "observed_complete", "e1", now=1)
    with pytest.raises(ValueError, match="dependencies"):
        ledger.set_status("b", "running")
    ledger.set_status("a", "observed_complete", "e1", now=1)
    ledger.set_status("b", "observed_complete", "e1", now=1)
    assert not ledger.pending()
    observe(state, "e2", 2, "floor")
    assert ledger.get("a").status == "invalidated"
    assert ledger.get("b").status == "invalidated"
    with pytest.raises(ValueError):
        ledger.set_status("a", "observed_complete", "e1", now=2)
    observe(state, "e3", 3)
    ledger.set_status("a", "observed_complete", "e3", now=3)
    assert ledger.get("b").status == "invalidated"


def test_same_time_conflict_prevents_recompletion(state):
    observe(state)
    state.add_task("t", "cup in cabinet", bindings=(("cup", "location", "cabinet"),))
    state.set_task_status("t", "observed_complete", "e1", now=1)
    observe(state, "conflict", 1, "floor")
    assert TaskLedger(state).get("t").status == "invalidated"
    with pytest.raises(ValueError, match="conflicting"):
        state.set_task_status("t", "observed_complete", "e1", now=1)


def test_missing_dependency_and_wrong_predicate_support(state):
    ledger = TaskLedger(state)
    with pytest.raises(ValueError):
        ledger.add(TaskPredicate("a", "goal", ("missing",)))
    assert ledger.get("a") is None
    ledger.add(TaskPredicate("a", "goal", bindings=(("cup", "location", "floor"),)))
    observe(state)
    with pytest.raises(ValueError, match="Current beliefs"):
        ledger.set_status("a", "observed_complete", "e1", now=1)


def test_ledger_persists_and_projects_dependencies(tmp_path):
    path = tmp_path / "state.db"
    with WorldState(path, "a") as state:
        state.add_task("a", "cup away", bindings=(("cup", "location", "cabinet"),))
        state.add_task("b", "finish", dependencies=("a",))
        observe(state)
        state.set_task_status("a", "observed_complete", "e1", now=1)
    with WorldState(path, "a") as state:
        ledger = TaskLedger(state)
        assert ledger.get("a").evidence == ("e1",)
        assert ledger.get("b").dependencies == ("a",)
        tasks = state.project("goal", [], [])["task_ledger"]
        assert tasks[1]["dependencies"] == ["a"]
        observe(state, "e2", 2, "floor")
        assert ledger.get("a").status == "invalidated"


def test_every_binding_must_have_fresh_observational_support(state):
    state.add_task(
        "t",
        "both away",
        bindings=(("cup", "location", "cabinet"), ("plate", "location", "cabinet")),
    )
    observe(state)
    state.add_evidence("e2", 10, "perception", "e2.png")
    state.update("plate", "location", "cabinet", "e2")
    with pytest.raises(ValueError, match="fresh"):
        state.set_task_status("t", "observed_complete", "e2", now=10)
    observe(state, "e3", 10)
    state.set_task_status("t", "observed_complete", "e2", now=10)
    assert TaskLedger(state).get("t").evidence == ("e2", "e3")


@pytest.mark.parametrize("goal", ["close every door", "cup in cabinet"])
def test_unbound_task_cannot_complete_from_current_belief(state, goal):
    observe(state)
    state.add_task("t", goal)
    with pytest.raises(ValueError, match="explicit task bindings"):
        state.set_task_status("t", "observed_complete", "e1", now=1)
    assert TaskLedger(state).get("t").status == "planned"
    assert TaskLedger(state).get("t").evidence == ()
