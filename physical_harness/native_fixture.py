"""Live callback bridge for a task-trained fixture, not a semantic task solver."""

import math
from dataclasses import asdict

from .contracts import EventType, RuntimeEvent, SkillRequest
from .executive import ExecutiveLoop
from .ledger import TaskLedger, TaskPredicate
from .runtime import HarnessRuntime
from .verification import VerificationRouter


class UnknownRadioWorld:
    name = "radio-semantic-detector-unavailable"

    def predicate_confidence(self, expression):
        return None

    def predicate_evidence(self, expression):
        return ()


class NativeFixtureBridge:
    def __init__(
        self,
        state,
        *,
        verifier=None,
        after_observer=None,
        on_verified=None,
    ):
        self.state = state
        self.ledger = TaskLedger(state)
        self.ledger.add(TaskPredicate("radio", "ON(radio)", bindings=(("radio", "power", "on"),)))
        self.verifier = verifier or VerificationRouter(UnknownRadioWorld())
        self.after_observer = after_observer
        self.on_verified = on_verified
        self.last_end = 0.0
        self.seen = set()
        self.records = []

    def execute(self, skill_id, start, callback, *, before_evidence_ids=()):
        if skill_id in self.seen or start != self.last_end:
            raise ValueError("Duplicate or discontinuous native boundary")
        self.seen.add(skill_id)  # Reserve before any physical action; never retry implicitly.
        state = self.state

        class Motor:
            name = "official-radio-fixture"

            def run_skill(self, request):
                return callback(request)

        class Executive:
            name = "deterministic-integration-executive-not-gpt"

            def decide(self, context):
                if context["boundary"] == "after" and not bridge.ledger.pending():
                    return {"tool": "finish", "arguments": {}}
                return {
                    "tool": "run_skill" if context["boundary"] == "before" else "inspect",
                    "arguments": {},
                }

        bridge = self
        runtime = HarnessRuntime(
            state.episode,
            Motor(),
            self.verifier,
            after_observer=self.after_observer,
            on_verified=self.on_verified,
        )
        boundary = "before"
        result = []

        def run_skill(arguments):
            self.ledger.set_status("radio", "running")
            state.record_command(skill_id, start, {"instruction": "turn on the radio"})
            receipt, verification = runtime.execute_skill(
                SkillRequest(
                    skill_id,
                    "radio_fixture_prefix",
                    "turn on the radio",
                    expected_predicates=("ON(radio)",),
                    target_entities=("radio",),
                ),
                before_evidence_ids=before_evidence_ids,
            )
            if (
                receipt.sim_time_start != start
                or not math.isfinite(receipt.sim_time_end)
                or receipt.sim_time_end <= start
            ):
                raise ValueError("Invalid native receipt clock")
            self.last_end = receipt.sim_time_end
            if self.ledger.get("radio").status != "observed_complete":
                self.ledger.set_status("radio", "needs_verification")
            result.append((receipt, verification))
            return receipt

        loop = ExecutiveLoop(
            state.episode,
            Executive(),
            lambda event: {
                **state.project("Turn on radio (integration only)", ["robot", "radio"], []),
                "boundary": boundary,
                "trigger": event.type.value,
            },
            {
                "run_skill": run_skill,
                "inspect": lambda args: {"status": "semantic_detector_required", "retry": False},
                "finish": lambda args: {"status": "verified_complete"},
            },
            can_finish=lambda: not self.ledger.pending(),
            max_decisions=2,
        )
        loop.on_event(RuntimeEvent(EventType.DECISION_REQUIRED, state.episode, start))
        boundary = "after"
        event = runtime.events.recent()[-1]
        loop.on_event(event)
        receipt, verification = result[0]
        record = {
            "receipt": asdict(receipt),
            "verification": asdict(verification) if verification else None,
            "event": asdict(event),
            "executive_trace": loop.trace,
            "executive_calls": loop.calls,
            "finished": loop.finished,
            "task_status": self.ledger.get("radio").status,
        }
        self.records.append(record)
        return record
