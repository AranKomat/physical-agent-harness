"""Sequential hybrid motor backend for the existing semantic HarnessRuntime.

The executive selects an operator-declared route. No model is called between
successful internal phases. Every callback must implement its own deadline;
Python cannot safely preempt a hung controller or turn process death into a stop.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from typing import Callable

from physical_harness.core.contracts import SkillReceipt, SkillRequest
from physical_harness.core.jobs import JobManager
from physical_harness.execution.handoff.contracts import (
    ROBOT_RESOURCES,
    GateReport,
    Phase,
    PolicyIdentity,
    Qualification,
    Regime,
    ResetReceipt,
    ResetRequest,
    Route,
    Snapshot,
    encoded,
    identifiers,
    integer,
    real,
    text,
)
from physical_harness.execution.handoff.telemetry import HandoffTelemetry, telemetry_payload


@dataclass(frozen=True)
class Backend:
    """Adapter around a qualified private driver, not a replacement controller.

    execute receives the FULL policy action interface, never a masked slice.
    Classical execution must count all hold/settle/streamed simulator actions.
    current_policy must fingerprint the loaded weights AND active runtime recipe.
    reset_policy clears queued chunks, temporal history and in-flight inference.
    """
    qualification: Qualification
    execute: Callable[[SkillRequest, Snapshot, float, Callable[[], bool]], SkillReceipt]
    guard: Callable[[Phase, str, Snapshot, float], GateReport]
    current_policy: Callable[[], PolicyIdentity] | None = None
    reset_policy: Callable[[ResetRequest, float], ResetReceipt] | None = None
    handoff_telemetry: Callable[[Phase, Snapshot, int], HandoffTelemetry] | None = None

    def __post_init__(self):
        if not isinstance(self.qualification, Qualification):
            raise ValueError("Qualification required")
        if not callable(self.execute) or not callable(self.guard):
            raise ValueError("Execution and sensor guard callbacks required")
        if self.qualification.regime == Regime.POLICY and (
            not callable(self.current_policy) or not callable(self.reset_policy)
        ):
            raise ValueError("Frozen policy requires identity and reset callbacks")
        if self.handoff_telemetry is not None and (
            self.qualification.regime != Regime.POLICY or not callable(self.handoff_telemetry)
        ):
            raise ValueError("Handoff telemetry requires a policy-backend callback")


class HybridExecutor:
    name = "hybrid-v0"

    def __init__(self, *, episode: str, routes: dict[str, Route], backends: dict[Regime, Backend],
                 observe: Callable[[float], Snapshot], stop: Callable[[float], bool],
                 policy: PolicyIdentity, emit: Callable[[str, dict], None],
                 jobs: JobManager | None = None, allow_simulated_motion: bool = False,
                 domain: str = "fixture", max_observation_age_s: float = 2.0,
                 stop_timeout_s: float = 5.0, control_dt: float = 1 / 30,
                 clock: Callable[[], float] = time.monotonic):
        self.episode = text(episode)
        if type(allow_simulated_motion) is not bool:
            raise ValueError("Explicit boolean motion permission required")
        if domain not in {"fixture", "behavior_sim"}:
            raise ValueError("Hybrid V0 is simulator-only")
        if not isinstance(policy, PolicyIdentity):
            raise ValueError("One pinned policy identity is required")
        if not routes or not all(isinstance(r, Route) for r in routes.values()):
            raise ValueError("Operator-defined routes are required")
        for key in routes:
            text(key, "action ID")
        for regime, backend in backends.items():
            if not isinstance(backend, Backend) or regime != backend.qualification.regime:
                raise ValueError("Backend regime mismatch")
            if backend.qualification.domain != domain:
                raise ValueError("Fixture qualifications cannot authorize BEHAVIOR motion")
            if regime == Regime.POLICY and backend.qualification.policy_fingerprint != policy.fingerprint:
                raise ValueError("Policy qualification does not match the pinned recipe")
        if any(p.regime not in backends for r in routes.values() for p in r.phases):
            raise ValueError("Missing qualified backend for a route phase")
        if not all(callable(c) for c in (observe, stop, emit, clock)):
            raise ValueError("Required callbacks missing")
        self.routes, self.backends = dict(routes), dict(backends)
        self.observe, self.stop_native, self.policy, self.emit = observe, stop, policy, emit
        self.jobs = jobs or JobManager([self.name])
        if self.name not in self.jobs.allowed:
            raise ValueError("Shared JobManager must allow hybrid-v0")
        self.allowed, self.domain, self.clock = allow_simulated_motion, domain, clock
        self.max_age = real(max_observation_age_s, "observation age", .001)
        self.stop_timeout = real(stop_timeout_s, "stop timeout", .001)
        self.dt = real(control_dt, "control_dt", .000001)
        self._mutex = threading.Lock()
        self._cancel = threading.Event()
        self._job_id = None
        self._faulted = False
        self._last_regime = None
        self._last_instruction = None
        self._generation = 0
        self._known_observations: dict[str, str] = {}
        self._frame_epoch = None
        self._latest_sim_time = -1.0
        self.trace: list[dict] = []

    def _record(self, kind, **body):
        # Freeze before handing it to a sink. No pixels, secrets or exception
        # messages are serialized; observations remain in the existing store.
        entry = {"seq": len(self.trace) + 1, "kind": kind, **body}
        frozen = json.loads(encoded(entry))
        self.trace.append(frozen)
        self.emit(kind, json.loads(encoded(frozen)))

    def cancel(self):
        """Cooperative request only. The executor retains its whole-robot lease."""
        self._cancel.set()

    def _check(self, deadline):
        if self._cancel.is_set():
            raise InterruptedError("Hybrid cancellation requested")
        if self._job_id is not None:
            job = self.jobs.jobs[self._job_id]
            if job.epoch != self.jobs.epoch or job.state != "running":
                raise InterruptedError("Hybrid execution epoch was invalidated")
        if self.clock() >= deadline:
            raise TimeoutError("Hybrid deadline exceeded")

    def _sample(self, deadline):
        self._check(deadline)
        snap = self.observe(deadline)
        if not isinstance(snap, Snapshot) or snap.episode != self.episode:
            raise ValueError("Foreign or untyped hybrid observation")
        self._fresh(snap)
        if snap.sim_time < self._latest_sim_time:
            raise ValueError("Hybrid observation time regressed")
        self._latest_sim_time = snap.sim_time
        old = self._known_observations.get(snap.observation_id)
        if old is not None and old != snap.fingerprint:
            raise ValueError("Observation ID was reused with different content")
        if len(self._known_observations) >= 10000 and old is None:
            raise ValueError("Bounded hybrid session observation limit reached")
        self._known_observations[snap.observation_id] = snap.fingerprint
        if self._frame_epoch is None:
            self._frame_epoch = snap.frame_epoch
        if snap.frame_epoch != self._frame_epoch:
            raise ValueError("Localization frame changed; invalidate and replan")
        self._check(deadline)
        return snap

    def _fresh(self, snapshot):
        age = self.clock() - snapshot.captured_wall
        if not 0 <= age <= self.max_age:
            raise ValueError("Stale/future hybrid observation")

    def _identity(self, backend):
        identity = backend.current_policy()
        if not isinstance(identity, PolicyIdentity) or identity != self.policy:
            raise PermissionError("Loaded frozen policy or inference recipe changed")

    def _gate(self, backend, phase, when, snap, deadline):
        result = backend.guard(phase, when, snap, deadline)
        if not isinstance(result, GateReport):
            raise ValueError("Typed evidence-bound gate required")
        self._record("gate", phase=phase.id, when=when, report=asdict(result))
        result.require(phase, when, snap)
        self._check(deadline)
        self._fresh(snap)

    def _stop(self, deadline):
        before = self.clock()
        try:
            acknowledged = self.stop_native(deadline) is True and self.clock() <= deadline
        except Exception:
            acknowledged = False
        self._record("stop", acknowledged=acknowledged, wall_s=self.clock() - before)
        if not acknowledged:
            self._faulted = True
        return acknowledged

    def stop(self):
        """Do not race an executing callback; cancel requests cooperative stop.

        When an unresolved session is idle, this may stop the backend, but it does
        not clear the latched fault or release an unresolved JobManager lease.
        Reconciliation remains an explicit operator-owned operation.
        """
        if not self._mutex.acquire(blocking=False):
            self.cancel()
            return False
        try:
            return self._stop(self.clock() + self.stop_timeout)
        finally:
            self._mutex.release()

    def _validate_receipt(self, receipt, request, start, regime):
        if not isinstance(receipt, SkillReceipt):
            raise ValueError("Native executor returned an untyped receipt")
        if receipt.skill_id != request.skill_id or receipt.sim_time_start != start.sim_time:
            raise ValueError("Native receipt ID or start clock mismatch")
        if receipt.outcome not in {"completed", "failed", "stalled", "timeout", "cancelled"}:
            raise ValueError("Unknown native outcome")
        end = real(receipt.sim_time_end, "receipt end", start.sim_time)
        for v in (receipt.policy_calls, receipt.chunks_generated, receipt.action_steps_executed):
            integer(v, "receipt counter")
        if receipt.action_steps_executed > request.metadata["max_action_steps"]:
            raise ValueError("Native executor exceeded action budget")
        if receipt.chunks_generated > request.max_policy_chunks:
            raise ValueError("Native executor exceeded chunk budget")
        if regime != Regime.POLICY and (receipt.policy_calls or receipt.chunks_generated):
            raise ValueError("Classical phase reported neural policy work")
        if abs(end - start.sim_time - receipt.action_steps_executed * self.dt) > 1e-5:
            raise ValueError("Receipt action count and simulated time disagree")
        if not hasattr(receipt.metadata, "get"):
            raise ValueError("Native metadata required")
        integer(receipt.metadata.get("execution_epoch"), "receipt epoch")
        if (receipt.metadata.get("episode_id"), receipt.metadata.get("execution_epoch")) != (
            self.episode, request.execution_epoch
        ):
            raise ValueError("Native receipt episode/epoch mismatch")
        if receipt.metadata.get("stop_acknowledged") is not True:
            raise RuntimeError("Native phase stop was not acknowledged")
        identifiers(receipt.evidence_ids, maximum=256)

    def run_skill(self, request: SkillRequest) -> SkillReceipt:
        """No automatic recovery, arbitrary phase generation, or implicit training."""
        if not self._mutex.acquire(blocking=False):
            raise RuntimeError("Hybrid executor already owns an active request")
        job = None
        stop_ack = False
        start = end = None
        totals = [0, 0, 0]  # policy calls, chunks, action steps
        evidence = []
        outcome, failure = "failed", None
        terminal_error = None
        self._cancel.clear()
        try:
            if self._faulted or not self.allowed:
                raise PermissionError("Hybrid motion disabled or session requires operator review")
            if not isinstance(request, SkillRequest):
                raise ValueError("SkillRequest required")
            text(request.skill_id, "skill ID")
            real(request.max_wall_s, "request wall budget", .001)
            integer(request.max_policy_chunks, minimum=1)
            integer(request.execution_epoch)
            identifiers(request.target_entities)
            if request.execution_epoch != self.jobs.epoch:
                raise ValueError("Stale request epoch")
            route = self.routes.get(request.metadata.get("action_id"))
            if route is None:
                raise ValueError("Action is not in the operator's hybrid route catalog")
            steps_cap = integer(request.metadata.get("max_action_steps"), "action cap", 1)
            if sum(p.max_steps for p in route.phases) > steps_cap:
                raise ValueError("Route phase step caps exceed the parent budget")
            if sum(p.max_policy_chunks for p in route.phases) > request.max_policy_chunks:
                raise ValueError("Route chunk caps exceed the parent budget")
            if any(set(p.target_entities) - set(request.target_entities) for p in route.phases):
                raise ValueError("Route introduced unrequested target entities")
            deadline = self.clock() + request.max_wall_s
            start = end = self._sample(deadline)
            if request.source_observation_id != start.observation_id:
                raise ValueError("Stale executive observation; no motion authorized")
            job = self.jobs.start(request.skill_id, self.name, ROBOT_RESOURCES,
                                  start.observation_id, start.captured_wall, deadline)
            self._job_id = job.id
            self._record("reserved", request_id=request.skill_id, route=route.id,
                         start=start.sim_time, source=start.fingerprint,
                         policy_fingerprint=self.policy.fingerprint, domain=self.domain)
            stop_ack = self._stop(min(deadline, self.clock() + self.stop_timeout))
            if not stop_ack:
                raise RuntimeError("Cannot establish exclusive stopped ownership")
            outcome = "completed"
            for n, phase in enumerate(route.phases):
                self._check(deadline)
                phase_deadline = min(deadline, self.clock() + phase.max_wall_s)
                backend = self.backends[phase.regime]
                current = self._sample(phase_deadline)
                if current.sim_time != end.sim_time:
                    raise ValueError("Unaccounted simulator steps between hybrid phases")
                if n == 0 and current.fingerprint != start.fingerprint:
                    raise ValueError("Executive snapshot changed before the first phase")
                if phase.regime == Regime.POLICY:
                    if phase.policy_entry == "ordinary_start" and self._last_regime not in {None, Regime.POLICY}:
                        raise PermissionError("Classical intervention requires the handoff admission gate")
                    self._identity(backend)
                    # Preserve temporal history across consecutive unchanged policy
                    # calls; clear it only on entry from another executor/instruction.
                    if self._last_regime != Regime.POLICY or self._last_instruction != phase.instruction:
                        self._generation += 1
                        reset = ResetRequest(self.episode, request.execution_epoch, self._generation,
                                             phase.instruction, current.observation_id,
                                             self.policy.fingerprint)
                        reply = backend.reset_policy(reset, phase_deadline)
                        if not isinstance(reply, ResetReceipt):
                            raise ValueError("Typed policy reset receipt required")
                        reply.require(reset)
                        self._record("policy_reset", request=asdict(reset))
                        self._identity(backend)
                    if backend.handoff_telemetry is not None:
                        telemetry = backend.handoff_telemetry(phase, current, self._generation)
                        if not isinstance(telemetry, HandoffTelemetry):
                            raise ValueError("Typed handoff telemetry required")
                        telemetry.require(phase, current, self.policy, self._generation)
                        self._check(phase_deadline)
                        self._fresh(current)
                        self._identity(backend)
                        self._record("handoff_telemetry", phase=phase.id,
                                     telemetry=telemetry_payload(telemetry))
                self._gate(backend, phase, "entry", current, phase_deadline)
                checked = self._sample(phase_deadline)
                if checked.fingerprint != current.fingerprint:
                    raise ValueError("Scene changed while admitting a phase")
                phase_id = request.skill_id + "/" + phase.id
                child = SkillRequest(
                    phase_id, phase.native_skill_type or phase.regime.value, phase.instruction,
                    target_entities=phase.target_entities,
                    destination_entity=request.destination_entity, resources=ROBOT_RESOURCES,
                    max_wall_s=max(.000001, phase_deadline - self.clock()),
                    max_policy_chunks=max(1, phase.max_policy_chunks),
                    source_observation_id=current.observation_id,
                    execution_epoch=request.execution_epoch,
                    metadata={**request.metadata, "action_id": request.metadata["action_id"], "phase_id": phase.id,
                              "max_action_steps": phase.max_steps,
                              "policy_fingerprint": self.policy.fingerprint},
                )
                self._check(phase_deadline)
                self._record("phase_start", phase=phase.id, regime=phase.regime.value,
                             observation=current.observation_id, sim_time=current.sim_time,
                             request=asdict(child) | {"resources": sorted(child.resources)})
                t0 = self.clock()
                stop_ack = False  # From here a thrown exception may mean partial motion.
                raw = backend.execute(child, current, phase_deadline,
                                      lambda: self._cancel.is_set() or self.jobs.epoch != request.execution_epoch)
                self._validate_receipt(raw, child, current, phase.regime)
                totals[0] += raw.policy_calls
                totals[1] += raw.chunks_generated
                totals[2] += raw.action_steps_executed
                evidence.extend(raw.evidence_ids)
                self._record("phase_result", phase=phase.id, regime=phase.regime.value,
                             wall_s=self.clock() - t0, receipt=asdict(raw))
                # Global stop drains the actual executor, not merely the RPC future.
                stop_ack = self._stop(min(deadline, self.clock() + self.stop_timeout))
                if not stop_ack:
                    raise RuntimeError("Cannot transfer ownership without a stopped executor")
                self._check(phase_deadline)
                end = self._sample(phase_deadline)
                if end.sim_time != raw.sim_time_end:
                    raise ValueError("Post-phase evidence does not match the receipt clock")
                if raw.action_steps_executed and end.observation_id == current.observation_id:
                    raise ValueError("Post-motion evidence must be new")
                self._last_regime, self._last_instruction = phase.regime, phase.instruction
                if raw.outcome != "completed":
                    outcome, failure = raw.outcome, raw.failure_reason or "phase_incomplete"
                    break  # No fall-through to another executor on failure.
                self._gate(backend, phase, "exit", end, phase_deadline)
                if phase.regime == Regime.POLICY:
                    self._identity(backend)
            self._check(deadline)
            self._record("complete", request_id=request.skill_id, outcome=outcome,
                         benchmark_success="not_claimed", task_verification="external")
        except BaseException as exc:
            terminal_error = exc
            self._faulted = True
            # No retries after an ambiguous transport, stale gate or partial action.
            try:
                self._record("fault", error_type=type(exc).__name__, request_id=getattr(request, "skill_id", "invalid"))
            except BaseException:
                pass
        finally:
            if job is not None:
                if not stop_ack:
                    try:
                        stop_ack = self._stop(self.clock() + self.stop_timeout)
                    except BaseException:
                        stop_ack = False
                if stop_ack:
                    if job.state == "running":
                        self.jobs.finish(job.id, "completed" if terminal_error is None and outcome == "completed" else "failed")
                    else:
                        self.jobs.acknowledge_stopped(job.id)
                else:
                    self.jobs.timeout(job.id)
                    self._faulted = True
            self._job_id = None
            self._mutex.release()
        if terminal_error is not None:
            raise terminal_error
        # Three-field metadata is intentionally compatible with the existing
        # strict ProcessNative decoder. Detailed phase metrics stay in the journal.
        return SkillReceipt(request.skill_id, self.name, outcome, start.sim_time, end.sim_time,
                            *totals, tuple(dict.fromkeys(evidence)), (), failure,
                            {"episode_id": self.episode, "execution_epoch": request.execution_epoch,
                             "stop_acknowledged": stop_ack})

    def metrics(self):
        rows = [r for r in self.trace if r["kind"] == "phase_result"]
        total = sum(r["receipt"]["action_steps_executed"] for r in rows)
        policy = sum(r["receipt"]["action_steps_executed"] for r in rows if r["regime"] == "policy")
        unresolved = sum(r["kind"] == "phase_start" for r in self.trace) - len(rows)
        return {"completed_phase_receipts": len(rows), "unresolved_phase_receipts": unresolved,
                "recorded_action_steps": total, "recorded_policy_steps": policy,
                "recorded_classical_steps": total - policy,
                "recorded_sim_s": total * self.dt,
                "policy_action_time_fraction": policy / total if total else None,
                "policy_calls": sum(r["receipt"]["policy_calls"] for r in rows),
                "policy_resets": sum(r["kind"] == "policy_reset" for r in self.trace),
                "faulted": self._faulted, "complete_accounting": unresolved == 0,
                "benchmark_success": "not_claimed", "energy_joules": None,
                "note": "Action-time share is not measured neural inference time or energy."}
