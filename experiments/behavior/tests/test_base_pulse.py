import numpy as np
import pytest

from experiments.behavior.base_pulse import run_pulses


def setup():
    p = np.zeros(61)
    p[[24, 25, 49, 50]] = .04
    return p


def test_six_pulses_preserve_all_nonbase_channels_and_count_stops():
    p = setup()
    commands = []

    def step(command):
        commands.append(command)
        p[:3] = np.array(command[:3]) * [.75, .75, 1]
        return p.copy()

    result = run_pulses(p.copy(), step, ((0, .05), (0, .05)), lambda r: None)
    assert result["passed"] and not result["motion_qualified"]
    assert result["actions_executed"] == result["actions_attempted"] == 125
    assert len(result["pulses"]) == 6
    assert all(r["braking_ticks"] == 5 and r["response_passed"] for r in result["pulses"])
    for command in commands:
        np.testing.assert_array_equal(command[3:], commands[0][3:])


def test_stuck_robot_fails_response_not_misreported_as_stopped_success():
    p = setup()
    saved = []
    with pytest.raises(RuntimeError, match="does not follow"):
        run_pulses(p, lambda c: p.copy(), ((0, .05), (0, .05)),
                   lambda r: saved.append(dict(r)))
    assert saved[-1]["stop_acknowledged"]
    assert saved[-1]["actions_executed"] == 25
    assert not saved[-1]["passed"]


def test_runaway_gets_bounded_emergency_hold():
    p = setup()
    calls = []
    saved = []

    def step(command):
        calls.append(command)
        p[0] = .1 if command[0] else 0.
        return p.copy()

    with pytest.raises(RuntimeError, match="abort limits"):
        run_pulses(p.copy(), step, ((0, .05), (0, .05)), lambda r: saved.append(dict(r)))
    assert len(calls) == 11
    assert all(c[0] == 0 for c in calls[-5:])
    assert saved[-1]["stop_acknowledged"]


def test_failed_stop_exhausts_bounded_initial_and_emergency_holds():
    p = setup()
    p[0] = .006
    saved = []
    with pytest.raises(RuntimeError, match="No measured stop"):
        run_pulses(p, lambda c: p.copy(), ((0, .05), (0, .05)),
                   lambda r: saved.append(dict(r)))
    assert saved[-1]["actions_executed"] == 120
    assert not saved[-1]["stop_acknowledged"]


def test_characterization_is_bounded_and_cannot_convert_failed_stop_to_success():
    p = setup()
    p[0] = .006
    result = run_pulses(p, lambda c: p.copy(), ((0, .05), (0, .05)), lambda r: None,
                        characterize_unsettled=True)
    assert result["actions_executed"] == 510
    assert result["characterization_completed"]
    assert not result["passed"] and not result["motion_qualified"]
    assert len(result["stop_failures"]) == 7
    assert all(r["acknowledgement_s"] is None for r in result["pulses"])


def test_even_successful_characterization_never_qualifies_motion():
    p = setup()

    def step(command):
        p[:3] = np.array(command[:3]) * [.75, .75, 1]
        return p.copy()

    result = run_pulses(p.copy(), step, ((0, .05), (0, .05)), lambda r: None,
                        characterize_unsettled=True)
    assert result["characterization_completed"] and result["stop_acknowledged"]
    assert not result["passed"]


def test_one_selected_pulse_is_25_ticks_not_six_pulses():
    p = setup()

    def step(command):
        p[:3] = np.array(command[:3]) * [.75, .75, 1]
        return p.copy()

    result = run_pulses(p.copy(), step, ((0, .05), (0, .05)), lambda r: None,
                        pulse_names=("forward",))
    assert result["actions_executed"] == 25
    assert [r["name"] for r in result["pulses"]] == ["forward"]


@pytest.mark.parametrize("names", [(), ("missing",), ("forward", "forward")])
def test_bad_pulse_selection_never_dispatches(names):
    def step(command):
        raise AssertionError("Must not dispatch")

    with pytest.raises(ValueError):
        run_pulses(setup(), step, ((0, .05), (0, .05)), lambda r: None, pulse_names=names)
