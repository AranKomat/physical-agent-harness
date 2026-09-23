"""Bounded novelty-triggered semantic sampling, independent of semantic models.

Novelty is a heuristic. A buffer improves transient coverage but cannot guarantee
seeing every brief object. Sensor safety monitoring is never gated by this code.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from physical_harness.core.actions import Pose, ids, integer, number, plain
from physical_harness.core.discovery import FrameRef, bounded_tuple


@dataclass(frozen=True)
class ViewSample:
    frame: FrameRef
    descriptor: tuple[float, ...]
    camera_pose: Pose | None = None
    tracks: tuple[str, ...] = ()
    important_lost: tuple[str, ...] = ()
    room_changed: bool = False
    requested: bool = False

    def __post_init__(self):
        if not isinstance(self.frame, FrameRef) or type(self.descriptor) is not tuple or not 1 <= len(self.descriptor) <= 4096:
            raise ValueError("Image reference and bounded numeric descriptor required")
        for n in self.descriptor:
            number(n, low=0, high=1)
        ids(self.tracks, limit=512)
        ids(self.important_lost, limit=64)
        if self.camera_pose is not None and self.camera_pose.frame != self.frame.basis.frame:
            raise ValueError("Camera pose must use observation's named frame")
        if type(self.room_changed) is not bool or type(self.requested) is not bool:
            raise ValueError("Boolean view events required")


@dataclass(frozen=True)
class TriggerConfig:
    image_difference: float = .12
    translation_m: float = .20
    rotation_rad: float = .35
    min_interval_s: float = .25
    buffer_seconds: float = 5.
    buffer_frames: int = 48
    cameras: int = 8
    batch_images: int = 3

    def __post_init__(self):
        number(self.image_difference, low=.001, high=1)
        number(self.translation_m, low=.001, high=10)
        number(self.rotation_rad, low=.001, high=math.pi)
        number(self.min_interval_s, low=0, high=60)
        number(self.buffer_seconds, low=.01, high=120)
        integer(self.buffer_frames, low=2, high=1024)
        integer(self.cameras, low=1, high=32)
        integer(self.batch_images, low=1, high=3)


def thumbnail_descriptor(image_bytes: bytes, frame: FrameRef, *, side: int = 16) -> tuple[float, ...]:
    """Exact supplied image -> small RGB thumbnail. No model or download."""
    import io

    from PIL import Image
    integer(side, low=2, high=32)
    frame.verify_bytes(image_bytes)
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.size != (frame.width, frame.height):
            raise ValueError("Decoded image dimensions changed")
        image = image.convert("RGB").resize((side, side), Image.Resampling.BILINEAR)
        return tuple(x/255. for x in image.tobytes())


def image_difference(a, b):
    if len(a) != len(b):
        raise ValueError("Descriptor preprocessing changed")
    return sum(abs(x-y) for x, y in zip(a, b))/len(a)


class SemanticKeyframes:
    def __init__(self, config: TriggerConfig = TriggerConfig()):
        self.config = config
        self.samples: list[ViewSample] = []
        self.checkpoints: dict[str, ViewSample] = {}
        self.last_wall: dict[str, float] = {}
        self.used: set[str] = set()
        self.episode = None
        self.evicted = 0

    def ingest(self, sample: ViewSample, *, now: float) -> tuple[str, ...]:
        if not isinstance(sample, ViewSample):
            raise ValueError("ViewSample required")
        f = sample.frame
        f.available(f.basis, now)
        if self.episode is None:
            self.episode = f.basis.episode
        if self.episode != f.basis.episode:
            raise PermissionError("New episode requires a new view buffer")
        if f.camera not in self.last_wall and len(self.last_wall) >= self.config.cameras:
            raise ValueError("Camera capacity exceeded")
        if f.asset_id in self.used or f.basis.captured_wall <= self.last_wall.get(f.camera, -1):
            raise PermissionError("Repeated or regressed camera capture")
        self.used.add(f.asset_id)
        self.last_wall[f.camera] = f.basis.captured_wall
        self.samples.append(sample)
        kept = [s for s in self.samples if now-s.frame.available_wall <= self.config.buffer_seconds]
        kept = kept[-self.config.buffer_frames:]
        self.evicted += len(self.samples)-len(kept)
        self.samples = kept
        # Bound dedup state as well; monotonic camera timestamps reject old replays.
        self.used = {s.frame.asset_id for s in kept}
        prior = self.checkpoints.get(f.camera)
        if prior is None:
            return ("initial_view",)
        reasons = []
        if sample.requested:
            reasons.append("executive_refresh")
        if sample.room_changed:
            reasons.append("new_place")
        if sample.important_lost:
            reasons.append("important_track_lost")
        if set(sample.tracks) - set(prior.tracks):
            reasons.append("new_track")
        if image_difference(sample.descriptor, prior.descriptor) >= self.config.image_difference:
            reasons.append("image_novelty")
        if f.basis.frame_epoch != prior.frame.basis.frame_epoch:
            reasons.append("local_frame_changed")
        elif sample.camera_pose and prior.camera_pose:
            a, b = sample.camera_pose, prior.camera_pose
            if math.dist(a.xyz, b.xyz) >= self.config.translation_m:
                reasons.append("translation")
            trace = sum(a.matrix[4*i+j]*b.matrix[4*i+j] for i in range(3) for j in range(3))
            if math.acos(max(-1., min(1., (trace-1)/2))) >= self.config.rotation_rad:
                reasons.append("rotation")
        if not sample.requested and f.available_wall-prior.frame.available_wall < self.config.min_interval_s:
            return ()
        return tuple(reasons)

    def select(self, current: FrameRef, *, now: float) -> tuple[FrameRef, ...]:
        """Current view plus diverse buffered views, returned chronologically.

        No all-frame prompt. Selection does not imply that omitted objects did not
        exist; emit buffer/selection counts with the request receipt.
        """
        current.available(current.basis, now)
        item = next((s for s in self.samples if s.frame == current), None)
        if item is None:
            raise ValueError("Current frame is not in the retained buffer")
        eligible = [s for s in self.samples if s.frame.available_wall <= now and
                    s.frame.basis.sim_time <= current.basis.sim_time and
                    now-s.frame.available_wall <= self.config.buffer_seconds]
        chosen = [item]
        while len(chosen) < self.config.batch_images:
            candidates = [s for s in eligible if s not in chosen]
            if not candidates:
                break
            def score(s):
                diversity = min(image_difference(s.descriptor, t.descriptor) for t in chosen)
                event = .15 * bool(s.important_lost or s.room_changed or s.requested)
                return diversity + event, s.frame.available_wall, s.frame.asset_id
            best = max(candidates, key=score)
            if score(best)[0] <= 0:
                break
            chosen.append(best)
        return tuple(s.frame for s in sorted(chosen, key=lambda s: (s.frame.basis.sim_time, s.frame.available_wall, s.frame.asset_id)))

    def acknowledge_submission(self, frames: tuple[FrameRef, ...]) -> None:
        bounded_tuple(frames, FrameRef, maximum=3, minimum=1)
        for f in frames:
            sample = next((s for s in self.samples if s.frame == f), None)
            if sample is None:
                raise ValueError("Cannot checkpoint an evicted/unobserved frame")
            old = self.checkpoints.get(f.camera)
            if old is None or f.basis.captured_wall > old.frame.basis.captured_wall:
                self.checkpoints[f.camera] = sample

    def report(self):
        return {"buffered_frames": len(self.samples), "evicted_frames": self.evicted,
                "checkpoint_ids": {k: v.frame.asset_id for k, v in self.checkpoints.items()},
                "thresholds": plain(self.config), "transient_coverage_guaranteed": False}
