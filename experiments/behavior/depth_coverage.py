"""Point visibility diagnostic. Never a swept-volume or motion authorization.

Transforms map optical camera coordinates into the points' reference frame;
depth is optical-axis z in metres. Even a supported sample is not proof that
the surrounding volume is free or that a robot collision proxy is complete.
"""

import numpy as np


def classify_depth_support(points, cameras, *, margin=0.02):
    """Count diagnostic support using conservative 3x3 depth neighborhoods.

    Each camera is (reference_from_optical, intrinsic_matrix, depth_image).
    Coverage is a union across cameras. Cameras must describe the same frozen
    observation; provenance/calibration validation belongs to the caller.
    """
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("Expected finite Nx3 points")
    if not np.isfinite(margin) or margin < 0:
        raise ValueError("Expected finite nonnegative depth margin")
    in_view = np.zeros(len(points), dtype=bool)
    valid = in_view.copy()
    depth_beyond = in_view.copy()
    for transform, intrinsic, depth in cameras:
        transform = np.asarray(transform, dtype=float)
        intrinsic = np.asarray(intrinsic, dtype=float)
        depth = np.asarray(depth, dtype=float)
        if (transform.shape != (4, 4) or not np.isfinite(transform).all()
                or not np.allclose(transform[3], [0, 0, 0, 1])
                or not np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3))
                or not np.isclose(np.linalg.det(transform[:3, :3]), 1)):
            raise ValueError("Expected rigid reference_from_optical transform")
        if (intrinsic.shape != (3, 3) or not np.isfinite(intrinsic).all()
                or intrinsic[0, 0] <= 0 or intrinsic[1, 1] <= 0
                or not np.allclose(intrinsic[2], [0, 0, 1])):
            raise ValueError("Expected calibrated intrinsic matrix")
        if depth.ndim != 2 or min(depth.shape) < 3:
            raise ValueError("Expected depth image at least 3x3")
        optical = (points - transform[:3, 3]) @ transform[:3, :3]
        z = optical[:, 2]
        projected = optical @ intrinsic.T
        xy = projected[:, :2] / np.where(z > 1e-6, z, 1)[:, None]
        h, w = depth.shape
        visible = ((z > 1e-6) & (xy[:, 0] >= 1) & (xy[:, 0] < w - 1)
                   & (xy[:, 1] >= 1) & (xy[:, 1] < h - 1))
        in_view |= visible
        ids = np.flatnonzero(visible)
        if not len(ids):
            continue
        pixels = np.floor(xy[ids]).astype(int)
        patches = np.stack([depth[pixels[:, 1] + dy, pixels[:, 0] + dx]
                            for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
        usable = np.all(np.isfinite(patches) & (patches > 0), axis=0)
        valid[ids[usable]] = True
        supported = usable & (np.min(patches, axis=0) > z[ids] + margin)
        depth_beyond[ids[supported]] = True
    return {"samples": len(points), "outside_all_views": int((~in_view).sum()),
            "in_view_without_valid_depth": int((in_view & ~valid).sum()),
            "valid_depth_without_beyond_support": int((valid & ~depth_beyond).sum()),
            "depth_beyond_sample": int(depth_beyond.sum())}
