"""Exact image annotations for selecting action IDs; annotations are not evidence of safety."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw

from .compiler import Catalog
from .geometry import Intrinsics
from .types import Basis, Pose, integer


def annotate_candidates(image_bytes: bytes, *, basis: Basis, catalog: Catalog,
                        intrinsics: Intrinsics, camera_to_frame: Pose,
                        max_candidates: int = 8) -> tuple[bytes, dict]:
    """Return PNG + marker->opaque-ID table, tied to the original observation.

    Green/red markers mean eligible/blocked according to the recorded REVIEW,
    not physical validation. The caller stores this derived overlay in the
    existing EvidenceStore alongside its immutable original RGB reference.
    """
    catalog.basis.require_same(basis)
    integer(max_candidates, low=1, high=32)
    if camera_to_frame.frame != basis.frame:
        raise ValueError("Overlay camera frame mismatch")
    with Image.open(io.BytesIO(image_bytes)) as src:
        if src.size != (intrinsics.width, intrinsics.height):
            raise ValueError("Overlay image/calibration dimensions disagree")
        src.load()
        image = src.convert('RGB')
    frame_to_camera = np.linalg.inv(np.asarray(camera_to_frame.matrix).reshape(4, 4))
    draw = ImageDraw.Draw(image)
    markers = []
    for action in catalog.actions:
        pose = action.program.proposal.parameters.pose
        if pose is None:
            continue
        xyz = frame_to_camera @ np.array([*pose.xyz, 1.])
        if xyz[2] <= .0001:
            continue
        u = intrinsics.fx*xyz[0]/xyz[2]+intrinsics.cx
        v = intrinsics.fy*xyz[1]/xyz[2]+intrinsics.cy
        if not 0 <= u < intrinsics.width or not 0 <= v < intrinsics.height:
            continue
        label = str(len(markers)+1)
        color = (20, 220, 110) if action.eligible else (240, 100, 80)
        draw.ellipse((u-4, v-4, u+4, v+4), outline=color, width=2)
        draw.text((min(u+5, image.width-12), max(0, min(v, image.height-12))), label, fill=color)
        markers.append({"marker": label, "action_id": action.id, "pixel_uv": [float(u), float(v)],
                        "intent": action.program.proposal.intent.verb.value,
                        "eligible": action.eligible})
        if len(markers) == max_candidates:
            break
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue(), {"catalog_id": catalog.id, "source_observation": basis.observation_id,
                           "source_evidence_ids": list(basis.evidence_ids), "markers": markers,
                           "note": "Projected TCP positions, not full grasp/trajectory or safety visualization"}
