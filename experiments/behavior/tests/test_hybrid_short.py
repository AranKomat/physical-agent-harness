import numpy as np
import pytest

from experiments.behavior.contracts import Observation, Stamp
from experiments.behavior.hybrid_short import (
    admit_perturbation_handoff,
    capture_record,
    execute_policy,
)


@pytest.mark.parametrize("track", [False, True])
def test_every_capture_retains_same_boundary_calibration(monkeypatch, track):
    observation = Observation(stamp=Stamp(session="capture", epoch=0, sequence=384),
                              observed_at=12.8, proprio=(0.,)*61, rgb={})
    evaluator = object()
    calibration = {"head": {"stamp": observation.stamp.model_dump()}}
    calls = []

    def calibrate(native, frozen):
        assert native is evaluator and frozen is observation
        calls.append(frozen.stamp)
        return calibration

    class Shadow:
        def update(self, frozen, intrinsics):
            assert frozen is observation and intrinsics is calibration
            return {"status": "recorded"}

    monkeypatch.setattr("experiments.behavior.hybrid_short.capture_intrinsics", calibrate)
    row = capture_record(evaluator, observation, Shadow() if track else None)
    assert row["calibration"] is calibration
    assert row["observation"] == observation.model_dump()
    assert len(calls) == 1
    assert ("head_depth_shadow" in row) == track


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
