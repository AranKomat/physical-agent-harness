"""Advisory recognition/tracking cadence; never suppresses physical safety sensing."""
from __future__ import annotations

from dataclasses import dataclass

from physical_harness.core.actions import number


@dataclass(frozen=True)
class PerceptionNeed:
    relevant_to_current_goal: bool
    visible: bool
    recognized_before: bool
    association_established: bool
    semantic_conflict: bool
    current_view_discriminative: bool
    metric_interaction_needed: bool
    current_geometry_fresh: bool
    since_independent_recognition_s: float

    def __post_init__(self):
        for key, value in vars(self).items():
            if key != "since_independent_recognition_s" and type(value) is not bool:
                raise ValueError("Explicit perception state required")
        number(self.since_independent_recognition_s, low=0)


@dataclass(frozen=True)
class PerceptionWork:
    recognize: bool
    track: bool
    reconstruct_local_geometry: bool
    request_inspection: bool
    reason: str


def schedule_perception(need: PerceptionNeed, *, reidentify_after_s: float = 30.) -> PerceptionWork:
    """Recognize sparsely, track relevant instances, reconstruct only useful geometry.

    This selects computation, NOT motions or sensor frame dropping. Use in shadow
    first; externally tuned intervals are hypotheses, not model quality guarantees.
    """
    number(reidentify_after_s, low=.001)
    if not need.relevant_to_current_goal:
        return PerceptionWork(False, False, False, False, "not_task_relevant_safety_sensing_unchanged")
    if not need.visible:
        return PerceptionWork(False, False, False, True, "reacquire_without_claiming_disappearance")
    uncertain = not need.recognized_before or not need.association_established or need.semantic_conflict
    refresh = uncertain or need.since_independent_recognition_s >= reidentify_after_s
    inspect = uncertain and not need.current_view_discriminative
    recognize = refresh and need.current_view_discriminative
    geometry = need.metric_interaction_needed and not need.current_geometry_fresh
    return PerceptionWork(recognize, True, geometry, inspect,
                          "gather_discriminating_evidence" if inspect else
                          "recognition_refresh" if recognize else "retain_semantics_update_track")
