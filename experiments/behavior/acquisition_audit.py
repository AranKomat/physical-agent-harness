"""Read-only audit of paired acquisition evidence; no simulator or model calls."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from experiments.behavior.behavior_skill import CAMERAS, extract_state
from experiments.behavior.contracts import Observation
from experiments.behavior.observations import EvidenceStore


def difference(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Mismatched or nonfinite arrays")
    delta = np.abs(a - b)
    return {"equal": bool(np.array_equal(a, b)), "max_abs": float(delta.max()),
            "mean_abs": float(delta.mean()), "rms": float(np.sqrt((delta**2).mean()))}


def depth_difference(a, b):
    if a.shape != b.shape:
        raise ValueError("Depth shapes differ")
    va, vb = np.isfinite(a) & (a > 0), np.isfinite(b) & (b > 0)
    joint = va & vb
    return {"validity_equal": bool(np.array_equal(va, vb)),
            "joint_valid_pixels": int(joint.sum()),
            "joint_valid_fraction": float(joint.mean()),
            "joint_valid_m": difference(a[joint], b[joint]) if joint.any() else None}


def audit(run):
    run = Path(run)
    paths = [run / c / "hybrid_short.json" for c in ("A", "B")]
    receipts = [json.loads(p.read_text()) for p in paths]
    a, b = receipts
    for key in ("seed", "instruction", "policy_load_receipt", "runner_sha256",
                "probe_code_sha256", "policy_noise_index"):
        if a[key] != b[key]:
            raise ValueError(f"Protocol mismatch: {key}")
    if a["condition"] != "A" or b["condition"] != "B":
        raise ValueError("Expected A/B labels")
    stores = []
    for path in paths:
        root = path.parent / "evidence"
        if not root.is_dir():
            raise ValueError("Missing evidence directory")
        stores.append(EvidenceStore(root))
    chunks = [r["policy_chunks"] for r in receipts]
    if not chunks[0] or len(chunks[0]) != len(chunks[1]):
        raise ValueError("Acquisition chunk counts differ or are empty")
    for r, cs in zip(receipts, chunks, strict=True):
        if r["policy_actions"] != 32 * len(cs):
            raise ValueError("Acquisition exposure mismatch")
        if [c["native_start"] for c in cs] != list(range(0, r["policy_actions"], 32)):
            raise ValueError("Acquisition schedule mismatch")
        if [c["policy_start"] for c in cs] != list(range(0, r["policy_actions"], 32)):
            raise ValueError("Policy schedule mismatch")
    log_path = run / "policy.json"
    calls = json.loads(log_path.read_text())["calls"]
    rows = []
    initial_depth = {}
    sessions = []
    for index, pair in enumerate(zip(*chunks, strict=True)):
        obs = [Observation.model_validate(c["observation"]) for c in pair]
        if index == 0:
            sessions = [o.stamp for o in obs]
            if sessions[0].same_episode(sessions[1]):
                raise ValueError("Pair must use distinct episodes")
        for o, c, session in zip(obs, pair, sessions, strict=True):
            if not o.stamp.same_episode(session) or o.stamp.sequence != c["native_start"]:
                raise ValueError("Observation boundary mismatch")
            if set(o.rgb) != set(CAMERAS):
                raise ValueError("Missing or unexpected policy camera")
            matches = [call for call in calls if call["stamp"] == o.stamp.model_dump()]
            if (len(matches) != 1 or matches[0]["noise_index_since_reset"] != index * 32
                    or matches[0]["instruction"] != a["instruction"]
                    or matches[0]["action_shape"] != [32, 23]):
                raise ValueError("Missing, ambiguous or mismatched policy-call receipt")
        rgb = {}
        for camera in CAMERAS:
            pixels = [s.read(o.rgb[camera]) for s, o in zip(stores, obs, strict=True)]
            if any(p.ndim != 3 or p.shape[-1] != 3 or p.dtype != np.uint8 for p in pixels):
                raise ValueError("Invalid RGB arrays")
            rgb[camera] = difference(*pixels)
            rgb[camera]["changed_pixel_fraction"] = float(
                np.any(pixels[0] != pixels[1], axis=-1).mean())
            if index == 0:
                if any(camera not in o.depth for o in obs):
                    raise ValueError("Missing initial depth evidence")
                depths = [s.read(o.depth[camera]) for s, o in zip(stores, obs, strict=True)]
                if any(d.shape != p.shape[:2] for d, p in zip(depths, pixels, strict=True)):
                    raise ValueError("Unaligned depth evidence")
                initial_depth[camera] = depth_difference(*depths)
        actions = [np.asarray(c["actions"], dtype=float) for c in pair]
        if any(x.shape != (32, 23) for x in actions):
            raise ValueError("Expected complete 32x23 native prefixes")
        action_delta = difference(*actions)
        action_delta["per_dimension_max_abs"] = np.abs(actions[0] - actions[1]).max(axis=0).tolist()
        rows.append({"sequence": index * 32, "rgb": rgb,
                     "proprio": difference(*(o.proprio for o in obs)),
                     "projected_state": difference(*(extract_state(o.proprio) for o in obs)),
                     "actions": action_delta})
    first = {}
    for kind in ("rgb", "proprio", "projected_state", "actions"):
        first[kind] = next((r["sequence"] for r in rows if
                           (any(not v["equal"] for v in r[kind].values()) if kind == "rgb"
                            else not r[kind]["equal"])), None)
    return {
        "scope": "offline_acquisition_divergence_not_causal_attribution",
        "model_calls": 0, "actions_sent": 0, "noise_schedule_receipts_match": True,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "receipt_sha256": {p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "policy_log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
        "first_unequal_sequence": first, "initial_depth": initial_depth, "chunks": rows,
        "caveats": ["Raw RGB metrics are not model-embedding differences.",
                    "State/action aggregates mix units; inspect per-dimension action differences.",
                    "Matching logged noise indices is not a GPU determinism test.",
                    "Equal depth/proprioception would not prove equal hidden simulator state.",
                    "Input differences do not isolate rendering, sampling or GPU numerical causes."],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(audit(args.run), indent=2, allow_nan=False)
    if args.output:
        with args.output.open("x") as stream:
            stream.write(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
