"""Synthetic fixtures only; no native stop evidence or simulator imports."""

import copy
import json
import math

import pytest

from experiments.behavior.joint_stop_shadow import (
    JOINT_NAMES,
    PINNED_REVISION,
    evaluate_joint_stop_shadow,
)


def packet(n=24, phase="post_policy_zero_base_hold"):
    dt = 1 / 120
    return {
        "schema_version": 1, "source_revision_attested": PINNED_REVISION,
        "dof_indices": [*range(10, 24, 2), *range(11, 24, 2), *range(6, 10), *range(24, 28)],
        "joint_names": list(JOINT_NAMES), "position_units": ["rad"] * 18 + ["m"] * 4,
        "velocity_units": ["rad/s"] * 18 + ["m/s"] * 4,
        "error": None, "rows_dropped": 0, "truncated": False,
        "callback_removed": True, "installed": False, "physics_dt_s": dt,
        "max_rows": 2000, "callbacks_seen": n,
        "rows": [{"callback_index": i + 1, "physics_step_index": 100 + i,
                  "control_sequence": 385 + i // 4, "phase": phase,
                  "sim_time_s": i * dt, "wall_elapsed_s": i * .02,
                  "joint_positions": [0.] * 22, "native_joint_velocities": [0.] * 22}
                 for i in range(n)],
    }


def test_stationary_readiness_units_labels_and_no_authority():
    p = packet()
    before = copy.deepcopy(p)
    result = evaluate_joint_stop_shadow(p)
    assert p == before and result["status"] == "evaluated"
    assert not result["motion_authorized"] and not result["base_stop_evaluated"]
    assert not result["native_provenance_verified"]
    rows = result["windows"]
    assert len(rows) == 24
    assert all(r["status"] == "not_ready" and r["joint_stationary_candidate"] is None
               and r["max_rates"] is None for r in rows[:20])
    assert rows[20]["interval_count"] == 20 and rows[20]["control_sequence"] == 390
    assert rows[20]["phase"] == "post_policy_zero_base_hold"
    assert all(r["joint_stationary_candidate"] for r in rows[20:])
    assert all(r["native_joint_stationary"] and not r["motion_authorized"] for r in rows)
    assert rows[20]["max_rates"] == {"joints_rad_s": 0., "fingers_m_s": 0.}
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("n", [0, 4, 8, 20])
def test_not_ready_short_complete_packets(n):
    result = evaluate_joint_stop_shadow(packet(n))
    assert result["status"] == "not_ready"
    assert not any(w["joint_stationary_candidate"] for w in result["windows"])


@pytest.mark.parametrize("joint,speed,key", [(0, .031, "joints_rad_s"),
                                          (18, .0051, "fingers_m_s")])
def test_moving_positions_cannot_be_hidden_by_zero_native_velocities(joint, speed, key):
    p = packet()
    for i, row in enumerate(p["rows"]):
        row["joint_positions"][joint] = i * speed * p["physics_dt_s"]
    result = evaluate_joint_stop_shadow(p)
    assert result["status"] == "evaluated"
    assert all(not w["joint_stationary_candidate"] for w in result["windows"][20:])
    assert result["windows"][-1]["max_rates"][key] == pytest.approx(speed)
    assert result["windows"][-1]["native_joint_stationary"]


def test_oscillation_is_not_mistaken_for_zero_endpoint_motion():
    p = packet()
    for i, row in enumerate(p["rows"]):
        row["joint_positions"][0] = .001 if i % 2 else 0.
    assert p["rows"][20]["joint_positions"][0] == p["rows"][0]["joint_positions"][0]
    result = evaluate_joint_stop_shadow(p)
    assert result["windows"][20]["max_rates"]["joints_rad_s"] == pytest.approx(.12)
    assert not result["windows"][20]["joint_stationary_candidate"]


@pytest.mark.parametrize("joint,limit,key", [(0, .03, "joints_rad_s"),
                                          (18, .005, "fingers_m_s")])
def test_threshold_equality_is_inclusive_without_tolerance(joint, limit, key):
    p = packet()
    # Use a 120 Hz representation whose computed quotient equals the limit exactly.
    # Alternation avoids accumulation error; no evaluator threshold epsilon is used.
    p["physics_dt_s"] = math.nextafter(math.nextafter(1 / 120, 0.), 0.)
    for i, row in enumerate(p["rows"]):
        row["sim_time_s"] = i * p["physics_dt_s"]
    delta = limit * p["physics_dt_s"]
    assert delta / p["physics_dt_s"] == limit
    for i, row in enumerate(p["rows"]):
        row["joint_positions"][joint] = delta if i % 2 else 0.
        row["native_joint_velocities"][joint] = limit
    result = evaluate_joint_stop_shadow(p)
    assert result["windows"][-1]["max_rates"][key] == limit
    assert result["windows"][-1]["joint_stationary_candidate"]
    assert result["windows"][-1]["native_joint_stationary"]
    p["rows"][-1]["native_joint_velocities"][joint] = math.nextafter(limit, math.inf)
    assert not evaluate_joint_stop_shadow(p)["windows"][-1]["native_joint_stationary"]
    p["rows"][-1]["joint_positions"][joint] = delta * 1.000001
    assert not evaluate_joint_stop_shadow(p)["windows"][-1]["joint_stationary_candidate"]


