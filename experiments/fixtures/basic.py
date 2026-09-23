"""Deterministic integration fixture. No real robot, model, or perception inference."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from physical_harness.core.contracts import SkillRequest, VerificationVerdict
from physical_harness.core.events import EventType, RuntimeEvent
from physical_harness.core.evidence import EvidenceStore
from physical_harness.core.ledger import TaskLedger, TaskPredicate
from physical_harness.core.runtime import HarnessRuntime
from physical_harness.execution.policy import (
    ChunkedMotorBackend,
    MotorObservation,
    PolicyChunk,
    SkillFeedback,
)
from physical_harness.reasoning.context.conservative import ContextProjector
from physical_harness.reasoning.selection import ExecutiveLoop
from physical_harness.reasoning.verification import VerificationRouter
from physical_harness.world.state import WorldState


def run_demo(directory: str | Path) -> dict:
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=False)
    episode, predicate = "offline-fixture-episode", "HELD_BY(candle_1,robot)"
    assets = EvidenceStore(output / "evidence")
    with WorldState(output / "world.sqlite", episode) as state:
        ledger = TaskLedger(state)
        ledger.add(TaskPredicate("pick", predicate, bindings=(("candle_1", "holder", "robot"),)))

        class Controller:
            steps = 0
            wall = 10.0
            latest_evidence = ""

            def observe(self):
                return MotorObservation(
                    episode,
                    f"o{self.steps}",
                    0,
                    self.steps / 30,
                    self.wall,
                    evidence_ids=(self.latest_evidence,) if self.latest_evidence else (),
                )

            def validate_action(self, action):
                if len(action) != 1 or not -1 <= action[0] <= 1:
                    raise ValueError("Fixture action outside bounds")

            def step(self, action, deadline):
                self.steps += 1
                self.wall += 0.01
                self.latest_evidence = f"frame-{self.steps}"
                data = json.dumps({"fixture": True, "step": self.steps}).encode()
                uri = assets.put(data, ".json")
                state.add_evidence(
                    self.latest_evidence, self.steps / 30, "perception", uri, {"fixture": True}
                )
                if self.steps >= 6:
                    state.update("candle_1", "holder", "robot", self.latest_evidence)
                return self.observe()

            def stop(self, resources):
                return True

        controller = Controller()

        class Policy:
            name = "deterministic-fixture-not-a-vla"

            def infer(self, observation, instruction, deadline):
                return PolicyChunk(episode, observation.observation_id, 0, ((0.1,),) * 4)

        class World:
            name = "fixture-observation-world"

            def predicate_confidence(self, expression):
                b = state.belief("candle_1", "holder")
                return 0.99 if expression == predicate and b and b["object"] == "robot" else None

            def predicate_evidence(self, expression):
                b = state.belief("candle_1", "holder")
                return (b["evidence_id"],) if expression == predicate and b else ()

        motor = ChunkedMotorBackend(
            episode,
            Policy(),
            controller,
            lambda obs, req: SkillFeedback(
                complete=controller.steps >= 6, progress=controller.steps
            ),
            qualified=True,
            prefix_steps=2,
            clock=lambda: controller.wall,
        )
        runtime = HarnessRuntime(episode, motor, VerificationRouter(World()))
        projector = ContextProjector(state)
        receipts = []

        def skill(arguments):
            if arguments != {"task_id": "pick"}:
                raise ValueError("Unknown fixture task")
            ledger.set_status("pick", "running")
            state.record_command("skill-pick", controller.steps / 30, {"task_id": "pick"})
            receipt, verification = runtime.execute_skill(
                SkillRequest(
                    "skill-pick",
                    "pick",
                    "pick up candle_1",
                    target_entities=("candle_1",),
                    expected_predicates=(predicate,),
                )
            )
            receipts.append(asdict(receipt))
            ledger.set_status("pick", "needs_verification")
            if verification and verification.verdict == VerificationVerdict.VERIFIED:
                ledger.set_status(
                    "pick",
                    "observed_complete",
                    verification.evidence_ids[0],
                    now=receipt.sim_time_end,
                )
            return receipt

        class Executive:
            name = "deterministic-fixture-not-gpt"

            def decide(self, context):
                pending = any(t["status"] != "observed_complete" for t in context["task_ledger"])
                return (
                    {"tool": "run_skill", "arguments": {"task_id": "pick"}}
                    if pending
                    else {"tool": "finish", "arguments": {}}
                )

        loop = ExecutiveLoop(
            episode,
            Executive(),
            lambda event: projector.build(
                goal="Pick up candle_1 (offline fixture)",
                relevant_entities=["candle_1"],
                image_evidence=[],
            ),
            {"run_skill": skill, "finish": lambda args: "finished"},
            can_finish=lambda: not ledger.pending() and not motor.jobs.owners,
        )
        loop.on_event(RuntimeEvent(EventType.DECISION_REQUIRED, episode, 0))
        loop.on_event(runtime.events.recent()[-1])
        summary = {
            "kind": "offline-integration-fixture",
            "native_ready": False,
            "real_model_calls": 0,
            "native_actions": 0,
            "executive_decisions": loop.calls,
            "finished": loop.finished,
            "task_status": ledger.get("pick").status,
            "receipts": receipts,
            "events": [asdict(e) for e in runtime.events.recent()],
            "trace": loop.trace,
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
