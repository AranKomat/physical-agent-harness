"""Bounded head-only fixed-reference depth registration, shadow output only."""

import numpy as np

from physical_harness.integrations.sensors.behavior import LegalObservation
from physical_harness.perception.localization import LocalizationLost, RGBDOdometry


def point_to_plane(previous_rgb, previous_depth, rgb, depth, calibration):
    return _register_clouds([_prepare_cloud(values, calibration)
                             for values in (previous_depth, depth)])


def _prepare_cloud(values, calibration):
    import open3d as o3d

    intr = o3d.camera.PinholeCameraIntrinsic(
        (calibration["width"] + 1) // 2, (calibration["height"] + 1) // 2,
        *(calibration[k] / 2 for k in ("fx", "fy", "cx", "cy")))
    image = o3d.geometry.Image(np.ascontiguousarray(values[::2, ::2], dtype=np.float32))
    cloud = o3d.geometry.PointCloud.create_from_depth_image(
        image, intr, depth_scale=1., depth_trunc=10., stride=1).voxel_down_sample(.01)
    if len(cloud.points) < 100:
        raise LocalizationLost("Insufficient head depth for fixed-reference registration")
    cloud.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=.04, max_nn=30))
    return cloud


def _register_clouds(clouds):
    import open3d as o3d

    reg = o3d.pipelines.registration
    result = reg.registration_icp(*clouds, .05, np.eye(4), reg.TransformationEstimationPointToPlane(),
                                  reg.ICPConvergenceCriteria(max_iteration=50))
    info = reg.get_information_matrix_from_point_clouds(*clouds, .05, result.transformation)
    # These checks reject poor fits, but do not establish world-motion observability.
    success = bool(result.fitness >= .75 and result.inlier_rmse <= .015)
    return success, result.transformation, info


class CachedPointToPlane:
    """Opt-in one-frame preparation cache, never a cached pose or acceptance decision."""

    def __init__(self):
        self._depth = self._calibration = self._cloud = None

    def __call__(self, previous_rgb, previous_depth, rgb, depth, calibration):
        key = tuple(calibration[k] for k in ('width', 'height', 'fx', 'fy', 'cx', 'cy'))
        previous = self._cloud if (
            self._depth is not None and key == self._calibration
            and previous_depth.dtype == self._depth.dtype
            and np.array_equal(previous_depth, self._depth)
        ) else _prepare_cloud(previous_depth, calibration)
        current = _prepare_cloud(depth, calibration)
        result = _register_clouds([previous, current])
        self._depth, self._calibration, self._cloud = depth.copy(), key, current
        return result


class HeadDepthShadow:
    """No robot pose or simulator access. Outputs camera motion, not base authority."""

    def __init__(self, store):
        self.store, self.refs = store, {}
        self.last_at = None
        self.lost = False
        self.tracker = RGBDOdometry(lambda ref: self.store.read(self.refs[ref]),
                                   motion_estimator=point_to_plane, reference_mode="first",
                                   max_translation_m=.05, max_rotation_deg=5)

    def update(self, observation, calibration):
        if self.lost:
            raise LocalizationLost("Head shadow lost; create a new episode explicitly")
        try:
            if self.last_at is not None and not 0 < observation.observed_at - self.last_at <= 2:
                raise LocalizationLost("Current head capture wall-time gap exceeded two seconds")
            k = calibration["head"]
            if (k["stamp"] != observation.stamp.model_dump()
                    or k["observed_at"] != observation.observed_at
                    or k["rgb_evidence_id"] != observation.rgb["head"].id
                    or k["depth_evidence_id"] != observation.depth["head"].id):
                raise ValueError("Head calibration/evidence boundary mismatch")
            rgb, depth = observation.rgb["head"], observation.depth["head"]
            self.refs = {rgb.id: rgb, depth.id: depth}
            matrix = np.asarray(k["intrinsic_matrix"])
            height, width = k["image_shape"]
            legal = LegalObservation.from_envelope({
                "schema_version": 1,
                "episode_id": f"{observation.stamp.session}:{observation.stamp.epoch}",
                "observation_id": f"frame-{observation.stamp.sequence}",
                "sim_time": observation.stamp.sequence / 30,
                "rgb_refs": {"head": rgb.id}, "depth_refs": {"head": depth.id},
                "proprioception": {"joint_positions": list(observation.proprio)},
                "camera_frames": {"head": "head_optical"},
                "camera_intrinsics": {"head": {"width": width, "height": height,
                    "fx": float(matrix[0, 0]), "fy": float(matrix[1, 1]),
                    "cx": float(matrix[0, 2]), "cy": float(matrix[1, 2]), "depth_scale_m": 1.}},
            })
            result = self.tracker(legal)
            self.last_at = observation.observed_at
            return {"scope": "shadow_camera_motion_not_base_or_clearance_authority", **result}
        except Exception:
            self.lost = True
            raise
