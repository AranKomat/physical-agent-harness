import numpy as np
import pytest

from experiments.behavior.behavior_skill import BehaviorSkillBackend, extract_state, sensor_inputs


def packet(sequence=0, instruction="Reach toward the radio"):
    return {"stamp": {"session": "skill-test", "epoch": 0, "sequence": sequence},
            "proprio": np.arange(61, dtype=np.float32), "instruction": instruction,
            "rgb": {key: np.full((8, 8, 3), index, dtype=np.uint8)
                    for index, key in enumerate(("head", "left_wrist", "right_wrist"))}}


def test_native_state_projection_order():
    compact = packet()["proprio"]
    expected = np.concatenate((compact[:3], compact[53:57], compact[3:10],
                               compact[28:35], [49, 99]))
    np.testing.assert_array_equal(extract_state(compact), expected)


@pytest.mark.parametrize("value", [np.zeros(60), np.full(61, np.nan)])
def test_bad_state(value):
    with pytest.raises(ValueError):
        extract_state(value)


def test_camera_order_and_no_privileged_fields_forwarded():
    p = packet()
    p["oracle_object_pose"] = [9, 9, 9]
    inputs = sensor_inputs(p, lambda image, h, w: image)
    assert set(inputs) == {"state", "image", "image_mask", "prompt"}
    assert [im[0, 0, 0] for im in inputs["image"].values()] == [0, 1, 2]


@pytest.mark.parametrize("case", ["float_rgb", "missing_camera", "empty_prompt"])
def test_reject_invalid_packet(case):
    p = packet()
    if case == "float_rgb":
        p["rgb"]["head"] = p["rgb"]["head"].astype(float)
    elif case == "missing_camera":
        del p["rgb"]["right_wrist"]
    else:
        p["instruction"] = " "
    with pytest.raises(ValueError):
        sensor_inputs(p, lambda image, h, w: image)


class FakePolicy:
    def __init__(self):
        self.calls = []
        self.invalid = False
        self.error = False

    def infer(self, inputs, *, noise):
        if self.error:
            raise RuntimeError("Inference failed")
        self.calls.append((inputs, noise))
        return {"actions": np.full((32, 32), np.nan if self.invalid else len(self.calls))}


def test_prompt_switch_produces_fresh_chunk_and_padding_removed():
    policy = FakePolicy()
    backend = BehaviorSkillBackend(policy, lambda image, h, w: image)
    backend.reset(packet()["stamp"])
    first = backend.infer(packet())
    second = backend.infer(packet(1, "Press the radio button"))
    assert first["actions"].shape == (32, 23)
    assert np.all(first["actions"] == 1) and np.all(second["actions"] == 2)
    assert policy.calls[-1][0]["prompt"] == "Press the radio button"
    with pytest.raises(ValueError, match="Stale"):
        backend.infer(packet(1))


def test_errors_never_return_previous_actions():
    policy = FakePolicy()
    backend = BehaviorSkillBackend(policy, lambda image, h, w: image)
    with pytest.raises(ValueError, match="uninitialized"):
        backend.infer(packet())
    backend.reset(packet()["stamp"])
    backend.infer(packet())
    policy.error = True
    with pytest.raises(RuntimeError):
        backend.infer(packet(1))
    policy.error = False
    policy.invalid = True
    with pytest.raises(ValueError, match="finite"):
        backend.infer(packet(1))
    assert len(backend.calls) == 1


def test_matched_noise_is_relative_to_handoff_reset_not_classical_exposure():
    policies = [FakePolicy(), FakePolicy()]
    for policy, offset in zip(policies, (0, 25), strict=True):
        backend = BehaviorSkillBackend(policy, lambda image, h, w: image)
        backend.reset(packet(offset)["stamp"])
        backend.infer(packet(offset))
        backend.infer(packet(offset + 32))
        assert [c["noise_index_since_reset"] for c in backend.calls] == [0, 32]
    for index in (0, 1):
        np.testing.assert_array_equal(policies[0].calls[index][1], policies[1].calls[index][1])
