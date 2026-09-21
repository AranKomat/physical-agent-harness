"""Closed-loop bounded Cartesian segments over reviewed native IK/step ports.

Not an impedance/force controller, obstacle planner, or hardware safety layer.
Contact strokes require an independent legal sensor monitor
unknown is a stop.
Every command is rechecked against the FULL robot swept path and carried object.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .runtime import StepReceipt
from .types import Basis, Pose, Primitive, number, vector


def _axis_angle(rotation):
    angle = math.acos(float(np.clip((np.trace(rotation)-1)*.5, -1, 1)))
    if angle < 1e-8:
        return np.array([1., 0., 0.]), 0.
    if math.pi-angle < 1e-5:
        values, vectors = np.linalg.eig(rotation)
        axis = np.real(vectors[:, int(np.argmin(np.abs(values-1)))])
        axis /= np.linalg.norm(axis)
        # Deterministic sign; either direction is valid exactly at pi.
        k = int(np.argmax(np.abs(axis)))
        if axis[k] < 0:
            axis = -axis
        return axis, angle
    axis = np.array([rotation[2, 1]-rotation[1, 2], rotation[0, 2]-rotation[2, 0],
                     rotation[1, 0]-rotation[0, 1]])/(2*math.sin(angle))
    return axis, angle


def pose_error(a: Pose, b: Pose):
    if a.frame != b.frame:
        raise ValueError("Cartesian poses must share a frame")
    ra, rb = (np.asarray(p.matrix).reshape(4, 4)[:3, :3] for p in (a, b))
    return math.dist(a.xyz, b.xyz), _axis_angle(rb @ ra.T)[1]


def bounded_pose_step(current: Pose, target: Pose, *, max_translation_m: float,
                      max_rotation_rad: float) -> Pose:
    """Bounded SE(3) reference step; actual native rates still need qualification."""
    number(max_translation_m, low=.00000001)
    number(max_rotation_rad, low=.00000001, high=math.pi)
    pose_error(current, target)
    a, b = (np.asarray(p.matrix).reshape(4, 4) for p in (current, target))
    delta = b[:3, 3]-a[:3, 3]
    distance = np.linalg.norm(delta)
    result = a.copy()
    result[:3, 3] += delta*min(1., max_translation_m/max(float(distance), 1e-12))
    axis, angle = _axis_angle(b[:3, :3] @ a[:3, :3].T)
    step = min(angle, max_rotation_rad)
    x, y, z = axis
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    rot = np.eye(3)+math.sin(step)*skew+(1-math.cos(step))*(skew@skew)
    result[:3, :3] = rot@a[:3, :3]
    return Pose(current.frame, tuple(float(v) for v in result.ravel()))


@dataclass(frozen=True)
class CartesianPort:
    tcp: Callable  # legal robot-only FK from measured proprioception -> Pose
    solve_ik: Callable  # (pose, current_basis, deadline) -> named-joint tuple
    collision_clear: Callable  # full swept current->joint-goal incl payload -> bool/None
    encode: Callable  # audited complete native vector, including untouched-axis holds
    validate_action: Callable
    step: Callable  # exactly one counted simulator tick -> Basis
    settled: Callable  # measured speeds/tolerances -> bool/None
    contact_monitor: Callable  # (program, index, current) -> bool/None
    stop: Callable  # no uncounted steps, measured stop acknowledgement
    action_dimensions: int = 23
    control_dt: float = 1/30


class CartesianExecutor:
    """A usable MOVE_EEF / guarded PRESS / prismatic PULL numerical executor.

    `contact_monitor` must validate the planned contact corridor and detect
    adverse contact, slip or tracking failure throughout the stroke. True does
    not mean semantic success. Fixed travel alone never proves radio activation.
    """
    def __init__(self, port: CartesianPort, *, position_tolerance_m=.002,
                 orientation_tolerance_rad=.02, angular_speed_rad_s=.2,
                 settle_samples=3, max_age_s=2., clock=time.monotonic):
        from .types import integer
        self.port, self.clock = port, clock
        self.position_tol = number(position_tolerance_m, low=.000001)
        self.orientation_tol = number(orientation_tolerance_rad, low=.000001)
        self.angular_speed = number(angular_speed_rad_s, low=.000001)
        self.settle_samples = integer(settle_samples, low=1, high=100)
        self.max_age = number(max_age_s, low=.001)
        number(port.control_dt, low=.000001)
        integer(port.action_dimensions, low=1, high=256)

    def __call__(self, program, index, before, deadline, cancelled):
        step = program.steps[index]
        if step.kind not in {Primitive.MOVE_EEF, Primitive.PRESS, Primitive.PULL}:
            raise ValueError("CartesianExecutor cannot run this primitive")
        target = step.end_pose if step.kind in {Primitive.PRESS, Primitive.PULL} else step.pose
        current, count, stable = before, 0, 0
        # Contact starts from the guarded precontact region and proceeds only
        # along its approved line. The monitor validates alignment/approach.
        while True:
            if cancelled():
                raise InterruptedError("Cartesian segment cancelled")
            if self.clock() >= deadline:
                raise TimeoutError("Cartesian segment deadline")
            current.fresh(self.clock(), self.max_age)
            actual = self.port.tcp(current)
            distance, angle = pose_error(actual, target)
            reached = distance <= self.position_tol and angle <= self.orientation_tol
            if step.kind in {Primitive.PRESS, Primitive.PULL}:
                if self.port.contact_monitor(program, index, current) is not True:
                    raise PermissionError("Contact monitor failed or is unknown")
                # No lateral shortcut around an obstacle while maintaining a press label.
                origin = np.asarray(step.pose.xyz)
                direction = np.asarray(program.proposal.parameters.direction)
                delta = np.asarray(actual.xyz)-origin
                lateral = np.linalg.norm(delta-direction*float(delta@direction))
                if lateral > self.position_tol*2:
                    raise PermissionError("TCP left the approved linear contact corridor")
            if reached and self.port.settled(current) is True:
                stable += 1
            else:
                stable = 0
            if stable >= self.settle_samples or count >= step.max_steps:
                break
            reference = target if reached else bounded_pose_step(
                actual, target, max_translation_m=step.max_speed_m_s*self.port.control_dt,
                max_rotation_rad=self.angular_speed*self.port.control_dt)
            q = self.port.solve_ik(reference, current, deadline)
            if self.port.collision_clear(current, q, program, index) is not True:
                raise PermissionError("Full swept collision clearance missing")
            action = self.port.encode(q, current)
            vector(action, self.port.action_dimensions, "full native action")
            if self.port.validate_action(action) is not True:
                raise PermissionError("Native action codec rejected the command")
            if cancelled() or self.clock() >= deadline:
                raise InterruptedError("Cancelled/expired before Cartesian dispatch")
            current.fresh(self.clock(), self.max_age)
            following = self.port.step(action, deadline)
            if not isinstance(following, Basis):
                raise ValueError("Native step did not return legal evidence")
            current.require_continuity(following)
            if following.observation_id == current.observation_id or abs(
                following.sim_time-current.sim_time-self.port.control_dt
            ) > 1e-6:
                raise ValueError("Native tick/evidence count mismatch")
            current = following
            count += 1
        end_pose = self.port.tcp(current)
        distance, angle = pose_error(end_pose, target)
        reached = distance <= self.position_tol and angle <= self.orientation_tol and stable >= self.settle_samples
        stopped = self.port.stop(deadline) is True and self.clock() <= deadline
        return StepReceipt(program.fingerprint, index, before, current,
                           "completed" if reached else "stalled", count, 0, 0,
                           stopped, current.evidence_ids)
