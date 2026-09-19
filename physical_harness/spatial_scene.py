"""On-demand local scene artifacts with explicit authority gates.

Persistent memory should stay sparse. When a manipulation step actually needs
geometry, a SceneBuilder can reconstruct a local model from selected posed RGB-D
keyframes. Visually plausible geometry is never automatically motion-authoritative.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Mapping, Protocol

from .memory.spatial_views import SpatialViewIndex


class SceneAuthority(IntEnum):
    DISPLAY = 1
    COLLISION = 2
    MOTION = 3


def _text(value: str, name: str, limit: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > limit:
        raise ValueError(f"{name} must be nonempty bounded text")
    return value


def _ids(values: tuple[str, ...], name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, tuple) or len(set(values)) != len(values) or len(values) > 64:
        raise ValueError(f"{name} must be a unique bounded tuple")
    if not allow_empty and not values:
        raise ValueError(f"{name} must not be empty")
    for value in values:
        _text(value, name)
    return values


@dataclass(frozen=True)
class SceneBuildRequest:
    request_id: str
    episode_id: str
    source_keyframe_ids: tuple[str, ...]
    focus_entities: tuple[str, ...]
    operation: str
    coordinate_frame: str = "local_map"
    minimum_authority: SceneAuthority = SceneAuthority.DISPLAY
    max_wall_s: float = 20.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.request_id, "request_id")
        _text(self.episode_id, "episode_id")
        _ids(self.source_keyframe_ids, "source_keyframe_ids", allow_empty=False)
        _ids(self.focus_entities, "focus_entities")
        _text(self.operation, "operation", 1024)
        _text(self.coordinate_frame, "coordinate_frame")
        if not isinstance(self.minimum_authority, SceneAuthority):
            raise ValueError("minimum_authority must be SceneAuthority")
        if isinstance(self.max_wall_s, bool) or not isinstance(self.max_wall_s, (int, float)):
            raise ValueError("max_wall_s must be finite")
        if not math.isfinite(self.max_wall_s) or self.max_wall_s <= 0:
            raise ValueError("max_wall_s must be finite and positive")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")


@dataclass(frozen=True)
class SceneArtifact:
    artifact_id: str
    episode_id: str
    source_keyframe_ids: tuple[str, ...]
    source_evidence_ids: tuple[str, ...]
    coordinate_frame: str
    observed_geometry_refs: tuple[str, ...] = ()
    inferred_geometry_refs: tuple[str, ...] = ()
    calibration_evidence_ids: tuple[str, ...] = ()
    display_ready: bool = False
    collision_ready: bool = False
    motion_ready: bool = False
    failure_reasons: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.artifact_id, "artifact_id")
        _text(self.episode_id, "episode_id")
        _ids(self.source_keyframe_ids, "source_keyframe_ids", allow_empty=False)
        _ids(self.source_evidence_ids, "source_evidence_ids", allow_empty=False)
        _text(self.coordinate_frame, "coordinate_frame")
        for name, values in (
            ("observed_geometry_refs", self.observed_geometry_refs),
            ("inferred_geometry_refs", self.inferred_geometry_refs),
            ("calibration_evidence_ids", self.calibration_evidence_ids),
            ("failure_reasons", self.failure_reasons),
        ):
            _ids(values, name)
        if any(type(value) is not bool for value in (
            self.display_ready, self.collision_ready, self.motion_ready
        )):
            raise ValueError("Scene readiness flags must be boolean")
        if self.collision_ready and not self.display_ready:
            raise ValueError("Collision authority requires display readiness")
        if self.motion_ready and not self.collision_ready:
            raise ValueError("Motion authority requires collision readiness")
        if self.motion_ready and not self.calibration_evidence_ids:
            raise ValueError("Motion authority requires calibration provenance")
        if self.collision_ready and not (self.observed_geometry_refs or self.inferred_geometry_refs):
            raise ValueError("Collision authority requires geometry")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")

    @property
    def authority(self) -> SceneAuthority | None:
        if self.motion_ready:
            return SceneAuthority.MOTION
        if self.collision_ready:
            return SceneAuthority.COLLISION
        if self.display_ready:
            return SceneAuthority.DISPLAY
        return None

    def require(self, authority: SceneAuthority) -> None:
        if not isinstance(authority, SceneAuthority):
            raise ValueError("authority must be SceneAuthority")
        if self.authority is None or self.authority < authority:
            reason = "; ".join(self.failure_reasons) or "scene authority not established"
            raise PermissionError(f"Scene does not satisfy {authority.name}: {reason}")


class SceneBuilder(Protocol):
    name: str

    def build(self, request: SceneBuildRequest) -> SceneArtifact: ...


def request_from_spatial_memory(
    index: SpatialViewIndex,
    *,
    request_id: str,
    now: float,
    operation: str,
    focus_entities: tuple[str, ...] = (),
    place_ids: tuple[str, ...] = (),
    limit: int = 6,
    minimum_authority: SceneAuthority = SceneAuthority.DISPLAY,
    max_age_s: float | None = 120.0,
) -> SceneBuildRequest:
    """Select a small relevant set of posed views for local reconstruction."""
    views = index.select_keyframes(
        now=now,
        entity_ids=focus_entities,
        place_ids=place_ids,
        limit=limit,
        max_age_s=max_age_s,
    )
    if not views:
        raise ValueError("No relevant posed keyframes available for local scene build")
    return SceneBuildRequest(
        request_id=request_id,
        episode_id=index.episode_id,
        source_keyframe_ids=tuple(view.keyframe_id for view in views),
        focus_entities=focus_entities,
        operation=operation,
        minimum_authority=minimum_authority,
    )
