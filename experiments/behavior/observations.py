"""The only native observation ingress. Everything not allowlisted is discarded."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import numpy as np
from PIL import Image

from experiments.behavior.contracts import Evidence, Observation, Stamp

CAMERAS = {
    "head": "robot_r1::robot_r1:zed_link:Camera:0",
    "left_wrist": "robot_r1::robot_r1:left_realsense_link:Camera:0",
    "right_wrist": "robot_r1::robot_r1:right_realsense_link:Camera:0",
}
RESOLUTIONS = {"head": (720, 720), "left_wrist": (480, 480), "right_wrist": (480, 480)}


def array(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def capture_intrinsics(evaluator, observation):
    """Bind allowlisted sensor intrinsics to a frozen observation, never world poses.

    Caller must capture without intervening simulator steps or sensor changes.
    This does not estimate or qualify camera extrinsics/localization.
    """
    calibration = {}
    for camera, prefix in CAMERAS.items():
        if evaluator.robot_camera_names[camera] != prefix:
            raise ValueError("Native camera mapping changed")
        rgb, depth = observation.rgb[camera], observation.depth[camera]
        if any(ref.stamp != observation.stamp or ref.observed_at != observation.observed_at
               for ref in (rgb, depth)):
            raise ValueError("Calibration evidence boundary mismatch")
        sensor_name = prefix.split("::", 1)[1]
        matrix = array(evaluator.robot.sensors[sensor_name].intrinsic_matrix).astype(float)
        if (matrix.shape != (3, 3) or not np.isfinite(matrix).all()
                or matrix[0, 0] <= 0 or matrix[1, 1] <= 0
                or not np.allclose(matrix[2], [0, 0, 1])):
            raise ValueError("Invalid native intrinsics")
        calibration[camera] = {
            "intrinsic_matrix": matrix.tolist(), "image_shape": list(RESOLUTIONS[camera]),
            "source": "native_camera_intrinsics", "extrinsics": None,
            "stamp": observation.stamp.model_dump(), "observed_at": observation.observed_at,
            "rgb_evidence_id": rgb.id, "depth_evidence_id": depth.id,
        }
    return calibration


class EvidenceStore:
    def __init__(self, root: Path, *, png_compress_level: int = 6):
        if type(png_compress_level) is not int or not 0 <= png_compress_level <= 9:
            raise ValueError("PNG compression level must be an integer from 0 to 9")
        self.png_compress_level = png_compress_level
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, pixels: np.ndarray, modality: str, stamp: Stamp, at: float) -> Evidence:
        data = io.BytesIO()
        if modality == "rgb":
            Image.fromarray(pixels).save(data, format="PNG", compress_level=self.png_compress_level)
            suffix = ".png"
        elif modality == "depth":
            np.save(data, pixels, allow_pickle=False)
            suffix = ".npy"
        else:
            raise ValueError("Unsupported evidence modality")
        content = data.getvalue()
        digest = hashlib.sha256(content).hexdigest()
        path = self.root / (digest + suffix)
        if not path.exists():
            path.write_bytes(content)
        identity = hashlib.sha256(
            f"{stamp.model_dump_json()}:{at}:{modality}:{digest}".encode()
        ).hexdigest()
        return Evidence(id=identity, stamp=stamp, observed_at=at, source=modality, uri=path.name)

    def _read_content(self, evidence: Evidence) -> bytes:
        path = (self.root / evidence.uri).resolve()
        if path.parent != self.root:
            raise ValueError("Evidence path escapes store")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != path.stem:
            raise ValueError("Evidence content hash mismatch")
        return content

    def read(self, evidence: Evidence) -> np.ndarray:
        content = self._read_content(evidence)
        if evidence.source == "rgb":
            return np.asarray(Image.open(io.BytesIO(content)).convert("RGB"))
        if evidence.source == "depth":
            return np.load(io.BytesIO(content), allow_pickle=False)
        raise ValueError("Not an image")

    def png(self, evidence: Evidence) -> bytes:
        if evidence.source != "rgb":
            raise ValueError("PNG delivery requires RGB evidence")
        content = self._read_content(evidence)
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            if image.format == "PNG" and image.mode == "RGB":
                return content
            data = io.BytesIO()
            image.convert("RGB").save(data, format="PNG", compress_level=self.png_compress_level)
            return data.getvalue()


class BehaviorObservationFilter:
    def __init__(self, store: EvidenceStore, *, require_native_resolution=True):
        self.store = store
        self.require_native_resolution = require_native_resolution

    def convert(self, raw: dict, stamp: Stamp, observed_at: float) -> Observation:
        rgb, depth = {}, {}
        for name, prefix in CAMERAS.items():
            color = array(raw[prefix + "::rgb"])
            distance = array(raw[prefix + "::depth_linear"])
            if color.ndim != 3 or color.shape[-1] not in (3, 4) or color.dtype != np.uint8:
                raise ValueError("Expected native uint8 RGB(A)")
            if distance.ndim == 3 and distance.shape[-1] == 1:
                distance = distance[..., 0]
            if distance.shape != color.shape[:2]:
                raise ValueError("Unaligned RGB-D")
            if self.require_native_resolution and color.shape[:2] != RESOLUTIONS[name]:
                raise ValueError("Use RGBDFullResWrapper; do not silently resize/crop")
            distance = distance.astype(np.float32, copy=True)
            distance[~np.isfinite(distance) | (distance <= 0)] = np.nan
            rgb[name] = self.store.put(color[..., :3], "rgb", stamp, observed_at)
            depth[name] = self.store.put(distance, "depth", stamp, observed_at)
        proprio = array(raw["robot_r1::proprio"])
        if proprio.ndim != 1 or not np.isfinite(proprio).all():
            raise ValueError("Invalid native proprioception")
        # Deliberately omit task_id, cam_rel_poses, segmentation, rewards and termination.
        return Observation(
            stamp=stamp,
            observed_at=observed_at,
            rgb=rgb,
            depth=depth,
            proprio=tuple(proprio.tolist()),
        )
