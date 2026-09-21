import json

import numpy as np
import pytest

from experiments.behavior.acquisition_audit import audit, depth_difference
from experiments.behavior.behavior_skill import CAMERAS
from experiments.behavior.contracts import Observation, Stamp
from experiments.behavior.observations import EvidenceStore


@pytest.fixture
def run(tmp_path):
    calls = []
    for condition in ("A", "B"):
        store = EvidenceStore(tmp_path / condition / "evidence")
        chunks = []
        for sequence in (0, 32):
            stamp = Stamp(session=condition, epoch=0, sequence=sequence)
            at = float(sequence + (condition == "B"))
            rgb = {c: store.put(np.zeros((4, 4, 3), dtype=np.uint8), "rgb", stamp, at)
                   for c in CAMERAS}
            depth = {c: store.put(np.ones((4, 4), dtype=np.float32), "depth", stamp, at)
                     for c in CAMERAS}
            obs = Observation(stamp=stamp, observed_at=at, rgb=rgb, depth=depth,
                              proprio=tuple(np.zeros(61)))
            chunks.append({"observation": obs.model_dump(), "native_start": sequence,
                           "policy_start": sequence, "actions": np.zeros((32, 23)).tolist()})
            calls.append({"stamp": stamp.model_dump(), "noise_index_since_reset": sequence,
                          "instruction": "approach", "action_shape": [32, 23]})
        receipt = dict(condition=condition, seed=0, instruction="approach", policy_load_receipt={},
                       runner_sha256="runner", probe_code_sha256={}, policy_noise_index="relative",
                       policy_actions=64, policy_chunks=chunks)
        (tmp_path / condition / "hybrid_short.json").write_text(json.dumps(receipt))
    (tmp_path / "policy.json").write_text(json.dumps({"calls": calls}))
    return tmp_path


def change(run, update):
    path = run / "B/hybrid_short.json"
    receipt = json.loads(path.read_text())
    update(receipt)
    path.write_text(json.dumps(receipt))


def test_distinct_stamps_and_wall_times_do_not_imply_sensor_difference(run):
    result = audit(run)
    assert set(result["first_unequal_sequence"].values()) == {None}
    assert result["model_calls"] == result["actions_sent"] == 0


def test_earliest_difference_uses_content_and_retains_native_dimensions(run):
    def update(r):
        c = r["policy_chunks"][0]
        obs = Observation.model_validate(c["observation"])
        store = EvidenceStore(run / "B/evidence")
        c["observation"]["rgb"]["head"] = store.put(
            np.ones((4, 4, 3), dtype=np.uint8), "rgb", obs.stamp, obs.observed_at).model_dump()
        c["actions"][0][4] = .5
        r["policy_chunks"][1]["observation"]["proprio"][0] = .2
    change(run, update)
    result = audit(run)
    assert result["first_unequal_sequence"] == dict(rgb=0, proprio=32, projected_state=32, actions=0)
    assert result["chunks"][0]["rgb"]["head"]["mean_abs"] == 1
    assert result["chunks"][0]["actions"]["per_dimension_max_abs"][4] == .5


@pytest.mark.parametrize("kind", ["seed", "schedule", "count", "empty", "nan", "shape", "camera", "stamp"])
def test_rejects_incomparable_or_invalid_receipts(run, kind):
    def update(r):
        c = r["policy_chunks"][0]
        if kind == "seed":
            r["seed"] = 1
        elif kind == "schedule":
            c["native_start"] = 1
        elif kind == "count":
            r["policy_actions"] = 63
        elif kind == "empty":
            r["policy_chunks"] = []
        elif kind == "nan":
            c["actions"][0][0] = float("nan")
        elif kind == "shape":
            c["actions"].pop()
        elif kind == "camera":
            del c["observation"]["rgb"]["head"]
        elif kind == "stamp":
            c["observation"]["stamp"]["sequence"] = 1
    change(run, update)
    with pytest.raises(ValueError):
        audit(run)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "noise", "instruction"])
def test_requires_unambiguous_matching_noise_log(run, kind):
    path = run / "policy.json"
    log = json.loads(path.read_text())
    if kind == "missing":
        log["calls"].pop(0)
    elif kind == "duplicate":
        log["calls"].append(log["calls"][0])
    elif kind == "noise":
        log["calls"][0]["noise_index_since_reset"] = 1
    else:
        log["calls"][0]["instruction"] = "other"
    path.write_text(json.dumps(log))
    with pytest.raises(ValueError, match="policy-call receipt"):
        audit(run)


def test_corrupt_content_is_not_treated_as_reproducibility_failure(run):
    path = next((run / "A/evidence").glob("*.png"))
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="hash mismatch"):
        audit(run)


def test_invalid_depth_is_not_zero_difference():
    result = depth_difference(np.array([np.nan, 0]), np.array([1, np.inf]))
    assert not result["validity_equal"]
    assert result["joint_valid_m"] is None
    assert result["joint_valid_pixels"] == 0
