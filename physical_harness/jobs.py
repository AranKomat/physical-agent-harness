"""Single-process execution ownership and stale-reply guards.

No motion is executed here. Hardware controllers and safety checks remain
independent. A timed-out/cancelled network request does NOT release a limb.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Job:
    id: str
    executor: str
    epoch: int
    resources: frozenset[str]
    observation_id: str
    observation_time: float
    deadline: float
    state: str = "running"


class JobManager:
    def __init__(self, allowed_executors: Iterable[str]):
        self.allowed = frozenset(allowed_executors)
        self.epoch = 0
        self.jobs: dict[str, Job] = {}
        self.owners: dict[str, str] = {}

    def start(
        self,
        identifier: str,
        executor: str,
        resources: Iterable[str],
        observation_id: str,
        observation_time: float,
        deadline: float,
    ) -> Job:
        if not identifier or identifier in self.jobs:
            raise ValueError("Job id missing or reused")
        if executor not in self.allowed:
            raise ValueError("Executor is not permitted")
        if not observation_id:
            raise ValueError("Observation id required")
        if (
            any(
                isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                for x in [observation_time, deadline]
            )
            or observation_time < 0
            or deadline < observation_time
        ):
            raise ValueError("Invalid time contract")
        resources = frozenset(resources)
        if not resources or any(not isinstance(r, str) or not r for r in resources):
            raise ValueError("Explicit resources required")
        if any(r in self.owners for r in resources):
            raise ValueError("Resource is still owned by an executing or unresolved job")
        job = Job(
            identifier, executor, self.epoch, resources, observation_id, observation_time, deadline
        )
        self.jobs[identifier] = job
        for r in resources:
            self.owners[r] = identifier
        return job

    def request_cancel(self, identifier: str) -> None:
        job = self.jobs[identifier]
        if job.state in {"running", "unknown"}:
            job.state = "cancel_requested"

    def timeout(self, identifier: str) -> None:
        job = self.jobs[identifier]
        if job.state in {"running", "cancel_requested"}:
            job.state = "unknown"

    def invalidate_goal(self) -> None:
        self.epoch += 1
        for job in self.jobs.values():
            if job.state in {"running", "unknown"}:
                job.state = "cancel_requested"

    def acknowledge_stopped(self, identifier: str) -> None:
        job = self.jobs[identifier]
        if job.state not in {"unknown", "cancel_requested"}:
            raise ValueError("No pending stop to acknowledge")
        job.state = "cancelled"
        self._release(job)

    def finish(self, identifier: str, outcome: str) -> None:
        job = self.jobs[identifier]
        if job.state != "running":
            raise ValueError("Ambiguous job must be reconciled before normal completion")
        if outcome not in {"completed", "failed"}:
            raise ValueError("Invalid executor outcome")
        job.state = outcome
        self._release(job)

    def _release(self, job: Job) -> None:
        for r in job.resources:
            if self.owners.get(r) == job.id:
                del self.owners[r]

    def accepts_reply(
        self, identifier: str, epoch: int, observation_id: str, now: float, max_age: float
    ) -> bool:
        if identifier not in self.jobs:
            return False
        if (
            any(
                isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                for x in [now, max_age]
            )
            or max_age < 0
        ):
            return False
        job = self.jobs[identifier]
        return (
            job.state == "running"
            and epoch == job.epoch == self.epoch
            and observation_id == job.observation_id
            and job.observation_time <= now <= job.deadline
            and now - job.observation_time <= max_age
        )
