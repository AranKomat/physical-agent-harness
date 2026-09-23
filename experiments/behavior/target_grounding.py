"""Pinned box detection; segmentation is delegated to SAM, never motion authority."""

import argparse
import hashlib
import io
import json
import time
from pathlib import Path

import numpy as np

from experiments.behavior.contracts import Observation
from experiments.behavior.grounding_manifest import (
    MODEL,
    REVISION,
    ROBOT_FILES,
    validate_detector_identity,
    verify_files,
)
from experiments.behavior.observations import EvidenceStore

PROMPT = "a radio."
TARGET_CANDIDATE_LIMIT = 4
DISTRACTOR_LIMIT = 4


class RobotSelfCheck:
    """Robot-only FK, not simulator/world poses or a collision certificate."""

    def __init__(self, assets):
        import yaml
        from scipy.spatial.transform import Rotation
        from yourdfpy import URDF

        expected = ROBOT_FILES
        for name, digest in expected.items():
            if hashlib.sha256((assets / name).read_bytes()).hexdigest() != digest:
                raise ValueError("Unverified robot-only geometry")
        self.model = URDF.load(str(assets / "native_r1pro_processed.urdf"),
                               load_meshes=False, load_collision_meshes=False)
        self.config = yaml.safe_load((assets / "native_r1pro_source_cfg.yaml").read_text())
        self.rotation = Rotation
        self.identity = {"assets_sha256": expected, "eef_ambiguity_radius_m": .18,
                         "scope": "reject_near_hand_ambiguity_not_full_robot_segmentation"}

    def offset(self, entry):
        result = np.eye(4)
        result[:3, :3] = self.rotation.from_quat(entry["orientation"]).as_matrix()
        result[:3, 3] = entry["position"]
        return result

    def transform(self, obs):
        p = np.asarray(obs.proprio)
        cfg = {f"torso_joint{i+1}": q for i, q in enumerate(p[53:57])}
        for side, start, grip in (("left", 3, 24), ("right", 28, 49)):
            cfg.update({f"{side}_arm_joint{i+1}": q for i, q in enumerate(p[start:start+7])})
            cfg.update({f"{side}_gripper_finger_joint{i+1}": q for i, q in enumerate(p[grip:grip+2])})
        self.model.update_cfg(cfg)
        for side, start in (("left", 17), ("right", 42)):
            eef = next(e for e in self.config["eef_vis_links"] if e["link"] == side+"_eef_link")
            pose = self.model.get_transform(eef["parent_link"], "base_link") @ self.offset(eef["offset"])
            if np.linalg.norm(pose[:3, 3]-p[start:start+3]) > .01:
                raise ValueError("Robot FK/proprio convention mismatch")
        camera = next(c for c in self.config["camera_links"] if c["link"] == "zed_link")
        return (self.model.get_transform("zed_link", "base_link") @ self.offset(camera["offset"])
                @ np.diag([1, -1, -1, 1]))

    def annotate(self, candidate, obs, transform):
        point = (transform @ np.r_[candidate["surface_median_camera_m"], 1.])[:3]
        distances = [float(np.linalg.norm(point-np.asarray(obs.proprio)[start:start+3])) for start in (17, 42)]
        candidate.update(surface_median_base_m=point.tolist(), eef_distances_m=distances)
        if min(distances) < .18:
            candidate["rejected"] = "near_end_effector_identity_ambiguous_not_a_verified_target"


def validate_packet(packet):
    obs = Observation.model_validate(packet["observation"])
    calibration = packet["calibration"]["head"]
    rgb, depth = np.asarray(packet["rgb"]), np.asarray(packet["depth"])
    if (calibration["stamp"] != obs.stamp.model_dump()
            or calibration["observed_at"] != obs.observed_at
            or any(calibration[k+"_evidence_id"] != getattr(obs, k)["head"].id for k in ("rgb", "depth"))):
        raise ValueError("Grounding calibration is detached from source evidence")
    if (rgb.dtype != np.uint8 or rgb.shape != (*depth.shape, 3)
            or list(depth.shape) != calibration["image_shape"] or depth.shape != (720, 720)
            or depth.dtype.kind not in "fiu"):
        raise ValueError("Grounding requires aligned native head RGB/depth")
    k = np.asarray(calibration["intrinsic_matrix"], dtype=float)
    if (k.shape != (3, 3) or not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0
            or not np.allclose(k[2], [0, 0, 1])):
        raise ValueError("Invalid grounding intrinsics")
    return obs, k, rgb, depth


