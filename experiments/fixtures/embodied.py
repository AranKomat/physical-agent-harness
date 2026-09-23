"""Explicit synthetic software fixture: no simulator, model, GPU or robot is used."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

from physical_harness.core.actions import (
    Basis,
    Check,
    Gripper,
    Intent,
    Parameters,
    Pose,
    Primitive,
    Program,
    Proposal,
    Review,
    Step,
    Verb,
)
from physical_harness.core.coordinator import DiscoveryCoordinator
from physical_harness.core.discovery import FrameRef, RegionRef
from physical_harness.core.jobs import JobManager
from physical_harness.core.tasks import Fact, FactPacket
from physical_harness.execution.actions import ActionExecutor, Driver, StepReceipt, StepReview
from physical_harness.integrations.experiment.journal import Journal
from physical_harness.perception.discovery import AsyncDiscovery
from physical_harness.perception.keyframes import (
    SemanticKeyframes,
    ViewSample,
    thumbnail_descriptor,
)
from physical_harness.planning.actions.compiler import Catalog, CompiledAction
from physical_harness.planning.tasks.capabilities import MacroRegistry, standard_macro
from physical_harness.reasoning.context.compact import ControlMode, ExecutiveOption, build_context
from physical_harness.reasoning.executive import ExecutiveCadence, ExecutiveSession, RebindReview
from physical_harness.world.inventory import SemanticInventory


def run_demo(output: str | Path) -> dict:
    """Write a new run directory with a real journal and fake perception/actuation."""
    from PIL import Image
    target = Path(output)
    target.mkdir(parents=True, exist_ok=False)
    now = [100.]
    journal = Journal(target / "journal.sqlite", "fixture", max_microusd=0, max_calls=10)
    worker = None
    images = {}

    def basis(seq, sim=0.):
        return Basis("fixture", f"obs-{seq}", f"hash-{seq}", sim, now[0], "local", "frame-v1", "geometry-v1",
                     0, "fixture-robot", "fixture-calibration", (f"evidence-{seq}",), "fixture")

    def image(b):
        im = Image.new("RGB", (64, 48), (125, 30, 30))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        raw = buf.getvalue()
        f = FrameRef(b, "image-"+b.observation_id, hashlib.sha256(raw).hexdigest(), "head", 64, 48, now[0])
        images[f.asset_id] = raw
        return f

    def read_only_semantics(request, deadline):
        f = request.frames[-1]
        return {"request_id": request.id, "request_fingerprint": request.fingerprint,
                "updates": [{"local_id": "found", "frame_id": f.asset_id,
                             "region_id": "region-1", "box": None, "known_id": None,
                             "description": "A red rectangular device: possible radio.",
                             "hypotheses": ["radio", "speaker"], "status": "hypothesis",
                             "retention": "retain", "value": {"task": 3, "future": 1, "landmark": 0,
                             "novelty": 1, "uncertainty_value": 2, "redundancy": 0, "transience": 0},
                             "needs_view": True}],
                "attention": [{"local_id": "found", "reason": "possible target", "significance": "high"}],
                "scene_summary": "Synthetic red patch only; not recognition evidence."}

    try:
        inventory = SemanticInventory(journal)
        cadence = ExecutiveCadence()
        worker = AsyncDiscovery(journal=journal, invoke=read_only_semantics, model_name="scripted-fixture",
                                enabled=True, clock=lambda: now[0])
        coordinator = DiscoveryCoordinator(journal=journal, keyframes=SemanticKeyframes(), worker=worker,
                                           inventory=inventory, executive_scheduler=cadence)
        b0 = basis(0)
        f0 = image(b0)
        request = coordinator.observe(ViewSample(f0, thumbnail_descriptor(images[f0.asset_id], f0)),
                                      now=now[0], task="Inspect the red radio", task_revision="goal-1",
                                      regions=(RegionRef("region-1", f0.asset_id, (.2,.2,.8,.8)),), room_id="room")
        if request is None:
            raise RuntimeError("Synthetic discovery request was not admitted")
        # Waiting here is confined to this fixture; production calls poll from the main loop.
        import time
        cutoff = time.monotonic()+2
        while not worker.completed and time.monotonic() < cutoff:
            time.sleep(.005)
        if not worker.completed:
            raise RuntimeError("Synthetic worker failed to return")
        delivered = coordinator.poll(current=b0, now=now[0], task_revision="goal-1")
        if not delivered or not inventory.records:
            raise RuntimeError("Discovery integration did not produce historical inventory")
        gripper = Gripper("fixture", "v1", "fixture", ("finger",), (.04,), (0.,), (0.,), (.05,), Pose("grasp"), .08)

        def catalog(b):
            proposal = Proposal(Intent(Verb.STAGE,"fixture-target"), b, Parameters(Pose("local")),
                                gripper.fingerprint, "fixture", "v1", b.evidence_ids)
            p = Program(proposal, (Step(Primitive.MOVE_EEF, pose=Pose("local"), max_steps=1),),
                        ("fixture_only",), 23, "synthetic_one_tick")
            rev = Review(p.fingerprint, b.fingerprint, "fixture", "fixture", (Check("fixture_only",True,b.evidence_ids),))
            return Catalog(b, gripper.fingerprint, (CompiledAction(p, rev, ()),), b.captured_wall+2)

        cat0 = catalog(b0)
        option = ExecutiveOption("inspect-target", ControlMode.CARTESIAN, cat0.actions[0].program.proposal.intent,
                                 "Synthetic admitted staging option", (cat0.actions[0].id,), ("fixture_ready",))
        packet = build_context(basis=b0, task="Inspect the red radio", task_revision="goal-1", subtask="Acquire evidence",
                               critical_state={"held_objects": [], "constraints": ["fixture only"],
                                               "unresolved_failures": [], "robot_state": "synthetic"},
                               facts=FactPacket(b0,(Fact("fixture_ready",True,b0,b0.evidence_ids,"fixture","v1"),)),
                               catalog=cat0, options=(option,), current_images=(f0,), now=now[0])

        class ScriptedExecutive:
            def call(self, *args):
                now[0] += 4.  # Simulated model latency, no real provider call.
                return {"packet_id": packet.fingerprint, "decision": "select", "option_id": option.id, "query": ""}

        def loader(f):
            return SimpleNamespace(id=f.asset_id, episode=f.basis.episode, width=f.width, height=f.height,
                                   data=images[f.asset_id])

        executive = ExecutiveSession(journal=journal, model=ScriptedExecutive(), image_loader=loader, clock=lambda: now[0])
        decision = executive.decide(packet)
        current = [basis(1)]  # Fresh capture at unchanged simulator time; old catalog expired.
        fresh = catalog(current[0])
        image(current[0])
        step_names = ("fresh_sensors", "robot_settled", "swept_collision", "native_codec", "payload_geometry", "joint_limits")

        def check_program(p,b,d):
            if b.domain != "fixture":
                raise PermissionError("Synthetic reviewers cannot authorize BEHAVIOR")
            return Review(p.fingerprint,b.fingerprint,"fixture","fixture",tuple(Check(n,True,b.evidence_ids) for n in p.required_checks))

        def step_review(p,i,b,d):
            return StepReview(p.fingerprint,i,b.fingerprint,tuple(Check(n,True,b.evidence_ids,"fixture") for n in step_names))

        def step(p,i,b,d,cancelled):
            if cancelled():
                raise InterruptedError("Fixture cancelled")
            now[0] += .01
            current[0] = basis(2, sim=b.sim_time+1/30)
            return StepReceipt(p.fingerprint,i,b,current[0],"completed",1,0,0,True,current[0].evidence_ids)

        jobs = JobManager((ActionExecutor.name,))
        driver = Driver("fixture","fixture","fixture-robot",gripper.fingerprint,frozenset({Primitive.MOVE_EEF}),
                        lambda d:current[0],check_program,step_review,step,lambda d:True)
        executor = ActionExecutor(driver=driver,jobs=jobs,journal=journal,allow_simulated_motion=True,clock=lambda:now[0])

        def rebind(p,o,a,b,t):
            if b.domain != "fixture":
                raise PermissionError("Fixture rebinding cannot authorize native action")
            names=("same_goal","same_target_instance","same_affordance","same_constraints",
                   "permitted_geometric_change","no_relevant_contradiction")
            return RebindReview(p.fingerprint,o.id,a.id,b.fingerprint,t,tuple(Check(n,True,b.evidence_ids,"fixture") for n in names))

        execution = executive.execute_selection(packet,decision,current=current[0],task_revision="goal-1",
                                                fresh_catalog=fresh,rebind_review=rebind,executor=executor,
                                                max_steps=1,max_wall_s=2)
        macros = MacroRegistry(journal=journal,deployment_fingerprint="fixture")
        for name in ("go_to","pick","place","inspect","press","pull_prismatic"):
            macros.register(standard_macro(name,deployment="fixture"))
        report = {"scope":"synthetic_software_fixture", "real_model_calls":0, "native_robot_actions":0,
                  "synthetic_counted_steps": execution.native_steps, "semantic_status":execution.semantic_status,
                  "discovery_has_actuator_authority":False, "inventory_records":len(inventory.records),
                  "executive_metadata_bytes":len(packet.metadata_json.encode()), "old_catalog_reused":False,
                  "fresh_catalog_id":fresh.id, "unresolved_robot_owners":len(jobs.owners),
                  "macros":macros.view(), "discovery_delivery":delivered}
        (target/"report.json").write_text(json.dumps(report,indent=2)+"\n")
        (target/"executive_context.json").write_text(packet.metadata_json+"\n")
        return report
    finally:
        if worker is not None and not worker.close(2):
            raise RuntimeError("Synthetic discovery worker did not stop")
        journal.close()
