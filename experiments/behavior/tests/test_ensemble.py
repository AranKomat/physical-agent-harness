import numpy as np
import pytest

from experiments.behavior.ensemble_backend import EnsembleBackend


class Wrapper:
    robot_obs = {"observation": {c: c + "_rgb" for c in
                                 ("head", "left_wrist", "right_wrist")}}

    def __init__(self):
        self.resets = 0
        self.bad = False

    def reset(self):
        self.resets += 1

    def act(self, inputs):
        assert set(inputs) == {*self.robot_obs["observation"].values(), "robot_r1::proprio"}
        return np.full(23, np.nan if self.bad else 0.5)


def packet(sequence=0, instruction="radio"):
    return {"stamp": {"session": "test", "epoch": 0, "sequence": sequence},
            "instruction": instruction, "proprio": np.zeros(61),
            "rgb": {c: np.zeros((4, 4, 3), dtype=np.uint8) for c in
                    Wrapper.robot_obs["observation"]}, "oracle": "must not be forwarded"}


def test_ensemble_persists_and_instruction_change_resets():
    wrapper = Wrapper()
    backend = EnsembleBackend(wrapper)
    backend.reset(packet()["stamp"])
    assert backend.infer(packet())["actions"].shape == (1, 23)
    resets = wrapper.resets
    backend.infer(packet(1))
    assert wrapper.resets == resets
    backend.infer(packet(2, "trash"))
    assert wrapper.resets == resets + 1
    assert wrapper.text_prompt == "trash"
    with pytest.raises(ValueError, match="Stale"):
        backend.infer(packet(2))


def test_failure_invalidates_episode():
    wrapper = Wrapper()
    backend = EnsembleBackend(wrapper)
    backend.reset(packet()["stamp"])
    wrapper.bad = True
    with pytest.raises(ValueError, match="finite"):
        backend.infer(packet())
    with pytest.raises(ValueError, match="uninitialized"):
        backend.infer(packet(1))


@pytest.mark.parametrize("field,value", [("proprio", [0] * 23), ("rgb", {}),
                                         ("instruction", "")])
def test_bad_sensor_inputs(field, value):
    backend = EnsembleBackend(Wrapper())
    data = packet()
    backend.reset(data["stamp"])
    data[field] = value
    with pytest.raises(ValueError):
        backend.infer(data)