def _read_bound_evidence(store, evidence):
    """Decode the same bytes whose content and stamped identity were verified."""
    from PIL import Image

    root = store.root.resolve()
    path = (root / evidence.uri).resolve()
    suffix = ".png" if evidence.source == "rgb" else ".npy"
    if (evidence.uri != path.name or path.parent != root or path.suffix != suffix):
        raise ValueError("Grounding evidence URI escapes store or has wrong modality suffix")
    content = path.read_bytes()
    content_hash = hashlib.sha256(content).hexdigest()
    if content_hash != path.stem:
        raise ValueError("Grounding evidence content hash mismatch")
    identity = hashlib.sha256(
        f"{evidence.stamp.model_dump_json()}:{evidence.observed_at}:"
        f"{evidence.source}:{content_hash}".encode()
    ).hexdigest()
    if identity != evidence.id:
        raise ValueError("Grounding evidence identity hash mismatch")
    if evidence.source == "rgb":
        with Image.open(io.BytesIO(content)) as image:
            return np.asarray(image.convert("RGB"))
    return np.load(io.BytesIO(content), allow_pickle=False)


def read_grounding_packet(row, store):
    """Shared online/offline ingress; validate before RPC or local inference."""
    obs = Observation.model_validate(row["observation"])
    packet = {**row, "rgb": _read_bound_evidence(store, obs.rgb["head"]),
              "depth": _read_bound_evidence(store, obs.depth["head"])}
    validate_packet(packet)
    return packet


class GroundingBackend:
    def __init__(self, checkpoint, prompt=PROMPT, robot_assets=None):
        import torch
        import transformers
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        checkpoint = Path(checkpoint).resolve(strict=True)
        if checkpoint.name != REVISION or not (checkpoint / "model.safetensors").is_file():
            raise ValueError("Expected pinned local safetensors snapshot")
        verified_files = verify_files(checkpoint)
        self.torch = torch
        if not isinstance(prompt, str) or not 1 <= len(prompt) <= 256 or not prompt.endswith("."):
            raise ValueError("Expected bounded grounding text ending in a period")
        self.prompt = prompt
        self.self_check = RobotSelfCheck(robot_assets) if robot_assets else None
        start = time.monotonic()
        self.processor = AutoProcessor.from_pretrained(checkpoint, local_files_only=True, trust_remote_code=False)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(
            checkpoint, local_files_only=True, trust_remote_code=False, use_safetensors=True).to("cuda").eval()
        self.identity = {"model": MODEL, "revision": REVISION, "license": "apache-2.0",
                         "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         "transformers": transformers.__version__, "torch": torch.__version__,
                         "prompt": prompt, "box_threshold": .4, "text_threshold": .3,
                         "load_s": time.monotonic()-start,
                         "weights_sha256": verified_files["model.safetensors"],
                         "files_sha256": verified_files}
        self.identity["geometry_backend"] = "none_detection_only"
        self.identity["robot_self_check"] = ({"assets_sha256": ROBOT_FILES,
            "scope": "robot_fk_validation_only_no_target_self_filter"} if self.self_check else None)

    def reset(self, stamp):
        return {"stamp": stamp}

    def infer(self, packet):
        from PIL import Image

        obs, _, rgb, _ = validate_packet(packet)
        started = time.monotonic()
        if self.self_check:
            self.self_check.transform(obs)
        inputs = self.processor(images=Image.fromarray(rgb), text=self.prompt, return_tensors="pt").to("cuda")
        with self.torch.inference_mode():
            outputs = self.model(**inputs)
        detections = self.processor.post_process_grounded_object_detection(
            outputs, inputs.input_ids, box_threshold=.4, text_threshold=.3, target_sizes=[rgb.shape[:2]])[0]
        candidates, distractors = [], []
        omitted_targets, omitted_distractors = 0, 0
        labels = detections.get("text_labels", detections.get("labels"))
        for index in np.argsort(-detections["scores"].detach().cpu().numpy(), kind="stable"):
            label = labels[index]
            target = label in ("radio", "a radio")
            if target and len(candidates) >= TARGET_CANDIDATE_LIMIT:
                omitted_targets += 1
                continue
            if not target and len(distractors) >= DISTRACTOR_LIMIT:
                omitted_distractors += 1
                continue
            box = detections["boxes"][index].detach().cpu().numpy().tolist()
            row = {"box_xyxy": box, "score_uncalibrated": float(detections["scores"][index]),
                   "label": label}
            if not target:
                distractors.append(row)
                continue
            row.update(geometry_status="unqualified_requires_sam_depth_association",
                       identity_verified=False)
            candidates.append(row)
        return {"stamp": obs.stamp.model_dump(), "rgb_evidence_id": obs.rgb["head"].id,
                "depth_evidence_id": obs.depth["head"].id, "identity": self.identity,
                "candidates": candidates, "distractors": distractors, "wall_s": time.monotonic()-started,
                "target_candidate_limit": TARGET_CANDIDATE_LIMIT,
                "distractor_limit": DISTRACTOR_LIMIT,
                "omitted_target_count": omitted_targets,
                "omitted_distractor_count": omitted_distractors,
                "scope": "object_grounding_shadow_no_motion_authority", "motion_authorized": False,
                "semantic_accuracy_qualified": False}


