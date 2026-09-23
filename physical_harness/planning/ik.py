"""Optional bounded numerical IK over an injected, robot-only FK function.

NumPy is imported lazily (already in the repository's dev/localization extras).
This module never reads a simulator, generates native actions or certifies
collision safety. Convergence is only a kinematic candidate for the staging gate.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable

from physical_harness.core.handoff import integer, real
from physical_harness.execution.handoff.classical import JointLimits, vector


@dataclass(frozen=True)
class Pose:
    """Translation in metres and row-major proper rotation in one known frame."""
    position: tuple[float, float, float]
    rotation: tuple[float, ...]

    def __post_init__(self):
        vector(self.position, "pose position", 3)
        vector(self.rotation, "pose rotation", 9)
        r = tuple(self.rotation[i:i+3] for i in (0, 3, 6))
        for i in range(3):
            for j in range(3):
                if abs(sum(r[i][k]*r[j][k] for k in range(3)) - (i == j)) > 1e-5:
                    raise ValueError("Pose rotation is not orthonormal")
        a, b, c = r
        determinant = a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
        if abs(determinant-1) > 1e-5:
            raise ValueError("Pose rotation must be proper")


@dataclass(frozen=True)
class IKResult:
    joints: tuple[float, ...]
    converged: bool
    position_error_m: float
    orientation_error_rad: float
    iterations: int
    fk_calls: int
    reason: str


def _rotation_log(rotation, np):
    cosine = max(-1., min(1., float((np.trace(rotation)-1)/2)))
    angle = math.acos(cosine)
    skew = np.array([rotation[2, 1]-rotation[1, 2], rotation[0, 2]-rotation[2, 0],
                     rotation[1, 0]-rotation[0, 1]])
    if angle < 1e-7:
        return .5*skew
    if math.pi-angle < 1e-5:
        # At pi, skew/sin(angle) is ill-conditioned. The rotation axis has
        # eigenvalue +1 in the symmetric part; sign is immaterial at exact pi.
        _, eigenvectors = np.linalg.eigh((rotation+rotation.T)/2)
        axis = eigenvectors[:, -1]
        if float(axis @ skew) < 0:
            axis = -axis
        return angle*axis
    return angle/(2*math.sin(angle))*skew


def solve_ik(*, fk: Callable[[tuple[float, ...]], Pose], seed: tuple[float, ...],
             target: Pose, limits: JointLimits, joint_step_limits: tuple[float, ...],
             deadline: float, clock: Callable[[], float] = time.monotonic,
             cancelled: Callable[[], bool] = lambda: False,
             max_iterations: int = 80, position_tolerance_m: float = .003,
             orientation_tolerance_rad: float = .02, damping: float = .01,
             orientation_weight_m_per_rad: float = .1, finite_difference_fraction: float = 1e-5
             ) -> IKResult:
    """Damped least squares + bounded per-joint steps and descending line search.

    FK uses JointLimits.names ordering and the SAME metric frame as target.
    joint_step_limits are explicit in each joint's own units (rad or metres);
    there is no inferred mapping from 61D proprioception or the 23D action.
    The seed should be the measured current posture. Joint limits are applied
    to IK search variables, NOT by clipping neural policy/native actions.

    FK/target/collision/frame qualification belongs to the private adapter. A
    callback must bound its own execution; the deadline is checked around every
    FK call but cannot forcibly interrupt an in-flight native function.
    """
    import numpy as np

    if not callable(fk) or not callable(clock) or not callable(cancelled):
        raise ValueError("FK/clock/cancellation callbacks required")
    if not isinstance(target, Pose) or not isinstance(limits, JointLimits):
        raise ValueError("Typed target and joint limits required")
    limits.require(seed)
    vector(joint_step_limits, n=len(seed))
    if any(v <= 0 for v in joint_step_limits):
        raise ValueError("Positive per-joint search step limits required")
    integer(max_iterations, minimum=1)
    if max_iterations > 1000:
        raise ValueError("IK iteration budget too large for the bounded helper")
    real(deadline, "deadline")
    for name, value in (("position tolerance", position_tolerance_m),
                        ("orientation tolerance", orientation_tolerance_rad),
                        ("damping", damping), ("orientation weight", orientation_weight_m_per_rad)):
        real(value, name, .000000001)
    real(finite_difference_fraction, "finite difference fraction", 1e-9, .01)
    lower, upper = np.array(limits.lower), np.array(limits.upper)
    # Normalize parameter columns by the caller's per-joint step units.
    scale = np.array(joint_step_limits)
    epsilon = np.maximum((upper-lower)*finite_difference_fraction, 1e-9)
    goal_p, goal_r = np.array(target.position), np.array(target.rotation).reshape(3, 3)
    q = np.array(seed, dtype=float)
    calls = 0

    def checkpoint():
        if cancelled():
            raise InterruptedError("IK cancelled")
        if clock() >= deadline:
            raise TimeoutError("IK budget exhausted")

    def evaluate(values):
        nonlocal calls
        checkpoint()
        pose = fk(tuple(float(x) for x in values))
        calls += 1
        checkpoint()
        if not isinstance(pose, Pose):
            raise ValueError("FK must return a validated Pose")
        return np.array(pose.position), np.array(pose.rotation).reshape(3, 3)

    def error(p, r):
        dp, dr = goal_p-p, _rotation_log(goal_r @ r.T, np)
        return np.concatenate((dp, orientation_weight_m_per_rad*dr)), float(np.linalg.norm(dp)), float(np.linalg.norm(dr))

    def result(iterations, reason):
        return IKResult(tuple(float(x) for x in q), reason == "converged", pos_err, angle_err,
                        iterations, calls, reason)

    current_p, current_r = evaluate(q)
    residual, pos_err, angle_err = error(current_p, current_r)
    for iteration in range(max_iterations+1):
        checkpoint()
        if pos_err <= position_tolerance_m and angle_err <= orientation_tolerance_rad:
            return result(iteration, "converged")
        if iteration == max_iterations:
            return result(iteration, "iteration_limit")
        jacobian = np.empty((6, len(q)))
        for j in range(len(q)):
            plus, minus = q.copy(), q.copy()
            plus[j] = min(upper[j], q[j]+epsilon[j])
            minus[j] = max(lower[j], q[j]-epsilon[j])
            width = plus[j]-minus[j]
            pp, rp = evaluate(plus)
            pm, rm = evaluate(minus)
            jacobian[:3, j] = (pp-pm)/width
            jacobian[3:, j] = orientation_weight_m_per_rad*_rotation_log(rp @ rm.T, np)/width
        normalized = jacobian*scale
        direction = normalized.T @ np.linalg.solve(normalized @ normalized.T + damping*damping*np.eye(6), residual)
        largest = float(np.max(np.abs(direction)))
        if largest > 1:
            direction /= largest
        delta = scale*direction
        baseline = float(residual @ residual)
        improved = False
        for alpha in (1., .5, .25, .125, .0625, .03125):
            candidate = np.clip(q+alpha*delta, lower, upper)
            if float(np.max(np.abs(candidate-q))) < 1e-12:
                continue
            p, r = evaluate(candidate)
            new_error, pe, ae = error(p, r)
            if float(new_error @ new_error) < baseline-1e-14:
                q, current_p, current_r = candidate, p, r
                residual, pos_err, angle_err = new_error, pe, ae
                improved = True
                break
        if not improved:
            return result(iteration+1, "stalled_or_singular")
    raise AssertionError("Unreachable IK loop exit")
