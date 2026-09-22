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


@pytest.mark.parametrize("observer,extra,admitted", [
    (True, [], True), (False, [], False),
    (True, ["--condition", "B"], False),
    (True, ["--exploratory-transit"], False),
    (True, ["--feedback-hold-diagnostic"], False),
    (True, ["--png-compress-level", "1"], True),
    (True, ["--png-compress-level", "10"], False),
])
def test_observer_only_extended_acquisition_is_isolated(monkeypatch, observer, extra, admitted):
    from experiments.behavior import hybrid_short

    class ReachedSourceCheck(Exception):
        pass

    def check_source(*args):
        raise ReachedSourceCheck

    monkeypatch.setattr(hybrid_short, "check_source", check_source)
    monkeypatch.setattr("sys.argv", ["hybrid_short", "--source", "/not-used", "--output", "/not-used",
        "--condition", "A", "--policy-load-receipt", "/not-used", "--extended-grounding-acquisition",
        "--allow-simulator", "--allow-unknown-clearance-exploration", "--licenses-accepted", *extra])
    with pytest.raises(ReachedSourceCheck if admitted else SystemExit):
        hybrid_short.main(capture_observer=(lambda *args: None) if observer else None)
