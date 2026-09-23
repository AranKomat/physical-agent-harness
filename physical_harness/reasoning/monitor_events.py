"""Connect existing deterministic/learned monitor results to recurrent GPT scheduling."""
from __future__ import annotations

from dataclasses import dataclass

from physical_harness.core.actions import Basis, ids, plain, text
from physical_harness.core.events import BoundaryEvent
from physical_harness.reasoning.monitors import MonitorSignal


@dataclass(frozen=True)
class DeterministicMonitorResult:
    id: str
    command_id: str
    basis: Basis
    state: str
    evidence_ids: tuple[str, ...]
    property_name: str
    method: str

    def __post_init__(self):
        for s in (self.id, self.command_id, self.property_name, self.method):
            text(s)
        if self.state not in {"progress", "arrived", "primitive_completed", "stalled", "lost", "unknown"}:
            raise ValueError("Unsupported deterministic monitor result")
        if not isinstance(self.basis, Basis):
            raise ValueError("Basis required")
        ids(self.evidence_ids, empty=False)


def monitor_event(result: MonitorSignal | DeterministicMonitorResult, *, task_revision: str,
                  available_wall: float) -> BoundaryEvent | None:
    if isinstance(result, MonitorSignal):
        if result.semantic_authority != "advisory_only":
            raise PermissionError("Learned monitor cannot establish task truth")
        kind = {"local_progress": None, "completion_candidate": "verifier_result",
                "subgoal_complete": "verifier_result", "verifier_uncertain": "verifier_result",
                "target_lost": "target_lost", "skill_failed": "skill_failed"}.get(result.event_type)
        identifier, evidence, basis = result.event_id, result.evidence_ids, result.basis
    elif isinstance(result, DeterministicMonitorResult):
        kind = {"progress": None, "arrived": "primitive_completed", "primitive_completed": "primitive_completed",
                "stalled": "skill_failed", "lost": "target_lost", "unknown": "verifier_result"}[result.state]
        identifier, evidence, basis = result.id, result.evidence_ids, result.basis
    else:
        raise ValueError("Typed existing monitor result required")
    if kind is None:
        return None
    return BoundaryEvent(identifier, kind, basis, available_wall, task_revision, evidence)


def emit_advisory(journal, result, *, task_revision: str, available_wall: float, scheduler):
    event = monitor_event(result, task_revision=task_revision, available_wall=available_wall)
    identifier = result.event_id if isinstance(result, MonitorSignal) else result.id
    journal.put("embodied_monitor_route", identifier, {"result": plain(result),
                 "advisory": True, "available_wall": available_wall, "event": plain(event)})
    return False if event is None else scheduler.add(event, active_task_revision=task_revision)
