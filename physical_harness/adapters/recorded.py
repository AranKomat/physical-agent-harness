"""Read-only bridge for the pinned physical-ai-lab native sensor archives.

Capture timestamps are monotonic wall time, NOT simulation time. Native action
packing and real-R1Pro policy conversion are deliberately outside this module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ..evidence import EvidenceStore
from .behavior import LegalObservation, fields, number, text, vector

BEHAVIOR_COMMIT = "b1979916ec1549b10a4e65e630bc6504a9af1b00"
CAMERAS = {"head": 720, "left_wrist": 480, "right_wrist": 480}


def decode_proprio(values: list[float]) -> dict:
    """Eval r1pro.yaml order: base, left arm/EEF/fingers, right, trunk.

    Joint arrays exported here are left arm (7), right arm (7), trunk (4).
    Finger positions are separate. EEF pose fields are not forwarded.
    """
    vector(values, 61)
    return {
        "base_velocity": values[:3],
        "joint_positions": values[3:10] + values[28:35] + values[53:57],
        "joint_velocities": values[10:17] + values[35:42] + values[57:61],
        "gripper_positions": values[24:26] + values[49:51],
    }


@dataclass(frozen=True)
class RecordedFrame:
    envelope: dict
    captured_wall: float
    sequence: int

    def at_sim_time(self, sim_time: float) -> LegalObservation:
        """Caller must supply independently known simulation time, never infer it."""
        return LegalObservation.from_envelope({**self.envelope, "sim_time": sim_time})


def read_archive(root: str | Path):
    """Validate full evidence bytes and yield legal sensor-only recorded frames."""
    root = Path(root)
    metadata = json.loads((root / "sequence.json").read_text())
    if metadata.get("source_commit") != BEHAVIOR_COMMIT or metadata.get("passed") is not True:
        raise ValueError("Unqualified archive source revision/capture")
    calibration = metadata["camera_calibration"]
    store = EvidenceStore(root / "legal-evidence")
    session = None
    previous_time = -1.0
    previous_sequence = -1
    count = 0
    with (root / "observations.jsonl").open() as stream:
        for line in stream:
            if len(line) > 1024 * 1024:
                raise ValueError("Oversized observation")
            raw = json.loads(line)
            stamp = raw["stamp"]
            fields(stamp, {"session", "epoch", "sequence"})
            text(stamp["session"])
            for key in ("epoch", "sequence"):
                if type(stamp[key]) is not int or stamp[key] < 0:
                    raise ValueError("Invalid recording stamp")
            identity = (stamp["session"], stamp["epoch"])
            session = session or identity
            captured = number(raw["observed_at"], 0)
            if (
                identity != session
                or stamp["sequence"] <= previous_sequence
                or captured <= previous_time
            ):
                raise ValueError("Foreign or stale recording frame")
            envelope = {
                "schema_version": 1,
                "episode_id": f"{session[0]}:{session[1]}",
                "observation_id": f"{session[0]}:{session[1]}:{stamp['sequence']}",
                "rgb_refs": {},
                "depth_refs": {},
                "camera_intrinsics": {},
                "camera_frames": {},
                "proprioception": decode_proprio(raw["proprio"]),
            }
            for modality in ("rgb", "depth"):
                if set(raw[modality]) != set(CAMERAS):
                    raise ValueError("Unexpected camera set")
                for camera, evidence in raw[modality].items():
                    if (
                        evidence["stamp"] != stamp
                        or evidence["observed_at"] != captured
                        or evidence["source"] != modality
                    ):
                        raise ValueError("Evidence is not aligned to recording frame")
                    suffix = ".png" if modality == "rgb" else ".npy"
                    if Path(evidence["uri"]).suffix != suffix:
                        raise ValueError("Unexpected evidence format")
                    store.read(evidence["uri"])
                    envelope[modality + "_refs"][camera] = evidence["uri"]
            for camera, size in CAMERAS.items():
                entry = calibration[camera]
                if entry["source"] != "native_camera_calibration":
                    raise ValueError("Unknown calibration source")
                matrix = entry["intrinsic_matrix"]
                if len(matrix) != 3:
                    raise ValueError("Invalid calibration matrix")
                for row in matrix:
                    vector(row, 3)
                if matrix[2] != [0, 0, 1] or matrix[0][1] != 0 or matrix[1][0] != 0:
                    raise ValueError("Unsupported camera skew")
                envelope["camera_intrinsics"][camera] = {
                    "width": size,
                    "height": size,
                    "fx": matrix[0][0],
                    "fy": matrix[1][1],
                    "cx": matrix[0][2],
                    "cy": matrix[1][2],
                    "depth_scale_m": 1.0,
                }
                envelope["camera_frames"][camera] = camera + "_optical"
            # Schema validation only; the temporary time is never exported.
            LegalObservation.from_envelope({**envelope, "sim_time": 0.0})
            yield RecordedFrame(envelope, captured, stamp["sequence"])
            previous_time, previous_sequence = captured, stamp["sequence"]
            count += 1
    if count != metadata["frames"] or count == 0:
        raise ValueError("Incomplete recording")


def audit_archive(root: str | Path) -> dict:
    frames = list(read_archive(root))
    refs = {
        ref
        for frame in frames
        for field in ("rgb_refs", "depth_refs")
        for ref in frame.envelope[field].values()
    }
    return {
        "kind": "recorded-native-sensor-audit",
        "passed": True,
        "frames": len(frames),
        "unique_artifacts_verified": len(refs),
        "source_sha256": hashlib.sha256(
            (Path(root) / "observations.jsonl").read_bytes()
        ).hexdigest(),
        "capture_wall_span_s": frames[-1].captured_wall - frames[0].captured_wall,
        "simulation_timestamps_available": False,
        "native_ready": False,
        "new_native_actions": 0,
        "model_calls": 0,
    }
