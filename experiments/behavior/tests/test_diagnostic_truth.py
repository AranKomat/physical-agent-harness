import json
from types import SimpleNamespace

import numpy as np

from experiments.behavior.contracts import Stamp
from experiments.behavior.native_base_exploration import record_diagnostic_truth
from experiments.behavior.observations import CAMERAS


def test_truth_is_separate_read_only_artifact_and_returns_no_control_input(tmp_path):
    class Prim:
        def get_position_orientation(self):
            return np.zeros(3), np.array([0., 0., 0., 1.])

    robot = SimpleNamespace(links={"base_link": Prim()}, sensors={
        prefix.split("::", 1)[1]: Prim() for prefix in CAMERAS.values()})
    observation = SimpleNamespace(stamp=Stamp(session="diagnostic", epoch=0, sequence=1))
    path = tmp_path / "diagnostic_truth.jsonl"
    assert record_diagnostic_truth(SimpleNamespace(robot=robot), observation, path) is None
    row = json.loads(path.read_text())
    assert row["scope"] == "quarantined_diagnostic_only_not_agent_input"
    assert set(row) == {"scope", "stamp", "base_link", "cameras"}
    assert set(row["cameras"]) == set(CAMERAS)
    assert set(vars(observation)) == {"stamp"}