def save_result(result, output):
    """Keep derived RGB masks distinct from original RGB/depth sensor evidence."""
    output.mkdir(parents=True, exist_ok=True)
    for candidate in result["candidates"]:
        if "mask" not in candidate:
            continue
        data = io.BytesIO()
        np.save(data, candidate.pop("mask"), allow_pickle=False)
        content = data.getvalue()
        digest = hashlib.sha256(content).hexdigest()
        path = output / (digest + ".npy")
        if not path.exists():
            path.write_bytes(content)
        candidate["derived_mask"] = {"uri": path.name, "sha256": digest,
                                     "rgb_evidence_id": result["rgb_evidence_id"], "stamp": result["stamp"]}
    return result


def ground_capture(row, store, transport, output):
    obs = Observation.model_validate(row["observation"])
    result = transport.infer(read_grounding_packet(row, store))
    if (result.get("stamp") != obs.stamp.model_dump()
            or result.get("rgb_evidence_id") != obs.rgb["head"].id
            or result.get("depth_evidence_id") != obs.depth["head"].id
            or result.get("motion_authorized") is not False):
        raise ValueError("Grounding result has stale evidence or invalid authority")
    validate_detector_identity(result.get("identity"))
    result["delivery"] = "synchronous_online_shadow_before_next_policy_chunk"
    result["completed_wall"] = time.monotonic()
    return save_result(result, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--runs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--serve-port", type=int)
    parser.add_argument("--prompt", default=PROMPT)
    parser.add_argument("--robot-assets", type=Path)
    args = parser.parse_args()
    backend = GroundingBackend(args.checkpoint, args.prompt, args.robot_assets)
    if args.serve_port:
        from experiments.behavior.policy_server import PolicyFacade
        PolicyFacade(backend).serve(transport="http", host="127.0.0.1", port=args.serve_port,
                                   parent_watch=False, session_sweep_s=None)
        return
    if not args.runs or not args.output:
        parser.error("Replay requires --runs and --output")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "retained_frame_grounding_not_online_qualification", "model": backend.identity,
              "motion_authorized": False, "gpt_calls": 0, "frames": []}
    for run in args.runs:
        receipt = json.loads((run / "hybrid_short.json").read_text())
        store = EvidenceStore(run / "evidence")
        for row in receipt["captures"]:
            result = backend.infer(read_grounding_packet(row, store))
            result["run"] = run.parent.name
            report["frames"].append(save_result(result, args.output / "masks"))
            (args.output / "grounding.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"frames": len(report["frames"]), "with_candidates":
                      sum(bool(r["candidates"]) for r in report["frames"])}))


if __name__ == "__main__":
    main()
