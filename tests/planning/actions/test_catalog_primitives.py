from dataclasses import replace

import jsonschema
import pytest

from experiments.fixtures.actions import Fixture
from experiments.fixtures.actions_evaluation import score_selection
from physical_harness.core.actions import Intent, Parameters, Pose, Primitive, Proposal, Verb
from physical_harness.planning.actions.compiler import compile_catalog
from physical_harness.planning.actions.primitives import compile_program
from physical_harness.reasoning.action_proposals import (
    analytic_parallel_grasps,
    diverse_grasps,
    filter_grasp_region,
)
from physical_harness.reasoning.attention import EventAttention, IntentQueue


def proposal(f, verb):
    p = Pose(f.current.frame).shifted((0., 0., 1.), .8)
    return Proposal(Intent(verb, 'obj', 'part'), f.current,
                    Parameters(None if verb in {Verb.INSPECT, Verb.POLICY} else p,
                               (0., 0., 1.) if verb in {Verb.PRESS, Verb.PULL} else None,
                               travel_m=.005, opening_m=.08,
                               attachment_id='held-obj' if verb == Verb.PLACE else None,
                               instruction='pick obj' if verb == Verb.POLICY else None),
                    f.gripper.fingerprint, 'fixture', '1', f.current.evidence_ids)


@pytest.mark.parametrize('verb', list(Verb))
def test_all_verbs_compile_to_bounded_programs(verb):
    f = Fixture()
    p = compile_program(proposal(f, verb), f.gripper, f.config)
    assert p.steps and p.max_steps >= 0
    assert not any(s.max_policy_calls for s in p.steps) if verb != Verb.POLICY else True


def test_grasp_must_be_measured_before_lifting():
    f = Fixture()
    p = compile_program(proposal(f, Verb.GRASP), f.gripper, f.config)
    kinds = [s.kind for s in p.steps]
    assert kinds.index(Primitive.CLOSE) < kinds.index(Primitive.HOLD_CHECK) < len(kinds)-1
    assert p.steps[-1].pose.xyz[1] < p.proposal.parameters.pose.xyz[1]  # calibrated up is -Y


def test_press_moves_into_surface_then_checks_release():
    f = Fixture()
    p = compile_program(proposal(f, Verb.PRESS), f.gripper, f.config)
    assert p.steps[0].pose.xyz[2] < p.steps[1].pose.xyz[2] < p.steps[1].end_pose.xyz[2]
    assert p.steps[2].kind == Primitive.RELEASE_CHECK


@pytest.mark.parametrize('verb', [Verb.GRASP, Verb.PLACE])
def test_no_assumed_world_vertical(verb):
    f = Fixture()
    with pytest.raises(ValueError, match='calibrated up'):
        compile_program(proposal(f, verb), f.gripper, replace(f.config, up_direction=None, up_evidence_id=None))


@pytest.mark.parametrize('verb,travel', [(Verb.PRESS, 0), (Verb.PRESS, .1), (Verb.PULL, .5)])
def test_contact_travel_limits(verb, travel):
    f = Fixture()
    p = proposal(f, verb)
    with pytest.raises(ValueError):
        compile_program(replace(p, parameters=replace(p.parameters, travel_m=travel)), f.gripper, f.config)


def test_gripper_fingerprint_pins_embodiment():
    f = Fixture()
    with pytest.raises(PermissionError):
        compile_program(replace(proposal(f, Verb.GRASP), gripper_fingerprint='another-robot'), f.gripper, f.config)


def test_missing_native_reviews_are_unknown_not_executable():
    f = Fixture()
    c = compile_catalog(basis=f.current, proposals=(proposal(f, Verb.GRASP),), gripper=f.gripper,
                        template=f.config, review=f.review, deadline=110, clock=f.clock)
    assert not c.actions[0].eligible and 'swept_collision' in c.actions[0].rejected_checks
    with pytest.raises(PermissionError):
        c.tool_schema()


def test_exact_program_binding_prevents_different_pose_after_review():
    f = Fixture()
    c = f.catalog()
    a = c.actions[0]
    changed = replace(a.program, recipe='different')
    assert a.review.failures(changed, f.current) == ('review_binding_mismatch',)


