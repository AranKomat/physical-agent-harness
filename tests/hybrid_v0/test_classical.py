import math
from dataclasses import replace

import pytest

from physical_harness.contracts import SkillRequest
from physical_harness.hybrid_v0.classical import (
    BasePose,
    HolonomicNavigation,
    JointLimits,
    JointTransit,
    StepPort,
    holonomic_step,
    quintic_transit,
)
from physical_harness.hybrid_v0.fixture import FixtureWorld


def limits():
    return JointLimits(("j1", "j2"), (-2., -2.), (2., 2.), (.5, .4), (1., 1.))


def port(world):
    return StepPort(world.step, world.stop, lambda a: len(a) == 23, clock=world.clock)


def req(max_steps=200):
    return SkillRequest("s", "stage", "observed target", ("target",),
                        metadata={"max_action_steps": max_steps})


def test_quintic_reaches_exact_endpoint_and_respects_discrete_rates():
    q0, q1, lim, dt = (0., 0.), (.8, -.5), limits(), 1/30
    path = quintic_transit(q0, q1, lim, dt=dt, max_steps=600, swept_clear=lambda a, b: True)
    assert path[-1] == q1
    positions = (q0,)+path+(q1,)
    velocities = [tuple((b-a)/dt for a, b in zip(p, q)) for p, q in zip(positions, positions[1:])]
    for v in velocities:
        assert all(abs(x) <= maximum+1e-9 for x, maximum in zip(v, lim.velocity))
    for v0, v1 in zip(velocities, velocities[1:]):
        assert all(abs(b-a)/dt <= maximum+1e-9 for a, b, maximum in zip(v0, v1, lim.acceleration))


@pytest.mark.parametrize("clear", [None, False, 1])
def test_unknown_or_truthy_collision_rejected(clear):
    with pytest.raises(PermissionError):
        quintic_transit((0., 0.), (.1, .1), limits(), swept_clear=lambda a, b: clear)


def test_stationary_configuration_still_needs_clearance():
    assert quintic_transit((0., 0.), (0., 0.), limits(), swept_clear=lambda a, b: True) == ()
    with pytest.raises(PermissionError):
        quintic_transit((0., 0.), (0., 0.), limits(), swept_clear=lambda a, b: None)


def test_budget_cannot_be_met_by_speeding_up_trajectory():
    with pytest.raises(ValueError):
        quintic_transit((0., 0.), (1., 1.), limits(), max_steps=1, swept_clear=lambda a, b: True)


def test_swept_edges_are_checked_not_just_endpoint():
    seen = []
    def swept(a, b):
        seen.append((a, b))
        return not (a[0] <= .05 < b[0])
    with pytest.raises(PermissionError):
        quintic_transit((0., 0.), (.1, .1), limits(), swept_clear=swept)
    assert len(seen) > 1


@pytest.mark.parametrize("q", [(9., 0.), (float("nan"), 0.), (True, 0.), [0, 0], (0.,)])
def test_joint_validation(q):
    with pytest.raises(ValueError):
        quintic_transit(q, (.1, .1), limits(), swept_clear=lambda a, b: True)


def test_local_map_error_rotated_to_base_frame():
    v = holonomic_step(BasePose(0, 0, math.pi/2), BasePose(1, 0, math.pi/2), linear_speed=.1)
    assert v.vx == pytest.approx(0, abs=1e-9)
    assert v.vy == pytest.approx(-.1)


def test_twist_speed_norm_and_yaw_bounds():
    v = holonomic_step(BasePose(0, 0, 0), BasePose(100, 100, math.pi), linear_speed=.2, angular_speed=.3)
    assert math.hypot(v.vx, v.vy) == pytest.approx(.2)
    assert abs(v.wz) <= .3


def test_yaw_wrap_chooses_short_turn():
    v = holonomic_step(BasePose(0, 0, math.pi-.01), BasePose(0, 0, -math.pi+.01))
    assert v.wz == pytest.approx(.02)


def test_joint_transit_executes_with_full_native_vector():
    w = FixtureWorld()
    executor = JointTransit(port(w), limits(), joints=lambda s: w.q, target=lambda r, s: (.1, -.1),
                            encode=w.encode_joints, safe=lambda *a: True,
                            tracking_tolerance=(.05, .05), endpoint_tolerance=(.001, .001))
    out = executor(req(), w.snapshot(), 200, lambda: False)
    assert out.outcome == "completed" and out.policy_calls == 0
    assert out.sim_time_end == pytest.approx(out.action_steps_executed/30)
    assert out.metadata["stop_acknowledged"] is True
    assert all(len(a) == 23 for a in w.commands)


