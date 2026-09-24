"""A runnable semantic loop, using existing WorldState/ExecutiveLoop/HarnessRuntime.

Historical memory stays shadow-only. Native motion and paid models are separately
opted in. This runner cannot make an incompatible motor policy compatible.
"""
from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from physical_harness.core.contracts import SkillRequest, VerificationRequest, VerificationVerdict
from physical_harness.core.events import EventBus, EventType, RuntimeEvent
from physical_harness.core.evidence import EvidenceStore
from physical_harness.integrations.experiment.actors import (
    FreshVisualVerifier,
    Goal,
    ModelCaptioner,
    ModelExecutive,
)
from physical_harness.integrations.experiment.curation import VisualCurator, validated_coverage
from physical_harness.integrations.experiment.journal import Journal
from physical_harness.integrations.experiment.media import ImageResolver, image_geometry
from physical_harness.integrations.experiment.memory_routing import (
    InformationNeed,
    MemoryTier,
    route_memory_tier,
)
from physical_harness.integrations.experiment.native import NativeBindings, Observation
from physical_harness.integrations.experiment.snapshots import ExperimentContext
from physical_harness.integrations.experiment.validation import (
    digest,
    dumps,
    fields,
    identifiers,
    integer,
    number,
    text,
)
from physical_harness.reasoning.context.rich import BroadMemorySelector, RichContextPolicy
from physical_harness.reasoning.runtime import HarnessRuntime
from physical_harness.reasoning.selection import ExecutiveLoop
from physical_harness.reasoning.verification import VerificationRouter
from physical_harness.world.ledger import TaskLedger, TaskPredicate
from physical_harness.world.memory.integration import DecisionCutoffLog, MemorySidecar
from physical_harness.world.memory.spatial_views import SpatialViewIndex
from physical_harness.world.memory.store import MemoryStore
from physical_harness.world.memory.writer import AsyncAnnotator
from physical_harness.world.state import WorldState


@dataclass(frozen=True)
class Action:
    id: str
    instruction: str
    targets: tuple[str, ...]
    goal_id: str | None = None
    skill_type: str = "policy"
    max_wall_s: float = 30
    max_policy_chunks: int = 20
    max_action_steps: int = 600
    max_settling_steps: int = 0

    def __post_init__(self):
        for value in (self.id, self.instruction, self.skill_type):
            text(value)
        identifiers(self.targets)
        number(self.max_wall_s, minimum=.01)
        integer(self.max_policy_chunks, minimum=1)
        integer(self.max_action_steps, minimum=1)
        integer(self.max_settling_steps, minimum=0)
        if self.max_settling_steps >= self.max_action_steps:
            raise ValueError("Settling reserve must leave at least one task action")
        if self.goal_id is not None:
            text(self.goal_id)


@dataclass(frozen=True)
class RunLimits:
    max_decisions: int = 12
    max_motion_calls: int = 5
    max_sim_s: float = 60
    max_wall_s: float = 600
    max_unchanged_inspections: int = 2
    max_repeated_action: int = 2
    allow_motion: bool = False
    allow_exploratory_motion: bool = False

    def __post_init__(self):
        for value in (self.max_decisions, self.max_motion_calls, self.max_unchanged_inspections,
                      self.max_repeated_action):
            integer(value, minimum=1)
        number(self.max_sim_s, minimum=.01)
        number(self.max_wall_s, minimum=.01)
        if type(self.allow_motion) is not bool or type(self.allow_exploratory_motion) is not bool:
            raise ValueError("Motion permissions must be boolean")
        if self.allow_exploratory_motion and not self.allow_motion:
            raise ValueError("Exploratory motion also requires motion permission")


class NoPredicateOracle:
    name = "no-qualified-geometric-verifier"

    def predicate_confidence(self, predicate):
        return None

    def predicate_evidence(self, predicate):
        return ()


