"""Synthetic protocol fixture. NOT R1Pro, a learned model, or a collision engine."""
from __future__ import annotations

from dataclasses import replace

from experiments.fixtures.graph_evaluation import runtime_report
from physical_harness.core.actions import Basis, Check, Gripper, Pose, Primitive, Verb, plain
from physical_harness.core.jobs import JobManager
from physical_harness.core.tasks import Capability, Effect, FactPacket
from physical_harness.execution.actions import ActionExecutor, Driver, StepReceipt, StepReview
from physical_harness.execution.graph import GraphSession, Handler, NodeResult
from physical_harness.execution.graph_bridge import CatalogActionHandler, identity_binding
from physical_harness.integrations.experiment.journal import Journal
from physical_harness.perception.identity import (
    AssociationProof,
    IdentityLedger,
    SemanticClaim,
    Tracklet,
)
from physical_harness.perception.visual import GoalKind, VisualGoal
from physical_harness.planning.actions.catalogs import (
    catalog_for_programs,
    enforce_extra_step_checks,
)
from physical_harness.planning.actions.compiler import ReviewEngine
from physical_harness.planning.actions.primitives import TemplateConfig
from physical_harness.planning.inspection import InspectionCandidate, inspection_program
from physical_harness.planning.tasks.graph import Graph, Node


class SyntheticActuation:
    """Instantly satisfies synthetic poses; its all-true checks are FIXTURE ONLY."""
    def __init__(self, journal):
        self.journal = journal
        self.tick = 0
        self.now = 100.
        self.executed = []
        self.stop_ok = True
        self.current = Basis("fixture", "obs-0", "capture-0", 0., 100., "local", "origin",
                             "geometry-0", 0, "fixture-robot", "calibration", ("rgb-0","depth-0"))
        self.gripper = Gripper("fixture-hand", "1", "fixture-assets", ("jaw",), (.04,), (0.,),
                               (0.,), (.05,), Pose("grasp"), .08)
        self.jobs = JobManager([ActionExecutor.name])

    def observe(self, deadline=None):
        return self.current

    def review(self, program, basis, deadline):
        if basis.domain != "fixture":
            raise PermissionError("Synthetic checks cannot authorize native execution")
        engine = ReviewEngine(qualification_id="fixture", domain="fixture", clock=lambda:self.now,
                              checks={n: (lambda p,b,d,n=n: Check(n,True,b.evidence_ids,"fixture-only"))
                                      for n in program.required_checks})
        return engine(program,basis,deadline)

    def step_review(self, program, index, basis, deadline):
        names = {"fresh_sensors","robot_settled","swept_collision","native_codec","payload_geometry",
                 "joint_limits","passive_capture","measured_grasp","measured_release"}
        names |= {n for n in program.required_checks if n.startswith("constraint_")}
        return StepReview(program.fingerprint,index,basis.fingerprint,
                          tuple(Check(n,True,basis.evidence_ids,"fixture-only") for n in sorted(names)))

    def step(self, program, index, basis, deadline, cancelled):
        if cancelled():
            raise InterruptedError()
        kind = program.steps[index].kind
        self.executed.append(kind.value)
        n = 0 if kind in {Primitive.INSPECT,Primitive.HOLD_CHECK,Primitive.RELEASE_CHECK} else 1
        self.tick += n
        self.now += .001
        self.current = replace(self.current,observation_id=f"obs-{self.tick}",source_fingerprint=f"capture-{self.tick}",
                               sim_time=self.tick/30, captured_wall=self.now,
                               geometry_revision=f"geometry-{self.tick}",evidence_ids=(f"rgb-{self.tick}",f"depth-{self.tick}"))
        # Passive actions use a fresh evidence basis but no fabricated physics tick.
        return StepReceipt(program.fingerprint,index,basis,self.current,"completed",n,0,0,True,
                           self.current.evidence_ids)

    def executor(self):
        driver = Driver("fixture","fixture",self.current.robot_fingerprint,self.gripper.fingerprint,
                        frozenset(Primitive),self.observe,self.review,self.step_review,self.step,
                        lambda d:self.stop_ok)
        checks = {n:(lambda p,i,b,d,n=n:Check(n,True,b.evidence_ids,"fixture-only")) for n in
                  ("situated_view_kinematics","situated_information_target","situated_camera_calibration",
                   "situated_direct_motion","situated_whole_path","situated_anchor_grounding",
                   "situated_gripper_transition")}
        driver = enforce_extra_step_checks(driver,checks)
        return ActionExecutor(driver=driver,jobs=self.jobs,journal=self.journal,
                              allow_simulated_motion=True,clock=lambda:self.now)


