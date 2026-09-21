import json
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.behavior.contracts import Stamp
from experiments.behavior.observations import CAMERAS, BehaviorObservationFilter, EvidenceStore
from experiments.behavior.radio import execute_loop, selected_prefix
from experiments.behavior.supervisor import MATCHED_EXECUTIVE, SkillSupervisor


def raw():
    result = {"robot_r1::proprio": np.zeros(61), "task_id": "hidden",
              "segmentation": "hidden", "native_success": True, "cam_rel_poses": "hidden"}
    for i, prefix in enumerate(CAMERAS.values()):
        result[prefix + "::rgb"] = np.full((4, 4, 3), i, dtype=np.uint8)
        result[prefix + "::depth_linear"] = np.ones((4, 4), dtype=np.float32)
    return result


class Model:
    def __init__(self):
        self.calls = []

    def call(self, call_id, role, instruction, context, images, schema):
        assert "hidden" not in json.dumps(context)
        self.calls.append((role, context["sequence"]))
        if role == "executive":
            return {"skill": "press_radio", "reason": "fixture"}
        return {"power": "uncertain", "unsafe_to_continue": False, "reason": "fixture"}


class Transport:
    def __init__(self, prefix):
        self.prefix, self.calls = prefix, 0

    def infer(self, packet):
        assert set(packet) == {"stamp", "instruction", "proprio", "rgb"}
        self.calls += 1
        return {"stamp": packet["stamp"], "actions": np.zeros((self.prefix, 23))}


@pytest.mark.parametrize("prefix,expected_calls", [(1, 3224), (32, 101)])
def test_full_frozen_loop_without_gpu_or_paid_calls(tmp_path, prefix, expected_calls):
    store = EvidenceStore(tmp_path / "evidence")
    ingress = BehaviorObservationFilter(store, require_native_resolution=False)
    hook = SimpleNamespace(action=None)
    model = Model()
    supervisor = SkillSupervisor(model, tmp_path / "supervisor.jsonl", MATCHED_EXECUTIVE)
    transport = Transport(prefix)

    class Evaluator:
        obs = raw()
        robot = None
        actions = 0

        def step(self):
            assert hook.action.shape == (23,)
            self.actions += 1
            hook.action = None
            return False, False

    evaluator = Evaluator()
    trial = {"actions_sent": 0, "calls": []}
    execute_loop(evaluator, hook, transport, supervisor, ingress,
                 Stamp(session="fixture", epoch=0, sequence=0), tmp_path,
                 trial, lambda: None, prefix, preprocessing=lambda *args: {})
    assert trial["actions_sent"] == evaluator.actions == 3224
    assert transport.calls == expected_calls
    assert len(model.calls) == 18 and model.calls[-1] == ("verifier", 3224)
    assert trial["stop_reason"] == "step_budget"
    rows = [json.loads(x) for x in (tmp_path / "trace.jsonl").read_text().splitlines()]
    assert rows[-1]["sequence"] + rows[-1]["prefix_steps"] == 3224
    assert all(set(r["observation"]) == {"stamp", "observed_at", "rgb", "depth", "proprio"}
               for r in rows)


def test_action_validation_never_changes_raw_values():
    stamp = {"session": "test", "epoch": 0, "sequence": 0}
    actions = np.full((32, 23), 1.005, dtype=np.float32)
    result = selected_prefix({"stamp": stamp, "actions": actions}, stamp, 7, 32)
    np.testing.assert_array_equal(result, actions[:7])
    with pytest.raises(ValueError):
        selected_prefix({"stamp": {}, "actions": actions}, stamp, 7, 32)
    with pytest.raises(ValueError):
        selected_prefix({"stamp": stamp, "actions": np.full((1, 23), np.nan)}, stamp, 7, 1)


def test_sensor_filter_rejects_wrong_native_dimensions(tmp_path):
    ingress = BehaviorObservationFilter(EvidenceStore(tmp_path))
    with pytest.raises(ValueError, match="FullRes"):
        ingress.convert(raw(), Stamp(session="x", epoch=0, sequence=0), 0)
