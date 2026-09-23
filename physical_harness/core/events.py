"""Runtime events and semantic boundary projections, with distinct clock contracts."""
from __future__ import annotations

import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from physical_harness.core.actions import (
    Basis,
    ids,
    number,
    text,
)


@dataclass(frozen=True)
class BoundaryEvent:
    id: str
    kind: str
    basis: Basis
    available_wall: float
    task_revision: str
    evidence_ids: tuple[str, ...]
    significance: str = "normal"

    def __post_init__(self):
        for s in (self.id, self.kind, self.task_revision):
            text(s)
        if not isinstance(self.basis, Basis):
            raise ValueError("Basis required")
        number(self.available_wall, low=self.basis.captured_wall)
        ids(self.evidence_ids, empty=False)
        if self.significance not in {"low", "normal", "high"}:
            raise ValueError("Invalid significance")


class EventType(str, Enum):
    SKILL_VERIFIED = "skill_verified"
    SKILL_FAILED = "skill_failed"
    SKILL_STALLED = "skill_stalled"
    TARGET_LOST = "target_lost"
    STATE_CONTRADICTION = "state_contradiction"
    VERIFIER_UNCERTAIN = "verifier_uncertain"
    PRECONDITION_VIOLATED = "precondition_violated"
    PLAN_EXHAUSTED = "plan_exhausted"
    DECISION_REQUIRED = "decision_required"
    EXECUTION_TIMEOUT = "execution_timeout"
    ARRIVED = "arrived"
    PATH_BLOCKED = "path_blocked"
    DOOR_BLOCKED = "door_blocked"
    WORLD_CHANGED = "world_changed"


@dataclass(frozen=True)
class RuntimeEvent:
    type: EventType
    episode_id: str
    sim_time: float
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    wall_time: float = field(default_factory=time.time)


BOUNDARY_WAKE_KINDS = frozenset({
    "initial", "primitive_completed", "relevant_discovery", "target_lost",
    "target_reacquired", "new_candidates", "verifier_result", "world_changed",
    "graph_judgment", "plan_exhausted", "explicit_request", "skill_failed",
})


class EventBus:
    """Small synchronous event bus for the first experiment.

    Replace with an async/distributed transport only after the synchronous
    control path is proven. Keeping this simple makes event ordering explicit.
    """

    def __init__(self, history: int = 256):
        self._subs: list[Callable[[RuntimeEvent], None]] = []
        self._history: deque[RuntimeEvent] = deque(maxlen=history)

    def subscribe(self, fn: Callable[[RuntimeEvent], None]) -> None:
        self._subs.append(fn)

    def publish(self, event: RuntimeEvent) -> None:
        self._history.append(event)
        for fn in tuple(self._subs):
            fn(event)

    def recent(self, n: int = 20) -> list[RuntimeEvent]:
        if n < 0:
            raise ValueError("n must be nonnegative")
        return list(self._history)[-n:] if n else []
