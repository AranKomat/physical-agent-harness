"""Live callback bridge for a task-trained fixture, not a semantic task solver."""

import math
from dataclasses import asdict

from physical_harness.core.contracts import SkillRequest
from physical_harness.core.events import EventBus, EventType, RuntimeEvent
from physical_harness.reasoning.runtime import HarnessRuntime
from physical_harness.reasoning.selection import ExecutiveLoop
from physical_harness.reasoning.verification import VerificationRouter
from physical_harness.world.ledger import TaskLedger, TaskPredicate


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
        memory_sidecar=None,
        current_place_id=None,
    ):
        self.state = state
        self.ledger = TaskLedger(state)
        self.ledger.add(TaskPredicate("radio", "ON(radio)", bindings=(("radio", "power", "on"),)))
        self.verifier = verifier or VerificationRouter(UnknownRadioWorld())
        self.after_observer = after_observer
        self.on_verified = on_verified
        self.memory_sidecar = memory_sidecar
        self.current_place_id = current_place_id
        if memory_sidecar is not None and memory_sidecar.episode_id != state.episode:
            raise ValueError("Memory sidecar belongs to another episode")
        self.last_end = 0.0
        self.seen = set()
        self.records = []
        self.memory_shadow = []

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
        event_bus = EventBus()
        if self.memory_sidecar is not None:
            places = (self.current_place_id,) if self.current_place_id else ()
            self.memory_sidecar.bind_skill(
                skill_id,
                entity_ids=("radio",),
                place_ids=places,
            )
            event_bus.subscribe(self.memory_sidecar.record_event)
        runtime = HarnessRuntime(
            state.episode,
            Motor(),
            self.verifier,
            events=event_bus,
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

        def build_context(event):
            base = {
                **state.project("Turn on radio (integration only)", ["robot", "radio"], []),
                "boundary": boundary,
                "trigger": event.type.value,
            }
            if self.memory_sidecar is None:
                return base
            context, decision, packet = self.memory_sidecar.prepare_decision(
                decision_id=f"memory:{event.event_id}",
                event_id=event.event_id,
                observed_through=event.sim_time,
                base_context=base,
                query=base["goal"],
                entity_id="radio",
                place_id=self.current_place_id,
                active=False,
            )
            if context != base or "episodic_memory" in context:
                raise RuntimeError("Shadow memory altered executive context")
            self.memory_shadow.append(
                {
                    "decision": asdict(decision),
                    "packet": packet,
                    "active": False,
                }
            )
            return context

        loop = ExecutiveLoop(
            state.episode,
            Executive(),
            build_context,
            {
                "run_skill": run_skill,
                "inspect": lambda args: {"status": "semantic_detector_required", "retry": False},
                "finish": lambda args: {"status": "verified_complete"},
            },
            can_finish=lambda: not self.ledger.pending(),
            max_decisions=2,
        )
        initial_event = RuntimeEvent(EventType.DECISION_REQUIRED, state.episode, start)
        if self.memory_sidecar is not None:
            places = (self.current_place_id,) if self.current_place_id else ()
            self.memory_sidecar.record_event(
                initial_event,
                entity_ids=("radio",),
                place_ids=places,
            )
        shadow_start = len(self.memory_shadow)
        loop.on_event(initial_event)
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
            "memory_shadow": self.memory_shadow[shadow_start:],
        }
        self.records.append(record)
        return record
