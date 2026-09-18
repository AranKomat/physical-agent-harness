from __future__ import annotations

from ..contracts import SkillReceipt, SkillRequest


class DeterministicMotorStub:
    name = "stub"

    def __init__(self, outcome: str = "completed"):
        self.outcome = outcome
        self.clock = 0.0

    def run_skill(self, request: SkillRequest) -> SkillReceipt:
        start = self.clock
        self.clock += 1.0
        return SkillReceipt(
            skill_id=request.skill_id,
            backend=self.name,
            outcome=self.outcome,
            sim_time_start=start,
            sim_time_end=self.clock,
            policy_calls=1,
            chunks_generated=1,
            action_steps_executed=8,
            observed_predicates=request.expected_predicates if self.outcome == "completed" else (),
        )
