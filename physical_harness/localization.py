"""Legal head-camera RGB-D odometry; simulator poses are never inputs."""

from __future__ import annotations

import math
from typing import Any, Callable

from .adapters.behavior import LegalObservation


class LocalizationLost(RuntimeError):
    """The current local map can no longer accept pose updates safely."""


class RGBDOdometry:
    """Stateful Open3D odometry suitable as ``BehaviorAdapter.pose_estimator``.

    ``load_artifact`` resolves only the RGB/depth references already present in
    a legal observation. An optional motion estimator supports deterministic
    testing and alternate legal RGB-D implementations. It must return
    ``(success, source_to_target_transform, 6x6_information_matrix)``.
    ``reference_mode="first"`` keeps a fixed reference for bounded diagnostics;
    freshness is still checked between consecutive current observations. It
    does not reset the map or turn registration quality into motion authority.
    """

    def __init__(
        self,
        load_artifact: Callable[[str], Any],
        *,
        camera: str = "head",
        motion_estimator: Callable[..., tuple[bool, Any, Any]] | None = None,
        max_translation_m: float = 0.5,
        max_rotation_deg: float = 35.0,
        max_frame_gap_s: float = 2.0,
        min_information: float = 10.0,
        reference_mode: str = "previous",
    ):
        if not callable(load_artifact) or not isinstance(camera, str) or not camera.strip():
            raise ValueError("Artifact loader and camera are required")
        values = (max_translation_m, max_rotation_deg, max_frame_gap_s, min_information)
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
            raise ValueError("Odometry bounds must be finite numbers")
        if min(values) <= 0:
            raise ValueError("Odometry bounds must be positive")
        if reference_mode not in ("previous", "first"):
            raise ValueError("Unknown odometry reference mode")
        self.reference_mode = reference_mode
        self.load_artifact = load_artifact
        self.camera = camera
        self.motion_estimator = motion_estimator
        self.max_translation_m = float(max_translation_m)
        self.max_rotation_deg = float(max_rotation_deg)
        self.max_frame_gap_s = float(max_frame_gap_s)
        self.min_information = float(min_information)
        self.previous: tuple[Any, Any, str] | None = None
        self.previous_observation: LegalObservation | None = None
        self.reference_observation: LegalObservation | None = None
        self.transform: Any = None
        self.lost = False

    @staticmethod
    def _numpy():
        try:
            import numpy as np
        except ImportError as error:
            raise RuntimeError("RGB-D localization requires the localization extra") from error
        return np

    @classmethod
    def _rigid(cls, transform):
        np = cls._numpy()
        value = np.asarray(transform, dtype=np.float64)
        if value.shape != (4, 4) or not np.isfinite(value).all():
            raise ValueError("Invalid estimated camera transform")
        rotation = value[:3, :3]
        if (
            not np.allclose(value[3], (0, 0, 0, 1), atol=1e-5)
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-4)
            or not np.isclose(np.linalg.det(rotation), 1, atol=1e-4)
        ):
            raise ValueError("Estimated camera transform is not rigid")
        return value

    @classmethod
    def _validate_images(cls, rgb, depth, calibration):
        np = cls._numpy()
        rgb = np.asarray(rgb)
        depth = np.asarray(depth, dtype=np.float32) * calibration["depth_scale_m"]
        shape = (calibration["height"], calibration["width"])
        if rgb.shape != (*shape, 3) or depth.shape != shape or rgb.dtype != np.uint8:
            raise ValueError("RGB-D artifacts do not match legal camera calibration")
        valid = np.isfinite(depth) & (depth > 0)
        if float(valid.mean()) < 0.05:
            raise LocalizationLost("Insufficient legal depth")
        return np.ascontiguousarray(rgb), np.ascontiguousarray(np.where(valid, depth, 0))

    @staticmethod
    def _open3d_estimate(previous_rgb, previous_depth, rgb, depth, calibration):
        try:
            import open3d as o3d
        except ImportError as error:
            raise RuntimeError("Open3D is required for the default RGB-D odometry backend") from error

        def frame(color, z):
            return o3d.geometry.RGBDImage.create_from_color_and_depth(
                o3d.geometry.Image(color),
                o3d.geometry.Image(z),
                depth_scale=1.0,
                depth_trunc=10.0,
                convert_rgb_to_intensity=True,
            )

        intrinsics = o3d.camera.PinholeCameraIntrinsic(
            calibration["width"],
            calibration["height"],
            calibration["fx"],
            calibration["fy"],
            calibration["cx"],
            calibration["cy"],
        )
        import numpy as np

        return o3d.pipelines.odometry.compute_rgbd_odometry(
            frame(previous_rgb, previous_depth),
            frame(rgb, depth),
            intrinsics,
            np.eye(4),
            o3d.pipelines.odometry.RGBDOdometryJacobianFromHybridTerm(),
            o3d.pipelines.odometry.OdometryOption(),
        )

    def __call__(self, observation: LegalObservation) -> dict[str, Any]:
        if self.lost:
            raise LocalizationLost("Odometry lost; start a new map/episode explicitly")
        envelope = observation.to_envelope()
        if envelope.get("estimated_pose") is not None:
            raise ValueError("Odometry accepts only unlocalized legal observations")
        if self.camera not in observation.rgb_refs:
            raise ValueError("Configured odometry camera is unavailable")
        previous = self.previous_observation
        if previous is not None:
            if observation.episode_id != previous.episode_id:
                raise ValueError("Odometry cannot cross episode boundaries")
            gap = observation.sim_time - previous.sim_time
            if gap <= 0:
                raise ValueError("Odometry received stale observation")
            if gap > self.max_frame_gap_s:
                self.lost = True
                raise LocalizationLost("RGB-D frame gap exceeds odometry bound")

        calibration = observation.camera_intrinsics[self.camera]
        if (self.reference_observation is not None
                and calibration != self.reference_observation.camera_intrinsics[self.camera]):
            self.lost = True
            raise LocalizationLost("Camera calibration changed within the local map")
        rgb, depth = self._validate_images(
            self.load_artifact(observation.rgb_refs[self.camera]),
            self.load_artifact(observation.depth_refs[self.camera]),
            calibration,
        )
        np = self._numpy()
        if self.transform is None:
            self.transform = np.eye(4)
            confidence = 1.0
            evidence_ids = [observation.observation_id]
        else:
            previous_rgb, previous_depth, _ = self.previous
            estimator = self.motion_estimator or self._open3d_estimate
            success, delta, information = estimator(
                previous_rgb, previous_depth, rgb, depth, calibration
            )
            try:
                delta = self._rigid(delta)
                information = np.asarray(information, dtype=np.float64)
                angle = math.degrees(
                    math.acos(float(np.clip((np.trace(delta[:3, :3]) - 1) / 2, -1, 1)))
                )
                diagonal = np.diag(information)
                if (
                    success is not True
                    or float(np.linalg.norm(delta[:3, 3])) > self.max_translation_m
                    or angle > self.max_rotation_deg
                    or information.shape != (6, 6)
                    or not np.isfinite(information).all()
                    or float(np.min(diagonal)) < self.min_information
                ):
                    raise ValueError("Odometry failed, jumped, or has insufficient information")
            except (TypeError, ValueError, np.linalg.LinAlgError) as error:
                self.lost = True
                raise LocalizationLost(str(error)) from error
            self.transform = self._rigid(
                np.linalg.inv(delta) if self.reference_mode == "first"
                else self.transform @ np.linalg.inv(delta))
            confidence = min(1.0, float(np.min(diagonal)) / (self.min_information * 2))
            evidence_ids = [self.reference_observation.observation_id, observation.observation_id]

        if self.previous is None or self.reference_mode == "previous":
            self.previous = (rgb, depth, observation.observation_id)
            self.reference_observation = observation
        self.previous_observation = observation
        return {
            "method": "rgbd_odometry",
            "frame": "local_map",
            "camera": self.camera,
            "transform": self.transform.tolist(),
            "evidence_ids": evidence_ids,
            "confidence": confidence,
        }
