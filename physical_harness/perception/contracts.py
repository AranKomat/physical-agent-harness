"""Evidence-bound discovery contracts; pixels, semantics and actuation stay separate.

All clocks suffixed ``wall`` share the monotonic clock of the run. Simulation
and wall time are NEVER subtracted from each other. These are references into
existing capture/media stores, not a replacement database or a sensor API.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

from physical_harness.core.actions import Basis, digest, encode, ids, integer, number, plain, text


def fields(value: dict, required: set[str]) -> None:
    if type(value) is not dict or set(value) != required:
        raise ValueError(f"Expected exactly {sorted(required)}")


def bounded_tuple(value, cls, *, maximum=128, minimum=0):
    if type(value) is not tuple or not minimum <= len(value) <= maximum:
        raise ValueError("Bounded immutable collection required")
    if any(not isinstance(v, cls) for v in value):
        raise ValueError(f"Expected {cls.__name__}")
    return value


def sha256(value: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Lowercase SHA-256 required")
    return value


@dataclass(frozen=True)
class FrameRef:
    """One actual observed image. Derived crops retain their parent and exact ROI."""
    basis: Basis
    asset_id: str
    content_sha256: str
    camera: str
    width: int
    height: int
    available_wall: float
    parent_id: str | None = None
    parent_box: tuple[float, float, float, float] | None = None

    def __post_init__(self):
        if not isinstance(self.basis, Basis):
            raise ValueError("Existing legal Basis required")
        for s in (self.asset_id, self.camera):
            text(s)
        sha256(self.content_sha256)
        integer(self.width, low=1, high=16384)
        integer(self.height, low=1, high=16384)
        number(self.available_wall, low=self.basis.captured_wall)
        if (self.parent_id is None) != (self.parent_box is None):
            raise ValueError("Crop must carry both parent ID and normalized parent ROI")
        if self.parent_id is not None:
            text(self.parent_id)
            if self.parent_id == self.asset_id:
                raise ValueError("Crop cannot be its own parent")
            validate_box(self.parent_box)

    def available(self, current: Basis, now: float) -> None:
        if (self.basis.episode, self.basis.robot_fingerprint, self.basis.domain) != (
            current.episode, current.robot_fingerprint, current.domain
        ):
            raise PermissionError("Foreign visual evidence")
        number(now, low=0)
        if now < current.captured_wall or self.basis.sim_time > current.sim_time or self.available_wall > now:
            raise PermissionError("Future visual evidence")

    def verify_bytes(self, data: bytes) -> None:
        if type(data) is not bytes or hashlib.sha256(data).hexdigest() != self.content_sha256:
            raise PermissionError("Image content does not match capture reference")

    @property
    def pixels(self):
        return self.width * self.height


def validate_box(box) -> tuple[float, float, float, float]:
    if type(box) is not tuple or len(box) != 4:
        raise ValueError("Immutable normalized xyxy box required")
    x0, y0, x1, y1 = (number(x, low=0, high=1) for x in box)
    if x0 >= x1 or y0 >= y1:
        raise ValueError("Nonempty normalized xyxy box required")
    return x0, y0, x1, y1


@dataclass(frozen=True)
class RegionRef:
    id: str
    frame_id: str
    box: tuple[float, float, float, float]
    # A local track ID is a reference, NOT physical-instance identity.
    scoped_track: tuple[str, str, str] | None = None  # camera, session, local_id

    def __post_init__(self):
        text(self.id)
        text(self.frame_id)
        validate_box(self.box)
        if self.scoped_track is not None:
            if type(self.scoped_track) is not tuple or len(self.scoped_track) != 3:
                raise ValueError("Camera/session/local-ID scope required")
            for s in self.scoped_track:
                text(s)


@dataclass(frozen=True)
class DiscoveryRequest:
    id: str
    task: str
    task_revision: str
    current: Basis
    frames: tuple[FrameRef, ...]
    regions: tuple[RegionRef, ...]
    known_ids: tuple[str, ...]
    inventory_revision: str
    submitted_wall: float
    deadline_wall: float
    reasons: tuple[str, ...]
    mode: str = "delta"
    max_updates: int = 4
    max_attention: int = 2
    known_summary_json: str = "[]"

    def __post_init__(self):
        for s in (self.id, self.task_revision, self.inventory_revision):
            text(s)
        text(self.task, limit=4096)
        if not isinstance(self.current, Basis):
            raise ValueError("Current Basis required")
        bounded_tuple(self.frames, FrameRef, minimum=1, maximum=3)
        bounded_tuple(self.regions, RegionRef, maximum=64)
        ids(tuple(f.asset_id for f in self.frames))
        ids(tuple(r.id for r in self.regions))
        ids(self.known_ids, limit=128)
        ids(self.reasons, empty=False, limit=16)
        number(self.submitted_wall, low=self.current.captured_wall)
        number(self.deadline_wall, low=self.submitted_wall + .001)
        if self.deadline_wall - self.submitted_wall > 300:
            raise ValueError("Unbounded semantic request")
        if self.mode not in {"room_initial", "delta"}:
            raise ValueError("Unknown semantic pass mode")
        integer(self.max_updates, low=1, high=12)
        integer(self.max_attention, low=0, high=4)
        for f in self.frames:
            f.available(self.current, self.submitted_wall)
        if not any(f.basis == self.current for f in self.frames):
            raise ValueError("Semantic batch must include a current image")
        if any(r.frame_id not in {f.asset_id for f in self.frames} for r in self.regions):
            raise ValueError("Region outside supplied images")
        from physical_harness.core.actions import strict_loads
        obj = strict_loads('{"items":' + self.known_summary_json + '}', max_bytes=12000)
        if type(obj["items"]) is not list or any(type(x) is not dict or x.get("id") not in self.known_ids for x in obj["items"]):
            raise ValueError("Known summary must refer only to supplied known IDs")

    @property
    def fingerprint(self):
        return digest(self)


class Retention(str, Enum):
    IGNORE = "ignore"
    AGGREGATE = "aggregate"
    SIGHTING = "sighting"
    RETAIN = "retain"
    FOCUS = "focus"


@dataclass(frozen=True)
class ValueHints:
    task: int = 0
    future: int = 0
    landmark: int = 0
    novelty: int = 0
    uncertainty_value: int = 0
    redundancy: int = 0
    transience: int = 0

    def __post_init__(self):
        for x in plain(self).values():
            integer(x, low=0, high=3)

    @property
    def rank(self):
        """Declared heuristic, not probability, calibrated utility or a safety gate."""
        return 4*self.task + 2*self.future + 2*self.landmark + self.novelty + self.uncertainty_value - self.redundancy - self.transience


@dataclass(frozen=True)
class SemanticUpdate:
    local_id: str
    frame_id: str
    region_id: str | None
    box: tuple[float, float, float, float] | None
    known_id: str | None
    description: str
    hypotheses: tuple[str, ...]
    status: str  # hypothesis | recognized | contradicts | unknown
    retention: Retention
    value: ValueHints
    needs_view: bool

    def __post_init__(self):
        for s in (self.local_id, self.frame_id):
            text(s)
        if self.region_id is None and self.box is None:
            raise ValueError("Ground to a supplied region or a coarse image box")
        if self.region_id is not None and self.box is not None:
            raise ValueError("Choose region OR box, not competing coordinates")
        if self.region_id is not None:
            text(self.region_id)
        if self.box is not None:
            validate_box(self.box)
        if self.known_id is not None:
            text(self.known_id)
        text(self.description, limit=640)
        ids(self.hypotheses, limit=3)
        if self.status not in {"hypothesis", "recognized", "contradicts", "unknown"}:
            raise ValueError("Explicit semantic status required")
        if self.status == "recognized" and not self.hypotheses:
            raise ValueError("Recognition without a category")
        if not isinstance(self.retention, Retention) or not isinstance(self.value, ValueHints):
            raise ValueError("Typed retention/value hints required")
        if type(self.needs_view) is not bool:
            raise ValueError("needs_view must be boolean")


@dataclass(frozen=True)
class AttentionUpdate:
    local_id: str
    reason: str
    significance: str

    def __post_init__(self):
        text(self.local_id)
        text(self.reason, limit=320)
        if self.significance not in {"low", "normal", "high"}:
            raise ValueError("Unknown significance")


@dataclass(frozen=True)
class DiscoveryResult:
    request: DiscoveryRequest
    model: str
    completed_wall: float
    updates: tuple[SemanticUpdate, ...]
    attention: tuple[AttentionUpdate, ...]
    scene_summary: str

    def __post_init__(self):
        if not isinstance(self.request, DiscoveryRequest):
            raise ValueError("Original request required")
        text(self.model)
        number(self.completed_wall, low=self.request.submitted_wall)
        bounded_tuple(self.updates, SemanticUpdate, maximum=self.request.max_updates)
        bounded_tuple(self.attention, AttentionUpdate, maximum=self.request.max_attention)
        ids(tuple(u.local_id for u in self.updates))
        ids(tuple(a.local_id for a in self.attention))
        if type(self.scene_summary) is not str or len(self.scene_summary.encode()) > 800:
            raise ValueError("Bounded scene summary required")
        frames = {f.asset_id: f for f in self.request.frames}
        regions = {r.id: r for r in self.request.regions}
        for u in self.updates:
            if u.frame_id not in frames or (u.known_id is not None and u.known_id not in self.request.known_ids):
                raise PermissionError("Unknown source or inventory reference")
            if u.region_id is not None and (u.region_id not in regions or regions[u.region_id].frame_id != u.frame_id):
                raise PermissionError("Region and image do not match")
        if any(a.local_id not in {u.local_id for u in self.updates} for a in self.attention):
            raise PermissionError("Attention must refer to a returned update")

    @property
    def fingerprint(self):
        return digest(self)


def frame_from_dict(value: dict) -> FrameRef:
    from physical_harness.core.tasks import basis_from_dict
    d = dict(value)
    d["basis"] = basis_from_dict(d["basis"])
    if d.get("parent_box") is not None:
        d["parent_box"] = tuple(d["parent_box"])
    return FrameRef(**d)


def immutable_json(value: Any, *, max_bytes=32000) -> str:
    raw = encode(value)
    if len(raw) > max_bytes:
        raise ValueError("JSON budget exceeded")
    return raw.decode()


def cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("Compatible nonempty feature vectors required")
    for x in a + b:
        number(x)
    aa, bb = math.sqrt(sum(x*x for x in a)), math.sqrt(sum(x*x for x in b))
    if aa < 1e-12 or bb < 1e-12:
        raise ValueError("Zero feature vector")
    return max(-1., min(1., sum(x*y for x, y in zip(a, b))/(aa*bb)))


def request_from_dict(value: dict) -> DiscoveryRequest:
    """Rehydrate only a journaled request, retaining both capture/availability clocks."""
    from physical_harness.core.tasks import basis_from_dict
    fields(value, set(DiscoveryRequest.__dataclass_fields__))
    d = dict(value)
    d["current"] = basis_from_dict(d["current"])
    d["frames"] = tuple(frame_from_dict(f) for f in d["frames"])
    d["regions"] = tuple(RegionRef(r["id"], r["frame_id"], tuple(r["box"]),
                                   tuple(r["scoped_track"]) if r["scoped_track"] is not None else None)
                         for r in d["regions"])
    for key in ("known_ids", "reasons"):
        d[key] = tuple(d[key])
    return DiscoveryRequest(**d)
