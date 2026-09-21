import numpy as np
import pytest

from experiments.behavior.empty_base_audit import fixture_posture
from experiments.behavior.native import BEHAVIOR_COMMIT


def receipt():
    return {"passed": True, "source_revision": BEHAVIOR_COMMIT,
            "hold_diagnostic": {"samples": [{"settled": True,
                "observation": {"proprio": np.arange(61).tolist(), "secret_scene_pose": [999, 999, 999]}}]}}


def test_fixture_posture_uses_only_joints_never_scene_or_virtual_base_pose():
    result = fixture_posture(receipt())
    assert result == [0.] * 6 + list(range(53, 57)) + list(range(3, 10)) + list(range(28, 35)) + [24, 25, 49, 50]


@pytest.mark.parametrize("change", ["passed", "source", "settled", "width", "finite"])
def test_invalid_fixture_posture_is_rejected(change):
    data = receipt()
    sample = data["hold_diagnostic"]["samples"][0]
    if change == "passed":
        data["passed"] = False
    elif change == "source":
        data["source_revision"] = "other"
    elif change == "settled":
        sample["settled"] = False
    elif change == "width":
        sample["observation"]["proprio"] = [0.]
    else:
        sample["observation"]["proprio"][0] = float("nan")
    with pytest.raises(ValueError):
        fixture_posture(data)
