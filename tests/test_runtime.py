from physical_harness.adapters.motor_stub import DeterministicMotorStub
from physical_harness.adapters.rtsm import RTSMWorldAdapter
from physical_harness.contracts import SkillRequest, VerificationVerdict
from physical_harness.ledger import TaskLedger, TaskPredicate
from physical_harness.runtime import HarnessRuntime
from physical_harness.state import WorldState
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


def test_closed_semantic_boundary_observes_verifies_updates_ledger_then_emits():
    order = []
    with WorldState(":memory:", "ep") as state:
        ledger = TaskLedger(state)
        ledger.add(TaskPredicate("radio", "ON(radio)", bindings=(("radio", "power", "on"),)))

        class World:
            name = "observed-radio"

            def predicate_confidence(self, predicate):
                order.append("verify")
                return 0.99

            def predicate_evidence(self, predicate):
                return ("after",)

        def observe_after(request, receipt):
            order.append("observe_after")
            state.add_evidence("after", receipt.sim_time_end, "perception", "after.png")
            state.update("radio", "power", "on", "after")
            return ("after",)

        def complete(request, receipt, verification):
            order.append("ledger")
            ledger.set_status("radio", "observed_complete", "after", now=receipt.sim_time_end)

        runtime = HarnessRuntime(
            "ep",
            DeterministicMotorStub(),
            VerificationRouter(World()),
            after_observer=observe_after,
            on_verified=complete,
        )
        runtime.events.subscribe(lambda event: order.append("event"))
        receipt, verification = runtime.execute_skill(
            SkillRequest("s", "press", "turn on radio", expected_predicates=("ON(radio)",)),
            before_evidence_ids=(),
        )
        assert receipt.outcome == "completed"
        assert verification.verdict == VerificationVerdict.VERIFIED
        assert ledger.get("radio").status == "observed_complete"
        assert order == ["observe_after", "verify", "ledger", "event"]


def test_closed_semantic_boundary_requires_after_evidence_and_never_completes_uncertain():
    called = []
    request = SkillRequest("s", "press", "turn on radio", expected_predicates=("ON(radio)",))
    runtime = HarnessRuntime(
        "ep",
        DeterministicMotorStub(),
        VerificationRouter(RTSMWorldAdapter()),
        after_observer=lambda *_: (),
        on_verified=lambda *_: called.append(True),
    )
    try:
        runtime.execute_skill(request)
    except ValueError as error:
        assert "fresh evidence" in str(error)
    else:
        raise AssertionError("Missing after evidence was accepted")
    assert called == []


def test_invalid_before_evidence_is_rejected_before_motor_action():
    motor = DeterministicMotorStub()
    runtime = HarnessRuntime("ep", motor, VerificationRouter(RTSMWorldAdapter()))
    try:
        runtime.execute_skill(
            SkillRequest("s", "press", "turn on radio", expected_predicates=("ON(radio)",)),
            before_evidence_ids=["not-a-tuple"],
        )
    except ValueError as error:
        assert "Before evidence" in str(error)
    else:
        raise AssertionError("Malformed before evidence was accepted")
    assert motor.clock == 0
