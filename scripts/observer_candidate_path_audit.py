"""Offline authored-hull path audit for a retained observer candidate.

This tool never starts a simulator or authorizes motion. It checks only joint
limits, discrete authored-hull self-collision, and the candidate camera
transform along an interpolated endpoint path.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import fcl
import numpy as np
import yaml
from audit_r1pro_convex import convex, query
from audit_r1pro_joint_paths import native_exclusions
from build_r1pro_collision_envelope import hashes, inspected_meshes, require_hashes
from check_r1pro_kinematics import joint_config, offset_matrix
from pxr import Usd
from yourdfpy import URDF


def run(lab: Path, survey: Path, sweep: Path, native: Path, output: Path, candidate_index: int):
    root = lab / "runs/released_policy_audit/kinematics"
    survey_data = json.loads(survey.read_text())
    sweep_data = json.loads(sweep.read_text())
    paths = {"asset": root / "r1pro.usda", "urdf": root / "native_r1pro_processed.urdf",
             "config": root / "native_r1pro_source_cfg.yaml", "receipt": sweep,
             "native": native, "script": Path(__file__)}
    input_hashes = hashes(paths)
    require_hashes(input_hashes, {key: survey_data["input_sha256"][key]
                                for key in ("asset", "urdf", "config", "receipt")})
    if not sweep_data.get("complete") or not sweep_data.get("scan_completed"):
        raise ValueError("Completed source sweep required")
    if candidate_index < 0:
        raise ValueError("Negative candidate index")
    if survey_data["observer_survey"]["rows"][candidate_index]["index"] != candidate_index:
        raise ValueError("Candidate index mismatch")
    candidate = survey_data["observer_survey"]["rows"][candidate_index]["joints"]
    start = joint_config(sweep_data["captures"][-1]["observation"]["proprio"])
    end = {key: float(value) for key, value in candidate.items()}
    if set(start) != set(end) or not all(np.isfinite(list(q.values())).all() for q in (start, end)):
        raise ValueError("Inconsistent or nonfinite joint configurations")

    model = URDF.load(str(root / "native_r1pro_processed.urdf"), load_meshes=False,
                      load_collision_meshes=False)
    stage = Usd.Stage.Open(str(root / "r1pro.usda"), load=Usd.Stage.LoadNone)
    meshes = inspected_meshes(stage, model)
    shapes = [(path, row[0], convex(row[1])) for path, row in sorted(meshes.items())
              if row[4] == "convexHull"]
    ignored_a, ignored_b = native_exclusions(json.loads(native.read_text()))
    ignored = ignored_a | ignored_b
    pairs = [(i, j) for i, j in itertools.combinations(range(len(shapes)), 2)
             if shapes[i][1] != shapes[j][1]
             and tuple(sorted((shapes[i][1], shapes[j][1]))) not in ignored]

    changed = {key: end[key] - start[key] for key in start if end[key] != start[key]}
    invalid = [key for key, value in end.items()
               if not model.joint_map[key].limit.lower <= value <= model.joint_map[key].limit.upper]
    path_collisions = []
    collision_count = 0
    minimum_distance = float("inf")
    minimum_pair = None
    checked_pairs = 0
    for step in range(65):
        fraction = step / 64
        posture = {key: start[key] + fraction * (end[key] - start[key]) for key in start}
        model.update_cfg(posture)
        if any(not model.joint_map[key].limit.lower <= value <= model.joint_map[key].limit.upper
               for key, value in posture.items()):
            raise ValueError("Interpolated posture exceeded a joint limit")
        poses = {link: model.get_transform(link, "base_link") for _, link, _ in shapes}
        objects = [fcl.CollisionObject(geometry, fcl.Transform(poses[link][:3, :3], poses[link][:3, 3]))
                   for _, link, geometry in shapes]
        for i, j in pairs:
            result = query(objects[i], objects[j])
            checked_pairs += 1
            if result["distance_m"] < minimum_distance:
                minimum_distance = result["distance_m"]
                minimum_pair = [shapes[i][0], shapes[j][0], fraction]
            if result["intersects"]:
                collision_count += 1
                if len(path_collisions) < 20:
                    path_collisions.append({"fraction": fraction,
                                            "meshes": [shapes[i][0], shapes[j][0]]})

    model.update_cfg(end)
    config = yaml.safe_load((root / "native_r1pro_source_cfg.yaml").read_text())
    camera = next(row for row in config["camera_links"] if row["link"] == "right_realsense_link")
    optical = (model.get_transform("right_realsense_link", "base_link")
               @ offset_matrix(camera["offset"])
               @ np.diag([1, -1, -1, 1]))
    camera_valid = (optical.shape == (4, 4) and np.isfinite(optical).all()
                    and np.allclose(optical[3], [0, 0, 0, 1]))
    report = {
        "scope": "offline_observer_candidate_joint_path_authored_hull_check",
        "input_sha256": input_hashes,
        "candidate_index": candidate_index,
        "motion_authorized": False,
        "actions": 0,
        "paid_calls": 0,
        "source_survey_sha256": hashlib.sha256(survey.read_bytes()).hexdigest(),
        "source_sweep_sha256": hashlib.sha256(sweep.read_bytes()).hexdigest(),
        "native_receipt_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
        "changed_joints": changed,
        "max_abs_joint_delta_rad": max(map(abs, changed.values()), default=0.0),
        "joint_l2_delta_rad": float(np.linalg.norm(list(changed.values()))),
        "sampled_fractions": 65,
        "checked_pairs": checked_pairs,
        "joint_limits_valid": not invalid,
        "invalid_joints": invalid,
        "path_collision_count": collision_count,
        "collision_list_truncated": collision_count > len(path_collisions),
        "path_collisions": path_collisions,
        "minimum_fcl_distance_m": minimum_distance,
        "minimum_pair": minimum_pair,
        "camera_transform_valid": bool(camera_valid),
        "limitations": [
            "Authored convex hulls only",
            "Discrete 65-point path, not continuous swept volume",
            "No reachability, actuation, scene occlusion or native stopping",
            "No motion authority",
        ],
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--survey", type=Path, required=True)
    parser.add_argument("--sweep", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-index", type=int, required=True)
    args = parser.parse_args()
    report = run(**vars(args))
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"changed_joints", "path_collisions"}}, indent=2))


if __name__ == "__main__":
    main()
