from dataclasses import replace

import pytest

from physical_harness.contracts import SkillRequest
from physical_harness.hybrid_v0.contracts import Phase, Regime, Route, Snapshot
from physical_harness.hybrid_v0.fixture import FixtureWorld
from physical_harness.hybrid_v0.telemetry import HandoffTelemetry, paused_world_compatibility


def telemetry(phase, snap, policy, generation=1):
    return HandoffTelemetry(
        phase.id, snap.fingerprint, snap.observation_id, snap.sim_time, "target",
        generation, policy.fingerprint, (snap.observation_id,),
        target_observed=True, base_target_distance_m=.6, eef_target_distance_m=.2,
        target_pixel_fraction=.05, pose_confidence=.9, localization_confidence=.8,
        gripper_positions=(.05, .05), controlled_joint_positions=(0.0, 0.0),
    )


def test_handoff_telemetry_binds_exact_boundary():
    w = FixtureWorld()
    s = w.snapshot()
    p = Phase("policy", Regime.POLICY, "fixture policy", ("target",), 8, 10, 1)
    t = telemetry(p, s, w.policy)
    assert t.require(p, s, w.policy, 1) is t
    with pytest.raises(PermissionError):
        t.require(replace(p, id="other"), s, w.policy, 1)


def test_executor_records_optional_handoff_telemetry():
    w = FixtureWorld()
    h = w.executor()
    old = h.backends[Regime.POLICY]
    def observe(phase, snap, generation):
        return telemetry(phase, snap, w.policy, generation)
    h.backends[Regime.POLICY] = replace(old, handoff_telemetry=observe)
    from physical_harness.contracts import SkillRequest
    r = SkillRequest(
        "demo-telemetry", "hybrid", "fixture", ("target",), max_wall_s=60,
        max_policy_chunks=1, source_observation_id="obs-0",
        metadata={"action_id": "demo", "max_action_steps": 208},
    )
    h.run_skill(r)
    rows = [row for row in h.trace if row["kind"] == "handoff_telemetry"]
    assert len(rows) == 1
    assert rows[0]["telemetry"]["target_entity"] == "target"


def test_paused_world_allows_new_capture_id_but_not_state_change():
    w = FixtureWorld()
    a = w.snapshot()
    env = a.envelope()
    env["observation_id"] = "fresh-capture"
    env["rgb_refs"]["head"] = "fresh-rgb"
    env["depth_refs"]["head"] = "fresh-depth"
    env["estimated_pose"]["evidence_ids"] = ["fresh-capture"]
    from physical_harness.hybrid_v0.contracts import Snapshot
    b = Snapshot.from_envelope(
        env, captured_wall=a.captured_wall + 30,
        frame_epoch=a.frame_epoch, geometry_revision=a.geometry_revision,
    )
    result = paused_world_compatibility(a, b)
    assert result.compatible and not result.reasons

    changed = b.envelope()
    changed["proprioception"]["joint_positions"][0] += .01
    c = Snapshot.from_envelope(
        changed, captured_wall=b.captured_wall,
        frame_epoch=b.frame_epoch, geometry_revision=b.geometry_revision,
    )
    result = paused_world_compatibility(a, c)
    assert not result.compatible
    assert any(reason.startswith("proprio_changed") for reason in result.reasons)


@pytest.mark.parametrize("change", ["calibration", "confidence", "capture_time"])
def test_recapture_rejects_changed_calibration_or_regressed_capture(change):
    a = FixtureWorld().snapshot()
    env = a.envelope()
    if change == "calibration":
        env["camera_intrinsics"]["head"]["fx"] += 1
    if change == "confidence":
        env["estimated_pose"]["confidence"] = .1
    b = Snapshot.from_envelope(env, captured_wall=a.captured_wall - (change == "capture_time"),
                              frame_epoch=a.frame_epoch, geometry_revision=a.geometry_revision)
    assert not paused_world_compatibility(a, b).compatible


@pytest.mark.parametrize("failure", ["stale", "untyped", "slow", "policy_changed"])
def test_bad_telemetry_prevents_policy_dispatch(failure):
    w = FixtureWorld()
    h = w.executor()
    phase = h.routes["demo"].phases[-1]
    h.routes = {"demo": Route("A", (phase,))}
    old = h.backends[Regime.POLICY]
    def capture(p, s, generation):
        value = telemetry(p, s, w.policy, generation)
        if failure == "untyped":
            return {}
        if failure == "stale":
            return replace(value, observation_id="old")
        if failure == "slow":
            w.clock.value += 3
        if failure == "policy_changed":
            w.policy = replace(w.policy, inference_recipe="changed")
        return value
    h.backends[Regime.POLICY] = replace(old, handoff_telemetry=capture)
    request = SkillRequest("bad-telemetry", "hybrid", "fixture", ("target",), max_wall_s=60,
                           max_policy_chunks=1, source_observation_id="obs-0",
                           metadata={"action_id": "demo", "max_action_steps": 8})
    with pytest.raises((ValueError, PermissionError)):
        h.run_skill(request)
    assert not w.commands and h.metrics()["faulted"]


def test_compatible_recapture_does_not_bypass_executor_source_guard():
    w = FixtureWorld()
    h = w.executor()
    decision = w.snapshot()
    env = decision.envelope()
    env["observation_id"] = "recapture"
    env["estimated_pose"]["evidence_ids"] = ["recapture"]
    fresh = Snapshot.from_envelope(env, captured_wall=decision.captured_wall,
                                  frame_epoch=decision.frame_epoch, geometry_revision=decision.geometry_revision)
    assert paused_world_compatibility(decision, fresh).compatible
    h.observe = lambda deadline: fresh
    request = SkillRequest("stale-decision", "hybrid", "fixture", ("target",), max_wall_s=60,
                           max_policy_chunks=1, source_observation_id=decision.observation_id,
                           metadata={"action_id": "demo", "max_action_steps": 208})
    with pytest.raises(ValueError, match="Stale executive"):
        h.run_skill(request)
    assert not w.commands
