import io
import math
import sys
from dataclasses import replace

import numpy as np
import pytest
from PIL import Image

from physical_harness.action_compiler.cartesian import (
    CartesianExecutor,
    CartesianPort,
    bounded_pose_step,
    pose_error,
)
from physical_harness.action_compiler.fixture import Fixture
from physical_harness.action_compiler.geometry import Intrinsics
from physical_harness.action_compiler.integration import CatalogMotor
from physical_harness.action_compiler.overlays import annotate_candidates
from physical_harness.action_compiler.primitives import compile_program
from physical_harness.action_compiler.types import (
    Intent,
    Parameters,
    Pose,
    Primitive,
    Proposal,
    Verb,
)
from physical_harness.action_compiler.worker_client import GraspWorkerClient
from physical_harness.contracts import SkillRequest


def native_request(f, c):
    return SkillRequest('semantic-action', 'compiled_catalog', 'select qualified action',
                        (c.actions[0].program.proposal.intent.entity,),
                        expected_predicates=('external-task-goal',),
                        source_observation_id=f.current.observation_id,
                        metadata={'action_id': c.actions[0].id, 'max_action_steps': 1000})


def test_catalog_bridge_returns_original_strict_receipt_and_no_goal_fact():
    f = Fixture()
    c = f.catalog()
    bridge = CatalogMotor(f.executor())
    bridge.publish(c)
    r = bridge.run_skill(native_request(f, c))
    assert set(r.metadata) == {'episode_id', 'execution_epoch', 'stop_acknowledged'}
    assert r.outcome == 'completed' and r.observed_predicates == ()
    assert r.action_steps_executed > 0


@pytest.mark.parametrize('change', ['target', 'source', 'action'])
def test_catalog_bridge_rejects_request_rebinding(change):
    f = Fixture()
    c = f.catalog()
    bridge = CatalogMotor(f.executor())
    bridge.publish(c)
    r = native_request(f, c)
    if change == 'target':
        r = replace(r, target_entities=('other',))
    if change == 'source':
        r = replace(r, source_observation_id='other')
    if change == 'action':
        r = replace(r, metadata={'action_id': 'other', 'max_action_steps': 1000})
    with pytest.raises(PermissionError):
        bridge.run_skill(r)
    assert not f.executed