def test_model_schema_and_no_metric_overrides():
    f = Fixture()
    c = f.catalog()
    answer = {'catalog_id': c.id, 'action_id': c.actions[0].id}
    jsonschema.validate(answer, c.tool_schema()['parameters'])
    c.resolve(answer, f.current, now=f.now)
    for key in ('x', 'yaw', 'force', 'code', 'qualified', 'max_steps'):
        with pytest.raises(ValueError):
            c.resolve(dict(answer, **{key: 1}), f.current, now=f.now)


@pytest.mark.parametrize('kind', ['catalog', 'action', 'future', 'expired', 'frame', 'geometry', 'calibration'])
def test_stale_or_invented_selection_fails(kind):
    f = Fixture()
    c = f.catalog()
    answer = {'catalog_id': c.id, 'action_id': c.actions[0].id}
    current, now = f.current, f.now
    if kind == 'catalog':
        answer['catalog_id'] = 'made-up'
    if kind == 'action':
        answer['action_id'] = 'made-up'
    if kind == 'future':
        now = 99
    if kind == 'expired':
        now = 102
    if kind == 'frame':
        current = replace(current, frame_epoch='new')
    if kind == 'geometry':
        current = replace(current, geometry_revision='new')
    if kind == 'calibration':
        current = replace(current, calibration_fingerprint='new')
    with pytest.raises(PermissionError):
        c.resolve(answer, current, now=now)


def test_context_limit_is_not_silent_truncation():
    c = Fixture().catalog()
    with pytest.raises(ValueError):
        c.view(max_bytes=100)
    view = c.view()
    assert all(a['parameter_count_exposed_to_model'] == 0 for a in view['actions'])
    assert all('matrix' not in a for a in view['actions'])


def test_semantic_region_requires_contact_volume_test():
    f = Fixture()
    cloud = f.cloud()
    proposals = analytic_parallel_grasps(cloud, f.gripper, max_candidates=3)
    assert not filter_grasp_region(proposals, allowed_region=cloud, closing_contacts=lambda *a: None)
    assert filter_grasp_region(proposals, allowed_region=cloud, closing_contacts=lambda *a: True) == proposals


def test_do_not_compare_unrelated_grasp_scores():
    f = Fixture()
    p = analytic_parallel_grasps(f.cloud(), f.gripper, max_candidates=1)[0]
    with pytest.raises(ValueError):
        diverse_grasps((p, replace(p, generator='other')))


def test_sparse_intent_queue_requires_semantic_verification():
    f = Fixture()
    p = proposal(f, Verb.INSPECT)
    catalog = f.catalog((p,))
    queue = IntentQueue((p.intent,))
    assert not queue.choose(catalog).wake
    with pytest.raises(PermissionError):
        queue.advance(intent=p.intent, verdict='completed', verification_id='v', evidence_ids=('rgb',))
    queue.advance(intent=p.intent, verdict='verified', verification_id='v', evidence_ids=('rgb',))
    assert queue.choose(catalog).wake


def test_ambiguous_candidates_wake_executive_not_arbitrary_ranking():
    f = Fixture()
    p = proposal(f, Verb.INSPECT)
    q = replace(p, generator_revision='other')
    queue = IntentQueue((p.intent,))
    assert queue.choose(f.catalog((p, q))).reason == 'semantic_choice_required'


def test_event_attention_debounce_and_no_per_frame_calls():
    gate = EventAttention(heartbeat_s=30)
    assert gate.consider(event_id='0', event_type='decision_required', now=100).wake
    assert not gate.consider(event_id='1', event_type='frame', now=101).wake
    assert gate.consider(event_id='2', event_type='target_lost', now=102).wake
    assert not gate.consider(event_id='2', event_type='target_lost', now=103).wake
    assert not gate.consider(event_id='3', event_type='heartbeat', now=104).wake
    assert gate.consider(event_id='4', event_type='heartbeat', now=134).wake


def test_tool_use_evaluation_does_not_execute_robot():
    f = Fixture()
    c = f.catalog()
    answer = {'catalog_id': c.id, 'action_id': c.actions[0].id}
    score = score_selection(c, answer, acceptable_action_ids=(c.actions[0].id,), current=f.current, now=f.now)
    assert score['valid_tool_use'] and score['semantically_acceptable'] and not score['robot_executed']
    assert not f.executed
