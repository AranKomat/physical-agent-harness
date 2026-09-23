import pytest

from physical_harness.core.events import EventType, RuntimeEvent
from physical_harness.core.evidence import EvidenceStore
from physical_harness.reasoning.selection import ExecutiveLoop


class Executive:
    name = "offline-fixture"

    def decide(self, context):
        return {"tool": "finish", "arguments": {}}


def test_executive_only_wakes_once_per_event():
    calls = []
    loop = ExecutiveLoop(
        "ep",
        Executive(),
        lambda event: {},
        {"finish": lambda args: calls.append(True)},
        can_finish=lambda: True,
    )
    event = RuntimeEvent(EventType.PLAN_EXHAUSTED, "ep", 0)
    loop.on_event(event)
    loop.on_event(event)
    assert loop.calls == len(calls) == 1


def test_finish_requires_verified_ledger():
    loop = ExecutiveLoop(
        "ep", Executive(), lambda event: {}, {"finish": lambda args: None}, can_finish=lambda: False
    )
    with pytest.raises(ValueError, match="verified"):
        loop.on_event(RuntimeEvent(EventType.PLAN_EXHAUSTED, "ep", 0))


def test_foreign_event_and_oversize_context_do_not_call_executive():
    loop = ExecutiveLoop(
        "ep",
        Executive(),
        lambda event: {"large": "x" * 100},
        {"finish": lambda args: None},
        can_finish=lambda: True,
        max_context_bytes=10,
    )
    for episode in ("other", "ep"):
        with pytest.raises(ValueError):
            loop.on_event(RuntimeEvent(EventType.DECISION_REQUIRED, episode, 0))
    assert loop.calls == 0


def test_evidence_immutable_hash_and_paths(tmp_path):
    store = EvidenceStore(tmp_path)
    name = store.put(b"frame", ".png")
    assert store.put(b"frame", ".png") == name
    assert store.read(name) == b"frame"
    with pytest.raises(ValueError):
        store.read("../outside")
    (tmp_path / name).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash"):
        store.read(name)
