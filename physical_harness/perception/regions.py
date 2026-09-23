"""Coarse VLM boxes -> source-faithful crop/SAM seeds, not metric motion targets."""
from __future__ import annotations

import hashlib
import io
import math
from dataclasses import dataclass

from physical_harness.core.actions import Basis, digest, ids, number, text
from physical_harness.perception.contracts import FrameRef, validate_box


@dataclass(frozen=True)
class BoxSeed:
    sighting_id: str
    source: FrameRef
    box_xyxy: tuple[float, float, float, float]
    semantic_hypotheses: tuple[str, ...]

    def __post_init__(self):
        text(self.sighting_id)
        if not isinstance(self.source, FrameRef):
            raise ValueError("Source frame required")
        validate_box(self.box_xyxy)
        ids(self.semantic_hypotheses, limit=3)

    @property
    def id(self):
        return "seed:" + digest(self)[:24]

    def sam_prompt(self, *, session_id: str, source_frame_index: int) -> dict:
        """Only for a session which contains THIS original frame.

        Never apply an old box to a new camera capture. The session/frame binding
        adapter must verify the source bytes/index before forwarding this request.
        """
        from physical_harness.core.actions import integer
        integer(source_frame_index)
        text(session_id)
        x0, y0, x1, y1 = self.box_xyxy
        return {"type": "add_prompt", "session_id": session_id, "frame_index": source_frame_index,
                "bounding_boxes": [[x0, y0, x1-x0, y1-y0]], "bounding_box_labels": [1],
                "rel_coordinates": True}


def crop_source(source: FrameRef, box: tuple[float, float, float, float], data: bytes,
                *, available_wall: float, store) -> FrameRef:
    """Lossless derived PNG into an injected existing evidence-store writer.

    store(png_bytes, metadata) -> asset ID; no local filenames supplied by a model.
    The full original frame must remain retrievable for reinterpretation/context.
    """
    from PIL import Image
    source.verify_bytes(data)
    box = validate_box(box)
    number(available_wall, low=source.available_wall)
    with Image.open(io.BytesIO(data)) as im:
        if im.size != (source.width, source.height):
            raise ValueError("Image dimensions differ from evidence")
        scaled = []
        for coordinate, size in zip(box, (source.width, source.height) * 2):
            pixel = coordinate * size
            nearest = round(pixel)
            # Undo only division/multiplication roundoff at integer pixel edges.
            if abs(pixel - nearest) <= 2 * math.ulp(pixel):
                pixel = nearest
            scaled.append(pixel)
        pixels = (math.floor(scaled[0]), math.floor(scaled[1]),
                  math.ceil(scaled[2]), math.ceil(scaled[3]))
        crop = im.convert("RGB").crop(pixels)
        out = io.BytesIO()
        crop.save(out, format="PNG")
        raw = out.getvalue()
    identifier = store(raw, {"parent_id": source.asset_id, "parent_hash": source.content_sha256,
                             "pixel_box": pixels, "normalized_box": box, "kind": "source_crop"})
    return FrameRef(source.basis, identifier, hashlib.sha256(raw).hexdigest(), source.camera,
                    crop.width, crop.height, available_wall, source.asset_id, box)


def require_seed_target(seed: BoxSeed, frame: FrameRef, *, now: float):
    if seed.source != frame:
        raise PermissionError("A discovery box may seed ONLY its original source frame")
    frame.available(frame.basis, now)


def require_current_tracking(seed: BoxSeed, current: Basis, *, source_hash: str,
                             session_id: str, mask_basis: Basis, mask_evidence: str,
                             association_check):
    """Validate lineage before a trusted adapter considers current association.

    This returns metadata, not an IdentityLedger proof, XYZ or a motion approval.
    """
    text(session_id)
    text(mask_evidence)
    if source_hash != seed.source.content_sha256:
        raise PermissionError("Tracker seed image changed")
    current.require_same(mask_basis)
    if current.episode != seed.source.basis.episode:
        raise PermissionError("Foreign tracking episode")
    if association_check(seed, mask_basis, mask_evidence) is not True:
        raise PermissionError("Current mask cannot be uniquely associated with original sighting")
    return {"seed_id": seed.id, "sighting_id": seed.sighting_id, "session": session_id,
            "current_mask": mask_evidence, "current_basis": current.fingerprint,
            "semantic_hypotheses": seed.semantic_hypotheses, "motion_authority": False}
