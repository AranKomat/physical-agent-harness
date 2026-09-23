import hashlib
import io
import json
from dataclasses import replace

import pytest
from PIL import Image

from physical_harness.core.tasks import FactPacket
from physical_harness.perception.contracts import FrameRef
from physical_harness.perception.identity import (
    AssociationProof,
    IdentityLedger,
    SemanticClaim,
    Tracklet,
    focus_identity_view,
)
from physical_harness.perception.regions import crop_source
from physical_harness.planning.actions.compiler import Catalog
from physical_harness.reasoning.context.compact import ContextBudget, ContextItem, build_context
from tests.reasoning.embodied.conftest import make_basis, make_frame


def track(n):
    return Tracklet(make_basis(n, sim=float(n), wall=100. + n), 'head', 'session',
                    '0', f'mask-{n}', (0., 0., 1.), .01)


def claim(label, evidence):
    return SemanticClaim(label, 'recognized', (evidence,), 'fixture')


def proof(identity, entity, new):
    return AssociationProof(entity, identity.revision(entity), new.fingerprint,
                            True, True, True, 'fixture', (new.mask_evidence_id,))


@pytest.mark.parametrize('changes', [
    {'sim_time': 0.}, {'captured_wall': 100.}, {'episode': 'other'},
    {'robot_fingerprint': 'other'}, {'domain': 'behavior_sim'},
])
def test_identity_view_rejects_future_or_foreign_state(journal, changes):
    identity = IdentityLedger(journal)
    source = track(1)
    entity = identity.new_entity(source, claim('radio', 'seen'))
    with pytest.raises(PermissionError):
        focus_identity_view(identity, entity, replace(source.basis, **changes))


@pytest.mark.parametrize('resolve', [False, True])
def test_later_conflict_or_resolution_cannot_enter_old_view(journal, resolve):
    identity = IdentityLedger(journal)
    first, second, third = track(0), track(1), track(2)
    entity = identity.new_entity(first, claim('radio', 'front'))
    identity.observe(entity, second, claim('box', 'side'), proof(identity, entity, second))
    cutoff = first.basis
    if resolve:
        identity.resolve_semantics(entity, third, claim('radio', 'new-front'),
                                   proof(identity, entity, third))
        cutoff = second.basis
    with pytest.raises(PermissionError, match='Future identity state'):
        focus_identity_view(identity, entity, cutoff)


def test_current_binding_and_past_semantics_survive_guard(journal):
    identity = IdentityLedger(journal)
    source = track(0)
    entity = identity.new_entity(source, claim('radio', 'front'))
    assert focus_identity_view(identity, entity, source.basis)['current_geometry_available']
    later = replace(track(1).basis, frame_epoch='reset')
    view = focus_identity_view(identity, entity, later)
    assert view['current_binding'] is None
    assert view['remembered_semantics']['label'] == 'radio'


def crop(box):
    image = Image.new('RGB', (720, 720), (1, 2, 3))
    output = io.BytesIO()
    image.save(output, format='PNG')
    raw = output.getvalue()
    frame = FrameRef(make_basis(), 'source', hashlib.sha256(raw).hexdigest(),
                     'head', 720, 720, 100.)
    saved = {}

    def store(data, metadata):
        saved.update(data=data, metadata=metadata)
        return 'crop'

    result = crop_source(frame, box, raw, available_wall=101., store=store)
    assert result.parent_id == frame.asset_id
    assert result.content_sha256 == hashlib.sha256(saved['data']).hexdigest()
    assert saved['metadata']['parent_hash'] == frame.content_sha256
    return saved['metadata']['pixel_box'], result


@pytest.mark.parametrize('pixels', [
    (310, 370, 720, 630), (0, 430, 110, 515), (438, 505, 556, 720),
    (0, 0, 720, 720),
])
def test_integer_pixel_boxes_roundtrip_exactly(pixels):
    actual, result = crop(tuple(x / 720 for x in pixels))
    assert actual == pixels
    assert (result.width, result.height) == (pixels[2] - pixels[0], pixels[3] - pixels[1])


