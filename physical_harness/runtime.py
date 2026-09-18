from __future__ import annotations

import uuid
from dataclasses import dataclass

from .backends.base import MotorBackend
from .contracts import (
    EventType,
    RuntimeEvent,
    SkillReceipt,
    SkillRequest,
    VerificationRequest,
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
    ):
        self.episode_id = episode_id
        self.motor = motor
        self.verifier = verifier
        self.events = events or EventBus()
        self.config = config or RuntimeConfig()

    def execute_skill(self, request: SkillRequest) -> tuple[SkillReceipt, object | None]:
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

        verification = self.verifier.verify(
            VerificationRequest(
                request_id=uuid.uuid4().hex,
                skill_id=request.skill_id,
                expected_predicates=request.expected_predicates,
                after_evidence_ids=receipt.evidence_ids,
                relevant_entities=request.target_entities,
                high_consequence=bool(request.metadata.get("high_consequence", False)),
            )
        )

        if verification.verdict == VerificationVerdict.VERIFIED:
            etype = EventType.SKILL_VERIFIED
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
