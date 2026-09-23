"""Opt-in SAM 3 / 3.1 causal-prefix tracking experiment, not a live replacement.

Uses the pinned public predictor API. Only the last frame of a bounded prefix is
published: processing a full retained video must not leak future frames into an
earlier simulated decision. IDs remain camera/session-local, not persistent IDs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from physical_harness.core.actions import (
    Basis,
    encode,
    ids,
    integer,
    number,
    plain,
    strict_loads,
    text,
)
from physical_harness.core.tasks import basis_from_dict
from physical_harness.perception.visual import VisualAsset, VisualRole

SAM_SOURCE_PIN = "2345a4ad109ac29c569da749c91d84f10dc08c40"


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class PrefixFrame:
    basis: Basis
    image: VisualAsset
    path: Path


def validate_prefix(frames: tuple[PrefixFrame, ...], cutoff: Basis, *, max_frames=64,
                    max_total_bytes=128*1024*1024):
    from PIL import Image
    integer(max_frames, low=1, high=256)
    integer(max_total_bytes, low=1, high=512*1024*1024)
    if type(frames) is not tuple or not 1 <= len(frames) <= max_frames:
        raise ValueError("Bounded prefix required")
    ids(tuple(f.image.asset_id for f in frames))
    total = 0
    dimensions = None
    for i, f in enumerate(frames):
        if not isinstance(f, PrefixFrame) or not isinstance(f.basis, Basis) or not isinstance(f.image, VisualAsset):
            raise ValueError("Typed prefix capture required")
        if f.image.role != VisualRole.OBSERVATION or f.image.camera != frames[0].image.camera:
            raise PermissionError("One camera, observed images only")
        f.image.require_available(cutoff)
        f.basis.require_continuity(cutoff)
        if f.image.observed_at != f.basis.sim_time or f.image.episode != f.basis.episode:
            raise PermissionError("Image/capture binding mismatch")
        if i and f.basis.sim_time <= frames[i-1].basis.sim_time:
            raise ValueError("Strictly chronological prefix required")
        if f.path.is_symlink() or not f.path.is_file() or f.path.suffix.lower() not in {".jpg", ".jpeg"}:
            raise ValueError("Explicit local JPEG export required; no implicit PNG recoding")
        total += f.path.stat().st_size
        if total > max_total_bytes:
            raise ValueError("Prefix exceeds byte budget")
        if sha_file(f.path) != f.image.sha256:
            raise PermissionError("Image content hash mismatch")
        with Image.open(f.path) as image:
            if image.format != "JPEG" or image.mode != "RGB" or min(image.size) < 1 or max(image.size) > 4096:
                raise ValueError("Bounded RGB JPEG required")
            if dimensions is not None and dimensions != image.size:
                raise ValueError("Video geometry must be consistent within a prefix")
            dimensions = image.size
            image.verify()
    cutoff.require_same(frames[-1].basis)
    return dimensions


def load_predictor(config: dict, *, allow_inference=False, licenses_accepted=False):
    """Run only in a dedicated inference process with operator-controlled egress."""
    if allow_inference is not True or licenses_accepted is not True:
        raise PermissionError("Explicit inference and license approval required")
    required = {"version", "source", "source_revision", "checkpoint", "checkpoint_sha256",
                "bpe", "bpe_sha256", "use_fa3"}
    if set(config) != required or config["version"] not in {"sam3", "sam3.1"}:
        raise ValueError("Strict local SAM configuration required")
    if config["source_revision"] != SAM_SOURCE_PIN or type(config["use_fa3"]) is not bool:
        raise PermissionError("Unreviewed SAM source/configuration")
    source = Path(config["source"]).resolve(strict=True)
    if subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], timeout=5).decode().strip() != SAM_SOURCE_PIN:
        raise PermissionError("SAM source commit mismatch")
    if subprocess.run(["git", "-C", str(source), "diff", "--quiet", "HEAD"], timeout=5).returncode:
        raise PermissionError("SAM source has unreviewed changes")
    for name in ("checkpoint", "bpe"):
        path = Path(config[name])
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError("Explicit local asset required")
        if sha_file(path) != config[name+"_sha256"]:
            raise PermissionError("SAM asset hash mismatch")
    if "sam3" in sys.modules:
        raise RuntimeError("Load SAM only in a clean dedicated inference process")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, str(source))
    builder = importlib.import_module("sam3.model_builder")
    if source not in Path(builder.__file__).resolve().parents:
        raise PermissionError("Imported a different SAM package")
    # Both explicit paths suppress the public builder's implicit HF download path.
    # SAM 3.1 upstream tolerates missing state keys: capture/check native load logs
    # before qualification. This experimental loader does not certify the weights.
    return builder.build_sam3_predictor(
        checkpoint_path=config["checkpoint"], bpe_path=config["bpe"], version=config["version"],
        compile=False, warm_up=False, async_loading_frames=False, use_fa3=config["use_fa3"],
    )


def run_prefix(predictor, *, frames: tuple[PrefixFrame, ...], cutoff: Basis,
               seed_point: tuple[float, float], seed_evidence_id: str, deadline: float,
               clock=time.monotonic) -> dict:
    """Known-instance point prompt once; propagate geometry, not repeated category search.

    This bounded replay restarts sessions between prefixes; it does NOT claim a
    live streaming performance gain. Temporal disambiguation inside a prefix is
    allowed only because its result is published at the final cutoff.
    """
    import numpy as np
    width, height = validate_prefix(frames, cutoff)
    if type(seed_point) is not tuple or len(seed_point) != 2:
        raise ValueError("Normalized seed point required")
    for v in seed_point:
        number(v, low=0, high=1)
    text(seed_evidence_id)
    if seed_evidence_id not in frames[0].image.evidence_ids:
        raise PermissionError("Seed must be grounded at the prefix's first observation")
    if clock() >= deadline:
        raise TimeoutError("Prefix deadline")
    session = None
    last = None
    with tempfile.TemporaryDirectory(prefix="situated-sam-prefix-") as tmp:
        try:
            for i, frame in enumerate(frames):
                dst = Path(tmp)/f"{i:06d}.jpg"
                shutil.copyfile(frame.path, dst)
                if sha_file(dst) != frame.image.sha256:
                    raise PermissionError("Image changed during copy")
            response = predictor.handle_request({"type": "start_session", "resource_path": tmp})
            session = response["session_id"]
            text(session)
            predictor.handle_request({"type": "add_prompt", "session_id": session, "frame_index": 0,
                                      "points": [list(seed_point)], "point_labels": [1],
                                      "obj_id": 1, "rel_coordinates": True})
            # Use a positive prefix length even for one frame. A zero bound has
            # different endpoint semantics in upstream detector/tracker paths.
            for response in predictor.handle_stream_request({
                "type": "propagate_in_video", "session_id": session,
                "start_frame_index": 0, "propagation_direction": "forward",
                "max_frame_num_to_track": len(frames), "force_tracker_propagation": True,
            }):
                if clock() >= deadline:
                    raise TimeoutError("Late SAM result; supervised worker must bound hung calls")
                index = response.get("frame_index")
                if type(index) is not int or not 0 <= index < len(frames):
                    raise ValueError("Predictor returned an out-of-prefix frame")
                if index == len(frames)-1:
                    if last is not None:
                        raise ValueError("Duplicate final-frame result")
                    last = response["outputs"]
            if last is None:
                raise ValueError("Missing final prefix result")
            def array(v):
                if hasattr(v, "detach"):
                    v = v.detach().cpu().numpy()
                return np.asarray(v)
            object_ids = array(last["out_obj_ids"])
            masks = array(last["out_binary_masks"])
            # Public predictors can use empty arrays/lists when nothing is tracked.
            # Preserve absence; never fabricate an all-zero mask as a detected object.
            if object_ids.ndim == 1 and len(object_ids) == 0 and masks.size == 0:
                masks = np.empty((0, height, width), dtype=bool)
            if object_ids.ndim != 1 or len(object_ids) > 64 or masks.ndim != 3 or len(masks) != len(object_ids):
                raise ValueError("Unexpected SAM output shape")
            if masks.shape[1:] != (height, width):
                raise ValueError("Tracker mask geometry differs from the source image")
            if masks.dtype != np.bool_ or masks.size > 64*4096*4096:
                raise ValueError("Bounded binary masks required")
            if len(set(object_ids.tolist())) != len(object_ids):
                raise ValueError("Duplicate local tracker identity")
            objects = []
            for obj, mask in zip(object_ids, masks):
                if not isinstance(obj, (int, np.integer)) or isinstance(obj, (bool, np.bool_)) or obj < 0:
                    raise ValueError("Integer local tracker ID required")
                # Exact mask bytes are returned to the private caller, not model context.
                objects.append({"local_id": int(obj), "mask": mask.copy()})
            return {"session_id": session, "camera": frames[0].image.camera,
                    "basis": plain(cutoff), "seed_evidence_id": seed_evidence_id,
                    "source_assets": [f.image.asset_id for f in frames], "objects": objects,
                    "causal_publication": "tail_only", "persistent_entity_ids": False}
        finally:
            if session is not None:
                predictor.handle_request({"type": "close_session", "session_id": session})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-inference", action="store_true")
    parser.add_argument("--licenses-accepted", action="store_true")
    args = parser.parse_args()
    if not (args.allow_inference and args.licenses_accepted):
        parser.error("Explicit inference/license opt-ins required")
    raw = strict_loads(args.prefix.read_bytes(), max_bytes=256000)
    if set(raw) != {"frames", "cutoff", "seed_point", "seed_evidence_id", "max_wall_s"}:
        raise ValueError("Strict prefix manifest required")
    cutoff = basis_from_dict(raw["cutoff"])
    frames = []
    for f in raw["frames"]:
        asset = dict(f["image"])
        asset["role"] = VisualRole(asset["role"])
        asset["evidence_ids"] = tuple(asset["evidence_ids"])
        frames.append(PrefixFrame(basis_from_dict(f["basis"]), VisualAsset(**asset), Path(f["path"])))
    validate_prefix(tuple(frames), cutoff)
    number(raw["max_wall_s"], low=.001, high=3600)
    args.output.mkdir(parents=True, exist_ok=False)
    predictor = None
    try:
        predictor = load_predictor(strict_loads(args.config.read_bytes()), allow_inference=True, licenses_accepted=True)
        result = run_prefix(predictor, frames=tuple(frames), cutoff=cutoff,
                            seed_point=tuple(raw["seed_point"]), seed_evidence_id=raw["seed_evidence_id"],
                            deadline=time.monotonic()+raw["max_wall_s"])
        import numpy as np
        for item in result["objects"]:
            name = f'mask-{item["local_id"]}.npy'
            np.save(args.output/name, item.pop("mask"), allow_pickle=False)
            item.update(mask_file=name, mask_sha256=sha_file(args.output/name))
        (args.output/"result.json").write_bytes(encode(result))
    finally:
        if predictor is not None:
            predictor.shutdown()


if __name__ == "__main__":
    main()
