"""Conservative current-image usability checks for learned visual consumers."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class ImageQualityThresholds:
    minimum_p95_luminance: float = 16.0
    maximum_near_black_fraction: float = 0.95
    maximum_near_white_fraction: float = 0.98
    minimum_p95_p05_range: float = 8.0


def assess_rgb_image(
    rgb: np.ndarray,
    thresholds: ImageQualityThresholds = ImageQualityThresholds(),
) -> dict:
    """Return a fail-closed, model-independent image usability assessment."""
    value = np.asarray(rgb)
    if value.ndim != 3 or value.shape[2] != 3 or value.size == 0:
        raise ValueError("RGB image must have shape (height, width, 3)")
    if value.dtype.kind not in "uif" or not np.isfinite(value).all():
        raise ValueError("RGB image must contain finite numeric values")
    if float(value.min()) < 0 or float(value.max()) > 255:
        raise ValueError("RGB image values must be in [0, 255]")
    rgb_float = value.astype(np.float32, copy=False)
    luminance = (
        0.2126 * rgb_float[..., 0]
        + 0.7152 * rgb_float[..., 1]
        + 0.0722 * rgb_float[..., 2]
    )
    p05, p95 = np.percentile(luminance, (5, 95))
    metrics = {
        "mean_luminance_0_255": float(luminance.mean()),
        "median_luminance_0_255": float(np.median(luminance)),
        "p05_luminance_0_255": float(p05),
        "p95_luminance_0_255": float(p95),
        "p95_p05_range_0_255": float(p95 - p05),
        "near_black_fraction": float((luminance <= 8).mean()),
        "near_white_fraction": float((luminance >= 247).mean()),
    }
    reasons = []
    if metrics["p95_luminance_0_255"] < thresholds.minimum_p95_luminance:
        reasons.append("insufficient_brightness")
    if metrics["near_black_fraction"] > thresholds.maximum_near_black_fraction:
        reasons.append("near_black_frame")
    if metrics["near_white_fraction"] > thresholds.maximum_near_white_fraction:
        reasons.append("near_white_frame")
    if metrics["p95_p05_range_0_255"] < thresholds.minimum_p95_p05_range:
        reasons.append("insufficient_dynamic_range")
    return {
        "usable": not reasons,
        "reasons": reasons,
        "metrics": metrics,
        "thresholds": asdict(thresholds),
    }
