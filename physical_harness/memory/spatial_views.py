"""Lightweight posed RGB-D keyframe memory and observation-coverage evidence.

This module deliberately does NOT reconstruct a permanent dense 3D world.
It records sparse, provenance-bearing views that can be retrieved when the
executive, verifier, or a local scene builder needs visual/metric evidence.

The intended source is the existing BEHAVIOR legal observation envelope:
RGB/depth references plus an optional legally-estimated camera->local_map pose.
Current truth still belongs in WorldState; these records are historical evidence.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

POSE_SOURCES = frozenset({"rgbd_odometry", "proprio_odometry", "rgbd_slam"})
COVERAGE_METHODS = frozenset(
    {"depth_visibility", "calibrated_sweep", "human_annotation", "view_coverage"}
)
KEYFRAME_REASONS = frozenset(
    {
        "initial",
        "place_entered",
        "object_sighting",
        "world_changed",
        "skill_verified",
        "skill_failed",
        "skill_stalled",
        "target_lost",
        "verifier_uncertain",
        "decision_required",
        "manual",
        "periodic_fallback",
    }
)


def _text(value: str, name: str, limit: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > limit:
        raise ValueError(f"{name} must be nonempty bounded text")
    return value


def _finite(value: float, name: str, low: float = 0.0, high: float = math.inf) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{name} outside allowed range")
    return value


def _ids(values: Iterable[str], name: str, limit: int = 64) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{name} must be an immutable tuple")
    result = tuple(values)
    if len(result) > limit or len(set(result)) != len(result):
        raise ValueError(f"{name} must be a unique bounded sequence")
    for value in result:
        _text(value, name)
    return result


def _matrix(values: Iterable[float]) -> tuple[float, ...]:
    if not isinstance(values, tuple):
        raise ValueError("camera_to_frame must be an immutable tuple")
    result = tuple(values)
    if len(result) != 16:
        raise ValueError("camera_to_frame must contain 16 row-major values")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in result):
        raise ValueError("camera_to_frame must contain finite numbers")
    if any(abs(a - b) > 1e-5 for a, b in zip(result[12:16], (0.0, 0.0, 0.0, 1.0))):
        raise ValueError("camera_to_frame must be a homogeneous transform")
    # Reject obviously invalid rotations while leaving full calibration validation
    # to the existing LegalObservation boundary.
    rot = [result[0:3], result[4:7], result[8:11]]
    for i in range(3):
        norm = sum(rot[i][k] * rot[i][k] for k in range(3))
        if abs(norm - 1.0) > 1e-3:
            raise ValueError("camera_to_frame rotation row is not unit length")
        for j in range(i + 1, 3):
            dot = sum(rot[i][k] * rot[j][k] for k in range(3))
            if abs(dot) > 1e-3:
                raise ValueError("camera_to_frame rotation rows are not orthogonal")
    determinant = (
        rot[0][0] * (rot[1][1] * rot[2][2] - rot[1][2] * rot[2][1])
        - rot[0][1] * (rot[1][0] * rot[2][2] - rot[1][2] * rot[2][0])
        + rot[0][2] * (rot[1][0] * rot[2][1] - rot[1][1] * rot[2][0])
    )
    if abs(determinant - 1.0) > 1e-3:
        raise ValueError("camera_to_frame rotation must be proper")
    return tuple(float(v) for v in result)


def _distance_xyz(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


@dataclass(frozen=True)
class PosedRGBDKeyframe:
    """Sparse historical view, not a current-world-state assertion."""

    keyframe_id: str
    episode_id: str
    observation_id: str
    sim_time: float
    camera: str
    rgb_asset_id: str
    depth_ref: str
    pose_frame: str
    camera_to_frame: tuple[float, ...]
    pose_source: str
    pose_confidence: float
    pose_evidence_ids: tuple[str, ...]
    reason: str
    entity_ids: tuple[str, ...] = ()
    place_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    quality: float = 1.0

    def __post_init__(self) -> None:
        for value, name in (
            (self.keyframe_id, "keyframe_id"),
            (self.episode_id, "episode_id"),
            (self.observation_id, "observation_id"),
            (self.camera, "camera"),
            (self.rgb_asset_id, "rgb_asset_id"),
            (self.depth_ref, "depth_ref"),
            (self.pose_frame, "pose_frame"),
        ):
            _text(value, name)
        _finite(self.sim_time, "sim_time")
        _matrix(self.camera_to_frame)
        if self.pose_source not in POSE_SOURCES:
            raise ValueError("Unsupported legal pose source")
        _finite(self.pose_confidence, "pose_confidence", 0, 1)
        _ids(self.pose_evidence_ids, "pose_evidence_ids", 4)
        if not self.pose_evidence_ids or self.pose_evidence_ids[-1] != self.observation_id:
            raise ValueError("Pose provenance must end with this observation")
        if self.reason not in KEYFRAME_REASONS:
            raise ValueError("Unknown keyframe reason")
        # This metadata is not an executive-context payload. Keep the bound
        # finite, but tolerate busy household observations in shadow memory.
        _ids(self.entity_ids, "entity_ids", 256)
        _ids(self.place_ids, "place_ids")
        _ids(self.tags, "tags")
        _finite(self.quality, "quality", 0, 1)

    @property
    def xyz(self) -> tuple[float, float, float]:
        return self.camera_to_frame[3], self.camera_to_frame[7], self.camera_to_frame[11]


@dataclass(frozen=True)
class CoverageObservation:
    """Evidence that a named region was actually inspected.

    ``target_seen=False`` is *not* an assertion that the target is elsewhere.
    It only supports the weaker statement that the target was not observed in
    the inspected region under the stated coverage/occlusion conditions.
    """

    coverage_id: str
    episode_id: str
    sim_time: float
    region_id: str
    coverage_fraction: float
    occlusion_fraction: float
    evidence_ids: tuple[str, ...]
    keyframe_ids: tuple[str, ...] = ()
    target_entity_id: str | None = None
    target_seen: bool | None = None
    method: str = "view_coverage"

    def __post_init__(self) -> None:
        _text(self.coverage_id, "coverage_id")
        _text(self.episode_id, "episode_id")
        _finite(self.sim_time, "sim_time")
        _text(self.region_id, "region_id")
        _finite(self.coverage_fraction, "coverage_fraction", 0, 1)
        _finite(self.occlusion_fraction, "occlusion_fraction", 0, 1)
        _ids(self.evidence_ids, "evidence_ids")
        if not self.evidence_ids:
            raise ValueError("Coverage requires source evidence")
        _ids(self.keyframe_ids, "keyframe_ids")
        if self.target_entity_id is not None:
            _text(self.target_entity_id, "target_entity_id")
        if self.target_seen is not None and type(self.target_seen) is not bool:
            raise ValueError("target_seen must be bool or None")
        if self.target_seen is not None and self.target_entity_id is None:
            raise ValueError("target_seen requires a target_entity_id")
        if self.method not in COVERAGE_METHODS:
            raise ValueError("Coverage method is not qualified")

    def supports_negative_evidence(
        self, *, min_coverage: float = 0.8, max_occlusion: float = 0.25
    ) -> bool:
        _finite(min_coverage, "min_coverage", 0, 1)
        _finite(max_occlusion, "max_occlusion", 0, 1)
        return (
            self.target_entity_id is not None
            and self.target_seen is False
            and self.coverage_fraction >= min_coverage
            and self.occlusion_fraction <= max_occlusion
        )


class SpatialViewIndex:
    """Small deterministic index over sparse views and coverage evidence.

    This is intentionally not a SLAM/map implementation. It can sit beside the
    existing MemoryStore and WorldState and be rebuilt from durable run records.
    """

    def __init__(self, episode_id: str):
        self.episode_id = _text(episode_id, "episode_id")
        self.keyframes: dict[str, PosedRGBDKeyframe] = {}
        self.coverage: dict[str, CoverageObservation] = {}

    def add_keyframe(self, keyframe: PosedRGBDKeyframe) -> bool:
        if keyframe.episode_id != self.episode_id:
            raise ValueError("Foreign episode keyframe")
        previous = self.keyframes.get(keyframe.keyframe_id)
        if previous is not None:
            if previous != keyframe:
                raise ValueError("Conflicting immutable keyframe ID")
            return False
        self.keyframes[keyframe.keyframe_id] = keyframe
        return True

    def add_coverage(self, observation: CoverageObservation) -> bool:
        if observation.episode_id != self.episode_id:
            raise ValueError("Foreign episode coverage record")
        for keyframe_id in observation.keyframe_ids:
            if keyframe_id not in self.keyframes:
                raise ValueError("Coverage references unknown keyframe")
        previous = self.coverage.get(observation.coverage_id)
        if previous is not None:
            if previous != observation:
                raise ValueError("Conflicting immutable coverage ID")
            return False
        self.coverage[observation.coverage_id] = observation
        return True

    def select_keyframes(
        self,
        *,
        now: float,
        entity_ids: tuple[str, ...] = (),
        place_ids: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        limit: int = 4,
        max_age_s: float | None = None,
        require_all_filters: bool = False,
        min_separation_m: float = 0.25,
    ) -> tuple[PosedRGBDKeyframe, ...]:
        now = _finite(now, "now")
        entity_ids = _ids(entity_ids, "entity_ids", 256)
        place_ids = _ids(place_ids, "place_ids")
        tags = _ids(tags, "tags")
        if type(require_all_filters) is not bool:
            raise ValueError("require_all_filters must be bool")
        min_separation_m = _finite(min_separation_m, "min_separation_m")
        if type(limit) is not int or limit < 0 or limit > 32:
            raise ValueError("limit outside allowed range")
        if max_age_s is not None:
            max_age_s = _finite(max_age_s, "max_age_s")
        if limit == 0:
            return ()

        entity_set, place_set, tag_set = set(entity_ids), set(place_ids), set(tags)
        query_has_filters = bool(entity_set or place_set or tag_set)
        candidates: list[tuple[float, PosedRGBDKeyframe]] = []
        for item in self.keyframes.values():
            if item.sim_time > now:
                continue
            age = now - item.sim_time
            if max_age_s is not None and age > max_age_s:
                continue
            e = len(entity_set.intersection(item.entity_ids))
            p = len(place_set.intersection(item.place_ids))
            t = len(tag_set.intersection(item.tags))
            if query_has_filters:
                matches = []
                if entity_set:
                    matches.append(e > 0)
                if place_set:
                    matches.append(p > 0)
                if tag_set:
                    matches.append(t > 0)
                if require_all_filters and not all(matches):
                    continue
                if not require_all_filters and not any(matches):
                    continue
            # Entity match dominates place/tags. Quality and pose confidence only
            # break ties; recency has a bounded effect so older exact evidence is
            # not discarded in favor of an unrelated recent view.
            score = 8.0 * e + 4.0 * p + 2.0 * t + item.quality + item.pose_confidence
            score += 1.0 / (1.0 + age)
            if item.reason in {"skill_failed", "target_lost", "verifier_uncertain"}:
                score += 0.25
            candidates.append((score, item))

        candidates.sort(key=lambda pair: (-pair[0], -pair[1].sim_time, pair[1].keyframe_id))
        if not candidates:
            return ()
        selected = [candidates[0][1]]
        cameras = {selected[0].camera}
        places = set(selected[0].place_ids)
        remaining = candidates[1:]

        # Greedily preserve camera/place novelty, then maximize metric baseline.
        # Candidate ordering remains the deterministic score/recency tie-breaker.
        while remaining and len(selected) < limit:
            diverse: list[tuple[tuple[int, int, float], int]] = []
            for index, (_, item) in enumerate(remaining):
                item_places = set(item.place_ids)
                structural_novelty = item.camera not in cameras or bool(item_places - places)
                separation = min(_distance_xyz(item.xyz, chosen.xyz) for chosen in selected)
                metric_novelty = separation >= min_separation_m
                if structural_novelty or metric_novelty:
                    diverse.append(
                        ((int(structural_novelty), int(metric_novelty), separation), index)
                    )
            if not diverse:
                break
            best_rank = max(rank for rank, _ in diverse)
            chosen_index = next(index for rank, index in diverse if rank == best_rank)
            _, chosen = remaining.pop(chosen_index)
            selected.append(chosen)
            cameras.add(chosen.camera)
            places.update(chosen.place_ids)
        if len(selected) == limit:
            return tuple(selected)
        # Second pass fills remaining slots by score.
        for _, item in candidates:
            if item not in selected:
                selected.append(item)
                if len(selected) == limit:
                    break
        return tuple(selected)

    def negative_evidence(
        self,
        *,
        target_entity_id: str,
        region_id: str,
        now: float,
        max_age_s: float = 60.0,
        min_coverage: float = 0.8,
        max_occlusion: float = 0.25,
    ) -> CoverageObservation | None:
        _text(target_entity_id, "target_entity_id")
        _text(region_id, "region_id")
        now = _finite(now, "now")
        max_age_s = _finite(max_age_s, "max_age_s")
        candidates = [
            item
            for item in self.coverage.values()
            if item.target_entity_id == target_entity_id
            and item.region_id == region_id
            and 0 <= now - item.sim_time <= max_age_s
            and item.supports_negative_evidence(
                min_coverage=min_coverage, max_occlusion=max_occlusion
            )
        ]
        return max(candidates, key=lambda item: (item.sim_time, item.coverage_id), default=None)

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "episode_id": self.episode_id,
            "keyframes": [asdict(v) for v in sorted(self.keyframes.values(), key=lambda x: x.keyframe_id)],
            "coverage": [asdict(v) for v in sorted(self.coverage.values(), key=lambda x: x.coverage_id)],
        }

    @classmethod
    def from_snapshot(cls, value: Mapping[str, Any]) -> "SpatialViewIndex":
        # JSON roundtrip first: callers cannot smuggle native objects into the store.
        data = json.loads(json.dumps(dict(value), allow_nan=False))
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported spatial-memory schema")
        result = cls(data["episode_id"])
        for raw in data.get("keyframes", []):
            raw = dict(raw)
            for name in ("camera_to_frame", "pose_evidence_ids", "entity_ids", "place_ids", "tags"):
                raw[name] = tuple(raw.get(name, ()))
            result.add_keyframe(PosedRGBDKeyframe(**raw))
        for raw in data.get("coverage", []):
            raw = dict(raw)
            for name in ("evidence_ids", "keyframe_ids"):
                raw[name] = tuple(raw.get(name, ()))
            result.add_coverage(CoverageObservation(**raw))
        return result


def keyframes_from_legal_envelope(
    envelope: Mapping[str, Any],
    *,
    rgb_asset_ids: Mapping[str, str],
    reason: str,
    entity_ids: tuple[str, ...] = (),
    place_ids: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
    quality_by_camera: Mapping[str, float] | None = None,
) -> tuple[PosedRGBDKeyframe, ...]:
    """Project an already-validated LegalObservation envelope into posed views.

    This helper intentionally refuses observations without ``estimated_pose``.
    The existing BEHAVIOR adapter must first validate the pose source, transform,
    confidence and provenance. The same estimated camera pose is recorded for
    every synchronized camera only when the envelope identifies that camera as
    the pose camera; other cameras need their own calibrated transform upstream.

    For v0.11 we therefore record only the pose camera, avoiding invented
    extrinsics. Multi-camera support should compose known rigid extrinsics in the
    adapter that owns calibration.
    """
    data = json.loads(json.dumps(dict(envelope), allow_nan=False))
    required = {"episode_id", "observation_id", "sim_time", "rgb_refs", "depth_refs", "estimated_pose"}
    if not required <= data.keys() or not isinstance(data.get("estimated_pose"), dict):
        raise ValueError("Posed keyframe projection requires a legal estimated_pose")
    pose = data["estimated_pose"]
    camera = pose.get("camera")
    if camera not in data["rgb_refs"] or camera not in data["depth_refs"]:
        raise ValueError("Pose camera missing synchronized RGB-D references")
    if set(rgb_asset_ids) != set(data["rgb_refs"]):
        raise ValueError("RGB asset IDs must cover the observation cameras")
    transform = tuple(float(v) for row in pose["transform"] for v in row)
    quality = 1.0 if quality_by_camera is None else quality_by_camera.get(camera, 1.0)
    keyframe = PosedRGBDKeyframe(
        keyframe_id=f"posed:{data['observation_id']}:{camera}",
        episode_id=data["episode_id"],
        observation_id=data["observation_id"],
        sim_time=float(data["sim_time"]),
        camera=camera,
        rgb_asset_id=rgb_asset_ids[camera],
        depth_ref=data["depth_refs"][camera],
        pose_frame=pose["frame"],
        camera_to_frame=transform,
        pose_source=pose["method"],
        pose_confidence=float(pose["confidence"]),
        pose_evidence_ids=tuple(pose["evidence_ids"]),
        reason=reason,
        entity_ids=entity_ids,
        place_ids=place_ids,
        tags=tags,
        quality=float(quality),
    )
    return (keyframe,)
