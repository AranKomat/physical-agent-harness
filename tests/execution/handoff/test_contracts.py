import json
from dataclasses import replace

import pytest

from experiments.fixtures.handoff import FixtureWorld
from physical_harness.execution.handoff.contracts import (
    Check,
    GateReport,
    Phase,
    Qualification,
    Regime,
    ResetReceipt,
    ResetRequest,
    Route,
    Snapshot,
)


def phase():
    return Phase("p", Regime.POLICY, "do task", ("target",), 32, 10, 1)


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -1., "1"])
def test_snapshot_rejects_bad_capture_time(bad):
    with pytest.raises(ValueError):
        replace(FixtureWorld().snapshot(), captured_wall=bad)


@pytest.mark.parametrize("key", ["score", "ground_truth_pose", "segmentation", "task_success"])
def test_snapshot_reuses_legal_observation_allowlist(key):
    value = FixtureWorld().snapshot().envelope()
    value[key] = 1
    with pytest.raises(ValueError):
        Snapshot.from_envelope(value, captured_wall=100, frame_epoch="f", geometry_revision="g")


def test_snapshot_does_not_alias_mutable_caller_data():
    value = FixtureWorld().snapshot().envelope()
    snap = Snapshot.from_envelope(value, captured_wall=100, frame_epoch="f", geometry_revision="g")
    value["proprioception"]["joint_positions"][0] = 9
    copy = snap.envelope()
    copy["proprioception"]["joint_positions"][0] = 8
    assert snap.envelope()["proprioception"]["joint_positions"][0] == 0


def test_snapshot_rejects_oracle_pose_source():
    value = FixtureWorld().snapshot().envelope()
    value["estimated_pose"]["method"] = "simulator_global"
    with pytest.raises(ValueError):
        Snapshot(json.dumps(value), 100, "f", "g")


@pytest.mark.parametrize("kwargs", [dict(max_steps=True), dict(max_steps=0),
                                    dict(max_wall_s=float("nan")), dict(max_policy_chunks=0),
                                    dict(target_entities=["a"]), dict(regime="policy")])
def test_phase_validation(kwargs):
    with pytest.raises(ValueError):
        replace(phase(), **kwargs)


def test_classical_phases_cannot_allocate_neural_chunks():
    with pytest.raises(ValueError):
        replace(phase(), regime=Regime.STAGE)


def test_duplicate_phases_rejected():
    with pytest.raises(ValueError):
        Route("r", (phase(), phase()))


@pytest.mark.parametrize("passed", [False, None])
def test_unknown_or_failed_gate_blocks(passed):
    world = FixtureWorld()
    snap, p = world.snapshot(), phase()
    report = world.guard(p, "entry", snap, 200)
    checks = (replace(report.checks[0], passed=passed),)+report.checks[1:]
    with pytest.raises(PermissionError):
        replace(report, checks=checks).require(p, "entry", snap)


def test_gate_requires_all_named_checks():
    snap, p = FixtureWorld().snapshot(), phase()
    report = GateReport(p.id, "entry", snap.fingerprint, (Check("robot_settled", True, ("obs-0",)),))
    with pytest.raises(PermissionError):
        report.require(p, "entry", snap)


def test_extra_failed_gate_cannot_be_ignored():
    w, p = FixtureWorld(), phase()
    s = w.snapshot()
    r = w.guard(p, "entry", s, 200)
    r = replace(r, checks=r.checks+(Check("extra_collision_check", False, (s.observation_id,)),))
    with pytest.raises(PermissionError):
        r.require(p, "entry", s)


@pytest.mark.parametrize("field,value", [("phase_id", "other"), ("when", "exit"),
                                        ("snapshot_fingerprint", "stale")])
def test_stale_gate_is_not_adopted(field, value):
    w, p = FixtureWorld(), phase()
    snap = w.snapshot()
    r = w.guard(p, "entry", snap, 200)
    with pytest.raises(PermissionError):
        replace(r, **{field: value}).require(p, "entry", snap)


@pytest.mark.parametrize("value", [1, "true", [], {}])
def test_boolean_gate_cannot_be_truthy_value(value):
    with pytest.raises(ValueError):
        Check("c", value, ("e",))


def test_policy_identity_pins_recipe_not_just_checkpoint():
    p = FixtureWorld().policy
    for field in ("normalization", "inference_recipe", "action_codec", "observation_codec"):
        assert replace(p, **{field: "different"}).fingerprint != p.fingerprint


def test_fixture_qualification_is_not_real_robot_qualification():
    with pytest.raises(ValueError):
        Qualification("q", Regime.STAGE, ("proof",), domain="hardware")


def test_reset_requires_all_acknowledgements_and_matching_request():
    r = ResetRequest("ep", 0, 1, "press", "obs", "pinned")
    ResetReceipt(r, True, True, True).require(r)
    for field in ("queue_cleared", "history_cleared", "in_flight_drained"):
        with pytest.raises(PermissionError):
            replace(ResetReceipt(r, True, True, True), **{field: False}).require(r)
    with pytest.raises(PermissionError):
        ResetReceipt(r, True, True, True).require(replace(r, generation=2))
