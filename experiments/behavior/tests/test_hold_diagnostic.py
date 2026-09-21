import sys
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.behavior import base_hold_audit as audit
from experiments.behavior.contracts import Observation, Stamp


def fixture(monkeypatch, mode="settle"):
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        tensor=lambda value, **kw: np.array(value), float32="float32"))
    p = np.zeros(61)
    p[24:26], p[49:51], p[57] = .04, .04, .35
    initial = Observation(stamp=Stamp(session="test", epoch=0, sequence=0),
                          observed_at=0, rgb={}, proprio=tuple(p))

    class Ingress:
        def __init__(self, store):
            pass

        def convert(self, raw, stamp, at):
            return initial.model_copy(update={"stamp": stamp, "observed_at": at,
                                               "proprio": tuple(raw)})

    class Evaluator:
        obs = p.copy()
        commands = []

        def step(self):
            self.commands.append(self.policy.forward(self.obs))
            if mode != "budget":
                self.obs[57] = 0
            if mode == "drift":
                self.obs[53] = .04
            return mode == "end", False

    monkeypatch.setattr(audit, "BehaviorObservationFilter", Ingress)
    return Evaluator(), initial


def test_hold_requires_five_measured_samples_and_keeps_initial_targets(monkeypatch):
    evaluator, initial = fixture(monkeypatch)
    saved = []
    result = audit.stationary_hold(evaluator, initial, None, ((0, .05), (0, .05)),
                                   60, lambda state: saved.append(state["actions_attempted"]))
    assert result["settled"] and result["actions_executed"] == 5
    assert result["physical_s"] == 5 / 30
    assert saved[0] == 1
    for command in evaluator.commands:
        np.testing.assert_array_equal(command, evaluator.commands[0])
        np.testing.assert_array_equal(command[:3], [0, 0, 0])


def test_hold_budget_is_not_a_stop_acknowledgement(monkeypatch):
    evaluator, initial = fixture(monkeypatch, "budget")
    result = audit.stationary_hold(evaluator, initial, None, ((0, .05), (0, .05)),
                                   3, lambda state: None)
    assert not result["settled"] and result["actions_executed"] == 3
    assert result["stop_reason"] == "hold_budget_exhausted"


def test_calibration_callback_follows_each_measured_capture(monkeypatch):
    evaluator, initial = fixture(monkeypatch)
    calls = []

    def capture(ev, obs):
        assert ev is evaluator
        calls.append(obs.stamp.sequence)
        return {"sequence": obs.stamp.sequence}

    result = audit.stationary_hold(evaluator, initial, None, ((0, .05), (0, .05)),
                                   60, lambda state: None, calibration_capture=capture)
    assert calls == [1, 2, 3, 4, 5]
    for sample in result["samples"]:
        assert sample["camera_calibration"]["sequence"] == sample["sequence"]
        assert sample["post_reset_control_time_s"] == sample["sequence"] / 30


def test_capture_failure_preserves_executed_action_count(monkeypatch):
    evaluator, initial = fixture(monkeypatch)
    saved = []

    def fail(ev, obs):
        raise ValueError("Calibration failed")

    with pytest.raises(ValueError, match="Calibration failed"):
        audit.stationary_hold(evaluator, initial, None, ((0, .05), (0, .05)),
                              60, lambda state: saved.append(dict(state)),
                              calibration_capture=fail)
    assert len(evaluator.commands) == 1
    assert saved[-1]["actions_attempted"] == saved[-1]["actions_executed"] == 1


def test_full_window_does_not_stop_at_first_five_settled_samples(monkeypatch):
    evaluator, initial = fixture(monkeypatch)
    result = audit.stationary_hold(evaluator, initial, None, ((0, .05), (0, .05)),
                                   60, lambda state: None, full_window=True)
    assert result["settled"] and result["actions_executed"] == 60
    assert result["stop_reason"] == "sustained_hold_window_complete"


def test_full_window_aborts_if_measured_settling_is_lost(monkeypatch):
    evaluator, initial = fixture(monkeypatch)
    old_step = evaluator.step

    def step():
        result = old_step()
        if len(evaluator.commands) == 10:
            evaluator.obs[57] = .04
        return result

    evaluator.step = step
    saved = []
    with pytest.raises(RuntimeError, match="Stationary state lost"):
        audit.stationary_hold(evaluator, initial, None, ((0, .05), (0, .05)),
                              60, lambda state: saved.append(dict(state)), full_window=True)
    assert saved[-1]["actions_executed"] == 10
    assert saved[-1]["stop_reason"] == "settled_state_lost"


@pytest.mark.parametrize("mode", ["drift", "end"])
def test_bad_native_state_aborts_without_extra_steps(monkeypatch, mode):
    evaluator, initial = fixture(monkeypatch, mode)
    saved = []
    with pytest.raises(RuntimeError):
        audit.stationary_hold(evaluator, initial, None, ((0, .05), (0, .05)),
                              60, lambda state: saved.append(dict(state)))
    assert len(evaluator.commands) == 1
    assert saved[-1]["actions_executed"] == 1


@pytest.mark.parametrize("cap", [0, 61, True])
def test_hold_cap_validation_precedes_dispatch(monkeypatch, cap):
    evaluator, initial = fixture(monkeypatch)
    with pytest.raises(ValueError):
        audit.stationary_hold(evaluator, initial, None, ((0, .05), (0, .05)), cap, lambda s: None)
    assert not evaluator.commands
