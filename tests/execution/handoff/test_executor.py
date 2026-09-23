from dataclasses import replace

import pytest

from experiments.fixtures.handoff import FixtureWorld, run_fixture
from physical_harness.core.contracts import SkillRequest
from physical_harness.execution.handoff.contracts import (
    ROBOT_RESOURCES,
    Check,
    Regime,
    ResetReceipt,
    Route,
    Snapshot,
)


def request(world, hybrid, id="s1", action="demo"):
    phases = hybrid.routes[action].phases
    return SkillRequest(id, "hybrid", "whole task", ("target",), max_wall_s=60,
                        max_policy_chunks=max(1, sum(p.max_policy_chunks for p in phases)),
                        source_observation_id=world.snapshot().observation_id,
                        metadata={"action_id": action, "max_action_steps": sum(p.max_steps for p in phases)})


def policy_only():
    w = FixtureWorld()
    h = w.executor()
    p = h.routes["demo"].phases[-1]
    h.routes = {"demo": Route("A", (p,))}
    return w, h


def test_complete_hybrid_fixture():
    result = run_fixture()
    assert result["receipt"]["outcome"] == "completed"
    assert result["metrics"]["completed_phase_receipts"] == 3
    assert result["metrics"]["recorded_policy_steps"] == 8
    assert result["metrics"]["recorded_classical_steps"] > 0
    assert result["native_action_widths"] == [23]
    assert not result["native_benchmark_run"]
    assert not result["policy_inference_performed"]


def test_whole_robot_ownership_held_across_phases():
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    def execute(req, s, deadline, cancelled):
        assert set(h.jobs.owners) == ROBOT_RESOURCES
        assert req.resources == ROBOT_RESOURCES
        assert req.instruction == "fixture policy"
        return old.execute(req, s, deadline, cancelled)
    h.backends[Regime.POLICY] = replace(old, execute=execute)
    out = h.run_skill(request(w, h))
    assert out.action_steps_executed == 8
    assert not h.jobs.owners


def test_public_rpc_metadata_shape_is_unchanged():
    w, h = policy_only()
    out = h.run_skill(request(w, h))
    assert set(out.metadata) == {"episode_id", "execution_epoch", "stop_acknowledged"}
    assert out.observed_predicates == ()


def test_disabled_motion_does_not_touch_native():
    w, h = policy_only()
    h.allowed = False
    with pytest.raises(PermissionError):
        h.run_skill(request(w, h))
    assert not w.commands and w.stop_count == 0


def test_conflicting_external_owner_is_not_cancelled_or_released():
    w, h = policy_only()
    other = h.jobs.start("external", h.name, ("right_arm",), "obs-0", 100, 200)
    with pytest.raises(ValueError):
        h.run_skill(request(w, h))
    assert h.jobs.owners["right_arm"] == other.id
    assert not w.commands and w.stop_count == 0


@pytest.mark.parametrize("field,value", [("source_observation_id", "old"), ("execution_epoch", 1),
                                        ("max_wall_s", 0), ("max_policy_chunks", True)])
def test_invalid_outer_request_never_dispatches(field, value):
    w, h = policy_only()
    with pytest.raises((ValueError, PermissionError)):
        h.run_skill(replace(request(w, h), **{field: value}))
    assert not w.commands


def test_unknown_action_cannot_create_new_route():
    w, h = policy_only()
    r = request(w, h)
    with pytest.raises(ValueError):
        h.run_skill(replace(r, metadata={"action_id": "arbitrary-code", "max_action_steps": 100}))
    assert not w.commands


def test_route_budget_checked_before_motion():
    w, h = policy_only()
    r = request(w, h)
    with pytest.raises(ValueError):
        h.run_skill(replace(r, metadata={"action_id": "demo", "max_action_steps": 1}))
    assert not w.commands


def test_route_cannot_invent_target():
    w, h = policy_only()
    with pytest.raises(ValueError):
        h.run_skill(replace(request(w, h), target_entities=("other",)))
    assert not w.commands


@pytest.mark.parametrize("change", ["stale", "future", "other_episode", "frame"])
def test_bad_observation_blocks(change):
    w, h = policy_only()
    initial = w.snapshot()
    if change == "frame":
        h._frame_epoch = "different-origin"
    def observe(deadline):
        if change == "stale":
            return replace(initial, captured_wall=1)
        if change == "future":
            return replace(initial, captured_wall=200)
        if change == "other_episode":
            e = initial.envelope()
            e["episode_id"] = "other"
            return Snapshot.from_envelope(e, captured_wall=100, frame_epoch="fixture-origin", geometry_revision="g")
        return initial
    h.observe = observe
    with pytest.raises(ValueError):
        h.run_skill(request(w, h))
    assert not w.commands


def test_stale_or_incomplete_entry_gate_blocks():
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    def guard(p, when, s, deadline):
        r = w.guard(p, when, s, deadline)
        return replace(r, checks=tuple(replace(c, passed=None) if c.name == "handoff_envelope" else c for c in r.checks))
    h.backends[Regime.POLICY] = replace(old, guard=guard)
    with pytest.raises(PermissionError):
        h.run_skill(request(w, h))
    assert not w.commands and not h.jobs.owners


