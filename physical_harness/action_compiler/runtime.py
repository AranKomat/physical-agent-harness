"""One-shot catalog execution using the existing JobManager and Journal contracts.

This is a motor backend beneath HarnessRuntime, not a replacement executive,
WorldState, verifier, memory system, policy codec, or robot controller. Install
one actuator authority only: do not nest a second resource-owning HybridExecutor
inside this runner. Reuse its native callbacks under the shared JobManager.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

from .compiler import Catalog
from .types import Basis, Check, Primitive, Review, digest, ids, integer, number, plain, text

RESOURCES = frozenset({"robot", "base", "torso", "trunk", "left_arm", "right_arm",
                       "left_gripper", "right_gripper", "head"})


@dataclass(frozen=True)
class StepReview:
    program_fingerprint: str
    step_index: int
    basis_fingerprint: str
    checks: tuple[Check, ...]

    def require(self, program, index, basis):
        if (self.program_fingerprint, self.step_index, self.basis_fingerprint) != (
            program.fingerprint, index, basis.fingerprint
        ):
            raise PermissionError("Stale per-step review")
        if type(self.checks) is not tuple or not all(isinstance(c, Check) for c in self.checks):
            raise ValueError("Typed per-step checks required")
        ids(tuple(c.name for c in self.checks), empty=False)
        kind = program.steps[index].kind
        required = {"fresh_sensors", "robot_settled"}
        if kind == Primitive.HOLD_CHECK:
            required.add("measured_grasp")
        elif kind == Primitive.RELEASE_CHECK:
            required.add("measured_release")
        elif kind == Primitive.INSPECT:
            required.add("passive_capture")
        elif kind == Primitive.POLICY:
            required.update({"policy_identity", "policy_recipe", "policy_handoff", "policy_queue_ready"})
        else:
            required.update({"swept_collision", "native_codec", "payload_geometry", "joint_limits"})
            if kind in {Primitive.PRESS, Primitive.PULL}:
                required.update({"contact_monitor", "bounded_contact"})
        required.update(n for n in program.required_checks if n.startswith("constraint_"))
        values = {c.name: c.passed for c in self.checks}
        if any(values.get(k) is not True for k in required) or any(c.passed is not True for c in self.checks):
            raise PermissionError("Unestablished per-step safety/measurement gates")


@dataclass(frozen=True)
class StepReceipt:
    program_fingerprint: str
    step_index: int
    before: Basis
    after: Basis
    outcome: str
    native_steps: int
    policy_calls: int
    policy_dofs: int
    stop_acknowledged: bool
    evidence_ids: tuple[str, ...]
    policy_inference_s: float | None = None
    chunks_generated: int = 0

    def validate(self, program, index, start, dt):
        if (self.program_fingerprint, self.step_index, self.before) != (program.fingerprint, index, start):
            raise ValueError("Receipt correlation mismatch")
        start.require_continuity(self.after)
        if self.outcome not in {"completed", "failed", "stalled", "timeout", "cancelled"}:
            raise ValueError("Invalid primitive outcome")
        for n in (self.native_steps, self.policy_calls, self.policy_dofs, self.chunks_generated):
            integer(n)
        if (self.policy_calls > program.steps[index].max_policy_calls
                or self.chunks_generated > program.steps[index].max_policy_chunks):
            raise ValueError("Primitive exceeded policy inference budget")
        if self.native_steps > program.steps[index].max_steps:
            raise ValueError("Primitive exceeded action budget")
        if abs(self.after.sim_time-start.sim_time-self.native_steps*dt) > 1e-5:
            raise ValueError("Unaccounted native/settling steps")
        if self.native_steps and self.after.observation_id == start.observation_id:
            raise ValueError("Post-motion receipt reused old evidence")
        if program.steps[index].kind == Primitive.POLICY:
            if self.policy_dofs != program.robot_dofs:
                raise PermissionError("Frozen policy must keep its full normal action space")
        elif self.policy_calls or self.policy_dofs:
            raise ValueError("Classical step reported policy control")
        if self.policy_inference_s is not None:
            number(self.policy_inference_s, low=0)
        if self.stop_acknowledged is not True:
            raise RuntimeError("Primitive stop is unresolved")
        ids(self.evidence_ids, empty=False)


@dataclass(frozen=True)
class Driver:
    """Reviewed native adapter, never constructed from model-visible parameters.

    Every callback enforces its own deadline. execute includes ALL braking/settle
    ticks in StepReceipt.native_steps. observe/stop must not step the simulator.
    Whole-robot collision includes open fingers, self-collision and attached load.
    """
    domain: str
    qualification_id: str
    robot_fingerprint: str
    gripper_fingerprint: str
    supported: frozenset[Primitive]
    observe: Callable
    review_program: Callable
    review_step: Callable
    execute: Callable
    stop: Callable

    def __post_init__(self):
        if self.domain not in {"fixture", "behavior_sim"}:
            raise ValueError("No physical hardware execution in this package")
        for s in (self.qualification_id, self.robot_fingerprint, self.gripper_fingerprint):
            text(s)
        if type(self.supported) is not frozenset or not all(isinstance(p, Primitive) for p in self.supported):
            raise ValueError("Explicit qualified primitive set required")
        if not all(callable(getattr(self, name)) for name in
                   ("observe", "review_program", "review_step", "execute", "stop")):
            raise ValueError("Native callbacks required")


@dataclass(frozen=True)
class ExecutionResult:
    attempt_id: str
    action_id: str
    before: Basis
    after: Basis
    outcome: str
    receipts: tuple[StepReceipt, ...]
    stop_acknowledged: bool
    semantic_status: str = "requires_external_verification"

    @property
    def native_steps(self):
        return sum(r.native_steps for r in self.receipts)


class ActionExecutor:
    name = "compiled-action-v1"

    def __init__(self, *, driver: Driver, jobs, journal, allow_simulated_motion: bool = False,
                 max_age_s: float = 2., stop_timeout_s: float = 5., control_dt: float = 1/30,
                 max_executions_per_intent: int = 3, clock=time.monotonic):
        if type(allow_simulated_motion) is not bool:
            raise ValueError("Explicit motion opt-in required")
        if self.name not in jobs.allowed:
            raise ValueError("Shared JobManager must allow compiled-action-v1")
        self.driver, self.jobs, self.journal = driver, jobs, journal
        self.allowed, self.clock = allow_simulated_motion, clock
        self.max_age = number(max_age_s, low=.001)
        self.stop_timeout = number(stop_timeout_s, low=.001)
        self.dt = number(control_dt, low=.000001)
        self.intent_cap = integer(max_executions_per_intent, low=1, high=100)
        self._lock, self._cancel = threading.Lock(), threading.Event()
        self.faulted = False
        self._seq = 0
        self._load_history()

    def _load_history(self):
        self.consumed, self.intent_counts = set(), {}
        reserved, terminal = set(), {}
        for p in self.journal.records("compiled_action"):
            if p["event"] == "reserved":
                reserved.add(p["attempt_id"])
                self.consumed.add(p["attempt_id"])
                key = p["intent_key"]
                self.intent_counts[key] = self.intent_counts.get(key, 0)+1
            elif p["event"] == "terminal":
                terminal[p["attempt_id"]] = (p["stop_acknowledged"] is True
                                             and p.get("fault_latched") is not True)
        if reserved-terminal.keys() or any(v is not True for v in terminal.values()):
            self.faulted = True  # Persisted uncertainty is not cleared by process restart.

    def _log(self, event, attempt, **data):
        self._seq += 1
        # attempt is unique per catalog/selection; sequence only orders this invocation.
        self.journal.put("compiled_action", f"{attempt}:{event}:{self._seq}",
                         {"event": event, "attempt_id": attempt, **plain(data)})

    def cancel(self):
        self._cancel.set()

    def _check(self, deadline, epoch):
        if self._cancel.is_set() or self.jobs.epoch != epoch:
            raise InterruptedError("Execution cancelled or epoch changed")
        if self.clock() >= deadline:
            raise TimeoutError("Compiled action deadline")

    def _observe(self, deadline):
        result = self.driver.observe(deadline)
        if not isinstance(result, Basis):
            raise ValueError("Typed legal observation basis required")
        result.fresh(self.clock(), self.max_age)
        return result

    def stop(self) -> bool:
        if not self._lock.acquire(blocking=False):
            self.cancel()
            return False
        try:
            deadline = self.clock()+self.stop_timeout
            return self.driver.stop(deadline) is True and self.clock() <= deadline
        finally:
            self._lock.release()

    def execute(self, catalog: Catalog, selection: dict | str | bytes, *,
                max_steps: int, max_wall_s: float) -> ExecutionResult:
        integer(max_steps, low=0, high=1000000)
        number(max_wall_s, low=.001)
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("Actuator writer already active")
        lease = None
        attempt = None
        recorded = []
        stopped = False
        start = current = None
        outcome = "failed"
        error = None
        self._cancel.clear()
        try:
            if not self.allowed or self.faulted:
                raise PermissionError("Motion disabled or unresolved session")
            deadline = self.clock()+max_wall_s
            current = start = self._observe(deadline)
            action = catalog.resolve(selection, current, now=self.clock(), max_age_s=self.max_age)
            program = action.program
            if (self.driver.domain, self.driver.robot_fingerprint, self.driver.gripper_fingerprint) != (
                current.domain, current.robot_fingerprint, catalog.gripper_fingerprint
            ):
                raise PermissionError("Native embodiment/domain mismatch")
            if not {s.kind for s in program.steps} <= self.driver.supported:
                raise PermissionError("Native primitive not qualified")
            if program.max_steps > max_steps:
                raise ValueError("Composite exceeds outer action budget")
            self._check(deadline, current.execution_epoch)
            refreshed = self.driver.review_program(program, current, deadline)
            if (not isinstance(refreshed, Review) or refreshed.failures(program, current)
                    or refreshed.qualification_id != self.driver.qualification_id):
                raise PermissionError("Program no longer passes native feasibility review")
            start.require_same(self._observe(deadline))
            self._check(deadline, current.execution_epoch)
            attempt = "attempt:"+digest([catalog.id, action.id])[:32]
            if attempt in self.consumed:
                raise PermissionError("One-shot action was already consumed")
            key = digest([current.episode, program.proposal.intent])
            if self.intent_counts.get(key, 0) >= self.intent_cap:
                raise PermissionError("Explicit per-intent execution budget exhausted")
            lease = self.jobs.start(attempt, self.name, RESOURCES, current.observation_id,
                                    current.captured_wall, deadline)
            # Reserve DURABLY before any actuator callback. No new database.
            self._log("reserved", attempt, intent_key=key, action_id=action.id,
                      catalog_id=catalog.id, program_fingerprint=program.fingerprint,
                      basis=plain(current), max_steps=max_steps, max_wall_s=max_wall_s)
            self.consumed.add(attempt)
            self.intent_counts[key] = self.intent_counts.get(key, 0)+1
            stop_deadline = min(deadline, self.clock()+self.stop_timeout)
            stopped = self.driver.stop(stop_deadline) is True and self.clock() <= stop_deadline
            if not stopped:
                raise RuntimeError("Cannot establish stopped actuator ownership")
            start.require_same(self._observe(deadline))
            outcome = "completed"
            for index, step in enumerate(program.steps):
                self._check(deadline, start.execution_epoch)
                before = self._observe(deadline)
                current.require_same(before)
                step_review = self.driver.review_step(program, index, before, deadline)
                if not isinstance(step_review, StepReview):
                    raise ValueError("Typed per-step review required")
                step_review.require(program, index, before)
                before.require_same(self._observe(deadline))
                self._check(deadline, start.execution_epoch)
                self._log("step_started", attempt, step_index=index, primitive=step.kind.value,
                          basis=plain(before), max_steps=step.max_steps, robot_dofs=program.robot_dofs)
                stopped = False
                t0 = self.clock()
                receipt = self.driver.execute(program, index, before, deadline,
                                               lambda: self._cancel.is_set() or self.jobs.epoch != start.execution_epoch)
                if not isinstance(receipt, StepReceipt):
                    raise ValueError("Typed native step receipt required")
                receipt.validate(program, index, before, self.dt)
                current = receipt.after
                observed = self._observe(deadline)
                current.require_same(observed)
                self._check(deadline, start.execution_epoch)
                stopped = True
                recorded.append(receipt)
                self._log("step_receipt", attempt, step_index=index, primitive=step.kind.value,
                          wall_s=self.clock()-t0, receipt=plain(receipt))
                if receipt.outcome != "completed":
                    outcome = receipt.outcome
                    break  # Never fall through to another motor on failure.
        except BaseException as exc:
            error = exc
            if lease is not None:
                self.faulted = True
        finally:
            if lease is not None:
                try:
                    stop_deadline = self.clock()+self.stop_timeout
                    stopped = self.driver.stop(stop_deadline) is True and self.clock() <= stop_deadline
                    # stop may not secretly advance physics; settling belongs to receipts.
                    if stopped and current is not None:
                        after_stop = self._observe(self.clock()+self.stop_timeout)
                        if after_stop.sim_time != current.sim_time:
                            raise RuntimeError("Stop callback advanced uncounted simulator steps")
                except BaseException as exc:
                    stopped = False
                    error = error or exc
                if not stopped:
                    self.faulted = True
                try:
                    self._log("terminal", attempt, outcome=outcome if error is None else "error",
                              error_type=type(error).__name__ if error else None,
                              stop_acknowledged=stopped, fault_latched=self.faulted,
                              validated_receipts=len(recorded),
                              semantic_status="requires_external_verification")
                except BaseException as exc:
                    self.faulted = True
                    error = error or exc
                try:
                    if stopped:
                        if lease.state == "running":
                            self.jobs.finish(lease.id, "completed" if error is None and outcome == "completed" else "failed")
                        else:
                            self.jobs.acknowledge_stopped(lease.id)
                    else:
                        self.jobs.timeout(lease.id)
                except BaseException as exc:
                    self.faulted = True
                    error = error or exc
                    # A lease reconciliation error is persisted as another
                    # terminal event, so process recreation cannot hide it.
                    try:
                        self._log("terminal", attempt, outcome="error",
                                  error_type=type(exc).__name__, stop_acknowledged=stopped,
                                  fault_latched=True, validated_receipts=len(recorded),
                                  semantic_status="requires_external_verification")
                    except BaseException:
                        pass
            self._lock.release()
        if error:
            raise error
        return ExecutionResult(attempt, action.id, start, current, outcome, tuple(recorded), stopped)
