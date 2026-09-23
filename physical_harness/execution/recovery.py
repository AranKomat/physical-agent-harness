"""One-shot, evidence-bound recovery previews. Native IK remains an injected service."""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, replace
from typing import Callable

from physical_harness.core.contracts import SkillReceipt
from physical_harness.core.jobs import JobManager
from physical_harness.execution.policy import MotorObservation


@dataclass(frozen=True)
class RecoveryPreview:
    token: str
    episode_id: str
    execution_epoch: int
    observation_id: str
    evidence_id: str
    arm: str
    delta_xyz: tuple[float, float, float]
    expires_at: float


class RecoveryService:
    name = "bounded-l3"

    def __init__(
        self,
        episode_id: str,
        jobs: JobManager,
        observe: Callable[[], MotorObservation],
        evidence_valid: Callable[[str, MotorObservation], bool],
        collision_check: Callable[[RecoveryPreview], bool],
        execute_native: Callable[[RecoveryPreview], SkillReceipt],
        *,
        recovery_allowed: Callable[[], bool],
        qualified: bool = False,
        max_translation_m: float = 0.10,
        ttl_s: float = 2,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not 0 < max_translation_m <= 0.25 or not 0 < ttl_s <= 5:
            raise ValueError("Invalid bounded recovery limits")
        self.episode, self.jobs, self.observe = episode_id, jobs, observe
        self.evidence_valid, self.collision_check, self.execute_native = (
            evidence_valid,
            collision_check,
            execute_native,
        )
        self.recovery_allowed, self.qualified = recovery_allowed, qualified
        self.max_translation, self.ttl, self.clock = max_translation_m, ttl_s, clock
        self._previews: dict[str, RecoveryPreview] = {}

    def preview(
        self, arm: str, delta_xyz: tuple[float, float, float], evidence_id: str
    ) -> RecoveryPreview:
        if not self.qualified or not self.recovery_allowed():
            raise ValueError("Native recovery is not qualified/authorized by current failure state")
        if arm not in {"left_arm", "right_arm"}:
            raise ValueError("Recovery supports one arm, never raw torques")
        if len(delta_xyz) != 3 or any(
            isinstance(x, bool) or not math.isfinite(x) for x in delta_xyz
        ):
            raise ValueError("Finite translation required")
        if math.sqrt(sum(x * x for x in delta_xyz)) > self.max_translation:
            raise ValueError("Recovery exceeds local translation bound")
        obs = self.observe()
        if obs.episode_id != self.episode or obs.execution_epoch != self.jobs.epoch:
            raise ValueError("Observation episode/epoch mismatch")
        if not 0 <= self.clock() - obs.captured_wall <= self.ttl:
            raise ValueError("Recovery observation is stale")
        if not self.evidence_valid(evidence_id, obs):
            raise ValueError("Target requires current legal depth/perception evidence")
        preview = RecoveryPreview(
            uuid.uuid4().hex,
            self.episode,
            self.jobs.epoch,
            obs.observation_id,
            evidence_id,
            arm,
            tuple(delta_xyz),
            self.clock() + self.ttl,
        )
        if self.collision_check(preview) is not True:
            raise ValueError("Collision clearance not established from legal observations")
        self._previews = {k: v for k, v in self._previews.items() if v.expires_at > self.clock()}
        self._previews[preview.token] = preview
        return preview

    def execute(self, token: str) -> SkillReceipt:
        preview = self._previews.pop(token, None)
        if preview is None:
            raise ValueError("Unknown or consumed recovery preview")
        obs = self.observe()
        if (
            not self.qualified
            or not self.recovery_allowed()
            or self.clock() >= preview.expires_at
            or obs.episode_id != preview.episode_id
            or obs.execution_epoch != preview.execution_epoch
            or self.jobs.epoch != preview.execution_epoch
            or obs.observation_id != preview.observation_id
            or not self.evidence_valid(preview.evidence_id, obs)
            or self.collision_check(preview) is not True
        ):
            raise ValueError("Stale or unsafe recovery preview")
        job = self.jobs.start(
            preview.token,
            self.name,
            (preview.arm,),
            obs.observation_id,
            obs.captured_wall,
            preview.expires_at,
        )
        try:
            receipt = self.execute_native(preview)
            if (
                receipt.skill_id != preview.token
                or receipt.metadata.get("stop_acknowledged") is not True
            ):
                raise ValueError("Recovery stop/receipt not acknowledged")
            if receipt.outcome not in {"completed", "failed", "cancelled", "timeout", "stalled"}:
                raise ValueError("Invalid recovery outcome")
            if self.clock() >= preview.expires_at:
                receipt = replace(
                    receipt,
                    outcome="timeout",
                    metadata={**receipt.metadata, "reason": "recovery_deadline"},
                )
            if job.state == "running":
                self.jobs.finish(
                    job.id, "completed" if receipt.outcome == "completed" else "failed"
                )
            else:
                self.jobs.acknowledge_stopped(job.id)
                receipt = replace(
                    receipt,
                    outcome="cancelled",
                    metadata={**receipt.metadata, "reason": "goal_invalidated"},
                )
            return receipt
        except Exception:
            self.jobs.timeout(job.id)
            raise
