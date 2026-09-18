"""Multi-chunk skills over injected, deadline-bounded policy/controller services.

No robot codec is assumed here. The controller adapter owns units, limits and
stop acknowledgement. RPC implementations must enforce the supplied deadline;
a synchronous Python callback cannot preempt a hung native controller.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from .contracts import SkillReceipt, SkillRequest
from .jobs import JobManager


@dataclass(frozen=True)
class MotorObservation:
    episode_id: str
    observation_id: str
    execution_epoch: int
    sim_time: float
    captured_wall: float
    payload: Mapping[str, Any] = field(default_factory=dict)
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyChunk:
    episode_id: str
    observation_id: str
    execution_epoch: int
    actions: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class SkillFeedback:
    complete: bool = False
    target_visible: bool = True
    progress: float | None = None
    evidence_ids: tuple[str, ...] = ()


class ChunkPolicy(Protocol):
    name: str

    def infer(
        self, observation: MotorObservation, instruction: str, deadline: float
    ) -> PolicyChunk: ...


class MotorController(Protocol):
    def observe(self) -> MotorObservation: ...
    def validate_action(self, action: tuple[float, ...]) -> None: ...
    def step(self, action: tuple[float, ...], deadline: float) -> MotorObservation: ...
    def stop(self, resources: frozenset[str]) -> bool: ...


class ChunkedMotorBackend:
    def __init__(
        self,
        episode_id: str,
        policy: ChunkPolicy,
        controller: MotorController,
        feedback: Callable[[MotorObservation, SkillRequest], SkillFeedback],
        *,
        qualified: bool = False,
        prefix_steps: int = 8,
        max_observation_age: float = 2.0,
        stall_chunks: int = 5,
        jobs: JobManager | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not isinstance(prefix_steps, int) or isinstance(prefix_steps, bool) or prefix_steps < 1:
            raise ValueError("Positive execution prefix required")
        if not math.isfinite(max_observation_age) or max_observation_age <= 0 or stall_chunks < 1:
            raise ValueError("Invalid freshness/stall limits")
        self.name = policy.name
        self.episode_id, self.policy, self.controller = episode_id, policy, controller
        self.feedback, self.qualified = feedback, qualified
        self.prefix_steps, self.max_age, self.stall_chunks = (
            prefix_steps,
            max_observation_age,
            stall_chunks,
        )
        self.jobs = jobs or JobManager([self.name])
        self.clock = clock
        self._cancel = threading.Event()
        self._active = threading.Lock()

    def cancel(self) -> None:
        self._cancel.set()

    def _observation(self, obs: MotorObservation, epoch: int, minimum_sim_time: float = 0) -> None:
        if (
            obs.episode_id != self.episode_id
            or obs.execution_epoch != epoch
            or not obs.observation_id
        ):
            raise ValueError("Observation episode/epoch mismatch")
        if not math.isfinite(obs.sim_time) or obs.sim_time < minimum_sim_time:
            raise ValueError("Invalid simulator clock")
        age = self.clock() - obs.captured_wall
        if not math.isfinite(age) or not 0 <= age <= self.max_age:
            raise ValueError("Stale observation")

    def run_skill(self, request: SkillRequest) -> SkillReceipt:
        if (
            not math.isfinite(request.max_wall_s)
            or request.max_wall_s <= 0
            or isinstance(request.max_policy_chunks, bool)
            or not isinstance(request.max_policy_chunks, int)
            or request.max_policy_chunks < 1
        ):
            raise ValueError("Finite positive skill budgets required")
        if not self._active.acquire(blocking=False):
            raise ValueError("Motor service already has an active skill")
        self._cancel.clear()
        calls = chunks = steps = 0
        start_sim = end_sim = 0.0
        evidence: tuple[str, ...] = ()
        inference_s: list[float] = []
        job = None
        outcome, reason = "failed", "unqualified_motor_backend"
        stopped = True
        try:
            if self.qualified:
                observation = self.controller.observe()
                self._observation(observation, request.execution_epoch)
                if (
                    request.source_observation_id
                    and request.source_observation_id != observation.observation_id
                ):
                    raise ValueError("Skill requested from a stale observation")
                if request.execution_epoch != self.jobs.epoch:
                    raise ValueError("Skill epoch is stale")
                start_sim = end_sim = observation.sim_time
                deadline = self.clock() + request.max_wall_s
                job = self.jobs.start(
                    request.skill_id,
                    self.name,
                    request.resources,
                    observation.observation_id,
                    observation.captured_wall,
                    deadline,
                )
                best_progress, stalled = -math.inf, 0
                outcome, reason = "timeout", "chunk_budget_exhausted"
                for _ in range(request.max_policy_chunks):
                    if self._cancel.is_set() or self.jobs.epoch != request.execution_epoch:
                        outcome, reason = "cancelled", "cancel_requested"
                        break
                    if self.clock() >= deadline:
                        outcome, reason = "timeout", "wall_budget_exhausted"
                        break
                    self._observation(observation, request.execution_epoch, end_sim)
                    job.observation_id = observation.observation_id
                    job.observation_time = observation.captured_wall
                    before = self.clock()
                    calls += 1
                    reply = self.policy.infer(observation, request.instruction, deadline)
                    inference_s.append(self.clock() - before)
                    if self._cancel.is_set() or self.jobs.epoch != request.execution_epoch:
                        outcome, reason = "cancelled", "cancel_requested"
                        break
                    if self.clock() >= deadline:
                        outcome, reason = "timeout", "wall_budget_exhausted"
                        break
                    if reply.episode_id != self.episode_id or not self.jobs.accepts_reply(
                        job.id,
                        reply.execution_epoch,
                        reply.observation_id,
                        self.clock(),
                        self.max_age,
                    ):
                        raise ValueError("Stale or mismatched policy reply")
                    if not reply.actions:
                        raise ValueError("Empty action chunk")
                    prefix = reply.actions[: self.prefix_steps]
                    for action in prefix:
                        if not action or any(
                            isinstance(x, bool)
                            or not isinstance(x, (int, float))
                            or not math.isfinite(x)
                            for x in action
                        ):
                            raise ValueError("Nonfinite or malformed action")
                        self.controller.validate_action(action)
                    chunks += 1
                    for action in prefix:
                        if self._cancel.is_set() or self.jobs.epoch != request.execution_epoch:
                            outcome, reason = "cancelled", "cancel_requested"
                            break
                        if self.clock() >= deadline:
                            outcome, reason = "timeout", "wall_budget_exhausted"
                            break
                        observation = self.controller.step(action, deadline)
                        steps += 1
                        self._observation(observation, request.execution_epoch, end_sim)
                        end_sim = observation.sim_time
                    else:
                        if self._cancel.is_set() or self.jobs.epoch != request.execution_epoch:
                            outcome, reason = "cancelled", "cancel_requested"
                            break
                        if self.clock() >= deadline:
                            outcome, reason = "timeout", "wall_budget_exhausted"
                            break
                        status = self.feedback(observation, request)
                        evidence = tuple(
                            dict.fromkeys((*observation.evidence_ids, *status.evidence_ids))
                        )
                        if status.complete:
                            outcome, reason = "completed", None
                            break
                        if not status.target_visible:
                            outcome, reason = "failed", "target_lost"
                            break
                        if status.progress is not None:
                            if not math.isfinite(status.progress):
                                raise ValueError("Invalid progress signal")
                            stalled = 0 if status.progress > best_progress + 1e-6 else stalled + 1
                            best_progress = max(best_progress, status.progress)
                            if stalled >= self.stall_chunks:
                                outcome, reason = "stalled", "no_observed_progress"
                                break
                        continue
                    break
        except Exception as error:
            outcome, reason = "failed", f"{type(error).__name__}: {error}"
        finally:
            if job is not None:
                try:
                    stopped = self.controller.stop(request.resources) is True
                except Exception:
                    stopped = False
                if stopped:
                    if job.state == "running":
                        self.jobs.finish(
                            job.id, "completed" if outcome == "completed" else "failed"
                        )
                    else:
                        self.jobs.acknowledge_stopped(job.id)
                else:
                    self.jobs.timeout(job.id)
                    outcome, reason = "failed", "stop_unacknowledged"
            self._active.release()
        return SkillReceipt(
            request.skill_id,
            self.name,
            outcome,
            start_sim,
            end_sim,
            calls,
            chunks,
            steps,
            evidence,
            (),
            reason,
            {
                "episode_id": self.episode_id,
                "execution_epoch": request.execution_epoch,
                "stop_acknowledged": stopped,
                "inference_s": inference_s,
                "resource_ownership_unresolved": not stopped,
            },
        )
