from physical_harness.adapters.motor_stub import DeterministicMotorStub
from physical_harness.adapters.rtsm import RTSMWorldAdapter
from physical_harness.contracts import SkillRequest, VerificationVerdict
from physical_harness.runtime import HarnessRuntime
from physical_harness.verification import VerificationRouter


def test_completed_skill_verified_by_world_predicate():
    class ObservedWorld:
        name = "observed-test-fixture"

        def predicate_confidence(self, predicate):
            return 0.97

        def predicate_evidence(self, predicate):
            return ("observed-frame",)

    world = ObservedWorld()
    runtime = HarnessRuntime(
        episode_id="ep1",
        motor=DeterministicMotorStub(),
        verifier=VerificationRouter(world=world),
    )
    receipt, verification = runtime.execute_skill(
        SkillRequest(
            skill_id="s1",
            skill_type="pick",
            instruction="pick up the candle",
            target_entities=("candle_1",),
            expected_predicates=("HELD_BY(candle_1,robot)",),
        )
    )
    assert receipt.outcome == "completed"
    assert verification.verdict == VerificationVerdict.VERIFIED
    assert runtime.events.recent()[-1].type.value == "skill_verified"


def test_failed_skill_does_not_call_verifier():
    world = RTSMWorldAdapter()
    runtime = HarnessRuntime(
        episode_id="ep2",
        motor=DeterministicMotorStub(outcome="failed"),
        verifier=VerificationRouter(world=world),
    )
    receipt, verification = runtime.execute_skill(
        SkillRequest(
            skill_id="s2",
            skill_type="pick",
            instruction="pick up the candle",
            expected_predicates=("HELD_BY(candle_1,robot)",),
        )
    )
    assert receipt.outcome == "failed"
    assert verification is None
    assert runtime.events.recent()[-1].type.value == "skill_failed"


def test_unverified_completion_is_not_a_verified_event():
    runtime = HarnessRuntime("ep", DeterministicMotorStub(), VerificationRouter(RTSMWorldAdapter()))
    runtime.execute_skill(SkillRequest("s", "inspect", "inspect"))
    assert runtime.events.recent()[-1].type.value == "decision_required"


def test_zero_recent_events_is_empty():
    runtime = HarnessRuntime("ep", DeterministicMotorStub(), VerificationRouter(RTSMWorldAdapter()))
    runtime.execute_skill(SkillRequest("s", "inspect", "inspect"))
    assert runtime.events.recent(0) == []
