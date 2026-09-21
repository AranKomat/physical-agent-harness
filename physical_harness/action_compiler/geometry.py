"""Local sensor geometry, not a complete scene reconstruction or collision map.

NumPy is needed only for these routines. Invalid depth is excluded explicitly
missing/occluded geometry is never extrapolated into free space.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .types import Basis, Pose, ids, integer, number, text, unit, vector


@dataclass(frozen=True)
class Intrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    depth_scale_m: float
    depth_convention: str  # optical_z or ray_range; must be explicit in native port

    def __post_init__(self):
        integer(self.width, low=1, high=10000)
        integer(self.height, low=1, high=10000)
        number(self.fx, low=.000001)
        number(self.fy, low=.000001)
        number(self.cx, low=0, high=self.width-1)
        number(self.cy, low=0, high=self.height-1)
        number(self.depth_scale_m, low=.000000001, high=100)
        if self.depth_convention not in {"optical_z", "ray_range"}:
            raise ValueError("Depth convention must be declared")


@dataclass(frozen=True)
class ObjectCloud:
    basis: Basis
    entity: str
    part: str
    points: tuple[tuple[float, float, float], ...]
    evidence_ids: tuple[str, ...]
    semantic_confidence: float
    source_camera: str
    camera_origin: tuple[float, float, float]
    valid_fraction: float
    # This records the observation support, not complete-object extent or free space.

    def __post_init__(self):
        if not isinstance(self.basis, Basis):
            raise ValueError("Evidence basis required")
        for s in (self.entity, self.part, self.source_camera):
            text(s)
        if type(self.points) is not tuple or not 3 <= len(self.points) <= 50000:
            raise ValueError("Bounded nonempty point cloud required")
        for p in self.points:
            vector(p, 3, "point")
        vector(self.camera_origin, 3)
        ids(self.evidence_ids, empty=False)
        number(self.semantic_confidence, low=0, high=1)
        number(self.valid_fraction, low=0, high=1)

    @property
    def centroid(self):
        return tuple(float(v) for v in np.mean(np.asarray(self.points), axis=0))


@dataclass(frozen=True)
class Surface:
    cloud: ObjectCloud
    point: tuple[float, float, float]
    outward_normal: tuple[float, float, float]
    residual_p95_m: float
    support_radius_m: float

    def __post_init__(self):
        if not isinstance(self.cloud, ObjectCloud):
            raise ValueError("Observed cloud required")
        vector(self.point, 3)
        unit(self.outward_normal)
        number(self.residual_p95_m, low=0)
        number(self.support_radius_m, low=0)


def deproject_masked_depth(*, basis: Basis, depth, mask, intrinsics: Intrinsics,
                          camera_to_frame: Pose, entity: str, part: str,
                          source_camera: str, evidence_ids: tuple[str, ...],
                          semantic_confidence: float, min_points: int = 16,
                          max_points: int = 4096, max_depth_m: float = 10,
                          minimum_valid_fraction: float = .5) -> ObjectCloud:
    """Use an RGB-derived mask aligned to this exact depth capture.

    The mask must come from legal RGB/RGB-D processing, not simulator segmentation.
    That provenance is enforced by the native evidence adapter, not by inspecting
    numeric mask values. Depth and masks are copied
    caller arrays are never edited.
    """
    if not isinstance(basis, Basis) or not isinstance(intrinsics, Intrinsics):
        raise ValueError("Typed basis/calibration required")
    if camera_to_frame.frame != basis.frame:
        raise ValueError("Camera transform is in a different frame")
    integer(min_points, low=3, high=50000)
    integer(max_points, low=min_points, high=50000)
    number(max_depth_m, low=.001, high=100)
    number(minimum_valid_fraction, low=0, high=1)
    d = np.array(depth, copy=True)
    m = np.array(mask, copy=True)
    shape = (intrinsics.height, intrinsics.width)
    if d.shape != shape or m.shape != shape or d.dtype.kind not in "uif":
        raise ValueError("Aligned numeric depth and mask dimensions required")
    if m.dtype != np.bool_:
        raise ValueError("Mask must be boolean, not arbitrary labels/probabilities")
    support = int(m.sum())
    if support < min_points:
        raise ValueError("Insufficient semantic mask support")
    d = d.astype(np.float64)*intrinsics.depth_scale_m
    valid = m & np.isfinite(d) & (d > 0) & (d <= max_depth_m)
    count = int(valid.sum())
    fraction = count/support
    if count < min_points or fraction < minimum_valid_fraction:
        raise ValueError("Insufficient valid observed depth")
    v, u = np.nonzero(valid)
    # Deterministic spatially dispersed sampling; never change original evidence.
    indices = np.linspace(0, len(u)-1, min(len(u), max_points), dtype=np.int64)
    u, v = u[indices], v[indices]
    rays = np.column_stack(((u-intrinsics.cx)/intrinsics.fx,
                            (v-intrinsics.cy)/intrinsics.fy, np.ones(len(u))))
    if intrinsics.depth_convention == "ray_range":
        rays /= np.linalg.norm(rays, axis=1, keepdims=True)
    camera_points = rays*d[v, u, None]
    transform = np.asarray(camera_to_frame.matrix).reshape(4, 4)
    points = camera_points @ transform[:3, :3].T + transform[:3, 3]
    return ObjectCloud(basis, entity, part,
                       tuple(tuple(float(x) for x in p) for p in points), evidence_ids,
                       semantic_confidence, source_camera, camera_to_frame.xyz, fraction)


def fit_surface(cloud: ObjectCloud, *, max_residual_m: float = .003,
                minimum_span_m: float = .002) -> Surface:
    """PCA plane with explicit support/error rejection and camera-facing normal.

    This is a local planar patch estimator. It does not infer that a patch is a
    button or that the object can tolerate contact. Non-planar/degenerate patches
    are rejected, not used as press targets.
    """
    number(max_residual_m, low=.0000001)
    number(minimum_span_m, low=.0000001)
    points = np.asarray(cloud.points)
    center = np.median(points, axis=0)
    centered = points-center
    _, singular, axes = np.linalg.svd(centered, full_matrices=False)
    if singular[1]/np.sqrt(len(points)) < minimum_span_m:
        raise ValueError("Surface support is collinear or too small")
    normal = axes[-1]
    ray_to_camera = np.asarray(cloud.camera_origin)-center
    if abs(float(np.dot(normal, ray_to_camera))) < 1e-8:
        raise ValueError("Surface normal sign cannot be established")
    if np.dot(normal, ray_to_camera) < 0:
        normal = -normal
    residual = float(np.quantile(np.abs(centered @ normal), .95))
    if residual > max_residual_m:
        raise ValueError("Patch is not sufficiently planar for this candidate generator")
    radius = float(np.quantile(np.linalg.norm(centered, axis=1), .5))
    return Surface(cloud, tuple(float(x) for x in center), tuple(float(x) for x in normal),
                   residual, radius)


def pose_from_approach(frame: str, point: tuple, approach: tuple) -> Pose:
    """Orient +Z along approach; a deterministic yaw choice is only a proposal."""
    z = np.asarray(unit(approach))
    reference = np.eye(3)[int(np.argmin(np.abs(z)))]
    x = np.cross(reference, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    result = np.eye(4)
    result[:3, :3] = np.column_stack((x, y, z))
    result[:3, 3] = vector(point, 3)
    return Pose(frame, tuple(float(v) for v in result.ravel()))


def compose_tcp(grasp: Pose, grasp_to_tcp: Pose) -> Pose:
    """T_frame_tcp = T_frame_grasp @ T_grasp_tcp (NOT the inverse)."""
    if grasp_to_tcp.frame != "grasp":
        raise ValueError("Explicit T_grasp_tcp calibration required")
    result = np.asarray(grasp.matrix).reshape(4, 4) @ np.asarray(grasp_to_tcp.matrix).reshape(4, 4)
    return Pose(grasp.frame, tuple(float(v) for v in result.ravel()))


def offset_pose(pose: Pose, direction: tuple, distance: float) -> Pose:
    return pose.shifted(direction, distance)
