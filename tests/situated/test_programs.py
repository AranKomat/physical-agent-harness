from dataclasses import replace

import pytest

from physical_harness.action_compiler.compiler import ReviewEngine
from physical_harness.action_compiler.primitives import TemplateConfig
from physical_harness.action_compiler.types import Pose, Primitive, Verb
from physical_harness.situated.inspection import (
    InspectionCandidate,
    inspection_program,
    orbit_views,
    rank_inspections,
)
from physical_harness.situated.motion import (
    MotionLimits,
    PoseAnchor,
    motion_program,
    proposal_schema,
)
from physical_harness.situated.programs import catalog_for_programs
from physical_harness.situated.visual import GoalKind, VisualGoal


def anchor(basis):
    return PoseAnchor('a', basis, 'radio', Pose(basis.frame), basis.evidence_ids)

def reply(basis, **overrides):
    result = {'basis_fingerprint': basis.fingerprint, 'arm': 'right_arm', 'waypoints': [{'anchor_id': 'a', 'offset_m': [0.01, 0, 0], 'rotvec_rad': [0, 0, 0], 'gripper': 'hold'}, {'anchor_id': 'a', 'offset_m': [0.02, 0, 0], 'rotvec_rad': [0, 0, 0.1], 'gripper': 'hold'}]}
    result.update(overrides)
    return result

def program(basis, gripper, value=None, **kwargs):
    return motion_program(value or reply(basis), basis=basis, entity='radio', anchors=(anchor(basis),), start_eef=Pose(basis.frame), gripper=gripper, template=TemplateConfig(step_cap=6), limits=kwargs.pop('limits', MotionLimits()), model_revision='test-not-a-model', **kwargs)

def test_keyposes_compile_not_execute(basis, gripper):
    p = program(basis, gripper)
    assert [s.kind for s in p.steps] == [Primitive.MOVE_EEF] * 2
    assert p.steps[-1].pose.xyz == pytest.approx((0.02, 0, 0))
    assert 'situated_direct_motion' in p.required_checks
    assert 'constraint_no_base_motion' in p.required_checks
    assert p.max_steps == 12

def test_schema_has_no_speed_force_joint_or_safety_overrides(basis):
    schema = proposal_schema(basis, (anchor(basis),), MotionLimits())
    assert set(schema['properties']) == {'basis_fingerprint', 'arm', 'waypoints'}
    assert schema['additionalProperties'] is False

@pytest.mark.parametrize('mutation', ['stale', 'extra', 'wrong_arm', 'unknown_anchor', 'bad_float', 'offset', 'rotation', 'too_many', 'gripper', 'path'])
def test_motion_rejects_invalid_or_unsafe_proposals(basis, gripper, mutation):
    r = reply(basis)
    limits = MotionLimits()
    if mutation == 'stale':
        r['basis_fingerprint'] = 'old'
    elif mutation == 'extra':
        r['collision_clear'] = True
    elif mutation == 'wrong_arm':
        r['arm'] = 'whole_robot'
    elif mutation == 'unknown_anchor':
        r['waypoints'][0]['anchor_id'] = 'invented'
    elif mutation == 'bad_float':
        r['waypoints'][0]['offset_m'][0] = float('nan')
    elif mutation == 'offset':
        r['waypoints'][0]['offset_m'][0] = 1
    elif mutation == 'rotation':
        r['waypoints'][0]['rotvec_rad'][0] = 3
    elif mutation == 'too_many':
        r['waypoints'] *= 4
    elif mutation == 'gripper':
        r['waypoints'][0]['gripper'] = 'open'
    else:
        limits = replace(limits, max_path_m=0.015)
    with pytest.raises((ValueError, PermissionError)):
        program(basis, gripper, r, limits=limits)

def test_distinct_paths_same_endpoint_have_distinct_ids(basis, gripper):
    a = program(basis, gripper)
    r = reply(basis)
    r['waypoints'][0]['offset_m'] = [0, 0.01, 0]
    b = program(basis, gripper, r)
    assert a.proposal.parameters.pose == b.proposal.parameters.pose
    assert a.proposal.id != b.proposal.id

@pytest.mark.parametrize('command,check', [('close', Primitive.HOLD_CHECK), ('open', Primitive.RELEASE_CHECK)])
def test_gripper_change_inserts_measurement_before_next_motion(basis, gripper, command, check):
    r = reply(basis)
    r['waypoints'][0]['gripper'] = command
    p = program(basis, gripper, r, limits=MotionLimits(allow_gripper_changes=True))
    assert p.steps[2].kind == check
    assert p.steps[3].kind == Primitive.MOVE_EEF
    assert 'situated_gripper_transition' in p.required_checks

def test_no_native_reviewers_means_blocked_catalog(basis, gripper):
    p = program(basis, gripper)
    review = ReviewEngine(qualification_id='fixture', domain='fixture', checks={}, clock=lambda: 100.0)
    c = catalog_for_programs(basis, (p,), review=review, deadline=101.0, clock=lambda: 100.0)
    assert not c.actions[0].eligible
    assert 'situated_whole_path' in c.actions[0].rejected_checks
    with pytest.raises(PermissionError):
        c.tool_schema()

def inspect_candidate(basis):
    goal = VisualGoal('inspect-button', GoalKind.INFORMATION, 'radio', 'button_identity', 'obtain a discriminating view')
    return InspectionCandidate(goal, basis, Pose(basis.frame), Pose(basis.frame), Verb.STAGE, 0.5, 0.05, basis.evidence_ids, 'fixture')

def test_inspection_is_motion_then_passive_capture_not_success(basis, gripper):
    p = inspection_program(inspect_candidate(basis), gripper, TemplateConfig(step_cap=5))
    assert [s.kind for s in p.steps] == [Primitive.MOVE_EEF, Primitive.INSPECT]
    assert p.steps[-1].max_steps == 0
    assert 'situated_view_kinematics' in p.required_checks

def test_orbit_uses_calibrated_up_and_respects_camera_travel(basis):
    p = Pose(basis.frame).shifted((1.0, 0.0, 0.0), 1.0)
    views = orbit_views(basis=basis, current_camera=p, target_xyz=(0.0, 0.0, 0.0), up=(0.0, 0.0, 1.0), up_evidence='gravity-calibration', angles_rad=(0.05, 0.1, 0.5), max_camera_travel_m=0.11)
    assert len(views) == 2
    for v in views:
        expected = tuple((-x for x in v.xyz))
        assert v.approach == pytest.approx(expected)
    assert not orbit_views(basis=basis, current_camera=p, target_xyz=(0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0), up_evidence='u', angles_rad=(0.5,), max_camera_travel_m=0.01)

def test_inspection_ranking_is_heuristic_and_stale_candidates_rejected(basis):
    c = inspect_candidate(basis)
    worse = replace(c, expected_gain=0.2)
    assert rank_inspections((worse, c), basis)[0] == c
    assert not rank_inspections((replace(c, expected_gain=0),), basis)
    with pytest.raises(PermissionError):
        rank_inspections((c,), replace(basis, geometry_revision='moved'))