def run_fixture(directory):
    journal = Journal(directory/"journal.sqlite","fixture",max_microusd=0,max_calls=1)
    try:
        sim = SyntheticActuation(journal)
        memory = IdentityLedger(journal)
        t0 = Tracklet(sim.current,"head","fixture-track","1","mask-front",(.4,0,.7),.01)
        entity = memory.new_entity(t0,SemanticClaim("radio","recognized",("rgb-0",),"fixture-recognition"))
        # New synthetic viewpoint, same scene time requires a new capture, not a fake native step.
        sim.now += .001
        sim.current = replace(sim.current,observation_id="obs-side",source_fingerprint="capture-side",
                              captured_wall=sim.now,evidence_ids=("rgb-side","depth-side"))
        side = Tracklet(sim.current,"head","fixture-track","1","mask-side",(.4,0,.7),.01)
        association = AssociationProof(entity,memory.revision(entity),side.fingerprint,True,True,True,
                                        "fixture-temporal-and-geometric",("mask-side",))
        memory.observe(entity,side,SemanticClaim(None,"ambiguous",("rgb-side",),"fixture-side-view"),association)
        remembered = memory.binding(entity,sim.current)
        goal = VisualGoal("find-power-control",GoalKind.INFORMATION,entity,"power-control-location",
                          "obtain a view that resolves the control, not just the radio body")
        candidate = InspectionCandidate(goal,sim.current,Pose("local"),Pose("local"),Verb.STAGE,
                                        .5,.02,sim.current.evidence_ids,"fixture-camera-kinematics")
        program = inspection_program(candidate,sim.gripper,TemplateConfig(step_cap=4))
        catalog = catalog_for_programs(sim.current,(program,),review=sim.review,deadline=sim.now+10,
                                       clock=lambda:sim.now)
        executor = sim.executor()
        act = CatalogActionHandler(executor=executor, resolve_intent=lambda c:program.proposal.intent,
                                   compile_current=lambda i,b,d:catalog)
        graph = Graph("inspect-radio","inspect",(
            Node("inspect","act","fixture.inspect",("target",),(),(("ok","verify"),)),
            Node("verify","monitor","fixture.verify",(),(),(("complete","done"),)),
            Node("done","done","existing_task_ledger")))
        verified = [False]
        def verify(ctx):
            verified[0] = True  # explicit independent FIXTURE outcome, not actual image reasoning
            return NodeResult(ctx.invocation_id,ctx.basis,ctx.basis,"complete",ctx.basis.evidence_ids,True)
        handlers = {
            "fixture.inspect":Handler(Capability("fixture.inspect",Effect.MOTION,"fixture","q",("fixture",)),act),
            "fixture.verify":Handler(Capability("fixture.verify",Effect.READ,"fixture","q",("fixture",)),verify)}
        session = GraphSession(graph=graph,session_id="fixture-session",journal=journal,handlers=handlers,
                               quiescent=lambda:not sim.jobs.owners,stop=lambda d:sim.stop_ok,
                               finish_allowed=lambda b:verified[0],clock=lambda:sim.now)
        binding = identity_binding(memory,role="target",entity=entity,part="whole",current=sim.current)
        session.advance(basis=sim.current,bindings=(binding,),facts=FactPacket(sim.current,()))
        session.advance(basis=sim.current,bindings=(),facts=FactPacket(sim.current,()))
        session.advance(basis=sim.current,bindings=(),facts=FactPacket(sim.current,()))
        return {"scope":"synthetic_software_fixture", "native_robot_actions":0,"model_calls":0,
                "synthetic_controller_ticks":sim.tick,"synthetic_graph_finished":session.finished,
                "remembered_semantics_current_geometry":remembered,"catalog":catalog.view(),
                "graph":plain(graph),"executed_synthetic_primitives":sim.executed,
                "report":runtime_report(journal)}
    finally:
        journal.close()
