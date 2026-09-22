from dataclasses import replace

import pytest

from physical_harness.situated.contracts import Fact, FactPacket
from physical_harness.situated.decision import Branch, branch_packet, resolve_branch
from physical_harness.situated.perception import PerceptionNeed, schedule_perception
from physical_harness.situated.reuse import Dependency, RepresentationCache


def facts(basis, value=True):
    return FactPacket(basis, (Fact('visible', value, basis, basis.evidence_ids, 'tracker', '1'),))

def test_structured_branch_uses_only_known_present_facts(basis):
    fs = facts(basis)
    packet = branch_packet(fs, (Branch('inspect', 'inspect current object', (('visible', True),)), Branch('reacquire', 'look for target', (('visible', False),))), ())
    assert [x['id'] for x in packet['choices']] == ['inspect']
    assert resolve_branch({'packet_id': packet['packet_id'], 'choice_id': 'inspect'}, packet, fs) == 'inspect'
    with pytest.raises(PermissionError):
        resolve_branch({'packet_id': packet['packet_id'], 'choice_id': 'reacquire'}, packet, fs)

@pytest.mark.parametrize('unknown,visual', [(True, False), (False, True)])
def test_text_router_refuses_missing_or_visual_evidence(basis, unknown, visual):
    with pytest.raises(PermissionError):
        branch_packet(facts(basis, None if unknown else True), (Branch('inspect', 'inspect', (('visible', True),)),), (), visual_reasoning_required=visual)

def test_changed_fact_same_basis_invalidates_decision(basis):
    packet = branch_packet(facts(basis), (Branch('inspect', 'inspect'),), ('visible',))
    with pytest.raises(PermissionError, match='facts changed'):
        resolve_branch({'packet_id': packet['packet_id'], 'choice_id': 'inspect'}, packet, facts(basis, False))

def test_mutated_branch_packet_is_not_an_authority(basis):
    fs = facts(basis)
    packet = branch_packet(fs, (Branch('inspect', 'inspect'),), ('visible',))
    packet['choices'].append({'id': 'move_anywhere', 'description': 'bad'})
    with pytest.raises(PermissionError, match='mutated'):
        resolve_branch({'packet_id': packet['packet_id'], 'choice_id': 'move_anywhere'}, packet, fs)

def deps(**changes):
    return tuple((Dependency(k, v) for k, v in dict(episode='e', model='m', preprocess='p', content='sha', **{}).items() if k not in changes)) + tuple((Dependency(k, v) for k, v in changes.items()))

def test_exact_reuse_invalidation_and_counts():
    disposed = []
    c = RepresentationCache(maximum=2, dispose=disposed.append)
    c.put('image_encoding', deps(), 'tensor-a', now=0, ttl_s=2)
    assert c.get('image_encoding', deps(), now=1) == 'tensor-a'
    assert c.get('image_encoding', deps(model='m2'), now=1) is None
    c.invalidate('content')
    assert disposed == ['tensor-a']
    assert c.get('image_encoding', deps(), now=1) is None
    assert c.hits == 1 and c.misses == 2

@pytest.mark.parametrize('kind', ['metric_pose', 'action_catalog', 'collision_free', 'frozen_policy_output'])
def test_cache_cannot_reuse_motion_authority(kind):
    with pytest.raises(PermissionError):
        RepresentationCache().put(kind, deps(), {}, now=0, ttl_s=1)

def test_cache_expires_and_requires_complete_dependency_key():
    c = RepresentationCache()
    with pytest.raises(ValueError):
        c.put('image_encoding', (Dependency('content', 'sha'),), {}, now=0, ttl_s=1)
    c.put('image_encoding', deps(), 'x', now=0, ttl_s=1)
    assert c.get('image_encoding', deps(), now=1) is None

def test_side_view_keeps_semantics_without_forcing_recognition():
    state = PerceptionNeed(True, True, True, True, False, False, True, False, 2.0)
    result = schedule_perception(state)
    assert not result.recognize and result.track and result.reconstruct_local_geometry
    assert not result.request_inspection
    ambiguous = replace(state, association_established=False)
    assert schedule_perception(ambiguous).request_inspection
    assert not schedule_perception(ambiguous).recognize
    assert schedule_perception(replace(state, visible=False)).request_inspection

def test_irrelevant_objects_do_not_trigger_expensive_geometry():
    state = PerceptionNeed(False, True, False, False, False, True, False, False, 0.0)
    work = schedule_perception(state)
    assert not any((work.recognize, work.track, work.reconstruct_local_geometry, work.request_inspection))
    assert 'safety_sensing_unchanged' in work.reason

def test_branch_boolean_is_not_interchangeable_with_numeric_zero():
    from physical_harness.situated.contracts import Fact, FactPacket
    from physical_harness.situated.decision import Branch, branch_packet

    from .conftest import make_basis
    b = make_basis()
    facts = FactPacket(b, (Fact('present', 0, b, b.evidence_ids, 'measured', '1'),))
    with pytest.raises(PermissionError):
        branch_packet(facts, (Branch('b', 'false', (('present', False),)),), ('present',))