class EpisodeRunner:
    def __init__(self, root: Path, episode: str, goal_text: str, native: NativeBindings,
                 goals: list[Goal], actions: list[Action], executive_model, verifier_model,
                 journal: Journal, *, limits: RunLimits | None = None,
                 context_policy: RichContextPolicy | None = None, topology=None,
                 narrator_model=None, narrator_max_calls: int = 5):
        self.root, self.episode, self.goal_text = Path(root), text(episode), text(goal_text)
        self.root.mkdir(parents=True, exist_ok=True)
        self.native, self.goals, self.actions = native, {g.id: g for g in goals}, {a.id: a for a in actions}
        if len(self.goals) != len(goals) or len(self.actions) != len(actions) or not goals:
            raise ValueError("Distinct goals and action IDs required")
        if len({g.expression for g in goals}) != len(goals):
            raise ValueError("Goal expressions must be unique")
        if any(a.goal_id is not None and a.goal_id not in self.goals for a in actions):
            raise ValueError("Action references unknown goal")
        self.journal = journal
        self.limits = limits or RunLimits()
        self.policy = context_policy or RichContextPolicy()
        if self.limits.allow_motion and not native.qualification_id:
            raise ValueError("A reviewed native binding/fixture qualification ID is required")
        if (
            self.limits.allow_motion
            and not native.motion_qualified
            and not self.limits.allow_exploratory_motion
        ):
            raise PermissionError(
                "Unqualified native motion requires explicit exploratory-motion permission"
            )
        self.world = WorldState(self.root / "world.sqlite", episode)
        self.blobs = EvidenceStore(self.root / "evidence")
        self.ledger = TaskLedger(self.world)
        for g in goals:
            self.ledger.add(TaskPredicate(g.id, g.expression, bindings=(g.binding,)))
        self.memory = MemoryStore(self.root / "episodic.sqlite", episode, self.blobs.read)
        self.cutoffs = DecisionCutoffLog(self.root / "memory-decisions.sqlite", episode)
        self.spatial_views = SpatialViewIndex(episode)
        self.sidecar = MemorySidecar(episode_id=episode, store=self.memory, decisions=self.cutoffs,
                                    resolve_rgb_ref=lambda ref: ref,
                                    current_place=lambda: self.current.place_id if self.current else None,
                                    spatial_index=self.spatial_views)
        self.caption_stop = threading.Event()
        self.annotator = None
        self.caption_timeout_s = 5
        if narrator_model is not None:
            captioner = ModelCaptioner(narrator_model, self.memory)
            stages = 2 if (narrator_model.settings.dialect == "responses" and
                           narrator_model.settings.use_input_token_endpoint) else 1
            self.caption_timeout_s = stages * getattr(narrator_model.transport, "timeout_s", 5) + 3

            def guarded_caption(packet):
                if self.caption_stop.is_set():
                    raise RuntimeError("Episode stopped; queued narration not sent")
                return captioner(packet)

            self.annotator = AsyncAnnotator(self.memory, guarded_caption, model=narrator_model.name,
                                            prompt_id="experiment-v010", queue_size=2,
                                            max_calls=narrator_max_calls).start()
            self.sidecar.annotator = self.annotator
        self.curator = VisualCurator(self.memory, self.blobs)
        self.context_builder = ExperimentContext(self.world, self.policy)
        self.selector = BroadMemorySelector(self.memory, self.policy)
        self.resolver = ImageResolver(self.world, self.blobs, self.memory)
        self.events = EventBus()
        self.events.subscribe(self._memory_event)
        self.current = None
        self.current_ids: dict[str, str] = {}
        self.coverage = []
        self.topology = topology
        self.memory_ok = True
        self.pending_motion = False
        self.motion_calls = 0
        self.last_receipt = None
        self.last_end = 0.0
        self.started = time.monotonic()
        self.initial_sim_time = None
        self.action_repeats = {}
        self.verification_attempts = set()
        self.inspections_unchanged = 0
        self._decision_id = ""
        self._last_capture_hash = None
        self.verifier = VerificationRouter(
            NoPredicateOracle(), frontier=FreshVisualVerifier(
                verifier_model, self.resolver, self.goals, self.now, lambda: self.last_end),
            evidence_validator=lambda eid, req: self.resolver.validate_after(
                eid, req, self.now(), self.last_end))
        self.runtime = HarnessRuntime(episode, self, self.verifier, events=self.events,
                                      after_observer=self._after, on_verified=self._completed)
        self.executive = ModelExecutive(executive_model, self.resolver, self.now,
                                        lambda: "executive:" + self._decision_id)
        self.loop = ExecutiveLoop(
            episode, self.executive, self._context,
            {"run_skill": self._skill_tool, "inspect": self._inspect,
             "request_verification": self._verify_tool, "finish": self._finish,
             "stop": self._stop},
            can_finish=self.can_finish, on_decision=self._route_shadow_memory,
            max_decisions=self.limits.max_decisions,
            max_context_bytes=self.policy.max_metadata_bytes)
        self.journal.put("run", "manifest", {
            "episode": episode, "goal_text": goal_text, "native": native.name,
            "native_qualification": native.qualification_id, "simulated": native.simulated,
            "motion_qualified": native.motion_qualified,
            "clearance_status": native.clearance_status,
            "exploratory_motion": self.limits.allow_exploratory_motion,
            "goals": [asdict(g) for g in goals], "actions": [asdict(a) for a in actions],
            "limits": asdict(self.limits), "context_policy": asdict(self.policy),
            "memory_mode": "shadow", "spatial_memory_mode": "shadow",
            "narrator_enabled": narrator_model is not None,
            "benchmark_success": "not_available_to_agent"})

    @property
    def name(self):
        return self.native.name

    def now(self):
        return self.current.sim_time if self.current else 0.0

    def _check_limits(self):
        if time.monotonic() - self.started > self.limits.max_wall_s:
            raise RuntimeError("Episode wall deadline exceeded")
        if self.initial_sim_time is not None and self.now() - self.initial_sim_time > self.limits.max_sim_s:
            raise RuntimeError("Episode simulation-time budget exceeded")

    def _memory_error(self, stage, exc):
        self.memory_ok = False
        self.journal.put("memory_error", stage + ":" + str(self.motion_calls) + ":" + str(self.loop.calls),
                         {"error": type(exc).__name__, "stage": stage,
                          "note": "Shadow failure cannot certify or request physical action"})

    def _memory_event(self, event):
        self.journal.put("event", event.event_id, asdict(event))
        if self.memory_ok:
            try:
                self.sidecar.record_event(event, narrate=(self.annotator is not None and event.type in {
                    EventType.SKILL_VERIFIED, EventType.SKILL_FAILED, EventType.SKILL_STALLED,
                    EventType.TARGET_LOST, EventType.ARRIVED, EventType.DOOR_BLOCKED}))
            except Exception as exc:
                self._memory_error("event", exc)

    def capture(self) -> bool:
        self._check_limits()
        observation = self.native.observe()
        if not isinstance(observation, Observation) or observation.episode != self.episode:
            raise ValueError("Native observer returned a foreign or untyped observation")
        descriptor = {"id": observation.id, "at": observation.sim_time,
                      "cameras": {c.camera: hashlib.sha256(c.data).hexdigest() for c in observation.cameras},
                      "estimates": [asdict(e) for e in observation.estimates],
                      "boxes": [asdict(b) for b in observation.boxes],
                      "place": observation.place_id, "description": observation.place_description,
                      "coverage": [asdict(c) for c in observation.coverage],
                      "legal_envelope": observation.legal_envelope}
        hashed = digest(descriptor)
        if self.current and observation.id == self.current.id:
            if hashed != self._last_capture_hash:
                raise ValueError("Same observation ID changed its content")
            return False
        if self.current and observation.sim_time <= self.current.sim_time:
            raise ValueError("New native observations require increasing simulation time")
        if self.initial_sim_time is None:
            self.initial_sim_time = observation.sim_time
        initial_observation = self.current is None
        self.current, self._last_capture_hash = observation, hashed
        self.current_ids = {}
        refs, intrinsics = {}, {}
        for camera in observation.cameras:
            width, height, suffix = image_geometry(camera.data)
            uri = self.blobs.put(camera.data, suffix)
            eid = "rgb:" + digest([self.episode, observation.id, camera.camera])[:40]
            self.world.add_evidence(eid, observation.sim_time, "perception", uri,
                                    {"media_type": "image", "camera": camera.camera,
                                     "width": width, "height": height,
                                     "observation_id": observation.id})
            self.current_ids[camera.camera] = eid
            refs[camera.camera] = uri
            intrinsics[camera.camera] = {"width": width, "height": height}
        for estimate in observation.estimates:
            self.world.update(estimate.entity, estimate.predicate, estimate.value,
                              self.current_ids[estimate.camera], epistemic=estimate.epistemic)
        # A tracker owns identity; no label-based merging or physical-state inference.
        for box in observation.boxes:
            self.world.update(box.entity, "identity_candidates", dumps(box.identity_candidates).decode(),
                              self.current_ids[box.camera])
        self.coverage = validated_coverage(observation, self.current_ids, self.world)
        if self.memory_ok:
            try:
                memory_envelope = {
                    "episode_id": self.episode, "observation_id": observation.id,
                    "sim_time": observation.sim_time, "rgb_refs": refs,
                    "camera_intrinsics": intrinsics,
                }
                keyframe_reason = None
                if observation.legal_envelope is not None:
                    memory_envelope = dict(observation.legal_envelope)
                    memory_envelope["rgb_refs"] = refs
                    keyframe_reason = "initial" if initial_observation else "decision_required"
                entity_ids = tuple(dict.fromkeys(
                    [box.entity for box in observation.boxes]
                    + [estimate.entity for estimate in observation.estimates]
                ))
                place_ids = (observation.place_id,) if observation.place_id else ()
                assets = self.sidecar.ingest_observation(
                    memory_envelope,
                    keyframe_reason=keyframe_reason,
                    keyframe_entity_ids=entity_ids,
                    keyframe_place_ids=place_ids,
                )
                self.sidecar.write_spatial_snapshot(self.root / "spatial-memory.json")
                cards = self.curator.ingest(observation, {a.camera: a for a in assets})
                self.journal.put("curation", observation.id, {"cards": cards})
                if self.annotator is not None:
                    for card_id in cards:
                        self.annotator.submit(card_id, self.memory.cutoff(observation.sim_time))
            except Exception as exc:
                self._memory_error("capture", exc)
        self.journal.put("observation", observation.id,
                         {"descriptor": descriptor, "images": self.current_ids})
        self._check_limits()
        return True

    def _context(self, event):
        self._check_limits()
        self._decision_id = event.event_id
        focus = tuple(dict.fromkeys(t for g in self.goals.values() for t in g.targets))
        context = self.context_builder.build(
            now=self.now(), goal=self.goal_text, focus_entities=focus,
            image_evidence=list(self.current_ids.values()), runtime_events=self.events.recent(24),
            current_place=self.current.place_id, topology=self.topology,
            observation_coverage=self.coverage,
            executor_summary={"outcome": self.last_receipt.outcome} if self.last_receipt else {})
        context["available_actions"] = [asdict(a) for a in self.actions.values()]
        context["available_goals"] = [{"id": g.id, "expression": g.expression,
                                      "observable_from_rgb": g.observable_from_rgb}
                                     for g in self.goals.values()]
        context["limits_remaining"] = {"motion_calls": self.limits.max_motion_calls - self.motion_calls,
                                      "decisions": self.limits.max_decisions - self.loop.calls}
        context["available_tools"] = self._available_tools()
        # Immutable M0 is captured now. Offline replay must NEVER rebuild from final WorldState.
        cutoff = self.memory.cutoff(self.now())
        record = {"base_context": context, "memory_cutoff": asdict(cutoff),
                  "context_policy": asdict(self.policy), "event_id": event.event_id,
                  "focus_entities": list(focus), "current_place": self.current.place_id}
        self.journal.put("decision", event.event_id, record)
        self.cutoffs.reserve(decision_id=event.event_id, event_id=event.event_id, cutoff=cutoff,
                             query="", entity_id=None, place_id=self.current.place_id, active=False)
        return context

    def _available_tools(self):
        tools = []
        if (
            self.limits.allow_motion
            and not self.pending_motion
            and self.motion_calls < self.limits.max_motion_calls
        ):
            tools.append("run_skill")
        if self.limits.max_decisions - self.loop.calls > 1:
            tools.append("inspect")
        if (
            self.current is not None
            and self.current.id not in self.verification_attempts
            and any(goal.observable_from_rgb for goal in self.goals.values())
        ):
            tools.append("request_verification")
        if self.can_finish():
            tools.append("finish")
        tools.append("stop")
        return tools

    def _route_shadow_memory(self, event, decision):
        """Freeze need and retrieve the selected shadow tier after model work."""
        if event.event_id != self._decision_id:
            raise ValueError("Shadow route does not match the active decision")
        try:
            need = InformationNeed.from_dict(decision.get("information_need"))
            route = route_memory_tier(need)
            saved = self.cutoffs.get(event.event_id)
            self.journal.put("shadow_route", event.event_id, {
                "event_id": event.event_id,
                "observed_through": saved.cutoff.observed_through,
                "information_need": asdict(need),
                "selected_tier": route.tier.value,
                "reasons": list(route.reasons),
                "active": False,
                "declared_before_retrieval": True,
            })
            if route.tier == MemoryTier.CURRENT:
                packet = {
                    "schema_version": 1,
                    "cutoff": asdict(saved.cutoff),
                    "cards": [],
                    "images": [],
                    "selection_policy": "M0: no historical retrieval",
                }
            else:
                focus = tuple(dict.fromkeys(t for g in self.goals.values() for t in g.targets))
                packet = self.selector.packet(
                    saved.cutoff,
                    goal=self.goal_text[:1900],
                    focus_entities=focus,
                    current_place=self.current.place_id,
                )
                if route.tier == MemoryTier.EVENTS:
                    policy = str(packet.get("selection_policy", ""))
                    packet = dict(
                        packet,
                        images=[],
                        selection_policy=(policy + "; M1 event/text-only shadow route").lstrip("; "),
                    )
            self.journal.put("shadow_packet", event.event_id, packet)
            self.cutoffs.finalize(
                event.event_id,
                tuple(card["card_id"] for card in packet["cards"]),
            )
        except Exception as exc:
            self._memory_error("prospective_routing", exc)

    def _arguments(self, arguments):
        fields(arguments, {"action_id", "goal_id", "reason"})
        if not isinstance(arguments["reason"], str) or len(arguments["reason"]) > 1200:
            raise ValueError("Bounded decision note required")

    def _skill_tool(self, arguments):
        self._arguments(arguments)
        if not self.limits.allow_motion:
            raise PermissionError("Motion disabled")
        if self.pending_motion or self.motion_calls >= self.limits.max_motion_calls:
            raise RuntimeError("Motion budget/ownership gate blocked the action")
        action = self.actions.get(arguments["action_id"])
        if action is None or arguments["goal_id"] != action.goal_id:
            raise ValueError("Unknown action or altered goal binding")
        repeats = self.action_repeats.get(action.id, 0) + 1
        if repeats > self.limits.max_repeated_action:
            raise RuntimeError("Repeated action limit; stop instead of blind retry")
        self.action_repeats[action.id] = repeats
        goal = self.goals.get(action.goal_id)
        request = SkillRequest(
            "skill:" + self._decision_id, action.skill_type, action.instruction,
            target_entities=action.targets, expected_predicates=(goal.expression,) if goal else (),
            max_wall_s=action.max_wall_s, max_policy_chunks=action.max_policy_chunks,
            source_observation_id=self.current.id,
            metadata={"action_id": action.id, "goal_id": action.goal_id,
                      "max_action_steps": action.max_action_steps,
                      "max_settling_steps": action.max_settling_steps})
        if goal:
            self.ledger.set_status(goal.id, "running")
        if self.memory_ok:
            try:
                self.sidecar.bind_skill(
                    request.skill_id,
                    entity_ids=action.targets,
                    place_ids=(self.current.place_id,) if self.current.place_id else (),
                )
            except Exception as exc:
                self._memory_error("bind_skill", exc)
        before = tuple(self.current_ids.values())
        receipt, verification = self.runtime.execute_skill(request, before_evidence_ids=before)
        if verification is not None:
            self.verification_attempts.add(self.current.id)
        if goal and self.ledger.get(goal.id).status != "observed_complete":
            self.ledger.set_status(goal.id, "needs_verification")
        self.journal.put("skill_result", request.skill_id, {
            "receipt": asdict(receipt), "verification": asdict(verification) if verification else None})
        return {"outcome": receipt.outcome, "verdict": verification.verdict.value if verification else None}

    def run_skill(self, request):
        self._check_limits()
        # Simulation is paused during reasoning in this first runner. Reobserve
        # before dispatch; a changed snapshot invalidates the decision before motion.
        if self.capture() or request.source_observation_id != self.current.id:
            raise RuntimeError("Stale executive decision; no native action dispatched")
        start = self.now()
        self.journal.put("action_reserved", request.skill_id, {
            "start": start, "instruction": request.instruction, "metadata": request.metadata})
        self.world.record_command(request.skill_id, start, {
            "instruction": request.instruction, "action_id": request.metadata["action_id"]})
        self.pending_motion = True
        self.motion_calls += 1
        receipt = self.native.run_skill(request)
        # Validate clock/epoch/stop BEFORE callbacks can verify or change a task.
        number(receipt.sim_time_start)
        if receipt.outcome not in {"completed", "failed", "stalled", "timeout", "cancelled"}:
            raise ValueError("Unknown native outcome")
        if receipt.skill_id != request.skill_id or receipt.sim_time_start != start:
            raise ValueError("Native receipt ID or start clock mismatch")
        if number(receipt.sim_time_end) <= start:
            raise ValueError("Native action did not advance simulation clock")
        for field in (receipt.policy_calls, receipt.chunks_generated, receipt.action_steps_executed):
            integer(field)
        if receipt.action_steps_executed > request.metadata["max_action_steps"]:
            raise ValueError("Native backend exceeded the action-step budget")
        if receipt.chunks_generated > request.max_policy_chunks:
            raise ValueError("Native backend exceeded the policy-chunk budget")
        integer(receipt.metadata.get("execution_epoch"))
        if receipt.metadata.get("episode_id") != self.episode or receipt.metadata.get("execution_epoch") != request.execution_epoch:
            raise ValueError("Native receipt requires explicit episode and epoch")
        if receipt.metadata.get("stop_acknowledged") is not True:
            raise RuntimeError("Native stop is unresolved; no further actions allowed")
        self.pending_motion = False
        self.last_receipt, self.last_end = receipt, receipt.sim_time_end
        self.capture()  # Also capture on failure, not just completed prefixes.
        if self.now() < self.last_end:
            raise ValueError("Native post-action observation predates the receipt")
        return receipt

    def _after(self, request, receipt):
        return tuple(self.current_ids.values())

    def _completed(self, request, receipt, verification):
        goal = next(g for g in self.goals.values() if request.expected_predicates == (g.expression,))
        if not goal.verifier_qualification or verification.verdict != VerificationVerdict.VERIFIED:
            raise ValueError("Unqualified completion")
        if not verification.evidence_ids or not all(
            self.resolver.validate_after(i, VerificationRequest(
                "check", request.skill_id, request.expected_predicates,
                after_evidence_ids=tuple(self.current_ids.values())), self.now(), self.last_end)
            for i in verification.evidence_ids
        ):
            raise ValueError("Completion requires fresh current visual evidence")
        eid = verification.evidence_ids[0]
        self.world.update(*goal.binding, eid)
        self.ledger.set_status(goal.id, "observed_complete", eid, now=self.now())

    def _inspect(self, arguments):
        self._arguments(arguments)
        if arguments["action_id"] is not None or arguments["goal_id"] is not None:
            raise ValueError("Inspect is passive and takes no action/goal ID")
        changed = self.capture()
        self.inspections_unchanged = 0 if changed else self.inspections_unchanged + 1
        if self.inspections_unchanged > self.limits.max_unchanged_inspections:
            raise RuntimeError("Repeated unchanged observations; reposition or change sensor is needed")
        self.events.publish(RuntimeEvent(EventType.DECISION_REQUIRED, self.episode, self.now()))
        return {"new_observation": changed}

    def _verify_tool(self, arguments):
        self._arguments(arguments)
        goal = self.goals.get(arguments["goal_id"])
        if arguments["action_id"] is not None or goal is None:
            raise ValueError("Verification requires one known goal")
        if self.current.id in self.verification_attempts:
            raise RuntimeError("Current observation was already verified")
        request = VerificationRequest("manual:" + self._decision_id, "inspect", (goal.expression,),
                                      after_evidence_ids=tuple(self.current_ids.values()),
                                      relevant_entities=goal.targets)
        result = self.verifier.verify(request)
        self.verification_attempts.add(self.current.id)
        if result.verdict == VerificationVerdict.VERIFIED:
            self._completed(SkillRequest("inspect", "inspect", "inspect",
                                        expected_predicates=(goal.expression,)), None, result)
        event = EventType.SKILL_VERIFIED if result.verdict == VerificationVerdict.VERIFIED else EventType.VERIFIER_UNCERTAIN
        self.events.publish(RuntimeEvent(event, self.episode, self.now(),
                                         {"verdict": result.verdict.value, "reason": result.explanation}))
        self.journal.put("verification", request.request_id, asdict(result))
        return {"verdict": result.verdict.value}

    def can_finish(self):
        return not self.pending_motion and not self.ledger.pending()

    def _finish(self, arguments):
        self._arguments(arguments)
        if arguments["goal_id"] is not None or arguments["action_id"] is not None:
            raise ValueError("Finish takes no action or goal ID")
        return {"harness_goals_complete": True, "benchmark_success": "not_claimed"}

    def _stop(self, arguments):
        self._arguments(arguments)
        if arguments["goal_id"] is not None or arguments["action_id"] is not None:
            raise ValueError("Stop takes no action or goal ID")
        return {"harness_goals_complete": False, "benchmark_success": "not_claimed"}

    def run(self) -> dict:
        error = None
        error_message = None
        stop_ack = False
        try:
            self.capture()
            self.events.publish(RuntimeEvent(EventType.DECISION_REQUIRED, self.episode, self.now()))
            while not self.loop.finished:
                self._check_limits()
                event = self.events.recent(1)[0]
                self.loop.on_event(event)
        except Exception as exc:
            error = type(exc).__name__
            error_message = str(exc)
            self.journal.put("run_error", "terminal", {
                "error": error, "message": error_message, "at": self.now(),
            })
        finally:
            # A stop acknowledgement is not inferred from elapsed time or process death.
            try:
                stop_ack = self.native.stop() is True
            except Exception:
                stop_ack = False
        self.caption_stop.set()
        narrator_stopped = self.annotator is None or self.annotator.close(self.caption_timeout_s)
        result = {"episode": self.episode, "simulated": self.native.simulated,
                  "narrator_stopped": narrator_stopped,
                  "harness_finished": self.loop.finished, "benchmark_success": "not_claimed",
                  "error": error, "error_message": error_message,
                  "stop_acknowledged": stop_ack,
                  "motion_qualified": self.native.motion_qualified,
                  "clearance_status": self.native.clearance_status,
                  "exploratory_motion": self.limits.allow_exploratory_motion,
                  "sim_time": self.now(), "executive_calls": self.loop.calls,
                  "motion_calls": self.motion_calls, "memory_shadow_ok": self.memory_ok,
                  "spatial_keyframes": len(self.spatial_views.keyframes),
                  "pending_goals": [g.id for g in self.ledger.pending()],
                  "accounting": self.journal.report()}
        (self.root / "report.json").write_bytes(dumps(result))
        self.journal.put("run", "report", result)
        return result

    def close(self):
        self.caption_stop.set()
        if self.annotator is not None and not self.annotator.close(self.caption_timeout_s):
            raise RuntimeError("Narrator transport did not stop; do not close a live memory database")
        self.cutoffs.close()
        self.memory.close()
        self.world.close()
