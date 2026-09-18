"""JSON-only legal sensor boundary. Simulator and image dependencies stay outside.

Sources export normalized RGB-D references and proprioception, never Gym info.
Sources, artifact writers and estimators are trusted, not an OS security sandbox.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, Protocol


def json_copy(value: Any) -> Any:
    def check(item: Any) -> None:
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("Expected finite JSON values, not native objects")

    check(value)
    return json.loads(json.dumps(value, allow_nan=False))


def fields(value: Any, required: set[str], optional: set[str] = frozenset()) -> None:
    if (
        not isinstance(value, dict)
        or not required <= value.keys()
        or value.keys() - required - optional
    ):
        raise ValueError("Missing or non-allowlisted fields")


def text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError("Expected bounded nonempty text")
    return value


def number(value: Any, low: float = -math.inf, high: float = math.inf) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Invalid finite number or range")
    return float(value)


def vector(value: Any, length: int | None = None) -> None:
    if not isinstance(value, list) or not value or (length is not None and len(value) != length):
        raise ValueError("Invalid vector dimensions")
    for element in value:
        number(element)


def validate_pose(pose: Any, observation_id: str, cameras: set[str]) -> None:
    fields(pose, {"method", "frame", "camera", "transform", "evidence_ids", "confidence"})
    if pose["method"] not in {"rgbd_odometry", "proprio_odometry", "rgbd_slam"}:
        raise ValueError("Pose must be legally estimated, not simulator global pose")
    if pose["frame"] != "local_map" or pose["camera"] not in cameras:
        raise ValueError("Pose must map a calibrated camera to an arbitrary local map")
    if pose["evidence_ids"] != [observation_id]:
        raise ValueError("Pose provenance must reference this observation")
    number(pose["confidence"], 0, 1)
    matrix = pose["transform"]
    if not isinstance(matrix, list) or len(matrix) != 4:
        raise ValueError("Expected 4x4 camera-to-local-map transform")
    for row in matrix:
        vector(row, 4)
    if any(abs(a - b) > 1e-5 for a, b in zip(matrix[3], [0, 0, 0, 1])):
        raise ValueError("Invalid homogeneous transform")
    for i in range(3):
        for j in range(3):
            if abs(sum(matrix[k][i] * matrix[k][j] for k in range(3)) - (i == j)) > 1e-4:
                raise ValueError("Rotation is not orthonormal")
    a, b, c = [row[:3] for row in matrix[:3]]
    determinant = (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )
    if abs(determinant - 1) > 1e-4:
        raise ValueError("Rotation must be proper")


@dataclass(frozen=True)
class LegalObservation:
    observation_id: str
    sim_time: float
    rgb_refs: Mapping[str, str]
    depth_refs: Mapping[str, str]
    proprioception: Mapping[str, Any]
    camera_intrinsics: Mapping[str, Any]
    camera_frames: Mapping[str, str]
    episode_id: str = ""
    estimated_pose: Mapping[str, Any] | None = None
    schema_version: int = 1

    def to_envelope(self) -> dict[str, Any]:
        value = json_copy(asdict(self))
        self._validate(value)
        return value

    @classmethod
    def from_envelope(cls, envelope: Mapping[str, Any]) -> LegalObservation:
        value = json_copy(envelope)
        cls._validate(value)
        return cls(**value)

    @staticmethod
    def _validate(value: dict[str, Any]) -> None:
        fields(
            value,
            {
                "schema_version",
                "episode_id",
                "observation_id",
                "sim_time",
                "rgb_refs",
                "depth_refs",
                "proprioception",
                "camera_intrinsics",
                "camera_frames",
            },
            {"estimated_pose"},
        )
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise ValueError("Unsupported observation schema")
        text(value["episode_id"])
        text(value["observation_id"])
        number(value["sim_time"], 0)
        for name in ("rgb_refs", "depth_refs", "camera_intrinsics", "camera_frames"):
            if not isinstance(value[name], dict) or not value[name]:
                raise ValueError("At least one aligned calibrated RGB-D camera required")
        cameras = set(value["rgb_refs"])
        if any(
            set(value[name]) != cameras
            for name in ("depth_refs", "camera_intrinsics", "camera_frames")
        ):
            raise ValueError("Camera calibration/reference mismatch")
        for camera in cameras:
            text(camera)
            for name in ("rgb_refs", "depth_refs"):
                text(value[name][camera])
            if value["camera_frames"][camera] != camera + "_optical":
                raise ValueError("Only camera optical frames accepted")
            calibration = value["camera_intrinsics"][camera]
            fields(calibration, {"width", "height", "fx", "fy", "cx", "cy", "depth_scale_m"})
            for dim in ("width", "height"):
                if type(calibration[dim]) is not int or calibration[dim] <= 0:
                    raise ValueError("Invalid image dimensions")
            for name in ("fx", "fy", "depth_scale_m"):
                if number(calibration[name], 0) == 0:
                    raise ValueError("Calibration scale/focal length must be positive")
            number(calibration["cx"], 0, calibration["width"] - 1)
            number(calibration["cy"], 0, calibration["height"] - 1)
        proprio = value["proprioception"]
        fields(
            proprio, {"joint_positions"}, {"joint_velocities", "gripper_positions", "base_velocity"}
        )
        for name, values in proprio.items():
            vector(values, 3 if name == "base_velocity" else None)
        if "joint_velocities" in proprio and len(proprio["joint_positions"]) != len(
            proprio["joint_velocities"]
        ):
            raise ValueError("Joint vector mismatch")
        if value.get("estimated_pose") is not None:
            validate_pose(value["estimated_pose"], value["observation_id"], cameras)


class ObservationSource(Protocol):
    def reset(self) -> Mapping[str, Any]: ...
    def step(self, action: Any) -> Mapping[str, Any]: ...


class BehaviorAdapter:
    """One instance per episode; logger receives legal JSON keyframe envelopes."""

    def __init__(
        self,
        source: ObservationSource,
        *,
        episode_id: str,
        action_bounds: list[list[float]],
        action_codec: Callable[[list[float]], Any] | None = None,
        pose_estimator: Callable[[LegalObservation], Mapping[str, Any]] | None = None,
        logger: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.source = source
        self.episode_id = text(episode_id)
        self.bounds = json_copy(action_bounds)
        if not self.bounds:
            raise ValueError("Explicit native controller bounds required")
        for pair in self.bounds:
            vector(pair, 2)
            if pair[0] > pair[1]:
                raise ValueError("Reversed action bounds")
        self.codec = action_codec or (lambda action: action)
        self.estimator, self.logger = pose_estimator, logger
        self.current: LegalObservation | None = None
        self._ids: set[str] = set()
        self._started = False
        self._failed = False

    def _accept(self, raw: Mapping[str, Any]) -> LegalObservation:
        value = json_copy(raw)
        if "estimated_pose" in value:
            raise ValueError("Source cannot supply pose; inject a legal estimator")
        observation = LegalObservation.from_envelope(value)
        if observation.episode_id != self.episode_id:
            raise ValueError("Different episode observation")
        if observation.observation_id in self._ids or (
            self.current and observation.sim_time <= self.current.sim_time
        ):
            raise ValueError("Stale/replayed observation")
        if self.estimator:
            value["estimated_pose"] = json_copy(
                self.estimator(LegalObservation.from_envelope(value))
            )
            observation = LegalObservation.from_envelope(value)
        if self.logger:
            self.logger(observation.to_envelope())
        self._ids.add(observation.observation_id)
        self.current = LegalObservation.from_envelope(observation.to_envelope())
        return observation

    def reset(self) -> LegalObservation:
        if self._started:
            raise ValueError("Create a new adapter/episode for reset")
        self._started = True
        try:
            return self._accept(self.source.reset())
        except Exception:
            self._failed = True
            raise

    def step(self, action: Any, *, source_observation_id: str | None = None) -> LegalObservation:
        if not self.current or self._failed:
            raise ValueError("Reset required or source failed; restart episode")
        if (
            source_observation_id is not None
            and source_observation_id != self.current.observation_id
        ):
            raise ValueError("Stale action observation")
        values = json_copy(action)
        vector(values, len(self.bounds))
        for value, (low, high) in zip(values, self.bounds):
            number(value, low, high)
        try:
            return self._accept(self.source.step(self.codec(values)))
        except Exception:
            self._failed = True
            raise

    def score_out_of_band(self) -> Mapping[str, Any]:
        raise RuntimeError("Scoring belongs to a separate evaluator")
