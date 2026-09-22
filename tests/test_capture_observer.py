import pytest

from experiments.behavior.hybrid_short import notify_capture


def test_observer_is_optional():
    notify_capture(None, {"observation": {}}, None, None)


def test_observer_cannot_modify_control_record_or_return_control():
    row = {"observation": {"proprio": [1, 2]}, "calibration": {"head": {"fx": 5}}}

    def observer(copy, store, output):
        copy["observation"]["proprio"][0] = 999
        copy["calibration"]["head"]["fx"] = 0
        assert store == "store" and output == "output"
        return {"actions": [999]}

    assert notify_capture(observer, row, "store", "output") is None
    assert row == {"observation": {"proprio": [1, 2]}, "calibration": {"head": {"fx": 5}}}


def test_observer_failure_stops_experiment():
    def observer(*args):
        raise ValueError("invalid provenance")

    with pytest.raises(ValueError, match="provenance"):
        notify_capture(observer, {}, None, None)
