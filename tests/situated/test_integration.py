import pytest

from physical_harness.action_compiler.primitives import TemplateConfig
from physical_harness.action_compiler.types import Pose
from physical_harness.situated.contracts import Binding, FactPacket
from physical_harness.situated.fixture import SyntheticActuation, run_fixture
from physical_harness.situated.graph import Node
from physical_harness.situated.graph_runtime import NodeContext
from physical_harness.situated.integration import CatalogActionHandler
from physical_harness.situated.motion import MotionLimits, PoseAnchor, motion_program
from physical_harness.situated.programs import catalog_for_programs, enforce_extra_step_checks


def make_program(sim):
    b = sim.current
    anchor = PoseAnchor('a', b, 'radio', Pose(b.frame), b.evidence_ids)
    raw = {'basis_fingerprint': b.fingerprint, 'arm': 'right_arm', 'waypoints': [{'anchor_id': 'a', 'offset_m': [0.01, 0, 0], 'rotvec_rad': [0, 0, 0], 'gripper': 'hold'}]}
    return motion_program(raw, basis=b, entity='radio', anchors=(anchor,), start_eef=Pose(b.frame), gripper=sim.gripper, template=TemplateConfig(step_cap=3), limits=MotionLimits(), model_revision='synthetic-model')

def test_real_existing_compiler_executor_jobs_and_journal_are_used(journal):
    sim = SyntheticActuation(journal)
    p = make_program(sim)
    c = catalog_for_programs(sim.current, (p,), review=sim.review, deadline=110, clock=lambda: sim.now)
    ex = sim.executor()
    handler = CatalogActionHandler(executor=ex, resolve_intent=lambda ctx: p.proposal.intent, compile_current=lambda *a: c)
    role = Binding('target', 'radio', 'whole', sim.current, sim.current.evidence_ids, True)
    ctx = NodeContext(Node('act', 'act', 'direct', ('target',)), sim.current, (role,), FactPacket(sim.current, ()), 110, 'invoke')
    result = handler(ctx)
    assert result.native_steps == 1 and result.execution_ref.startswith('attempt:')
    assert not sim.jobs.owners
    assert journal.records('compiled_action')[-1]['semantic_status'] == 'requires_external_verification'
    assert result.outcome == 'ok'

def test_extra_step_review_is_mandatory_not_just_initial_review(journal):
    sim = SyntheticActuation(journal)
    ex = sim.executor()
    p = make_program(sim)
    c = catalog_for_programs(sim.current, (p,), review=sim.review, deadline=110, clock=lambda: sim.now)
    ex.driver = enforce_extra_step_checks(ex.driver, {})
    with pytest.raises(PermissionError, match='per-step'):
        ex.execute(c, {'catalog_id': c.id, 'action_id': c.actions[0].id}, max_steps=3, max_wall_s=10)
    assert not sim.executed
    assert ex.faulted
    assert journal.records('compiled_action')[-1]['fault_latched'] is True

def test_no_new_actuator_permission_created_by_handler(journal):
    sim = SyntheticActuation(journal)
    ex = sim.executor()
    ex.allowed = False
    p = make_program(sim)
    c = catalog_for_programs(sim.current, (p,), review=sim.review, deadline=110, clock=lambda: sim.now)
    with pytest.raises(PermissionError):
        ex.execute(c, {'catalog_id': c.id, 'action_id': c.actions[0].id}, max_steps=3, max_wall_s=10)
    assert not sim.executed

def test_synthetic_end_to_end_demo_reports_scope(tmp_path):
    result = run_fixture(tmp_path)
    assert result['native_robot_actions'] == 0 and result['model_calls'] == 0
    assert result['synthetic_graph_finished']
    assert result['remembered_semantics_current_geometry']['canonical']['label'] == 'radio'
    assert result['executed_synthetic_primitives'] == ['move_eef', 'passive_inspect']
    assert result['report']['unresolved_nodes'] == 0
