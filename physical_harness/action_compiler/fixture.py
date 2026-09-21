"""Synthetic contract fixture, NOT a robot, collision engine or model benchmark.

The fake driver instantly satisfies pose/contact goals. All-true checks are
intentionally confined to domain='fixture'. Never adapt these checks to BEHAVIOR.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from .compiler import ReviewEngine, compile_catalog
from .geometry import Intrinsics, deproject_masked_depth, fit_surface
from .metrics import summarize
from .primitives import TemplateConfig
from .proposals import analytic_parallel_grasps, inspect_candidate, press_candidate
from .runtime import ActionExecutor, Driver, StepReceipt, StepReview
from .types import Basis, Check, Gripper, Pose, Primitive, encode, plain


class MemoryJournal:
    """Fixture-only Journal.put/records test double. Real runs use existing Journal."""
    def __init__(self):
        self.rows = {}

    def put(self, kind, identifier, payload):
        import json
        value = json.loads(encode(payload))
        old = self.rows.get((kind, identifier))
        if old is not None and old != value:
            raise ValueError("Conflicting immutable fixture journal record")
        self.rows[(kind, identifier)] = value

    def records(self, kind):
        import json
        return [{"id": identifier, **json.loads(encode(value))}
                for (k, identifier), value in self.rows.items() if k == kind]


class Fixture:
    def __init__(self):
        self.now = 100.
        self.tick = 0
        self.current = Basis("fixture", "obs-0", "sensor-0", 0., 100., "fixture_map",
                             "origin-1", "geom-0", 0, "fixture-robot", "fixture-calibration",
                             ("rgb-0", "depth-0"))
        self.gripper = Gripper("fixture-jaw", "1", "fixture-assets", ("jaw",),
                               (.04,), (0.,), (0.,), (.05,), Pose("grasp"), .1)
        self.config = TemplateConfig(step_cap=6, policy_steps=4, up_direction=(0., -1., 0.),
                                     up_evidence_id="fixture-up")
        self.journal = MemoryJournal()
        self.executed = []
        self.stop_ok = True
        self.hold_ok = True
        self.step_fault = None
        self.review = ReviewEngine(qualification_id="fixture-q", domain="fixture", checks={}, clock=self.clock)

    def clock(self):
        return self.now

    def cloud(self, part="whole"):
        intr = Intrinsics(16, 16, 200., 200., 7.5, 7.5, .001, "optical_z")
        return deproject_masked_depth(basis=self.current, depth=np.full((16, 16), 800.),
                                      mask=np.ones((16, 16), dtype=bool), intrinsics=intr,
                                      camera_to_frame=Pose("fixture_map"), entity="object-1", part=part,
                                      source_camera="head", evidence_ids=self.current.evidence_ids,
                                      semantic_confidence=.9)

    def review_program(self, program, basis, deadline):
        from .types import Review
        return Review(program.fingerprint, basis.fingerprint, "fixture-q", "fixture",
                      tuple(Check(n, True, basis.evidence_ids, "fixture only") for n in program.required_checks))

    def review_step(self, program, index, basis, deadline):
        # Deliberate test truth, never a production default.
        names = ("fresh_sensors", "robot_settled", "swept_collision", "native_codec", "payload_geometry",
                 "joint_limits", "measured_grasp", "measured_release", "passive_capture", "policy_identity",
                 "policy_recipe", "policy_handoff", "policy_queue_ready", "contact_monitor", "bounded_contact")
        return StepReview(program.fingerprint, index, basis.fingerprint,
                          tuple(Check(n, self.hold_ok if n == "measured_grasp" else True,
                                      basis.evidence_ids) for n in names))

    def execute(self, program, index, before, deadline, cancelled):
        if self.step_fault:
            return self.step_fault(program, index, before, deadline, cancelled)
        if cancelled():
            raise InterruptedError()
        step = program.steps[index]
        n = min(2, step.max_steps)
        self.tick += n
        self.now += .001
        self.current = replace(before, observation_id=f"obs-{self.tick}-{index}",
                               source_fingerprint=f"sensor-{self.tick}-{index}", sim_time=before.sim_time+n/30,
                               captured_wall=self.now, geometry_revision=f"geom-{self.tick}-{index}",
                               evidence_ids=(f"rgb-{self.tick}-{index}",))
        self.executed.append(step.kind)
        policy = step.kind == Primitive.POLICY
        return StepReceipt(program.fingerprint, index, before, self.current, "completed", n,
                           int(policy), program.robot_dofs if policy else 0, True,
                           self.current.evidence_ids, chunks_generated=int(policy))

    def driver(self):
        return Driver("fixture", "fixture-q", "fixture-robot", self.gripper.fingerprint,
                      frozenset(Primitive), lambda deadline: self.current, self.review_program,
                      self.review_step, self.execute, lambda deadline: self.stop_ok)

    def executor(self, jobs=None):
        from ..jobs import JobManager
        return ActionExecutor(driver=self.driver(), jobs=jobs or JobManager([ActionExecutor.name]),
                              journal=self.journal, allow_simulated_motion=True, clock=self.clock)

    def catalog(self, proposals=None):
        if proposals is None:
            proposals = (analytic_parallel_grasps(self.cloud(), self.gripper, max_candidates=1)
                         +(press_candidate(fit_surface(self.cloud("button")), self.gripper, travel_m=.005),
                           inspect_candidate(self.current, self.gripper)))
        return compile_catalog(basis=self.current, proposals=proposals, gripper=self.gripper,
                               template=self.config, review=self.review_program,
                               deadline=self.now+10, clock=self.clock)


def run_fixture():
    fixture = Fixture()
    catalog = fixture.catalog()
    schema = catalog.tool_schema()
    from .scene import SceneView
    scene = SceneView(fixture.current, (fixture.cloud(),), catalog).view()
    selection = {"catalog_id": catalog.id, "action_id": catalog.actions[0].id}
    result = fixture.executor().execute(catalog, selection, max_steps=1000, max_wall_s=10)
    return {"kind": "synthetic-action-compiler-fixture", "benchmark_success": "not_tested",
            "robot_motion": False, "model_inference": False,
            "catalog": catalog.view(), "scene": scene, "tool_schema": schema, "selection": selection,
            "execution": plain(result), "usage": summarize(fixture.journal),
            "events": fixture.journal.records("compiled_action")}
