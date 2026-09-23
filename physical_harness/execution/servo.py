"""Target-relative bounded visual servo and trajectory streaming under existing ownership.

This is numerical control software, not R1Pro codec/collision qualification. No
force channel, impedance behavior or contact safety is inferred from RGB-D.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from physical_harness.core.actions import Basis, Pose, Primitive, ids, integer, number, text, vector
from physical_harness.execution.actions import StepReceipt
from physical_harness.integrations.curobo import JointTrajectory, PlanRequest
from physical_harness.planning.actions.cartesian import bounded_pose_step, pose_error


@dataclass(frozen=True)
class ServoObservation:
    basis: Basis
    measured_tcp: Pose
    target_tcp: Pose
    entity_id: str
    identity_revision: str
    current_mask_id: str
    current_depth_id: str
    target_visible: bool
    association_established: bool

    def __post_init__(self):
        if not isinstance(self.basis, Basis):
            raise ValueError("Basis required")
        for p in (self.measured_tcp, self.target_tcp):
            if not isinstance(p, Pose) or p.frame != self.basis.frame:
                raise ValueError("Servo poses require same current frame")
        for s in (self.entity_id, self.identity_revision, self.current_mask_id, self.current_depth_id):
            text(s)
        if type(self.target_visible) is not bool or type(self.association_established) is not bool:
            raise ValueError("Explicit visibility and association flags required")


@dataclass(frozen=True)
class ServoLimits:
    dt: float = 1/30
    translation_speed_m_s: float = .02
    rotation_speed_rad_s: float = .2
    max_total_path_m: float = .10
    max_target_jump_m: float = .03
    max_target_jump_rad: float = .3
    target_age_s: float = .25
    position_tolerance_m: float = .003
    rotation_tolerance_rad: float = .03
    convergence_samples: int = 3
    max_steps: int = 120

    def __post_init__(self):
        for k, v in self.__dict__.items():
            if k in {"convergence_samples", "max_steps"}:
                integer(v, low=1, high=10000)
            else:
                number(v, low=.000001)
        if self.translation_speed_m_s > .5 or self.rotation_speed_rad_s > 2:
            raise ValueError("Servo envelope too large")


class VisualServo:
    """Pure bounded setpoint generator. Native port must solve IK and check the sweep.

    Goal estimates may update at each observation; identity, frame continuity,
    jump limits and total correction path are enforced. It stops on loss rather
    than executing a last-known correction. No initial label is reacquired by name.
    """
    def __init__(self, first: ServoObservation, limits=ServoLimits()):
        self.first, self.last, self.limits = first, None, limits
        self.steps = self.streak = 0
        self.path = 0.
        self.done = False

    def propose(self, observation: ServoObservation, *, now: float) -> Pose | None:
        if self.done:
            raise PermissionError("Servo session is closed")
        self.first.basis.require_continuity(observation.basis)
        observation.basis.fresh(now, self.limits.target_age_s)
        if observation.entity_id != self.first.entity_id or not observation.target_visible or not observation.association_established:
            self.done = True
            raise PermissionError("Servo target lost or identity changed")
        if self.last:
            if observation.basis.sim_time <= self.last.basis.sim_time or observation.basis.observation_id == self.last.basis.observation_id:
                raise PermissionError("Servo requires a new measured control boundary")
            move, rotation = pose_error(self.last.target_tcp, observation.target_tcp)
            if move > self.limits.max_target_jump_m or rotation > self.limits.max_target_jump_rad:
                self.done = True
                raise PermissionError("Servo target jumped outside qualified envelope")
        if self.steps >= self.limits.max_steps:
            self.done = True
            raise TimeoutError("Servo step budget")
        distance, rotation = pose_error(observation.measured_tcp, observation.target_tcp)
        self.streak = self.streak+1 if distance <= self.limits.position_tolerance_m and rotation <= self.limits.rotation_tolerance_rad else 0
        self.last = observation
        if self.streak >= self.limits.convergence_samples:
            self.done = True
            return None
        target = bounded_pose_step(observation.measured_tcp, observation.target_tcp,
                                   max_translation_m=self.limits.translation_speed_m_s*self.limits.dt,
                                   max_rotation_rad=self.limits.rotation_speed_rad_s*self.limits.dt)
        delta = math.dist(target.xyz, observation.measured_tcp.xyz)
        if self.path+delta > self.limits.max_total_path_m:
            self.done = True
            raise PermissionError("Servo correction path budget exhausted")
        self.path += delta
        self.steps += 1
        return target


@dataclass(frozen=True)
class JointSample:
    basis: Basis
    names: tuple[str, ...]
    positions: tuple[float, ...]
    fixed_names: tuple[str, ...] = ()
    fixed_positions: tuple[float, ...] = ()

    def __post_init__(self):
        if not isinstance(self.basis, Basis):
            raise ValueError("Current joint sample requires Basis")
        ids(self.names, empty=False)
        vector(self.positions, len(self.names))
        ids(self.fixed_names)
        vector(self.fixed_positions, len(self.fixed_names))
        if set(self.names) & set(self.fixed_names):
            raise ValueError("Controlled/fixed joint overlap")


class TrajectoryStreamer:
    """Run behind Driver.execute; NEVER acquire a second robot lease.

    port.observe(deadline) -> JointSample, no physics steps.
    port.check_segment(request, from_q, to_q, sample, deadline) -> literal True.
    port.command(request, q, sample, deadline) -> next JointSample, exactly one tick.
    port.settle(request, sample, remaining, deadline) -> tuple[JointSample,...].
    port.stopped(sample) -> bool, independent measured stopping.
    port.endpoint_reached(request, sample, deadline) -> True after measured FK/TCP check.
    Every confirmed tick including braking appears in the returned StepReceipt.
    Uncertain callback completion raises; the outer ActionExecutor latches a fault.
    """
    def __init__(self, *, port, clock, tracking_tolerance: tuple[float, ...],
                 fixed_tolerance: tuple[float, ...] = (), max_age_s: float = .25):
        if type(tracking_tolerance) is not tuple or type(fixed_tolerance) is not tuple:
            raise ValueError("Immutable per-joint tolerances required")
        self.port, self.clock, self.tolerance = port, clock, tracking_tolerance
        self.fixed_tolerance = fixed_tolerance
        self.max_age_s = number(max_age_s, low=.000001)
        for x in tracking_tolerance + fixed_tolerance:
            number(x, low=0)

    def run(self, program, index: int, start: Basis, request: PlanRequest,
            trajectory: JointTrajectory, deadline: float, cancelled) -> StepReceipt:
        step = program.steps[index]
        if step.kind != Primitive.MOVE_EEF:
            raise PermissionError("Free-space trajectory backend only accepts MOVE_EEF")
        start.require_same(request.basis)
        trajectory.validate(request)
        if len(self.tolerance) != len(request.limits.names):
            raise ValueError("Per-joint tracking tolerances required")
        if len(trajectory.positions)-1 >= step.max_steps:
            raise ValueError("Trajectory must reserve at least one step for settling")
        if len(self.fixed_tolerance) != len(request.fixed_joint_names):
            raise ValueError("Every fixed joint needs a hold tolerance")
        def check(sample):
            if not isinstance(sample, JointSample):
                raise ValueError("Missing native joint receipt")
            sample.basis.fresh(self.clock(), self.max_age_s)
            if sample.names != request.limits.names or sample.fixed_names != request.fixed_joint_names:
                raise PermissionError("Native controlled/fixed joint order changed")
            if any(abs(a-b) > t for a,b,t in zip(sample.fixed_positions, request.fixed_joint_positions,
                                               self.fixed_tolerance)):
                raise PermissionError("Fixed-joint hold left its envelope")
            if cancelled() or self.clock() >= deadline:
                raise InterruptedError("Cancelled/expired trajectory")
        sample = self.port.observe(deadline)
        check(sample)
        start.require_same(sample.basis)
        if sample.names != request.limits.names:
            raise ValueError("Native joint order mismatch")
        if any(abs(a-b) > t for a,b,t in zip(sample.positions, request.start, self.tolerance)):
            raise PermissionError("Measured joints changed since planning")
        count = 0
        previous = request.start
        for q in trajectory.positions[1:]:
            check(sample)
            if self.port.check_segment(request, previous, q, sample, deadline) is not True:
                raise PermissionError("Current swept segment is not established clear")
            confirmed = self.port.observe(deadline)
            check(confirmed)
            sample.basis.require_same(confirmed.basis)
            if confirmed != sample:
                raise PermissionError("Measured state changed during segment review")
            after = self.port.command(request, q, sample, deadline)
            check(after)
            sample.basis.require_continuity(after.basis)
            if after.names != sample.names or after.basis.observation_id == sample.basis.observation_id or abs(after.basis.sim_time-sample.basis.sim_time-request.dt) > 1e-6:
                raise ValueError("Uncounted/reused trajectory feedback")
            count += 1
            if any(abs(a-b) > t for a,b,t in zip(after.positions, q, self.tolerance)):
                raise PermissionError("Measured trajectory tracking left envelope")
            sample, previous = after, q
        check(sample)
        braking = self.port.settle(request, sample, step.max_steps-count, deadline)
        if type(braking) is not tuple or len(braking) > step.max_steps-count:
            raise ValueError("Invalid settling receipt sequence")
        for after in braking:
            # Returned historical braking samples may be older than the last wall
            # deadline; check lineage/holds here, then freshness of final sample.
            if not isinstance(after, JointSample) or after.fixed_names != request.fixed_joint_names:
                raise ValueError("Missing fixed-joint settling evidence")
            if any(abs(a-b) > t for a,b,t in zip(after.fixed_positions, request.fixed_joint_positions,
                                               self.fixed_tolerance)):
                raise PermissionError("Settling violated fixed-joint hold")
            sample.basis.require_continuity(after.basis)
            if after.basis.observation_id == sample.basis.observation_id or after.names != sample.names or abs(after.basis.sim_time-sample.basis.sim_time-request.dt) > 1e-6:
                raise ValueError("Uncounted settling feedback")
            sample = after
            count += 1
        check(sample)
        if self.clock() > deadline or self.port.stopped(sample) is not True:
            raise RuntimeError("Trajectory stop unresolved")
        if self.port.endpoint_reached(request, sample, deadline) is not True:
            raise PermissionError("Measured endpoint did not establish requested TCP target")
        check(sample)
        observed = self.port.observe(deadline)
        check(observed)
        if observed != sample:
            raise PermissionError("Final observation differs from counted trajectory receipt")
        receipt = StepReceipt(program.fingerprint, index, start, sample.basis, "completed", count,
                              0, 0, True, sample.basis.evidence_ids)
        receipt.validate(program, index, start, request.dt)
        return receipt