def test_scene_change_during_gate_blocks_dispatch():
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    def guard(p, when, s, deadline):
        r = w.guard(p, when, s, deadline)
        w.pose = replace(w.pose, x=.1)
        return r
    h.backends[Regime.POLICY] = replace(old, guard=guard)
    with pytest.raises(ValueError):
        h.run_skill(request(w, h))
    assert not w.commands


def test_slow_gate_cannot_authorize_stale_pixels():
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    def guard(p, when, s, deadline):
        r = w.guard(p, when, s, deadline)
        w.clock.value += 3
        return r
    h.backends[Regime.POLICY] = replace(old, guard=guard)
    with pytest.raises(ValueError):
        h.run_skill(request(w, h))
    assert not w.commands


def test_policy_weights_or_recipe_change_rejected():
    w, h = policy_only()
    w.policy = replace(w.policy, inference_recipe="unreviewed-horizon")
    with pytest.raises(PermissionError):
        h.run_skill(request(w, h))
    assert not w.commands


@pytest.mark.parametrize("ack", [False, None, 1])
def test_policy_reset_must_drain_old_actions(ack):
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    h.backends[Regime.POLICY] = replace(old, reset_policy=lambda r, d: ResetReceipt(r, True, True, ack))
    with pytest.raises(PermissionError):
        h.run_skill(request(w, h))
    assert not w.commands


def test_unchanged_consecutive_policy_calls_keep_temporal_history():
    w, h = policy_only()
    h.run_skill(request(w, h, "one"))
    h.run_skill(request(w, h, "two"))
    assert len(w.resets) == 1


def test_instruction_change_resets_history_once():
    w, h = policy_only()
    h.run_skill(request(w, h, "one"))
    p = replace(h.routes["demo"].phases[0], instruction="another supported instruction")
    h.routes = {"demo": Route("next", (p,))}
    h.run_skill(request(w, h, "two"))
    assert len(w.resets) == 2
    assert w.resets[-1].instruction == p.instruction


def test_classical_intervention_resets_policy_even_for_same_instruction():
    w = FixtureWorld()
    h = w.executor()
    h.run_skill(request(w, h, "one"))
    h.run_skill(request(w, h, "two"))
    assert len(w.resets) == 2


def test_failed_phase_does_not_fall_through_to_policy():
    w = FixtureWorld()
    h = w.executor()
    old = h.backends[Regime.NAVIGATE]
    def execute(*args):
        return replace(old.execute(*args), outcome="stalled", failure_reason="blocked")
    h.backends[Regime.NAVIGATE] = replace(old, execute=execute)
    out = h.run_skill(request(w, h))
    assert out.outcome == "stalled" and out.failure_reason == "blocked"
    assert not w.resets
    assert [r["regime"] for r in h.trace if r["kind"] == "phase_start"] == ["navigate"]


def test_failed_exit_gate_prevents_next_executor():
    w = FixtureWorld()
    h = w.executor()
    old = h.backends[Regime.NAVIGATE]
    def guard(p, when, s, deadline):
        r = w.guard(p, when, s, deadline)
        if when == "exit":
            r = replace(r, checks=r.checks+(Check("payload_slip", False, (s.observation_id,)),))
        return r
    h.backends[Regime.NAVIGATE] = replace(old, guard=guard)
    with pytest.raises(PermissionError):
        h.run_skill(request(w, h))
    assert not w.resets and h.metrics()["faulted"]


def test_failed_stop_retains_lease_and_latches_session():
    w, h = policy_only()
    w.stop_ok = False
    with pytest.raises(RuntimeError):
        h.run_skill(request(w, h))
    assert h.jobs.owners and h.jobs.jobs["s1"].state == "unknown"
    assert not w.commands
    w.stop_ok = True
    assert h.stop() is True
    assert h.jobs.owners  # Stopping alone is not operator reconciliation.
    with pytest.raises(PermissionError):
        h.run_skill(request(w, h, "s2"))


@pytest.mark.parametrize("case", ["id", "start", "end", "epoch", "stop", "steps", "chunks", "type", "outcome"])
def test_invalid_receipts_stop_and_cannot_certify(case):
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    def execute(*args):
        raw = old.execute(*args)
        if case == "type":
            return {"completed": True}
        changes = {"id": {"skill_id": "other"}, "start": {"sim_time_start": 4},
                   "end": {"sim_time_end": 999}, "epoch": {"metadata": dict(raw.metadata, execution_epoch=7)},
                   "stop": {"metadata": dict(raw.metadata, stop_acknowledged=False)},
                   "steps": {"action_steps_executed": 999}, "chunks": {"chunks_generated": 99},
                   "outcome": {"outcome": "success"}}
        return replace(raw, **changes[case])
    h.backends[Regime.POLICY] = replace(old, execute=execute)
    with pytest.raises((ValueError, RuntimeError)):
        h.run_skill(request(w, h))
    assert h.metrics()["faulted"] and w.stop_count >= 2
    assert not h.jobs.owners
    assert h.metrics()["unresolved_phase_receipts"] == 1