@pytest.mark.parametrize('angle', [0., .5, math.pi-1e-6, math.pi])
def test_pose_step_bounded_translation_and_rotation(angle):
    a = Pose('map')
    matrix = np.eye(4)
    c, s = math.cos(angle), math.sin(angle)
    matrix[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    matrix[:3, 3] = [1, 2, 3]
    b = Pose('map', tuple(float(v) for v in matrix.ravel()))
    result = bounded_pose_step(a, b, max_translation_m=.01, max_rotation_rad=.05)
    distance, rotation = pose_error(a, result)
    assert distance <= .0100001 and rotation <= .0500001


class PoseFixture:
    def __init__(self):
        self.f = Fixture()
        self.pose = Pose(self.f.current.frame)
        self.steps = 0
        self.monitor = True
        self.collision = True
        self.reference = None

    def solve(self, pose, basis, deadline):
        self.reference = pose
        return (0.,)

    def step(self, action, deadline):
        self.pose = self.reference
        self.steps += 1
        self.f.now += .001
        self.f.current = replace(self.f.current, observation_id=f'motion-{self.steps}',
                                 source_fingerprint=f'motion-{self.steps}',
                                 sim_time=self.f.current.sim_time+1/30, captured_wall=self.f.now)
        return self.f.current

    def execute(self, *, kind=Verb.STAGE, max_steps=100):
        f = self.f
        goal = Pose(f.current.frame).shifted((0., 0., 1.), .005)
        proposal = Proposal(Intent(kind, 'obj'), f.current,
                            Parameters(goal, (0., 0., 1.) if kind == Verb.PRESS else None,
                                       travel_m=.002), f.gripper.fingerprint, 'fixture', '1', f.current.evidence_ids)
        program = compile_program(proposal, f.gripper, replace(f.config, step_cap=max_steps))
        index = 1 if kind == Verb.PRESS else 0
        port = CartesianPort(lambda b: self.pose, self.solve,
                             lambda *a: self.collision, lambda *a: (0.,)*23,
                             lambda a: True, self.step, lambda b: True,
                             lambda *a: self.monitor, lambda d: True)
        ex = CartesianExecutor(port, position_tolerance_m=.0001, clock=f.clock)
        return ex(program, index, f.current, 110., lambda: False)


def test_cartesian_actual_closed_loop_and_counted_settling():
    w = PoseFixture()
    result = w.execute()
    assert result.outcome == 'completed'
    assert result.native_steps == w.steps and result.native_steps >= 3
    assert w.pose.xyz == pytest.approx((0, 0, .005))


def test_cartesian_budget_exhaustion_is_not_success():
    result = PoseFixture().execute(max_steps=1)
    assert result.outcome == 'stalled' and result.native_steps == 1


@pytest.mark.parametrize('condition', ['unknown_collision', 'unknown_contact', 'lateral_contact'])
def test_cartesian_monitors_stop_before_bad_command(condition):
    w = PoseFixture()
    if condition == 'unknown_collision':
        w.collision = None
    if condition == 'unknown_contact':
        w.monitor = None
    if condition == 'lateral_contact':
        w.pose = w.pose.shifted((1., 0., 0.), .01)
    with pytest.raises(PermissionError):
        w.execute(kind=Verb.STAGE if condition == 'unknown_collision' else Verb.PRESS)
    assert w.steps == 0


def worker_code(mode):
    intro = 'import json,sys,time; print(json.dumps({"version":1,"status":"ready","revision":"fixture"}),flush=True); '
    if mode == 'oversize':
        return intro+'r=json.loads(sys.stdin.readline()); print("x"*200000,flush=True); time.sleep(1)'
    if mode == 'timeout':
        return intro+'r=json.loads(sys.stdin.readline()); time.sleep(10)'
    if mode == 'wrong-id':
        return intro+'r=json.loads(sys.stdin.readline()); print(json.dumps({"version":1,"id":"wrong","proposals":[],"error":None}),flush=True)'
    return intro+'r=json.loads(sys.stdin.readline()); print(json.dumps({"version":1,"id":r["id"],"proposals":[],"error":None}),flush=True)'


def test_worker_valid_empty_result_and_clean_reaping():
    w = GraspWorkerClient([sys.executable, '-c', worker_code('okay')], expected_revision='fixture')
    try:
        assert w.propose(Fixture().cloud(), timeout_s=2) == ()
    finally:
        w.close()
    assert w.process.poll() is not None


@pytest.mark.parametrize('mode', ['timeout', 'wrong-id', 'oversize'])
def test_worker_failure_poisoned_no_retry(mode):
    w = GraspWorkerClient([sys.executable, '-c', worker_code(mode)], expected_revision='fixture', max_bytes=100000 if mode == 'oversize' else 16000000)
    try:
        with pytest.raises((TimeoutError, ValueError)):
            w.propose(Fixture().cloud(), timeout_s=.2 if mode == 'timeout' else 2)
        assert w.poisoned and w.process.poll() is not None
        with pytest.raises(RuntimeError):
            w.propose(Fixture().cloud())
    finally:
        w.close()


def test_annotation_id_map_and_source_binding():
    f = Fixture()
    catalog = f.catalog()
    image = Image.new('RGB', (16, 16))
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    annotated, mapping = annotate_candidates(buf.getvalue(), basis=f.current, catalog=catalog,
        intrinsics=Intrinsics(16,16,200.,200.,7.5,7.5,.001,'optical_z'), camera_to_frame=Pose(f.current.frame))
    assert annotated.startswith(b'\x89PNG')
    assert mapping['catalog_id'] == catalog.id and mapping['markers']
    assert mapping['markers'][0]['action_id'] in {a.id for a in catalog.actions}


def test_unknown_constraints_are_not_silently_dropped():
    f = Fixture()
    p = f.catalog().actions[0].program.proposal
    with pytest.raises(ValueError, match='Unsupported semantic'):
        compile_program(replace(p, intent=replace(p.intent, constraints=('do_magic',))), f.gripper, f.config)
    constrained = compile_program(replace(p, intent=replace(p.intent, constraints=('keep_upright',))), f.gripper, f.config)
    assert 'constraint_keep_upright' in constrained.required_checks


def test_dispatcher_tracks_classical_interventions_but_not_passive_reads():
    from physical_harness.action_compiler.integration import PrimitiveDispatcher
    from physical_harness.action_compiler.proposals import inspect_candidate
    f = Fixture()
    notifications = []
    class Port:
        def notify_classical_intervention(self):
            notifications.append('reset-needed')
    port = Port()
    dispatcher = PrimitiveDispatcher({p: lambda *args: 'executed' for p in Primitive
                                      if p != Primitive.POLICY}, frozen_policy=port)
    program = f.catalog().actions[0].program
    for i in range(len(program.steps)):
        dispatcher(program, i, f.current, 200, lambda: False)
    assert len(notifications) == sum(s.kind not in {Primitive.INSPECT, Primitive.HOLD_CHECK,
                                                   Primitive.RELEASE_CHECK}
                                     for s in program.steps)
    passive = compile_program(inspect_candidate(f.current, f.gripper), f.gripper, f.config)
    n = len(notifications)
    dispatcher(passive, 0, f.current, 200, lambda: False)
    assert len(notifications) == n
    with pytest.raises(InterruptedError):
        dispatcher(program, 0, f.current, 200, lambda: True)


def test_default_contact_budget_can_cover_configured_press_envelope():
    from physical_harness.action_compiler.primitives import TemplateConfig
    cfg = TemplateConfig()
    assert cfg.contact_step_cap/30 > (cfg.approach_m+cfg.press_limit_m)/cfg.contact_speed_m_s
