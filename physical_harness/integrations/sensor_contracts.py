"""Dormant hardware extension descriptions, not added BEHAVIOR observation channels."""
from __future__ import annotations

from dataclasses import dataclass

from physical_harness.core.actions import ids, integer, text
from physical_harness.perception.contracts import FrameRef


@dataclass(frozen=True)
class SensorCapability:
    id: str
    modality: str
    source: str  # legal_onboard | derived_from_legal | hardware_only
    calibration_revision: str
    available: bool = False

    def __post_init__(self):
        for s in (self.id, self.calibration_revision):
            text(s)
        if self.modality not in {"rgb", "depth", "proprioception", "lidar", "force_torque", "tactile", "high_resolution_rgb"}:
            raise ValueError("Unknown sensor modality")
        if self.source not in {"legal_onboard", "derived_from_legal", "hardware_only"} or type(self.available) is not bool:
            raise ValueError("Explicit source/availability required")


def admitted_sensors(sensors: tuple[SensorCapability, ...], *, domain: str):
    if domain != "behavior_sim":
        raise PermissionError("Hardware descriptors are dormant; real execution needs separate qualification")
    result = []
    for s in sensors:
        if s.available and (s.modality not in {"rgb", "depth", "proprioception"} or s.source == "hardware_only"):
            raise PermissionError("Additional sensor channels are not enabled in BEHAVIOR")
        if s.available:
            result.append(s)
    ids(tuple(s.id for s in result))
    return tuple(result)


@dataclass(frozen=True)
class FoveatedRequest:
    source: FrameRef
    region_id: str
    purpose: str
    max_pixels: int

    def __post_init__(self):
        text(self.region_id)
        text(self.purpose, limit=512)
        integer(self.max_pixels, low=1, high=16000000)

    def plan(self):
        return {"source_image": self.source.asset_id, "region_id": self.region_id,
                "purpose": self.purpose, "max_pixels": min(self.max_pixels, self.source.pixels),
                "choices": ["source_preserving_crop", "qualified_closer_view"],
                "synthetic_upscaling_is_measurement": False, "move_camera_automatically": False}
