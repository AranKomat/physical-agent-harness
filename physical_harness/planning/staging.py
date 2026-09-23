"""Legal target geometry and conservative base-staging pose selection.

This module does not detect objects, read simulator poses, or command motion.
The private perception stack supplies a target pixel/depth observation and the
existing legal observation supplies calibrated intrinsics plus a legally
estimated camera->local_map pose. Candidate base poses remain proposals until
the normal Hybrid V0 localization/collision/trajectory gates admit them.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from physical_harness.core.handoff import Snapshot, identifiers, integer, real, text
from physical_harness.execution.handoff.classical import BasePose


def _vector(values, name, n):
    if not isinstance(values, tuple) or len(values) != n:
        raise ValueError(f"{name} must be an immutable {n}-vector")
    return tuple(real(v, name, -math.inf) for v in values)


@dataclass(frozen=True)
class TargetPoint:
    """One depth-supported target point bound to an exact legal snapshot."""
    entity_id: str
    xyz_local: tuple[float, float, float]
    snapshot_fingerprint: str
    observation_id: str
    evidence_ids: tuple[str, ...]
    confidence: float

    def __post_init__(self):
        text(self.entity_id, "entity_id")
        object.__setattr__(self, "xyz_local", _vector(self.xyz_local, "xyz_local", 3))
        text(self.snapshot_fingerprint, "snapshot_fingerprint")
        text(self.observation_id, "observation_id")
        identifiers(self.evidence_ids, "evidence_ids")
        if not self.evidence_ids:
            raise ValueError("Target point requires source evidence")
        real(self.confidence, "confidence", 0, 1)

    def require_snapshot(self, snapshot: Snapshot):
        if (
            not isinstance(snapshot, Snapshot)
            or snapshot.fingerprint != self.snapshot_fingerprint
            or snapshot.observation_id != self.observation_id
        ):
            raise PermissionError("Target point is stale or belongs to another snapshot")


@dataclass(frozen=True)
class StagingConfig:
    """Finite candidate family, not a learned or globally optimal planner."""
    radii_m: tuple[float, ...] = (0.55, 0.65, 0.75)
    angle_offsets_rad: tuple[float, ...] = (
        0.0,
        math.radians(15),
        -math.radians(15),
        math.radians(30),
        -math.radians(30),
        math.radians(45),
        -math.radians(45),
    )
    preferred_radius_m: float = 0.65
    max_candidates: int = 8

    def __post_init__(self):
        if not isinstance(self.radii_m, tuple) or not self.radii_m:
            raise ValueError("At least one immutable staging radius is required")
        if not isinstance(self.angle_offsets_rad, tuple) or not self.angle_offsets_rad:
            raise ValueError("At least one immutable angle offset is required")
        if len(self.radii_m) * len(self.angle_offsets_rad) > 4096:
            raise ValueError("Staging search exceeds 4096 candidate evaluations")
        for r in self.radii_m:
            real(r, "staging radius", .05, 3.0)
        for a in self.angle_offsets_rad:
            real(a, "angle offset", -math.pi, math.pi)
        real(self.preferred_radius_m, "preferred radius", .05, 3.0)
        integer(self.max_candidates, "max_candidates", 1)
        if self.max_candidates > 64:
            raise ValueError("Too many staging candidates")


@dataclass(frozen=True)
class StagingCandidate:
    pose: BasePose
    travel_distance_m: float
    target_distance_m: float
    reachability: float
    visibility: float
    angle_offset_rad: float

    def __post_init__(self):
        if not isinstance(self.pose, BasePose):
            raise ValueError("Typed BasePose required")
        real(self.travel_distance_m, "travel_distance_m")
        real(self.target_distance_m, "target_distance_m", .001)
        real(self.reachability, "reachability", 0, 1)
        real(self.visibility, "visibility", 0, 1)
        real(self.angle_offset_rad, "angle_offset_rad", -math.pi, math.pi)


@dataclass(frozen=True)
class StagingPlan:
    snapshot_fingerprint: str
    target: TargetPoint
    candidates: tuple[StagingCandidate, ...]
    selected: StagingCandidate

    def __post_init__(self):
        text(self.snapshot_fingerprint, "snapshot_fingerprint")
        if not isinstance(self.target, TargetPoint):
            raise ValueError("TargetPoint required")
        if not isinstance(self.candidates, tuple) or not self.candidates:
            raise ValueError("At least one staging candidate required")
        if len(self.candidates) > 64 or not all(isinstance(c, StagingCandidate) for c in self.candidates):
            raise ValueError("Bounded typed staging candidates required")
        if self.snapshot_fingerprint != self.target.snapshot_fingerprint:
            raise ValueError("Staging plan and target refer to different snapshots")
        if self.selected not in self.candidates:
            raise ValueError("Selected candidate must come from candidates")


def transform_point(matrix, point):
    """Apply a validated 4x4 row-major homogeneous transform to a 3D point."""
    if not isinstance(matrix, list) or len(matrix) != 4 or any(
        not isinstance(row, list) or len(row) != 4 for row in matrix
    ):
        raise ValueError("Expected 4x4 transform")
    x, y, z = _vector(tuple(point), "point", 3)
    out = []
    for row in matrix[:3]:
        out.append(row[0] * x + row[1] * y + row[2] * z + row[3])
    return tuple(real(v, "transformed point", -math.inf) for v in out)


def target_from_depth_pixel(
    snapshot: Snapshot,
    *,
    entity_id: str,
    camera: str,
    pixel_uv: tuple[float, float],
    depth_value: float,
    evidence_ids: tuple[str, ...],
    confidence: float,
    depth_is_meters: bool = False,
) -> TargetPoint:
    """Deproject one target pixel using only the legal pose camera.

    A detector/segmenter must choose the pixel and a private depth reader must
    supply its measured depth. For non-pose cameras, compose calibrated rigid
    extrinsics upstream; this helper never invents them.
    """
    if not isinstance(snapshot, Snapshot):
        raise ValueError("Snapshot required")
    text(entity_id, "entity_id")
    text(camera, "camera")
    u, v = _vector(pixel_uv, "pixel_uv", 2)
    if type(depth_is_meters) is not bool:
        raise ValueError("depth_is_meters must be boolean")
    raw = real(depth_value, "depth_value", .000001)
    identifiers(evidence_ids, "evidence_ids")
    env = snapshot.envelope()
    intr = env["camera_intrinsics"].get(camera)
    pose = env.get("estimated_pose")
    if intr is None or not isinstance(pose, dict) or pose.get("camera") != camera:
        raise ValueError("Target projection requires the legally posed camera")
    if not (0 <= u <= intr["width"] - 1 and 0 <= v <= intr["height"] - 1):
        raise ValueError("Target pixel outside calibrated image")
    depth_m = raw if depth_is_meters else raw * intr["depth_scale_m"]
    real(depth_m, "depth_m", .000001, 50.0)
    # Optical convention used by LegalObservation: x right, y down, z forward.
    x = (u - intr["cx"]) * depth_m / intr["fx"]
    y = (v - intr["cy"]) * depth_m / intr["fy"]
    camera_point = (x, y, depth_m)
    local_point = transform_point(pose["transform"], camera_point)
    return TargetPoint(
        entity_id,
        local_point,
        snapshot.fingerprint,
        snapshot.observation_id,
        tuple(dict.fromkeys((snapshot.observation_id, env["depth_refs"][camera], *evidence_ids))),
        real(confidence, "confidence", 0, 1),
    )


def _quality(value, name):
    if value is None:
        return None
    if type(value) is bool:
        return 1.0 if value else 0.0
    return real(value, name, 0, 1)


def resolve_staging_pose(
    snapshot: Snapshot,
    target: TargetPoint,
    current_base: BasePose,
    *,
    clearance: Callable[[BasePose, TargetPoint, Snapshot], bool | None],
    reachable: Callable[[BasePose, TargetPoint, Snapshot], float | bool | None],
    visible: Callable[[BasePose, TargetPoint, Snapshot], float | bool | None],
    config: StagingConfig | None = None,
) -> StagingPlan:
    """Select a conservative candidate from explicit geometry/perception callbacks.

    Unknown clearance/reachability/visibility rejects a candidate. Ranking is
    lexicographic: maximize worst of reachability/visibility, then mean quality,
    then prefer the configured radius, shorter travel, and smaller angular offset.
    """
    if not isinstance(snapshot, Snapshot) or not isinstance(target, TargetPoint):
        raise ValueError("Snapshot and TargetPoint required")
    if not isinstance(current_base, BasePose):
        raise ValueError("Current BasePose required")
    if not all(callable(fn) for fn in (clearance, reachable, visible)):
        raise ValueError("Qualified staging callbacks required")
    target.require_snapshot(snapshot)
    cfg = config or StagingConfig()
    tx, ty, _ = target.xyz_local
    nominal = math.atan2(current_base.y - ty, current_base.x - tx)
    candidates = []
    for radius in cfg.radii_m:
        for offset in cfg.angle_offsets_rad:
            angle = nominal + offset
            x = tx + radius * math.cos(angle)
            y = ty + radius * math.sin(angle)
            yaw = math.atan2(ty - y, tx - x)
            pose = BasePose(x, y, yaw)
            if clearance(pose, target, snapshot) is not True:
                continue
            reach = _quality(reachable(pose, target, snapshot), "reachability")
            view = _quality(visible(pose, target, snapshot), "visibility")
            if reach is None or view is None or reach <= 0 or view <= 0:
                continue
            travel = math.hypot(x - current_base.x, y - current_base.y)
            candidates.append(
                StagingCandidate(pose, travel, radius, reach, view, offset)
            )
    if not candidates:
        raise ValueError("No staging candidate has established clearance, reachability and visibility")
    candidates.sort(
        key=lambda c: (
            -min(c.reachability, c.visibility),
            -(c.reachability + c.visibility) / 2,
            abs(c.target_distance_m - cfg.preferred_radius_m),
            c.travel_distance_m,
            abs(c.angle_offset_rad),
            c.pose.x,
            c.pose.y,
        )
    )
    bounded = tuple(candidates[: cfg.max_candidates])
    return StagingPlan(snapshot.fingerprint, target, bounded, bounded[0])
