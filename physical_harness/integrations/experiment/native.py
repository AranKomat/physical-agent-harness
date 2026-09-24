"""Native callback contract. No weights, simulator GT, action-codec guesses, or torques."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from physical_harness.core.contracts import SkillReceipt, SkillRequest
from physical_harness.integrations.experiment.media import image_geometry
from physical_harness.integrations.experiment.validation import identifiers, number, text


@dataclass(frozen=True)
class CameraCapture:
    camera: str
    data: bytes

    def __post_init__(self):
        text(self.camera, "camera", 256)
        image_geometry(self.data)


@dataclass(frozen=True)
class BeliefEstimate:
    entity: str
    predicate: str
    value: str
    camera: str
    epistemic: str = "inferred"

    def __post_init__(self):
        for value in (self.entity, self.predicate, self.value, self.camera):
            text(value, maximum=1024)
        if self.predicate not in {"label", "visibility", "location", "place", "IN", "ON",
                                  "HELD_BY", "open_state", "confidence", "identity_candidates"}:
            raise ValueError("Unapproved estimator predicate")
        if self.epistemic not in {"observed", "inferred"}:
            raise ValueError("Estimator must declare its epistemic status")


@dataclass(frozen=True)
class ObjectBox:
    entity: str
    camera: str
    box: tuple[int, int, int, int]
    label: str
    identity_candidates: tuple[str, ...] = ()

    def __post_init__(self):
        for value in (self.entity, self.camera, self.label):
            text(value, maximum=256)
        identifiers(self.identity_candidates)
        if len(self.box) != 4 or any(type(x) is not int or x < 0 for x in self.box):
            raise ValueError("Box must contain four nonnegative pixel coordinates")
        if self.box[2] <= self.box[0] or self.box[3] <= self.box[1]:
            raise ValueError("Box has no area")


@dataclass(frozen=True)
class CoverageScan:
    scope: str
    targets: tuple[str, ...]
    cameras: tuple[str, ...]
    measured_fraction: float
    method: str
    result: str

    def __post_init__(self):
        text(self.scope)
        if not identifiers(self.targets) or not identifiers(self.cameras):
            raise ValueError("Coverage needs explicit targets and source cameras")
        if not 0 <= number(self.measured_fraction) <= 1:
            raise ValueError("Coverage fraction outside [0,1]")
        if self.method not in {"depth_visibility", "calibrated_sweep", "human_annotation"}:
            raise ValueError("Unqualified coverage method; a VLM guess is not measured coverage")
        if self.result not in {"seen", "not_seen", "partial", "unknown"}:
            raise ValueError("Invalid coverage result")


@dataclass(frozen=True)
class Observation:
    episode: str
    id: str
    sim_time: float
    cameras: tuple[CameraCapture, ...]
    estimates: tuple[BeliefEstimate, ...] = ()
    boxes: tuple[ObjectBox, ...] = ()
    place_id: str | None = None
    place_description: str | None = None
    coverage: tuple[CoverageScan, ...] = ()
    legal_envelope: Mapping[str, Any] | None = None

    def __post_init__(self):
        text(self.episode, maximum=256)
        text(self.id, maximum=256)
        number(self.sim_time)
        if not self.cameras or len(self.cameras) > 8:
            raise ValueError("One to eight legal RGB views required")
        names = [c.camera for c in self.cameras]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate camera names")
        if self.place_id is not None:
            text(self.place_id, maximum=256)
        if self.place_description is not None:
            text(self.place_description, maximum=1600)
        for estimate in self.estimates:
            if estimate.camera not in names:
                raise ValueError("Estimate must cite a supplied camera")
        for box in self.boxes:
            if box.camera not in names:
                raise ValueError("Object box must cite a supplied camera")
            capture = next(c for c in self.cameras if c.camera == box.camera)
            width, height, _ = image_geometry(capture.data)
            if box.box[2] > width or box.box[3] > height:
                raise ValueError("Object box exceeds camera image")
        for scan in self.coverage:
            if not set(scan.cameras) <= set(names):
                raise ValueError("Coverage references an unavailable camera")
        if self.legal_envelope is not None:
            from physical_harness.integrations.sensors.behavior import LegalObservation

            legal = LegalObservation.from_envelope(self.legal_envelope).to_envelope()
            if (
                legal["episode_id"] != self.episode
                or legal["observation_id"] != self.id
                or legal["sim_time"] != self.sim_time
                or set(legal["rgb_refs"]) != set(names)
            ):
                raise ValueError("Legal envelope does not match the observation")
            object.__setattr__(self, "legal_envelope", legal)


@dataclass
class NativeBindings:
    """Your private BEHAVIOR driver implements only this boundary.

    observe must capture legal sensors and observation-derived estimates only.
    run_skill must enforce its own deadline and report stop acknowledgement.
    stop must enforce its own deadline and return True only after motion stops.
    No claim is made that a Python callback can be forcibly interrupted safely.
    """
    name: str
    observe: Callable[[], Observation]
    run_skill: Callable[[SkillRequest], SkillReceipt]
    stop: Callable[[], bool]
    simulated: bool = True
    qualification_id: str | None = None
    motion_qualified: bool = False
    clearance_status: str = "unknown"

    def __post_init__(self):
        text(self.name, "name", 256)
        if self.qualification_id is not None:
            text(self.qualification_id, "qualification_id", 256)
        if type(self.simulated) is not bool or type(self.motion_qualified) is not bool:
            raise ValueError("Native simulation and qualification flags must be boolean")
        if self.clearance_status not in {"unknown", "qualified"}:
            raise ValueError("Native clearance status must be unknown or qualified")
        if self.motion_qualified != (self.clearance_status == "qualified"):
            raise ValueError("Motion qualification and clearance status disagree")
