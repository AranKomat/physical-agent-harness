"""Small, executable classical controllers; no simulator or learned policy import.

These are conservative LOCAL methods, not global navigation, obstacle avoidance,
IK or a certified collision engine. Connect them to already qualified perception,
FK/IK, full-robot swept collision checks and an audited native action codec.
Unknown collision space is rejected, never assumed empty.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable

from ..contracts import SkillReceipt, SkillRequest
from .contracts import Snapshot, identifiers, integer, real


def vector(values, name="vector", n=None):
    if not isinstance(values, tuple) or not values or (n is not None and len(values) != n):
        raise ValueError(f"Immutable {name} with correct width required")
    for x in values:
        real(x, name, -math.inf)
    return values


@dataclass(frozen=True)
class JointLimits:
    names: tuple[str, ...]
    lower: tuple[float, ...]
    upper: tuple[float, ...]
    velocity: tuple[float, ...]
    acceleration: tuple[float, ...]

    def __post_init__(self):
        identifiers(self.names)
        if not self.names:
            raise ValueError("Named joints required")
        for value in (self.lower, self.upper, self.velocity, self.acceleration):
            vector(value, n=len(self.names))
        for lo, hi, speed, accel in zip(self.lower, self.upper, self.velocity, self.acceleration):
            if lo >= hi or speed <= 0 or accel <= 0:
                raise ValueError("Invalid joint bounds or rate limits")

    def require(self, q):
        vector(q, n=len(self.names))
        if any(not lo <= value <= hi for value, lo, hi in zip(q, self.lower, self.upper)):
            raise ValueError("Joint target outside limits")


def quintic_transit(start, goal, limits: JointLimits, *, dt=1/30, max_steps=600,
                    swept_clear: Callable[[tuple, tuple], bool | None]):
    """Rest-to-rest joint-space interpolation with velocity/acceleration bounds.

    Samples EXCLUDE the starting pose. swept_clear must check the FULL robot's
    swept motion between joint states, including attached objects. Checking only
    the endpoint is insufficient. A non-straight obstacle route needs an external
    planner; this function refuses it rather than tunnelling through the obstacle.
    """
    limits.require(start)
    limits.require(goal)
    dt = real(dt, "dt", .000001)
    integer(max_steps, minimum=1)
    delta = tuple(b-a for a, b in zip(start, goal))
    if all(abs(d) <= 1e-12 for d in delta):
        if swept_clear(start, goal) is not True:
            raise PermissionError("Stationary configuration is not collision-cleared")
        return ()
    # For s(u)=10u^3-15u^4+6u^5: max s'=1.875; max |s''|=10/sqrt(3).
    duration = max([dt] + [1.875*abs(d)/v for d, v in zip(delta, limits.velocity)]
                   + [math.sqrt((10/math.sqrt(3))*abs(d)/a)
                      for d, a in zip(delta, limits.acceleration)])
    count = math.ceil(duration/dt)
    if count > max_steps:
        raise ValueError("Transit cannot fit the action budget at configured joint limits")
    points = []
    previous = start
    for k in range(1, count+1):
        u = k/count
        s = u*u*u*(10 + u*(-15 + 6*u))
        q = goal if k == count else tuple(a+s*d for a, d in zip(start, delta))
        limits.require(q)
        if swept_clear(previous, q) is not True:
            raise PermissionError("Swept collision clearance missing; do not execute")
        points.append(q)
        previous = q
    return tuple(points)


@dataclass(frozen=True)
class BasePose:
    x: float
    y: float
    yaw: float

    def __post_init__(self):
        for x in (self.x, self.y, self.yaw):
            real(x, low=-math.inf)


@dataclass(frozen=True)
class BodyTwist:
    vx: float
    vy: float
    wz: float

    def __post_init__(self):
        for x in (self.vx, self.vy, self.wz):
            real(x, low=-math.inf)


def wrap_angle(x):
    return math.atan2(math.sin(x), math.cos(x))


def holonomic_step(pose: BasePose, goal: BasePose, *, linear_speed=.1, angular_speed=.25,
                   gain=1.0) -> BodyTwist:
    """Local-map error -> body-frame m/s and rad/s (NOT a 23D native action).

    Intended for a short qualified staging corridor. It is not a global route
    planner; feed waypoints from the existing sensor-derived occupancy planner.
    """
    speed = real(linear_speed, "linear speed", .000001)
    angular = real(angular_speed, "angular speed", .000001)
    gain = real(gain, "gain", .000001)
    dx, dy = (goal.x-pose.x)*gain, (goal.y-pose.y)*gain
    length = math.hypot(dx, dy)
    if length > speed:
        dx, dy = dx*speed/length, dy*speed/length
    c, s = math.cos(pose.yaw), math.sin(pose.yaw)
    return BodyTwist(c*dx+s*dy, -s*dx+c*dy,
                     max(-angular, min(angular, gain*wrap_angle(goal.yaw-pose.yaw))))


@dataclass(frozen=True)
class StepPort:
    """The private driver owns native units, indices, absolute holds and saturation.

    step must run exactly ONE simulator controller tick and return legal sensors.
    validate_action checks the entire native action without rewriting it. It may
    return True for documented native saturation, but must never globally clip
    absolute joint/torso channels. These callbacks must enforce their deadline.
    """
    step: Callable[[tuple[float, ...], float], Snapshot]
    stop: Callable[[float], bool]
    validate_action: Callable[[tuple[float, ...]], bool]
    action_dimensions: int = 23
    dt: float = 1/30
    max_observation_age_s: float = 2.0
    clock: Callable[[], float] = time.monotonic

    def __post_init__(self):
        integer(self.action_dimensions, minimum=1)
        real(self.dt, "dt", .000001)
        real(self.max_observation_age_s, "observation age", .001)
        if not all(callable(c) for c in (self.step, self.stop, self.validate_action, self.clock)):
            raise ValueError("StepPort requires reviewed callbacks")

    def check(self, snapshot, deadline, cancelled):
        if cancelled():
            raise InterruptedError("Classical execution cancelled")
        if self.clock() >= deadline:
            raise TimeoutError("Classical execution deadline")
        if not 0 <= self.clock()-snapshot.captured_wall <= self.max_observation_age_s:
            raise ValueError("Stale classical observation")

    def apply(self, action, previous, deadline, cancelled):
        self.check(previous, deadline, cancelled)
        vector(action, "native action", self.action_dimensions)
        if self.validate_action(action) is not True:
            raise PermissionError("Native action validation failed")
        self.check(previous, deadline, cancelled)
        after = self.step(action, deadline)
        if not isinstance(after, Snapshot) or after.episode != previous.episode:
            raise ValueError("Native step returned foreign sensors")
        if after.observation_id == previous.observation_id:
            raise ValueError("Native action returned old evidence")
        if abs(after.sim_time-previous.sim_time-self.dt) > 1e-6:
            raise ValueError("Native step did not advance exactly one controller tick")
        if after.frame_epoch != previous.frame_epoch:
            raise ValueError("Localization reset during classical motion")
        self.check(after, deadline, cancelled)
        return after


def _receipt(request, start, end, steps, stop_ack, outcome, reason=None):
    return SkillReceipt(request.skill_id, "classical-local-v0", outcome,
                        start.sim_time, end.sim_time, action_steps_executed=steps,
                        failure_reason=reason,
                        metadata={"episode_id": start.episode,
                                  "execution_epoch": request.execution_epoch,
                                  "stop_acknowledged": stop_ack})


class JointTransit:
    """Executable rest-to-rest staging, using audited named-joint/native codecs.

    target(request, snapshot) must derive its goal from current allowed sensors
    and qualified robot-only FK/IK. It must not read a simulator object pose.
    encode(q, snapshot) must HOLD non-owned axes in their real command convention.
    safe(snapshot, from_q, to_q) rechecks full swept collision AND carried payload.
    No IK solver, collision model, or endpoint-success proof is fabricated here.
    """
    def __init__(self, port: StepPort, limits: JointLimits, *, joints, target, encode,
                 safe, tracking_tolerance: tuple[float, ...], endpoint_tolerance: tuple[float, ...]):
        self.port, self.limits = port, limits
        self.joints, self.target, self.encode, self.safe = joints, target, encode, safe
        for v in (tracking_tolerance, endpoint_tolerance):
            vector(v, n=len(limits.names))
            if any(x <= 0 for x in v):
                raise ValueError("Positive measured-error tolerances required")
        self.tracking, self.endpoint = tracking_tolerance, endpoint_tolerance

    def __call__(self, request: SkillRequest, start: Snapshot, deadline, cancelled):
        self.port.check(start, deadline, cancelled)
        q0 = self.joints(start)
        goal = self.target(request, start)
        self.limits.require(q0)
        self.limits.require(goal)
        cap = integer(request.metadata["max_action_steps"], minimum=1)
        def clearance(a, b):
            self.port.check(start, deadline, cancelled)
            return self.safe(start, a, b)

        points = quintic_transit(q0, goal, self.limits, dt=self.port.dt, max_steps=cap,
                                 swept_clear=clearance)
        current, reference, count, stopped = start, q0, 0, False
        try:
            for q in points:
                self.port.check(current, deadline, cancelled)
                actual = self.joints(current)
                self.limits.require(actual)
                if any(abs(a-b) > t for a, b, t in zip(actual, reference, self.tracking)):
                    raise RuntimeError("Joint tracking departed from the validated corridor")
                if self.safe(current, actual, q) is not True:
                    raise PermissionError("Updated swept collision clearance missing")
                current = self.port.apply(self.encode(q, current), current, deadline, cancelled)
                count += 1
                reference = q
            actual = self.joints(current)
            self.limits.require(actual)
            reached = all(abs(a-b) <= t for a, b, t in zip(actual, goal, self.endpoint))
        finally:
            stopped = self.port.stop(deadline) is True and self.port.clock() <= deadline
        return _receipt(request, start, current, count, stopped,
                        "completed" if reached else "stalled",
                        None if reached else "joint_endpoint_not_reached")


class HolonomicNavigation:
    """A bounded local waypoint follower, NOT room-scale SLAM or global planning.

    resolve returns legal observed waypoints in the current local_map frame.
    safe(snapshot, twist, dt) must include stopping distance, unknown/occupied
    space, robot footprint, torso/arms and any carried object. A planner timeout
    or an unknown clearance result aborts instead of waking a VLA blindly.
    """
    def __init__(self, port: StepPort, *, pose, resolve, encode, safe,
                 linear_speed=.1, angular_speed=.25, tolerance_m=.03, tolerance_rad=.04,
                 max_stall_steps=60, progress_epsilon_m=.0001):
        self.port, self.pose, self.resolve, self.encode, self.safe = port, pose, resolve, encode, safe
        self.speed = real(linear_speed, "speed", .000001)
        self.angular = real(angular_speed, "angular", .000001)
        self.tolerance = real(tolerance_m, "tolerance_m", .000001)
        self.yaw_tolerance = real(tolerance_rad, "tolerance_rad", .000001)
        self.stall_limit = integer(max_stall_steps, minimum=1)
        self.epsilon = real(progress_epsilon_m, "progress_epsilon", .00000001)

    def __call__(self, request, start, deadline, cancelled):
        self.port.check(start, deadline, cancelled)
        route = self.resolve(request, start)
        if not isinstance(route, tuple) or not 1 <= len(route) <= 256 or not all(isinstance(p, BasePose) for p in route):
            raise ValueError("A bounded, observed local waypoint route is required")
        cap = integer(request.metadata["max_action_steps"], minimum=1)
        current, count, index, stalled = start, 0, 0, 0
        best = math.inf
        stopped = False
        try:
            while index < len(route) and count < cap:
                self.port.check(current, deadline, cancelled)
                p = self.pose(current)
                if not isinstance(p, BasePose):
                    raise ValueError("Legal estimated base pose required")
                goal = route[index]
                distance = math.hypot(goal.x-p.x, goal.y-p.y)
                angle = abs(wrap_angle(goal.yaw-p.yaw))
                if distance <= self.tolerance and angle <= self.yaw_tolerance:
                    index += 1
                    best, stalled = math.inf, 0
                    continue
                # Scale yaw error into a distance-like score only for stall detection.
                score = distance + self.tolerance/self.yaw_tolerance*angle
                if score < best-self.epsilon:
                    best, stalled = score, 0
                else:
                    stalled += 1
                if stalled >= self.stall_limit:
                    break
                command = holonomic_step(p, goal, linear_speed=self.speed, angular_speed=self.angular)
                if self.safe(current, command, self.port.dt) is not True:
                    raise PermissionError("Local navigation clearance unknown or blocked")
                current = self.port.apply(self.encode(command, current), current, deadline, cancelled)
                count += 1
            # Check terminal geometry even when the final step exhausted the cap.
            while index < len(route):
                p, goal = self.pose(current), route[index]
                if math.hypot(goal.x-p.x, goal.y-p.y) > self.tolerance or abs(wrap_angle(goal.yaw-p.yaw)) > self.yaw_tolerance:
                    break
                index += 1
        finally:
            stopped = self.port.stop(deadline) is True and self.port.clock() <= deadline
        return _receipt(request, start, current, count, stopped,
                        "completed" if index == len(route) else "stalled",
                        None if index == len(route) else "navigation_progress_or_budget_exhausted")