def test_native_comparison_is_ending_row_not_window_or_base_stop():
    p = packet()
    p["rows"][20]["native_joint_velocities"][14] = .031
    result = evaluate_joint_stop_shadow(p)
    assert result["windows"][20]["joint_stationary_candidate"]
    assert not result["windows"][20]["native_joint_stationary"]
    assert result["windows"][21]["native_joint_stationary"]


@pytest.mark.parametrize("key,value", [
    ("source_revision_attested", "other"), ("schema_version", True),
    ("error", "feedback_read_failed"), ("rows_dropped", 1), ("rows_dropped", False),
    ("truncated", True), ("installed", True), ("callback_removed", False),
    ("physics_dt_s", 0), ("physics_dt_s", -1), ("physics_dt_s", 1/240),
    ("physics_dt_s", float("nan")), ("callbacks_seen", 23), ("max_rows", 2001),
])
def test_refuse_invalid_metadata(key, value):
    p = packet()
    p[key] = value
    result = evaluate_joint_stop_shadow(p)
    assert result["status"] == "refused" and result["windows"] == []
    assert result["reason"] and not result["motion_authorized"]


@pytest.mark.parametrize("key", ["joint_names", "position_units", "velocity_units"])
def test_exact_named_joint_contract(key):
    p = packet()
    p[key][0] = "bad"
    assert evaluate_joint_stop_shadow(p)["status"] == "refused"
    p = packet()
    p["joint_names"][1] = p["joint_names"][0]
    assert evaluate_joint_stop_shadow(p)["status"] == "refused"


@pytest.mark.parametrize("indices", [None, [], list(range(21)), list(range(23)),
                                     [0] * 22, [-1, *range(21)],
                                     [True, *range(1, 22)], [0., *range(1, 22)],
                                     ["0", *range(1, 22)], [[0], *range(1, 22)]])
def test_refuse_malformed_declared_dof_mapping(indices):
    p = packet()
    p["dof_indices"] = indices
    result = evaluate_joint_stop_shadow(p)
    assert result["status"] == "refused" and result["windows"] == []
    assert result["reason"] == "Invalid declared DOF mapping"
    assert not result["motion_authorized"]


def test_mapping_required_but_not_claimed_authenticated():
    p = packet()
    del p["dof_indices"]
    assert evaluate_joint_stop_shadow(p)["status"] == "refused"
    p["dof_indices"] = list(reversed(range(22)))
    result = evaluate_joint_stop_shadow(p)
    assert result["status"] == "evaluated"
    assert not result["native_provenance_verified"]


@pytest.mark.parametrize("key,value", [
    ("callback_index", 2), ("physics_step_index", 103), ("sim_time_s", 0.),
    ("sim_time_s", .03), ("wall_elapsed_s", -1.), ("control_sequence", 387),
    ("phase", "other"), ("phase", "policy_motion"),
])
def test_refuse_gaps_stale_rows_and_phase_changes(key, value):
    p = packet()
    p["rows"][2][key] = value
    result = evaluate_joint_stop_shadow(p)
    assert result["status"] == "refused" and result["windows"] == []


def test_30hz_aliased_subset_is_refused_not_rescaled():
    p = packet(96)
    p["rows"] = p["rows"][::4]
    p["callbacks_seen"] = len(p["rows"])
    assert evaluate_joint_stop_shadow(p)["status"] == "refused"


@pytest.mark.parametrize("n", [1, 3, 21, 25, 2004])
def test_refuse_incomplete_groups_or_oversized_packet(n):
    assert evaluate_joint_stop_shadow(packet(n))["status"] == "refused"


@pytest.mark.parametrize("key", ["joint_positions", "native_joint_velocities"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True])
def test_refuse_nonfinite_or_non_numeric_arrays(key, value):
    p = packet()
    p["rows"][10][key][0] = value
    assert evaluate_joint_stop_shadow(p)["status"] == "refused"


def test_no_future_influence_and_no_history_between_packets():
    early = packet(24, phase="policy_motion")
    late = packet(48, phase="policy_motion")
    for row in late["rows"][24:]:
        row["joint_positions"][0] = 1.
        row["native_joint_velocities"][0] = 1.
    first = evaluate_joint_stop_shadow(early)
    extended = evaluate_joint_stop_shadow(late)
    assert first["windows"] == extended["windows"][:24]
    assert not extended["windows"][24]["joint_stationary_candidate"]
    # The transition interval leaves the causal window after exactly 20 intervals.
    assert not extended["windows"][43]["joint_stationary_candidate"]
    assert extended["windows"][44]["joint_stationary_candidate"]
    hold = evaluate_joint_stop_shadow(packet(20))
    assert hold["status"] == "not_ready" and len(hold["windows"]) == 20
