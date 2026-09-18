from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable

from .backends.base import MotorBackend
from .contracts import (
    EventType,
    RuntimeEvent,
    SkillReceipt,
    SkillRequest,
    VerificationRequest,
    VerificationResult,
    VerificationVerdict,
)
from .events import EventBus
from .verification import VerificationRouter


@dataclass
class RuntimeConfig:
    verify_completed_skills: bool = True


class HarnessRuntime:
    """Synchronous semantic-boundary runtime for the first BEHAVIOR experiment."""

    def __init__(
        self,
        episode_id: str,
        motor: MotorBackend,
        verifier: VerificationRouter,
        events: EventBus | None = None,
        config: RuntimeConfig | None = None,
        *,
        after_observer: Callable[[SkillRequest, SkillReceipt], tuple[str, ...]] | None = None,
        on_verified: Callable[[SkillRequest, SkillReceipt, VerificationResult], None]
        | None = None,
    ):
        self.episode_id = episode_id
        self.motor = motor
        self.verifier = verifier
        self.events = events or EventBus()
        self.config = config or RuntimeConfig()
        self.after_observer = after_observer
        self.on_verified = on_verified

    def execute_skill(
        self, request: SkillRequest, *, before_evidence_ids: tuple[str, ...] = ()
    ) -> tuple[SkillReceipt, VerificationResult | None]:
        if not isinstance(before_evidence_ids, tuple) or any(
            not isinstance(value, str) or not value.strip() for value in before_evidence_ids
        ):
            raise ValueError("Before evidence IDs must be a tuple of nonempty strings")
        receipt = self.motor.run_skill(request)
        if receipt.skill_id != request.skill_id:
            raise ValueError("Motor receipt does not match skill request")
        if receipt.metadata.get("episode_id", self.episode_id) != self.episode_id:
            raise ValueError("Motor receipt belongs to another episode")
        if (
            receipt.metadata.get("execution_epoch", request.execution_epoch)
            != request.execution_epoch
        ):
            raise ValueError("Motor receipt belongs to another epoch")

        if receipt.outcome != "completed":
            etype = {
                "failed": EventType.SKILL_FAILED,
                "stalled": EventType.SKILL_STALLED,
                "timeout": EventType.EXECUTION_TIMEOUT,
            }.get(receipt.outcome, EventType.SKILL_FAILED)
            if receipt.failure_reason == "target_lost":
                etype = EventType.TARGET_LOST
            self.events.publish(
                RuntimeEvent(
                    etype,
                    self.episode_id,
                    receipt.sim_time_end,
                    {
                        "skill_id": request.skill_id,
                        "reason": receipt.failure_reason or receipt.outcome,
                    },
                )
            )
            return receipt, None

        if not self.config.verify_completed_skills or not request.expected_predicates:
            self.events.publish(
                RuntimeEvent(
                    EventType.DECISION_REQUIRED,
                    self.episode_id,
                    receipt.sim_time_end,
                    {"skill_id": request.skill_id, "verification": "not_performed"},
                )
            )
            return receipt, None

        after_evidence_ids = receipt.evidence_ids
        if self.after_observer is not None:
            after_evidence_ids = self.after_observer(request, receipt)
            if (
                not isinstance(after_evidence_ids, tuple)
                or not after_evidence_ids
                or any(not isinstance(value, str) or not value.strip() for value in after_evidence_ids)
            ):
                raise ValueError("After-observation hook must return fresh evidence IDs")
        verification = self.verifier.verify(
            VerificationRequest(
                request_id=uuid.uuid4().hex,
                skill_id=request.skill_id,
                expected_predicates=request.expected_predicates,
                before_evidence_ids=before_evidence_ids,
                after_evidence_ids=after_evidence_ids,
                relevant_entities=request.target_entities,
                high_consequence=bool(request.metadata.get("high_consequence", False)),
            )
        )

        if verification.verdict == VerificationVerdict.VERIFIED:
            etype = EventType.SKILL_VERIFIED
            if self.on_verified is not None:
                self.on_verified(request, receipt, verification)
        elif verification.verdict == VerificationVerdict.UNCERTAIN:
            etype = EventType.VERIFIER_UNCERTAIN
        else:
            etype = EventType.SKILL_FAILED

        self.events.publish(
            RuntimeEvent(
                etype,
                self.episode_id,
                receipt.sim_time_end,
                {
                    "skill_id": request.skill_id,
                    "verifier": verification.verifier,
                    "verdict": verification.verdict.value,
                    "confidence": verification.confidence,
                },
            )
        )
        return receipt, verification
