import json

import numpy as np
import pytest

from experiments.behavior.assisted_probe import run_assisted_probe, validate_selection
from experiments.behavior.contracts import Observation, Stamp
from experiments.behavior.observations import EvidenceStore


def observation(store, sequence):
    stamp = Stamp(session="assisted", epoch=0, sequence=sequence)
    at = float(sequence)
    return Observation(stamp=stamp, observed_at=at, proprio=(0.,)*61,
        rgb={"head": store.put(np.zeros((10, 10, 3), dtype=np.uint8), "rgb", stamp, at)},
        depth={"head": store.put(np.ones((10, 10), dtype=np.float32), "depth", stamp, at)})


def selection(obs, decision="yaw"):
    return {"stamp": obs.stamp.model_dump(), "rgb_evidence_id": obs.rgb["head"].id,
            "depth_evidence_id": obs.depth["head"].id, "decision": decision,
            "direction": 1, "pixel_uv": [5, 5]}


@pytest.mark.parametrize("change", [
    {"direction": True}, {"direction": 2}, {"pixel_uv": [-1, 5]},
    {"pixel_uv": [5.0, 5]}, {"rgb_evidence_id": "old"}, {"depth_evidence_id": "old"},
])
def test_selection_rejects_invalid_or_stale_annotation(tmp_path, change):
    store = EvidenceStore(tmp_path / "evidence")
    obs = observation(store, 5)
    with pytest.raises(ValueError):
        validate_selection({**selection(obs), **change}, obs, store)


@pytest.mark.parametrize("decision, count, passed", [("yaw", 25, True), ("not_visible", 5, False)])
def test_probe_is_bounded_and_refuses_missing_target(tmp_path, decision, count, passed):
    store = EvidenceStore(tmp_path / "evidence")
    (tmp_path / "selection_response.json").write_text(json.dumps(selection(observation(store, 5), decision)))
    actions, saved = [], {}

    def step(action):
        actions.append(action)
        return False

    run_assisted_probe(observation(store, 0), store, [[0, .05], [0, .05]], step,
        lambda: observation(store, len(actions)), tmp_path, lambda report: saved.update(report))
    assert len(actions) == count and saved["passed"] is passed
    assert saved["stop_acknowledged"]
    assert not saved["motion_qualified"] and not saved["strict_gates_overridden"]
    assert sum(a[2] != 0 for a in actions) == (15 if passed else 0)
    assert all(a[:2] == (0., 0.) for a in actions)


def test_failed_initial_stop_never_sends_yaw(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")
    actions, saved = [], {}

    def capture():
        return observation(store, len(actions)).model_copy(update={"proprio": (.005,)+(0.,)*60})

    def step(action):
        actions.append(action)
        return False

    with pytest.raises(RuntimeError, match="stopping"):
        run_assisted_probe(observation(store, 0), store, [[0, .05], [0, .05]], step,
                           capture, tmp_path, lambda report: saved.update(report))
    assert len(actions) == 120 and all(a[2] == 0 for a in actions)
    assert not (tmp_path / "selection_request.json").exists()
    assert not saved["passed"] and "stop_error" in saved