def test_joint_following_error_aborts_and_stops():
    w = FixtureWorld()
    p = replace(port(w), step=lambda a, d: w.step((1., 1.)+(0.,)*21, d))
    exe = JointTransit(p, limits(), joints=lambda s: w.q, target=lambda r, s: (.1, .1),
                       encode=w.encode_joints, safe=lambda *a: True,
                       tracking_tolerance=(.01, .01), endpoint_tolerance=(.001, .001))
    with pytest.raises(RuntimeError):
        exe(req(), w.snapshot(), 200, lambda: False)
    assert w.stop_count == 1


def test_updated_collision_geometry_blocks_next_joint_step():
    w = FixtureWorld()
    exe = JointTransit(port(w), limits(), joints=lambda s: w.q, target=lambda r, s: (.1, .1),
                       encode=w.encode_joints, safe=lambda s, a, b: True if s.sim_time == 0 else None,
                       tracking_tolerance=(.05, .05), endpoint_tolerance=(.001, .001))
    with pytest.raises(PermissionError):
        exe(req(), w.snapshot(), 200, lambda: False)
    assert len(w.commands) == 1 and w.stop_count == 1


def test_base_unknown_corridor_has_zero_commands():
    w = FixtureWorld()
    nav = HolonomicNavigation(port(w), pose=lambda s: w.pose,
                              resolve=lambda r, s: (BasePose(1, 0, 0),),
                              encode=w.encode_twist, safe=lambda *a: None)
    with pytest.raises(PermissionError):
        nav(req(), w.snapshot(), 200, lambda: False)
    assert not w.commands and w.stop_count == 1


def test_base_action_budget_returns_stalled_not_arrived():
    w = FixtureWorld()
    nav = HolonomicNavigation(port(w), pose=lambda s: w.pose,
                              resolve=lambda r, s: (BasePose(1, 0, 0),),
                              encode=w.encode_twist, safe=lambda *a: True)
    out = nav(req(3), w.snapshot(), 200, lambda: False)
    assert out.outcome == "stalled" and out.action_steps_executed == 3


def test_base_blocked_tracking_stalls_before_budget():
    w = FixtureWorld()
    # The command is accepted by transport but physical position does not advance.
    p = replace(port(w), step=lambda a, d: w.step((0.,)*23, d))
    nav = HolonomicNavigation(p, pose=lambda s: w.pose,
                              resolve=lambda r, s: (BasePose(1, 0, 0),),
                              encode=w.encode_twist, safe=lambda *a: True, max_stall_steps=3)
    out = nav(req(100), w.snapshot(), 200, lambda: False)
    assert out.outcome == "stalled" and out.action_steps_executed < 100


def test_waypoint_follower_does_not_call_policy():
    w = FixtureWorld()
    nav = HolonomicNavigation(port(w), pose=lambda s: w.pose,
                              resolve=lambda r, s: (BasePose(.015, 0, 0), BasePose(.025, 0, 0)),
                              encode=w.encode_twist, safe=lambda *a: True, tolerance_m=.005)
    out = nav(req(), w.snapshot(), 200, lambda: False)
    assert out.outcome == "completed" and out.chunks_generated == out.policy_calls == 0


@pytest.mark.parametrize("action", [(0.,)*22, (0.,)*24, (float("nan"),)+(0.,)*22, [0.]*23])
def test_step_port_never_pads_or_clips_action(action):
    w = FixtureWorld()
    with pytest.raises(ValueError):
        port(w).apply(action, w.snapshot(), 200, lambda: False)
    assert not w.commands


def test_step_port_native_validation_has_final_authority():
    w = FixtureWorld()
    p = replace(port(w), validate_action=lambda a: False)
    with pytest.raises(PermissionError):
        p.apply((0.,)*23, w.snapshot(), 200, lambda: False)
    assert not w.commands


def test_step_port_cancellation_before_send():
    w = FixtureWorld()
    with pytest.raises(InterruptedError):
        port(w).apply((0.,)*23, w.snapshot(), 200, lambda: True)
    assert not w.commands


def test_wrong_simulator_timestep_is_not_silently_accepted():
    w = FixtureWorld()
    p = replace(port(w), dt=.1)
    with pytest.raises(ValueError):
        p.apply((0.,)*23, w.snapshot(), 200, lambda: False)


def test_stale_step_response_aborts():
    w = FixtureWorld()
    p = replace(port(w), step=lambda a, d: w.snapshot())
    with pytest.raises(ValueError):
        p.apply((0.,)*23, w.snapshot(), 200, lambda: False)
