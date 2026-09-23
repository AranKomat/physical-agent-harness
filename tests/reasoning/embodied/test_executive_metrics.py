from dataclasses import replace
from types import SimpleNamespace

import jsonschema
import pytest

from physical_harness.core.actions import (
    Check,
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
from physical_harness.core.compute import ComputeLedger, ComputeReceipt, receipt_images
from physical_harness.core.events import BoundaryEvent
from physical_harness.core.tasks import Fact, FactPacket
from physical_harness.integrations.sensor_contracts import (
    FoveatedRequest,
    SensorCapability,
    admitted_sensors,
)
from physical_harness.planning.actions.compiler import Catalog, CompiledAction
from physical_harness.reasoning.context.compact import (
    ContextBudget,
    ContextItem,
    ControlMode,
    ExecutiveOption,
    build_context,
)
from physical_harness.reasoning.executive import (
    ExecutiveCadence,
    ExecutiveSession,
    RebindReview,
    decision_schema,
    parse_decision,
)
from physical_harness.reasoning.monitor_events import (
    DeterministicMonitorResult,
    emit_advisory,
    monitor_event,
)
from physical_harness.reasoning.monitors import MonitorSignal
from physical_harness.world.semantic_cache import SemanticRepresentationCache
from tests.reasoning.embodied.conftest import make_basis, make_frame


def make_catalog(basis, gripper, *, count=1):
    values = []
    for n in range(count):
        proposal = Proposal(Intent(Verb.STAGE, 'radio'), basis, Parameters(Pose('local').shifted((1.0, 0.0, 0.0), 0.01 * n)), gripper.fingerprint, 'fixture', '1', basis.evidence_ids)
        program = Program(proposal, (Step(Primitive.MOVE_EEF, pose=proposal.parameters.pose, max_steps=5),), ('fixture_only',), 23, 'fixture')
        review = Review(program.fingerprint, basis.fingerprint, 'fixture', 'fixture', (Check('fixture_only', True, basis.evidence_ids),))
        values.append(CompiledAction(program, review, ()))
    return Catalog(basis, gripper.fingerprint, tuple(values), basis.captured_wall + 2)

def packet(gripper, *, seq=0, options=True, **changes):
    b = make_basis(seq, wall=100.0 + seq, sim=float(seq))
    f, _ = make_frame(seq, basis=b)
    cat = make_catalog(b, gripper)
    facts = FactPacket(b, (Fact('target_known', True, b, b.evidence_ids, 'fixture', '1'),))
    opts = (ExecutiveOption('stage', ControlMode.CARTESIAN, cat.actions[0].program.proposal.intent, 'Stage beside the radio', (cat.actions[0].id,), ('target_known',)),) if options else ()
    args = dict(basis=b, task='Turn on the red radio', task_revision='task-v1', subtask='Inspect power control', critical_state={'held_objects': [], 'constraints': ['do not move furniture'], 'unresolved_failures': [], 'robot_state': {'settled': True}}, facts=facts, catalog=cat, options=opts, current_images=(f,), now=b.captured_wall)
    args.update(changes)
    return (build_context(**args), cat)

def test_compact_context_preserves_constraints_and_only_optional_trimming(gripper):
    items = tuple((ContextItem(str(n), 'memory', '{"note":"historical"}', n) for n in range(10)))
    p, _ = packet(gripper, items=items, budget=ContextBudget(optional_items=2))
    assert len(p.metadata()['items']) == 2 and len(p.omitted_items) == 8
    assert p.metadata()['critical_state']['constraints'] == ['do not move furniture']
    with pytest.raises(ValueError):
        packet(gripper, critical_state={})
    with pytest.raises(ValueError):
        packet(gripper, items=(ContextItem('critical', 'focus_entity', '{"x":"' + 'a' * 4000 + '"}', mandatory=True),), budget=ContextBudget(metadata_bytes=3000))

def test_semantic_model_token_counter_is_not_approximated(gripper):
    p, _ = packet(gripper, token_counter=lambda *a: 1000)
    assert p.counted_input_tokens == 1000
    with pytest.raises(ValueError):
        packet(gripper, token_counter=lambda *a: 100000)
    assert packet(gripper)[0].counted_input_tokens is None

def test_reference_images_keep_historical_roles_and_source_clocks(gripper):
    old, _ = make_frame(0)
    p, _ = packet(gripper, seq=1, historical_images=(old,))
    assert [i['role'] for i in p.metadata()['images']] == ['current', 'historical']
    future, _ = make_frame(5)
    with pytest.raises(PermissionError):
        packet(gripper, seq=1, historical_images=(future,))

def test_no_actions_still_allows_hold_or_retrieval(gripper):
    p, _ = packet(gripper, options=False)
    schema = decision_schema(p)
    jsonschema.Draft202012Validator.check_schema(schema)
    d = {'packet_id': p.fingerprint, 'decision': 'hold', 'option_id': None, 'query': ''}
    jsonschema.validate(d, schema)
    assert parse_decision(d, p)['decision'] == 'hold'

@pytest.mark.parametrize('change', [{'option_id': 'invented'}, {'packet_id': 'wrong'}, {'decision': 'move'}, {'query': 'also move'}, {'xyz': [0, 0, 0]}])
def test_executive_cannot_invent_action_parameters(gripper, change):
    p, _ = packet(gripper)
    d = {'packet_id': p.fingerprint, 'decision': 'select', 'option_id': 'stage', 'query': ''}
    d.update(change)
    with pytest.raises((ValueError, PermissionError)):
        parse_decision(d, p)

def test_mode_cannot_disguise_policy_as_classical(gripper):
    p, cat = packet(gripper)
    with pytest.raises(ValueError):
        replace(p.options[0], mode=ControlMode.FROZEN_VLA)

def test_unknown_current_fact_blocks_offered_action(gripper):
    p, cat = packet(gripper)
    b = p.basis
    with pytest.raises(PermissionError):
        packet(gripper, facts=FactPacket(b, (Fact('target_known', None, b, b.evidence_ids, 'f', '1'),)))

def test_cadence_recurring_boundaries_not_progress_or_every_tick():
    c = ExecutiveCadence()
    e = BoundaryEvent('e', 'primitive_completed', make_basis(), 100, 'task-v1', ('e',))
    assert not c.add(replace(e, kind='progress'), active_task_revision='task-v1')
    assert c.add(e, active_task_revision='task-v1')
    assert c.due(now=100, active_task_revision='task-v1') == (e,)
    c.start((e,), now=100)
    assert not c.due(now=101, active_task_revision='task-v1')
    c.add(replace(e, id='e2', kind='new_candidates'), active_task_revision='task-v1')
    c.finish()
    assert c.due(now=101, active_task_revision='task-v1')

def test_old_task_attention_does_not_interrupt_new_task():
    c = ExecutiveCadence()
    e = BoundaryEvent('e', 'relevant_discovery', make_basis(), 104, 'old', ('e',))
    assert not c.add(e, active_task_revision='new')
    assert not c.due(now=104, active_task_revision='new')
REBIND = ('same_goal', 'same_target_instance', 'same_affordance', 'same_constraints', 'permitted_geometric_change', 'no_relevant_contradiction')

def review(packet, option, candidate, basis, revision, bad=False):
    return RebindReview(packet.fingerprint, option.id, candidate.id, basis.fingerprint, revision, tuple((Check(n, not bad, basis.evidence_ids) for n in REBIND)))

def test_slow_gpt_rebinds_semantics_not_old_metric_catalog(journal, gripper):
    p, old = packet(gripper)
    new = make_basis(1, wall=107, sim=1)
    fresh = make_catalog(new, gripper)
    ex = ExecutiveSession(journal=journal, model=None, image_loader=None, clock=lambda: 107)
    decision = {'packet_id': p.fingerprint, 'decision': 'select', 'option_id': 'stage', 'query': ''}
    with pytest.raises(PermissionError):
        old.resolve({'catalog_id': old.id, 'action_id': old.actions[0].id}, new, now=107)
    calls = []
    executor = SimpleNamespace(execute=lambda *a, **kw: calls.append((a, kw)) or 'accepted')
    got = ex.execute_selection(p, decision, current=new, task_revision='task-v1', fresh_catalog=fresh, rebind_review=review, executor=executor, max_steps=5, max_wall_s=1)
    assert got == 'accepted' and calls[0][0][0] is fresh
    assert calls[0][0][1]['action_id'] == fresh.actions[0].id
    with pytest.raises(PermissionError):
        ex.execute_selection(p, decision, current=new, task_revision='task-v1', fresh_catalog=fresh, rebind_review=review, executor=executor, max_steps=5, max_wall_s=1)

@pytest.mark.parametrize('case', ['goal', 'ambiguous', 'unqualified', 'stale', 'frame_reset'])
def test_no_unsafe_rebind_fallback(journal, gripper, case):
    p, _ = packet(gripper)
    new = make_basis(1, wall=107, sim=1)
    if case == 'frame_reset':
        new = replace(new, frame_epoch='other')
    fresh = make_catalog(new, gripper, count=2 if case == 'ambiguous' else 1)
    ex = ExecutiveSession(journal=journal, model=None, image_loader=None, clock=lambda: 110 if case == 'stale' else 107)
    decision = {'packet_id': p.fingerprint, 'decision': 'select', 'option_id': 'stage', 'query': ''}
    executor = SimpleNamespace(execute=lambda *a, **kw: pytest.fail('should not execute'))
    with pytest.raises(PermissionError):
        ex.execute_selection(p, decision, current=new, task_revision='wrong' if case == 'goal' else 'task-v1', fresh_catalog=fresh, rebind_review=lambda *a: review(*a, bad=case == 'unqualified'), executor=executor, max_steps=5, max_wall_s=1)
    assert not journal.records('embodied_selection')

def test_existing_guarded_model_transport_receives_pixels_and_short_schema(journal, gripper):
    p, _ = packet(gripper)
    calls = []

    class Model:

        def call(self, *a):
            calls.append(a)
            return {'packet_id': p.fingerprint, 'decision': 'hold', 'option_id': None, 'query': ''}

    def loader(f):
        _, raw = make_frame(0, basis=p.basis)
        return SimpleNamespace(id=f.asset_id, episode='ep', width=32, height=24, data=raw)
    ex = ExecutiveSession(journal=journal, model=Model(), image_loader=loader, clock=lambda: 100)
    assert ex.decide(p)['decision'] == 'hold'
    assert len(calls) == 1 and calls[0][1] == 'embodied_executive'
    assert calls[0][3]['task'] == 'Turn on the red radio'

def test_metrics_distinguish_unknown_cost_reasoning_and_repeated_pixels(journal):
    f, _ = make_frame()
    a = ComputeReceipt('a', 'executive', 'configured-model', 'r', 'completed', 100, 101, 1000, 200, 80, 50, None, **receipt_images((f,)))
    led = ComputeLedger(journal)
    led.add(a)
    led.add(a)
    led.add(replace(a, id='b', request_fingerprint='r2', status='unknown', input_tokens=None, cached_input_tokens=None))
    out = led.report()['roles']['executive']
    assert out['calls'] == 2 and out['pixels_sent'] == 2 * f.pixels
    assert out['first_seen_content_pixels'] == out['repeated_content_pixels'] == f.pixels
    assert out['output_tokens_known'] == 160 and out['reasoning_tokens_known'] == 100
    assert out['missing_cost_calls'] == 2 and out['missing_usage_calls'] == 1

@pytest.mark.parametrize('changes', [{'cached_input_tokens': 1100}, {'reasoning_output_tokens': 99}, {'input_tokens': True}, {'inference_seconds': 2.0, 'queue_seconds': 1.0}])
def test_impossible_usage_rejected(changes):
    base = dict(id='a', role='gpt', model='m', request_fingerprint='r', status='completed', start_wall=100, end_wall=101, input_tokens=1000, cached_input_tokens=100, output_tokens=80, reasoning_output_tokens=50)
    base.update(changes)
    with pytest.raises(ValueError):
        ComputeReceipt(**base)

def test_cache_exact_dependencies_and_no_safety_authority():
    c = SemanticRepresentationCache(maximum=2)
    kwargs = dict(episode='ep', model='glm', preprocessing='v1', contents=('imagehash',), prompt='objects', schema='s1', scope_revision='v1')
    d = c.dependencies(**kwargs)
    value = {'label': 'radio?', 'source': 'old'}
    c.put('semantic_annotation', d, value, now=1, ttl_s=2)
    value['label'] = 'wrong'
    assert c.get('semantic_annotation', d, now=2)['label'] == 'radio?'
    assert c.get('semantic_annotation', c.dependencies(**dict(kwargs, prompt='other')), now=2) is None
    assert c.get('semantic_annotation', d, now=4) is None
    with pytest.raises(PermissionError):
        c.put('collision_approval', d, {}, now=1, ttl_s=2)

def test_monitor_routes_advisory_only(journal):
    b = make_basis()
    scheduler = ExecutiveCadence()
    result = DeterministicMonitorResult('m', 'cmd', b, 'arrived', ('e',), 'arrival', 'geometry')
    assert emit_advisory(journal, result, task_revision='task-v1', available_wall=100, scheduler=scheduler)
    assert scheduler.due(now=100, active_task_revision='task-v1')[0].kind == 'primitive_completed'
    signal = MonitorSignal('l', 'cmd', b, 'completion_candidate', 'complete', ('e',))
    assert monitor_event(signal, task_revision='task-v1', available_wall=100).kind == 'verifier_result'
    with pytest.raises(PermissionError):
        monitor_event(replace(signal, semantic_authority='truth'), task_revision='task-v1', available_wall=100)

@pytest.mark.parametrize('modality', ['lidar', 'tactile', 'force_torque', 'high_resolution_rgb'])
def test_hardware_sensors_stay_dormant_in_behavior(modality):
    s = SensorCapability('s', modality, 'hardware_only', 'c', True)
    with pytest.raises(PermissionError):
        admitted_sensors((s,), domain='behavior_sim')
    assert admitted_sensors((replace(s, available=False),), domain='behavior_sim') == ()

def test_foveation_crops_source_not_invents_resolution():
    f, _ = make_frame()
    result = FoveatedRequest(f, 'region', 'inspect', 100000).plan()
    assert result['max_pixels'] == f.pixels
    assert result['synthetic_upscaling_is_measurement'] is False

def test_single_call_keypose_mode_reuses_v2_bounds_and_never_executes(journal, gripper):
    from physical_harness.planning.actions.primitives import TemplateConfig
    from physical_harness.planning.motion import MotionLimits, PoseAnchor
    p, _ = packet(gripper)
    anchors = (PoseAnchor('anchor', p.basis, 'radio', Pose('local'), p.basis.evidence_ids),)
    calls = []

    class Model:

        def call(self, *a):
            calls.append(a)
            return {'basis_fingerprint': p.basis.fingerprint, 'arm': 'right_arm', 'waypoints': [{'anchor_id': 'anchor', 'offset_m': [0.01, 0.0, 0.0], 'rotvec_rad': [0.0, 0.0, 0.0], 'gripper': 'hold'}]}
    _, raw = make_frame()

    def loader(f):
        return SimpleNamespace(id=f.asset_id, episode=f.basis.episode, width=f.width, height=f.height, data=raw)
    session = ExecutiveSession(journal=journal, model=Model(), image_loader=loader, clock=lambda: 100)
    result = session.propose_keyposes(p, entity='radio', anchors=anchors, start_eef=Pose('local'), gripper=gripper, template=TemplateConfig(), limits=MotionLimits(), model_revision='mock')
    assert len(calls) == 1 and calls[0][1] == 'embodied_keypose'
    assert 'situated_whole_path' in result.required_checks
    assert not journal.records('compiled_action')
    assert journal.records('embodied_keypose')[0]['authority'] == 'proposal_only'
