from dataclasses import replace

import pytest

from physical_harness.situated.identity import (
    AssociationProof,
    IdentityLedger,
    SemanticClaim,
    Tracklet,
    geometric_candidates,
)
from physical_harness.situated.integration import identity_binding

from .conftest import make_basis


def track(n=0, **kwargs):
    return replace(Tracklet(make_basis(n), 'head', 'sam-session', '1', f'mask-{n}', (0.4, 0.2, 0.7), 0.01), **kwargs)

def claim(label='radio', status='recognized', e='recognition-front'):
    return SemanticClaim(label, status, (e,), 'fixture-recognizer')

def proof(mem, entity, new, **kwargs):
    return replace(AssociationProof(entity, mem.revision(entity), new.fingerprint, True, True, True, 'fixture-association', (new.mask_evidence_id,)), **kwargs)

def test_old_semantics_new_geometry_and_real_journal_replay(journal):
    mem = IdentityLedger(journal)
    entity = mem.new_entity(track(), claim())
    new = track(1, center=(0.41, 0.2, 0.7))
    mem.observe(entity, new, claim(None, 'ambiguous', 'side'), proof(mem, entity, new))
    binding = mem.binding(entity, new.basis)
    assert binding['canonical']['label'] == 'radio'
    assert binding['canonical']['observed_at'] == 0.0
    assert binding['canonical']['evidence_ids'] == ['recognition-front']
    assert binding['geometry']['center'][0] == 0.41
    assert IdentityLedger(journal).binding(entity, new.basis) == binding
    role = identity_binding(mem, role='target', entity=entity, part='whole', current=new.basis)
    assert role.unambiguous

def test_repeat_recognition_does_not_retimestamp_original_claim(journal):
    mem = IdentityLedger(journal)
    entity = mem.new_entity(track(), claim())
    new = track(1)
    mem.observe(entity, new, claim(e='propagated-label'), proof(mem, entity, new))
    assert mem.state(entity)['canonical']['observed_at'] == 0

@pytest.mark.parametrize('field,value', [('unique', False), ('unique', None), ('temporal_support', None), ('geometry_support', False), ('geometry_support', None)])
def test_uncertain_association_never_attributes_current_geometry(journal, field, value):
    mem = IdentityLedger(journal)
    entity = mem.new_entity(track(), claim())
    new = track(1)
    mem.observe(entity, new, claim(), proof(mem, entity, new, **{field: value}))
    assert mem.state(entity)['last_track']['basis']['observation_id'] == 'obs-0'
    with pytest.raises(PermissionError):
        mem.binding(entity, new.basis)

def test_alternatives_override_spurious_unique_claim(journal):
    mem = IdentityLedger(journal)
    entity = mem.new_entity(track(), claim())
    new = track(1)
    mem.observe(entity, new, claim(), proof(mem, entity, new), alternatives=('other-entity',))
    assert mem.state(entity)['association'] == 'ambiguous'

def test_contradiction_requires_new_evidence_to_resolve(journal):
    mem = IdentityLedger(journal)
    entity = mem.new_entity(track(), claim())
    new = track(1)
    mem.observe(entity, new, claim('box', e='side-box'), proof(mem, entity, new))
    with pytest.raises(PermissionError):
        mem.binding(entity, new.basis)
    assert mem.state(entity)['canonical']['label'] == 'radio'
    assert identity_binding(mem, role='target', entity=entity, part='whole', current=new.basis, require_semantics=False).unambiguous
    third = track(2)
    with pytest.raises(PermissionError, match='new discriminating'):
        mem.resolve_semantics(entity, third, claim('box', e='side-box'), proof(mem, entity, third))
    mem.resolve_semantics(entity, third, claim('radio', e='new-front'), proof(mem, entity, third))
    assert mem.binding(entity, third.basis)['canonical']['evidence_ids'] == ['new-front']

def test_not_observed_retains_label_but_blocks_actions(journal):
    mem = IdentityLedger(journal)
    entity = mem.new_entity(track(), claim())
    mem.mark_not_observed(entity, make_basis(1), ('fresh-side-camera',))
    assert mem.state(entity)['canonical']['label'] == 'radio'
    assert mem.state(entity)['last_track']['center'] == [0.4, 0.2, 0.7]
    with pytest.raises(PermissionError):
        mem.binding(entity, make_basis(1))

def test_cross_camera_local_ids_never_merge_automatically(journal):
    mem = IdentityLedger(journal)
    a = mem.new_entity(track(), claim())
    b = mem.new_entity(track(camera='wrist'), claim('box'))
    assert a != b
    new = track(1, camera='wrist')
    with pytest.raises(PermissionError, match='another entity'):
        mem.observe(a, new, claim(None, 'ambiguous'), proof(mem, a, new))

def test_cross_camera_proof_can_link_unassigned_track(journal):
    mem = IdentityLedger(journal)
    a = mem.new_entity(track(), claim())
    new = track(1, camera='wrist', session='wrist-session')
    mem.observe(a, new, claim(None, 'ambiguous'), proof(mem, a, new))
    assert mem.binding(a, new.basis)['canonical']['label'] == 'radio'

def test_stale_and_foreign_proofs_rejected(journal):
    mem = IdentityLedger(journal)
    a = mem.new_entity(track(), claim())
    new = track(1)
    with pytest.raises(PermissionError):
        mem.observe(a, new, claim(), proof(mem, a, new, prior_revision='old'))
    foreign = replace(new, basis=make_basis(1, episode='other'))
    with pytest.raises(PermissionError):
        mem.observe(a, foreign, claim(), proof(mem, a, foreign))

def test_geometry_matches_are_only_suggestions(journal):
    mem = IdentityLedger(journal)
    a = mem.new_entity(track(), claim())
    b = mem.new_entity(track(local_id='2'), claim('box'))
    matches = geometric_candidates(track(1), (mem.state(a), mem.state(b)), max_gap_s=2, max_distance_m=0.02)
    assert set(matches) == {a, b}
    new = track(1, basis=make_basis(1, frame_epoch='reset'))
    assert geometric_candidates(new, (mem.state(a),), max_gap_s=2, max_distance_m=0.02) == ()

def test_relocalization_keeps_semantics_not_old_geometry(journal):
    mem = IdentityLedger(journal)
    a = mem.new_entity(track(), claim())
    with pytest.raises(PermissionError):
        mem.binding(a, make_basis(1, frame_epoch='new'))

def test_failed_journal_write_does_not_change_identity(journal, monkeypatch):
    mem = IdentityLedger(journal)
    a = mem.new_entity(track(), claim())
    revision = mem.revision(a)
    monkeypatch.setattr(journal, 'put', lambda *a: (_ for _ in ()).throw(OSError('full')))
    new = track(1)
    with pytest.raises(OSError):
        mem.observe(a, new, claim(), proof(mem, a, new))
    assert mem.revision(a) == revision

@pytest.mark.parametrize('kwargs', [{'center': (0.1, 0.2, 0.3), 'radius_error_m': None}, {'center': None, 'radius_error_m': 0.1}, {'center': (float('nan'), 0.1, 0.1)}, {'center': [1, 2, 3]}])
def test_invalid_track_geometry(kwargs):
    with pytest.raises(ValueError):
        track(**kwargs)
