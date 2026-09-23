"""Research telemetry for policy handoffs and paused-world recapture checks.

These records are diagnostic evidence, not motion authority. In particular,
paused_world_compatibility does not weaken HybridExecutor's stale-decision guard;
a private runner may use it only under an explicitly reviewed paused-simulator
protocol.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from physical_harness.core.handoff import (
    Phase,
    PolicyIdentity,
    Snapshot,
    identifiers,
    integer,
    real,
    text,
)


def _optional_real(value, name, low=0.0, high=math.inf):
    if value is None:
        return None
    return real(value, name, low, high)


def _finite_tuple(values, name, maximum=64):
    if not isinstance(values, tuple) or len(values) > maximum:
        raise ValueError(f"Bounded immutable {name} required")
    return tuple(real(v, name, -math.inf) for v in values)


@dataclass(frozen=True)
class HandoffTelemetry:
    """Measured state at a classical->policy boundary."""
    phase_id: str
    snapshot_fingerprint: str
    observation_id: str
    sim_time: float
    target_entity: str
    policy_generation: int
    policy_fingerprint: str
    evidence_ids: tuple[str, ...]
    target_observed: bool | None = None
    base_target_distance_m: float | None = None
    eef_target_distance_m: float | None = None
    target_pixel_fraction: float | None = None
    pose_confidence: float | None = None
    localization_confidence: float | None = None
    gripper_positions: tuple[float, ...] = ()
    controlled_joint_positions: tuple[float, ...] = ()
    note: str = ""

    def __post_init__(self):
        for value, name in (
            (self.phase_id, "phase_id"),
            (self.snapshot_fingerprint, "snapshot_fingerprint"),
            (self.observation_id, "observation_id"),
            (self.target_entity, "target_entity"),
            (self.policy_fingerprint, "policy_fingerprint"),
        ):
            text(value, name)
        real(self.sim_time, "sim_time")
        integer(self.policy_generation, "policy_generation")
        identifiers(self.evidence_ids, "evidence_ids")
        if not self.evidence_ids:
            raise ValueError("Handoff telemetry requires evidence")
        if self.target_observed is not None and type(self.target_observed) is not bool:
            raise ValueError("target_observed must be boolean or unknown")
        _optional_real(self.base_target_distance_m, "base_target_distance_m")
        _optional_real(self.eef_target_distance_m, "eef_target_distance_m")
        _optional_real(self.target_pixel_fraction, "target_pixel_fraction", 0, 1)
        _optional_real(self.pose_confidence, "pose_confidence", 0, 1)
        _optional_real(self.localization_confidence, "localization_confidence", 0, 1)
        _finite_tuple(self.gripper_positions, "gripper_positions", 8)
        _finite_tuple(self.controlled_joint_positions, "controlled_joint_positions", 64)
        if not isinstance(self.note, str) or len(self.note.encode()) > 1600:
            raise ValueError("Bounded telemetry note required")

    def require(self, phase: Phase, snapshot: Snapshot, policy: PolicyIdentity, generation: int):
        if (
            self.phase_id != phase.id
            or self.snapshot_fingerprint != snapshot.fingerprint
            or self.observation_id != snapshot.observation_id
            or self.sim_time != snapshot.sim_time
            or self.policy_generation != generation
            or self.policy_fingerprint != policy.fingerprint
            or self.target_entity not in phase.target_entities
        ):
            raise PermissionError("Handoff telemetry is stale or belongs to another boundary")
        return self


@dataclass(frozen=True)
class PausedWorldComparison:
    compatible: bool
    reasons: tuple[str, ...]
    decision_observation_id: str
    dispatch_observation_id: str

    def __post_init__(self):
        if type(self.compatible) is not bool:
            raise ValueError("compatible must be boolean")
        identifiers(self.reasons, "reasons")
        text(self.decision_observation_id, "decision_observation_id")
        text(self.dispatch_observation_id, "dispatch_observation_id")


def _max_abs_diff(a, b):
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b):
        return math.inf
    try:
        return max((abs(float(x) - float(y)) for x, y in zip(a, b)), default=0.0)
    except (TypeError, ValueError):
        return math.inf


def paused_world_compatibility(
    decision: Snapshot,
    dispatch: Snapshot,
    *,
    proprio_tolerance: float = 1e-6,
    pose_element_tolerance: float = 1e-6,
) -> PausedWorldComparison:
    """Diagnose whether two fresh captures describe the same paused simulator state.

    Observation IDs and wall capture times may differ. Sim time, localization
    epoch, geometry revision, camera set, proprioception and estimated pose must
    remain compatible. This helper never authorizes motion by itself.
    """
    if not isinstance(decision, Snapshot) or not isinstance(dispatch, Snapshot):
        raise ValueError("Typed snapshots required")
    p_tol = real(proprio_tolerance, "proprio_tolerance", 0)
    x_tol = real(pose_element_tolerance, "pose_element_tolerance", 0)
    a, b = decision.envelope(), dispatch.envelope()
    reasons = []
    if a["episode_id"] != b["episode_id"]:
        reasons.append("episode_changed")
    if a["sim_time"] != b["sim_time"]:
        reasons.append("sim_time_changed")
    if decision.frame_epoch != dispatch.frame_epoch:
        reasons.append("frame_epoch_changed")
    if decision.geometry_revision != dispatch.geometry_revision:
        reasons.append("geometry_revision_changed")
    if dispatch.captured_wall < decision.captured_wall:
        reasons.append("capture_time_regressed")
    if set(a["rgb_refs"]) != set(b["rgb_refs"]):
        reasons.append("camera_set_changed")
    for key in ("camera_intrinsics", "camera_frames"):
        if a[key] != b[key]:
            reasons.append(key + "_changed")
    pa, pb = a["proprioception"], b["proprioception"]
    if set(pa) != set(pb):
        reasons.append("proprio_schema_changed")
    else:
        for name in pa:
            if _max_abs_diff(pa[name], pb[name]) > p_tol:
                reasons.append("proprio_changed:" + name)
    xa, xb = a.get("estimated_pose"), b.get("estimated_pose")
    if (xa is None) != (xb is None):
        reasons.append("pose_presence_changed")
    elif xa is not None:
        for name in ("method", "frame", "camera", "confidence"):
            if xa[name] != xb[name]:
                reasons.append("pose_contract_changed:" + name)
        flat_a = [v for row in xa["transform"] for v in row]
        flat_b = [v for row in xb["transform"] for v in row]
        if _max_abs_diff(flat_a, flat_b) > x_tol:
            reasons.append("estimated_pose_changed")
    return PausedWorldComparison(
        not reasons, tuple(reasons), decision.observation_id, dispatch.observation_id
    )


def telemetry_payload(value: HandoffTelemetry) -> dict:
    if not isinstance(value, HandoffTelemetry):
        raise ValueError("HandoffTelemetry required")
    return asdict(value)
