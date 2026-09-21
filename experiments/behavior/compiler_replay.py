"""Read-only retained RGB-D replay, never a native controller or target detector.

Camera-local geometry is observed support, not free space or a complete object.
The compiler requires a Gripper even for INSPECT: its explicit placeholder below
is only a blocked contract probe, never an R1Pro calibration or qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

from physical_harness.action_compiler.compiler import ReviewEngine, compile_catalog
from physical_harness.action_compiler.geometry import (
    Intrinsics,
    deproject_masked_depth,
    fit_surface,
    pose_from_approach,
)
from physical_harness.action_compiler.primitives import TemplateConfig
from physical_harness.action_compiler.proposals import inspect_candidate, pose_candidate
from physical_harness.action_compiler.types import (
    Basis,
    Gripper,
    Intent,
    Pose,
    Verb,
    digest,
    plain,
)

from .contracts import Evidence, Stamp

CAMERAS = ("head", "left_wrist", "right_wrist")
MISSING_PREREQUISITES = (
    "qualified_actual_gripper_geometry_and_grasp_to_tcp",
    "camera_to_robot_or_world_extrinsics",
    "calibrated_up_direction",
    "semantic_contact_region_and_contact_tolerance",
    "robot_ik_and_full_swept_collision_review",
    "native_codec_stop_contact_and_grasp_monitors",
    "fresh_online_observation_and_execution_qualification",
)
DEPTH_CONTRACT = {
    "convention": "optical_z", "scale_m": 1.0,
    "source": "BehaviorObservationFilter.convert retains native depth_linear unchanged in meters; "
              "OmniGibson VisionSensor maps depth_linear to distance_to_image_plane",
    "qualification": "retained_sensor_contract_not_independent_metric_calibration",
}


def _read_evidence(raw: dict, root: Path, modality: str, stamp: Stamp, at: float):
    ref = Evidence.model_validate(raw)
    if ref.source != modality or ref.stamp != stamp or ref.observed_at != at:
        raise ValueError("Evidence stamp/time/modality mismatch")
    root = root.resolve()
    path = (root / ref.uri).resolve()
    suffix = ".png" if modality == "rgb" else ".npy"
    if path.parent != root or ref.uri != path.name or path.suffix != suffix:
        raise ValueError("Evidence path escapes store or has wrong modality suffix")
    content = path.read_bytes()
    content_hash = hashlib.sha256(content).hexdigest()
    if content_hash != path.stem:
        raise ValueError("Evidence content hash mismatch")
    identity = hashlib.sha256(
        f"{stamp.model_dump_json()}:{at}:{modality}:{content_hash}".encode()
    ).hexdigest()
    if identity != ref.id:
        raise ValueError("Evidence identity hash mismatch")
    if modality == "rgb":
        with Image.open(io.BytesIO(content)) as image:
            return np.asarray(image.convert("RGB"))
    return np.load(io.BytesIO(content), allow_pickle=False)


def read_capture(capture: dict, evidence_dir: Path, camera: str):
    """Validate a retained camera pair; return basis, intrinsics, depth, RGB.

    Identity transform means optical frame to itself, NOT a guessed camera pose.
    Recorded observed_at is monotonic, not Unix wall time; sim_time=0 is an
    unavailable-time sentinel needed by Basis, not a measured simulation time.
    Nothing in this module performs freshness authorization or dispatch.
    """
    if camera not in CAMERAS:
        raise ValueError("Unsupported retained camera")
    observation = capture["observation"]
    stamp = Stamp.model_validate(observation["stamp"])
    at = observation["observed_at"]
    if type(at) not in (int, float) or not np.isfinite(at) or at < 0:
        raise ValueError("Invalid recorded observation time")
    calibration = capture["calibration"][camera]
    rgb_ref, depth_ref = (observation[k][camera] for k in ("rgb", "depth"))
    if (calibration["source"] != "native_camera_intrinsics"
            or calibration["stamp"] != stamp.model_dump()
            or calibration["observed_at"] != at
            or calibration["rgb_evidence_id"] != rgb_ref["id"]
            or calibration["depth_evidence_id"] != depth_ref["id"]):
        raise ValueError("Calibration evidence binding mismatch")
    matrix = np.asarray(calibration["intrinsic_matrix"], dtype=float)
    if (matrix.shape != (3, 3) or not np.isfinite(matrix).all()
            or not np.allclose(matrix[2], [0, 0, 1])
            or matrix[0, 1] != 0 or matrix[1, 0] != 0):
        raise ValueError("Invalid or unsupported camera intrinsics")
    height, width = calibration["image_shape"]
    intrinsics = Intrinsics(width, height, float(matrix[0, 0]), float(matrix[1, 1]),
                            float(matrix[0, 2]), float(matrix[1, 2]), 1.0, "optical_z")
    rgb = _read_evidence(rgb_ref, evidence_dir, "rgb", stamp, at)
    depth = _read_evidence(depth_ref, evidence_dir, "depth", stamp, at)
    if (rgb.shape != (height, width, 3) or depth.shape != (height, width)
            or depth.dtype.kind not in "uif"):
        raise ValueError("Aligned RGB/depth/calibration shapes required")
    calibration_id = "calibration:" + digest(calibration)
    source = {"stamp": stamp.model_dump(), "observed_at": at,
              "rgb": rgb_ref, "depth": depth_ref, "calibration": calibration}
    capture_id = digest(source)
    frame = f"optical:{camera}:{capture_id[:20]}"
    basis = Basis(stamp.session, "retained:" + capture_id, digest(source), 0., at,
                  frame, frame, "depth:" + depth_ref["id"], stamp.epoch,
                  "UNQUALIFIED-retained-robot", calibration_id,
                  (rgb_ref["id"], depth_ref["id"], calibration_id), domain="behavior_sim")
    return basis, intrinsics, depth, rgb


def _annotation_mask(annotation, rgb_id, intrinsics):
    if (annotation["inspected"] is not True
            or annotation["method"] != "annotation_assisted_rectangle"
            or annotation["rgb_evidence_id"] != rgb_id):
        raise ValueError("Annotation requires inspected, evidence-bound RGB provenance")
    if (annotation["entity"] not in {"radio", "trash_bin", "observed_object"}
            or annotation["part"] != "visible_body_patch"
            or not isinstance(annotation["note"], str) or not annotation["note"].strip()):
        raise ValueError("Only described object-body patches, not semantic buttons, are allowed")
    box = annotation["box_xyxy"]
    if (not isinstance(box, list) or len(box) != 4
            or any(type(value) is not int for value in box)):
        raise ValueError("Integer xyxy annotation box required")
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= intrinsics.width and 0 <= y0 < y1 <= intrinsics.height):
        raise ValueError("Annotation box is empty or outside RGB")
    mask = np.zeros((intrinsics.height, intrinsics.width), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


def _cloud(basis, intrinsics, depth, mask, camera, entity, part):
    return deproject_masked_depth(
        basis=basis, intrinsics=intrinsics, depth=depth, mask=mask,
        camera_to_frame=Pose(basis.frame), entity=entity, part=part,
        source_camera=camera, evidence_ids=basis.evidence_ids,
        semantic_confidence=0., max_points=4096,
    )


def _geometry(cloud):
    points = np.asarray(cloud.points)
    return {"frame": cloud.basis.frame, "basis_fingerprint": cloud.basis.fingerprint,
            "entity": cloud.entity, "part": cloud.part,
            "point_count": len(points), "centroid_m": list(cloud.centroid),
            "bounds_m": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
            "valid_fraction": cloud.valid_fraction, "evidence_ids": list(cloud.evidence_ids),
            "points_m": points.tolist(), "complete_object": False, "free_space": False,
            "semantic_confidence": "unqualified_not_scored"}


def placeholder_gripper():
    """Type-contract constants only: deliberately NOT derived from robot assets."""
    return Gripper("UNQUALIFIED-contract-probe-placeholder", "not-a-robot-profile",
                   "NO-QUALIFIED-ASSET-DIGEST", ("placeholder_joint",), (.04,), (0.,),
                   (0.,), (.05,), Pose("grasp"), .1)


def replay_run(run_dir: Path, annotations: dict | None = None) -> dict:
    """Replay every captures row, including malformed/empty/absent-target rows.

    annotations maps capture-index strings to lists of inspected RGB body boxes.
    Missing keys mean unannotated, [] means explicitly no annotated target.
    Neither means proof of physical absence. Only captures is consumed: policy
    actions, task state, outcome, privileged poses and rewards are not inputs.
    """
    run_dir = Path(run_dir)
    manifest_path = run_dir / "hybrid_short.json"
    content = manifest_path.read_bytes()
    captures = json.loads(content)["captures"]
    if not isinstance(captures, list):
        raise ValueError("Retained captures list required")
    annotations = {} if annotations is None else annotations
    if (not isinstance(annotations, dict)
            or any(key not in {str(i) for i in range(len(captures))} for key in annotations)):
        raise ValueError("Annotations must reference existing capture indices")
    gripper = placeholder_gripper()
    reviewer = ReviewEngine(qualification_id="UNQUALIFIED-offline-contract-probe",
                            domain="behavior_sim", checks={})
    results = []
    for index, capture in enumerate(captures):
        row = {"capture_index": index, "status": "unannotated", "errors": [],
               "cameras": [], "geometry": [], "contract_probe_catalog": {},
               "real_candidate_catalog": {"status": "missing_prerequisites", "actions": []},
               "target_annotation_status": "unannotated" if str(index) not in annotations
                                           else "empty"}
        entries = annotations.get(str(index), [])
        if (not isinstance(entries, list) or len(entries) > 8
                or any(not isinstance(a, dict) or a.get("camera") not in CAMERAS for a in entries)):
            row["errors"].append("Invalid annotation list/camera (maximum eight body patches)")
            entries = []
        for camera in CAMERAS:
            view = {"camera": camera, "status": "error"}
            row["cameras"].append(view)
            try:
                basis, intrinsics, depth, _ = read_capture(capture, run_dir / "evidence", camera)
                selected = [a for a in entries if a["camera"] == camera]
                annotation_ids = tuple("annotation:" + digest(a) for a in selected)
                basis = replace(basis, evidence_ids=basis.evidence_ids + annotation_ids,
                                geometry_revision=digest((basis.geometry_revision, selected)))
                support = np.ones(depth.shape, dtype=bool)
                scene = _cloud(basis, intrinsics, depth, support, camera,
                               "unlabeled_scene", "depth_support_not_object_mask")
                valid_depth = depth[np.isfinite(depth) & (depth > 0) & (depth <= 10)]
                view.update(status="ok", basis=plain(basis), observed_geometry=_geometry(scene),
                            depth_range_m=[float(valid_depth.min()), float(valid_depth.max())])
                proposals = [inspect_candidate(basis, gripper)]
                for annotation in selected:
                    mask = _annotation_mask(annotation, basis.evidence_ids[0], intrinsics)
                    cloud = _cloud(basis, intrinsics, depth, mask, camera,
                                   annotation["entity"], annotation["part"])
                    geometry = _geometry(cloud)
                    geometry.update(camera=camera, annotation=annotation,
                                    mask_pixels=int(mask.sum()), annotation_assisted=True,
                                    contact_qualified=False)
                    row["geometry"].append(geometry)
                    try:
                        surface = fit_surface(cloud)
                        geometry["surface"] = {
                            "point_m": list(surface.point),
                            "camera_facing_normal": list(surface.outward_normal),
                            "residual_p95_m": surface.residual_p95_m,
                            "support_radius_m": surface.support_radius_m,
                            "semantic_contact_region": False,
                        }
                        pose = pose_from_approach(basis.frame, surface.point,
                                                  tuple(-v for v in surface.outward_normal))
                        proposals.append(pose_candidate(
                            basis=basis, intent=Intent(Verb.STAGE, cloud.entity, cloud.part),
                            pose=pose.shifted(surface.outward_normal, .05), gripper=gripper,
                            evidence_ids=basis.evidence_ids))
                    except ValueError as exc:
                        geometry["surface_rejection"] = str(exc)
                catalog = compile_catalog(basis=basis, proposals=tuple(proposals), gripper=gripper,
                                          template=TemplateConfig(), review=reviewer,
                                          deadline=time.monotonic() + 10)
                view["contract_probe_catalog"] = catalog.view()
                view["programs_and_reviews"] = [plain(a) for a in catalog.actions]
                row["contract_probe_catalog"][camera] = catalog.view()
                # With no reviewer callbacks even passive reobservation stays UNKNOWN.
                if any(action.eligible for action in catalog.actions):
                    raise RuntimeError("Replay contract probe unexpectedly eligible")
            except (KeyError, TypeError, ValueError, OSError) as exc:
                view.update(status="error", error=f"{type(exc).__name__}: {exc}")
                row["errors"].append(f"{camera}: {view['error']}")
        if row["geometry"]:
            row["target_annotation_status"] = "annotated"
        row["status"] = ("error" if row["errors"] else "ok" if row["geometry"]
                         else row["target_annotation_status"])
        results.append(row)
    views = [v for row in results for v in row["cameras"]]
    actions = [a for v in views for a in v.get("contract_probe_catalog", {}).get("actions", [])]
    summary = {"status_counts": dict(Counter(row["status"] for row in results)),
               "camera_count": len(views), "valid_camera_count": sum(v["status"] == "ok" for v in views),
               "geometry_count": sum(len(row["geometry"]) for row in results),
               "contract_probe_actions": len(actions),
               "contract_probe_verbs": dict(Counter(a["intent"]["verb"] for a in actions)),
               "eligible_actions": sum(a["eligible"] for a in actions),
               "real_qualified_candidates": 0,
               "blocked_checks": dict(Counter(c for a in actions for c in a["blocked_by"]))}
    return {"schema": "compiler-replay-v1", "run": run_dir.parent.name + "/" + run_dir.name,
            "manifest_sha256": hashlib.sha256(content).hexdigest(),
            "annotations_sha256": digest(annotations), "denominator": len(captures),
            "processed": len(results), "captures": results, "summary": summary,
            "robot_motion": False, "gpt_calls": 0, "model_calls": 0, "executable": False,
            "clock_semantics": "retained monotonic time; sim_time sentinel 0; never refreshed",
            "depth_contract": DEPTH_CONTRACT,
            "geometry_scope": "per-capture optical camera coordinates; no cross-frame fusion",
            "contract_probe_only": True, "placeholder_gripper": plain(gripper),
            "missing_prerequisites": list(MISSING_PREREQUISITES),
            "withheld_verbs": {"grasp": "No qualified actual gripper/TCP or up direction",
                               "press": "No grounded semantic contact region or contact tolerance",
                               "navigate": "No camera extrinsics/localization or known free space"}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if (not output.name.startswith("compiler_replay")
            or output.is_relative_to(args.run_dir.resolve())):
        parser.error("Use a separate private compiler_replay* output, never inside the source run")
    annotations = json.loads(args.annotations.read_text()) if args.annotations else None
    report = replay_run(args.run_dir, annotations)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(output), "denominator": report["denominator"],
                      **report["summary"]}, sort_keys=True))
    return int(report["summary"]["status_counts"].get("error", 0) > 0)


if __name__ == "__main__":
    raise SystemExit(main())