@pytest.mark.parametrize('epsilon', [1e-7, .25])
def test_fractional_edges_remain_conservative(epsilon):
    actual, _ = crop(tuple(x / 720 for x in (
        110 - epsilon, 370 - epsilon, 440 + epsilon, 505 + epsilon)))
    assert actual == (109, 369, 441, 506)


def packet(items, budget):
    frame, _ = make_frame()
    basis = frame.basis
    return build_context(
        basis=basis, task='task', task_revision='v1', subtask='review',
        critical_state={'held_objects': 'unknown', 'constraints': ['no motion'],
                        'unresolved_failures': ['unknown stop'], 'robot_state': {}},
        facts=FactPacket(basis, ()), catalog=Catalog(basis, 'catalog', (), 102.),
        options=(), current_images=(frame,), now=100.25, items=items, budget=budget)


def item(identifier, size, *, importance=0., mandatory=False):
    return ContextItem(identifier, 'memory', json.dumps({'x': 'a' * size}), importance, mandatory)


def test_omission_ids_prevent_overbudget_admission():
    mandatory = item('required', 20, mandatory=True)
    high = item('high', 1000, importance=2.)
    low = item('low', 2000, importance=1.)
    # Exactly enough for required + high, but not the later low omission ID.
    limit = len(packet((mandatory, high), ContextBudget()).metadata_json.encode())
    result = packet((low, mandatory, high), ContextBudget(metadata_bytes=limit))
    assert [i['id'] for i in result.metadata()['items']] == ['required']
    assert result.omitted_items == ('high', 'low')
    assert len(result.metadata_json.encode()) <= limit
    assert result == packet((high, low, mandatory), ContextBudget(metadata_bytes=limit))


def test_byte_pruning_keeps_higher_priority_optional():
    items = (item('required', 10, mandatory=True), item('high', 500, importance=2.),
             item('low', 2000, importance=1.))
    reference = packet(items, ContextBudget(optional_items=1))
    limit = len(reference.metadata_json.encode())
    result = packet(tuple(reversed(items)), ContextBudget(metadata_bytes=limit))
    assert result.metadata() == reference.metadata()
    assert result.omitted_items == ('low',)


def test_equal_priority_pruning_uses_stable_id_order():
    items = (item('b', 1000), item('a', 1000))
    reference = packet(items, ContextBudget(optional_items=1))
    result = packet(items, ContextBudget(metadata_bytes=len(reference.metadata_json.encode())))
    assert [i['id'] for i in result.metadata()['items']] == ['a']
    assert result.omitted_items == ('b',)


@pytest.mark.parametrize('optional_limit', [1, 3])
def test_oversized_high_priority_item_does_not_block_small_item(optional_limit):
    items = (item('required', 10, mandatory=True), item('huge', 10000, importance=3.),
             item('small', 100, importance=2.), item('later', 100, importance=1.))
    budget = ContextBudget(metadata_bytes=1024, optional_items=optional_limit)
    result = packet(items, budget)
    kept = [i['id'] for i in result.metadata()['items']]
    assert kept == (['required', 'small'] if optional_limit == 1
                    else ['required', 'small', 'later'])
    assert result.omitted_items == (('huge', 'later') if optional_limit == 1 else ('huge',))
    assert len(result.metadata_json.encode()) <= budget.metadata_bytes
    assert result == packet(tuple(reversed(items)), budget)


def test_mandatory_or_omission_metadata_overflow_fails():
    with pytest.raises(ValueError, match='Required context'):
        packet((item('required', 2000, mandatory=True),), ContextBudget(metadata_bytes=1024))
    items = tuple(item(f'{n:03d}-' + 'x' * 100, 1) for n in range(20))
    with pytest.raises(ValueError, match='Required context'):
        packet(items, ContextBudget(metadata_bytes=1024, optional_items=0))
