import numpy as np
import pytest

from experiments.behavior.contracts import Observation, Stamp
from experiments.behavior.hybrid_short import admit_perturbation_handoff, execute_policy


@pytest.mark.parametrize("offset", [0, 25])
def test_equal_policy_exposure_keeps_native_provenance_and_prefix(offset):
    report = {"native_actions": offset, "policy_actions": 0, "policy_chunks": []}
    stamps = []

    def capture():
        return Observation(stamp=Stamp(session="short", epoch=0, sequence=report["native_actions"]),
                           observed_at=float(report["native_actions"]), proprio=(0.,)*61, rgb={})

    class Transport:
        def reset(self, stamp):
            assert stamp["sequence"] == offset
            return {"stamp": stamp}

        def infer(self, packet):
            stamps.append(packet["stamp"]["sequence"])
            return {"stamp": packet["stamp"], "actions": np.zeros((32, 23))}

    def step(action):
        assert len(action) == 23
        report["native_actions"] += 1
        return False

    execute_policy(Transport(), capture(), None, step, capture, report, lambda: None, lambda _: "checked")
    assert stamps == list(range(offset, offset+384, 32))
    assert report["policy_actions"] == 384 and report["native_actions"] == offset+384
    assert report["preprocessing_proof"] == "checked"


def test_handoff_refuses_failed_stop_missing_shadow_or_drift():
    rows = [{"head_depth_shadow": {"transform": np.eye(4).tolist()}} for _ in range(5)]
    report = {"classical": {"passed": True, "stop_acknowledged": True}, "captures": rows}
    admit_perturbation_handoff(report)
    report["classical"]["stop_acknowledged"] = False
    with pytest.raises(ValueError, match="stop failed"):
        admit_perturbation_handoff(report)
    report["classical"]["stop_acknowledged"] = True
    rows[-1]["head_depth_shadow"]["transform"][0][3] = .003
    with pytest.raises(ValueError, match="stabilized"):
        admit_perturbation_handoff(report)
    rows[-1]["head_depth_shadow"] = {"error": "lost"}
    with pytest.raises(ValueError, match="Missing"):
        admit_perturbation_handoff(report)