def test_native_exception_does_not_silently_retry():
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    calls = []
    def execute(*args):
        calls.append(1)
        raise TimeoutError("ambiguous native send")
    h.backends[Regime.POLICY] = replace(old, execute=execute)
    with pytest.raises(TimeoutError):
        h.run_skill(request(w, h))
    assert len(calls) == 1 and not h.jobs.owners


@pytest.mark.parametrize("error", [KeyboardInterrupt, SystemExit])
def test_native_interrupt_latches_fault_and_never_completes_job(error):
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    def execute(*args):
        raise error()
    h.backends[Regime.POLICY] = replace(old, execute=execute)
    with pytest.raises(error):
        h.run_skill(request(w, h))
    assert h.jobs.jobs["s1"].state == "failed"
    assert h.metrics()["faulted"] and not h.jobs.owners
    assert not h._mutex.locked()
    with pytest.raises(PermissionError):
        h.run_skill(request(w, h, "s2"))


def test_cleanup_interrupt_retains_unresolved_ownership_and_unlocks_mutex():
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    def interrupted_stop(deadline):
        raise KeyboardInterrupt()
    def execute(*args):
        h.stop_native = interrupted_stop
        raise TimeoutError("ambiguous dispatch")
    h.backends[Regime.POLICY] = replace(old, execute=execute)
    with pytest.raises(TimeoutError):
        h.run_skill(request(w, h))
    assert h.jobs.jobs["s1"].state == "unknown"
    assert h.jobs.owners and h.metrics()["faulted"]
    assert not h._mutex.locked()


def test_journal_failure_before_dispatch_prevents_motion():
    w, h = policy_only()
    def emit(kind, body):
        if kind == "phase_start":
            raise OSError("journal unavailable")
    h.emit = emit
    with pytest.raises(OSError):
        h.run_skill(request(w, h))
    assert not w.commands


def test_cancellation_and_epoch_invalidation_prevent_following_phase():
    for mode in ("cancel", "epoch"):
        w = FixtureWorld()
        h = w.executor()
        old = h.backends[Regime.NAVIGATE]
        def execute(*args):
            result = old.execute(*args)
            if mode == "cancel":
                h.cancel()
            else:
                h.jobs.invalidate_goal()
            return result
        h.backends[Regime.NAVIGATE] = replace(old, execute=execute)
        with pytest.raises(InterruptedError):
            h.run_skill(request(w, h))
        assert not w.resets and not h.jobs.owners


def test_reentrant_executor_request_is_rejected():
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    def execute(*args):
        with pytest.raises(RuntimeError):
            h.run_skill(request(w, h, "nested"))
        return old.execute(*args)
    h.backends[Regime.POLICY] = replace(old, execute=execute)
    assert h.run_skill(request(w, h)).outcome == "completed"


def test_receipt_completion_does_not_create_world_or_task_truth():
    w, h = policy_only()
    old = h.backends[Regime.POLICY]
    def execute(*args):
        return replace(old.execute(*args), observed_predicates=("ON(radio)",))
    h.backends[Regime.POLICY] = replace(old, execute=execute)
    out = h.run_skill(request(w, h))
    assert out.observed_predicates == ()
    assert h.metrics()["benchmark_success"] == "not_claimed"


def test_baseline_does_not_require_target_visible_before_search():
    w, h = policy_only()
    p = replace(h.routes["demo"].phases[0], policy_entry="ordinary_start")
    h.routes = {"demo": Route("A", (p,))}
    assert "target_observed" not in p.required_checks("entry")
    assert "ordinary_start_or_uninterrupted_policy" in p.required_checks("entry")
    assert h.run_skill(request(w, h)).outcome == "completed"


def test_classical_route_cannot_bypass_handoff_using_baseline_gate():
    w = FixtureWorld()
    h = w.executor()
    route = h.routes["demo"]
    h.routes["demo"] = replace(route, phases=route.phases[:-1]+(replace(route.phases[-1], policy_entry="ordinary_start"),))
    with pytest.raises(PermissionError, match="handoff"):
        h.run_skill(request(w, h))
    assert not w.resets


def test_observation_time_cannot_regress_across_requests():
    w, h = policy_only()
    h.run_skill(request(w, h, "one"))
    w.steps = 0
    with pytest.raises(ValueError, match="regressed"):
        h.run_skill(request(w, h, "two"))


def test_native_recipe_skill_type_and_parent_metadata_are_preserved():
    w, h = policy_only()
    p = replace(h.routes["demo"].phases[0], native_skill_type="upstream-recipe")
    h.routes = {"demo": Route("r", (p,))}
    old = h.backends[Regime.POLICY]
    def execute(r, s, d, c):
        assert r.skill_type == "upstream-recipe"
        assert r.metadata["goal_id"] == "visible-radio"
        assert r.destination_entity == "observed-counter"
        return old.execute(r, s, d, c)
    h.backends[Regime.POLICY] = replace(old, execute=execute)
    r = request(w, h)
    r = replace(r, destination_entity="observed-counter", metadata=dict(r.metadata, goal_id="visible-radio"))
    assert h.run_skill(r).outcome == "completed"
