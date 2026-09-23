import json

import pytest

from experiments.fixtures.basic import run_demo


def test_end_to_end_offline_demo(tmp_path):
    directory = tmp_path / "demo"
    result = run_demo(directory)
    assert result["finished"] and result["task_status"] == "observed_complete"
    assert result["executive_decisions"] == 2
    assert result["receipts"][0]["policy_calls"] == 3
    assert result["receipts"][0]["action_steps_executed"] == 6
    assert result["real_model_calls"] == result["native_actions"] == 0
    assert (
        json.loads((directory / "summary.json").read_text())["kind"]
        == "offline-integration-fixture"
    )
    with pytest.raises(FileExistsError):
        run_demo(directory)
