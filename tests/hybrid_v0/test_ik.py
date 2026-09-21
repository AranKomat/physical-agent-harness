import math

import pytest

from physical_harness.hybrid_v0.classical import JointLimits
from physical_harness.hybrid_v0.ik import Pose, solve_ik

IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)


def translation_fk(q):
    return Pose(q, IDENTITY)


def test_numeric_ik_translation_and_seed_already_reached():
    limits = JointLimits(("x", "y", "z"), (-1.,)*3, (1.,)*3, (1.,)*3, (1.,)*3)
    goal = Pose((.3, -.2, .1), IDENTITY)
    result = solve_ik(fk=translation_fk, seed=(0.,)*3, target=goal, limits=limits,
                      joint_step_limits=(.1,)*3, deadline=200, clock=lambda: 100)
    assert result.converged and result.position_error_m <= .003
    exact = solve_ik(fk=translation_fk, seed=goal.position, target=goal, limits=limits,
                     joint_step_limits=(.1,)*3, deadline=200, clock=lambda: 100)
    assert exact.converged and exact.iterations == 0 and exact.fk_calls == 1


def planar_fk(q):
    a, b = q
    angle = a+b
    c, s = math.cos(angle), math.sin(angle)
    return Pose((math.cos(a)+math.cos(angle), math.sin(a)+math.sin(angle), 0.),
                (c, -s, 0., s, c, 0., 0., 0., 1.))


def test_planar_arm_recovers_position_and_orientation():
    limits = JointLimits(("a", "b"), (-math.pi,)*2, (math.pi,)*2, (1.,)*2, (1.,)*2)
    result = solve_ik(fk=planar_fk, seed=(.1, -.1), target=planar_fk((.6, -.9)),
                      limits=limits, joint_step_limits=(.2, .2), deadline=200, clock=lambda: 100)
    assert result.converged and result.orientation_error_rad <= .02


@pytest.mark.parametrize("angle", [1.2, math.pi-.000001, math.pi])
def test_rotation_log_handles_large_angle_and_pi(angle):
    def fk(q):
        c, s = math.cos(q[0]), math.sin(q[0])
        return Pose((0., 0., 0.), (c, -s, 0., s, c, 0., 0., 0., 1.))
    lim = JointLimits(("yaw",), (-3.2,), (3.2,), (1.,), (1.,))
    result = solve_ik(fk=fk, seed=(0.,), target=fk((angle,)), limits=lim,
                      joint_step_limits=(.2,), deadline=200, clock=lambda: 100)
    assert result.converged


def test_unreachable_target_is_not_reported_as_converged():
    lim = JointLimits(("x", "y", "z"), (-1.,)*3, (1.,)*3, (1.,)*3, (1.,)*3)
    result = solve_ik(fk=translation_fk, seed=(0.,)*3, target=Pose((4., 0., 0.), IDENTITY),
                      limits=lim, joint_step_limits=(.1,)*3, deadline=200, clock=lambda: 100)
    assert not result.converged and result.position_error_m > 2
    assert all(-1 <= q <= 1 for q in result.joints)


def test_iteration_limit_is_explicit():
    lim = JointLimits(("x", "y", "z"), (-1.,)*3, (1.,)*3, (1.,)*3, (1.,)*3)
    result = solve_ik(fk=translation_fk, seed=(0.,)*3, target=Pose((.5, 0., 0.), IDENTITY),
                      limits=lim, joint_step_limits=(.01,)*3, deadline=200, clock=lambda: 100,
                      max_iterations=1)
    assert not result.converged and result.reason == "iteration_limit"


@pytest.mark.parametrize("kind", ["deadline", "cancellation"])
def test_ik_budget_guard_prevents_fk(kind):
    def fk(q):
        raise AssertionError("Must not call FK")
    lim = JointLimits(("x",), (-1.,), (1.,), (1.,), (1.,))
    expected = TimeoutError if kind == "deadline" else InterruptedError
    with pytest.raises(expected):
        solve_ik(fk=fk, seed=(0.,), target=Pose((0.,)*3, IDENTITY), limits=lim,
                 joint_step_limits=(.1,), deadline=50 if kind == "deadline" else 200,
                 clock=lambda: 100, cancelled=lambda: kind == "cancellation")


def test_reflection_is_not_a_rotation():
    with pytest.raises(ValueError, match="proper"):
        Pose((0., 0., 0.), (-1., 0., 0., 0., 1., 0., 0., 0., 1.))


def test_bad_fk_output_is_rejected():
    lim = JointLimits(("x",), (-1.,), (1.,), (1.,), (1.,))
    with pytest.raises(ValueError):
        solve_ik(fk=lambda q: {"pose": (0.,)*3}, seed=(0.,), target=Pose((0.,)*3, IDENTITY),
                 limits=lim, joint_step_limits=(.1,), deadline=200, clock=lambda: 100)
