import io

import pytest
from PIL import Image

from physical_harness.perception.discovery import parse_response
from physical_harness.perception.identity import IdentityLedger, SemanticClaim, Tracklet
from physical_harness.perception.keyframes import (
    SemanticKeyframes,
    TriggerConfig,
    ViewSample,
    thumbnail_descriptor,
)
from physical_harness.perception.regions import (
    BoxSeed,
    crop_source,
    require_current_tracking,
    require_seed_target,
)
from physical_harness.world.inventory import (
    CanonicalView,
    InventoryLimits,
    SemanticInventory,
    choose_canonical_views,
)
from tests.reasoning.embodied.conftest import make_basis, make_frame, make_request, response


def result(req=None, count=1, retention=None):
    req = req or make_request()
    raw = response(req, count=count)
    if retention:
        for u in raw['updates']:
            u['retention'] = retention
    return parse_response(raw, req, model='mock-discovery', completed_wall=req.submitted_wall + 4)

def add(inv, req=None, **kwargs):
    res = result(req, **kwargs)
    return inv.accept(res, received_wall=res.completed_wall, current_task_revision='task-v1')

def test_inventory_result_is_historical_and_reopens(journal):
    inv = SemanticInventory(journal)
    key, = add(inv)
    row = inv.state(key, cutoff_sim=0, cutoff_wall=104)
    assert row['kind'] == 'sighting' and row['manipulation_authority'] is False
    assert row['entity_id'] is None
    assert SemanticInventory(journal).revision == inv.revision
    assert not hasattr(inv, 'execute')

def test_future_semantics_not_visible_even_when_simulator_paused(journal):
    inv = SemanticInventory(journal)
    key, = add(inv)
    with pytest.raises(ValueError):
        inv.state(key, cutoff_sim=0, cutoff_wall=103.9)
    assert inv.state(key, cutoff_sim=0, cutoff_wall=104)['observed_sim'] == 0

def test_future_revision_does_not_change_past_context(journal):
    inv = SemanticInventory(journal)
    add(inv)
    old = inv.tier_view(current=make_basis(), now=104, task_revision='task-v1')
    add(inv, make_request('future', seq=2))
    assert inv.tier_view(current=make_basis(), now=104, task_revision='task-v1') == old

def test_duplicate_result_and_cross_episode_rejected(journal):
    inv = SemanticInventory(journal)
    res = result()
    inv.accept(res, received_wall=104, current_task_revision='task-v1')
    with pytest.raises(PermissionError):
        inv.accept(res, received_wall=104, current_task_revision='task-v1')
    other_frame, _ = make_frame(basis=make_basis(episode='other'))
    other = result(make_request('other', frames=(other_frame,)))
    with pytest.raises(PermissionError):
        inv.accept(other, received_wall=104, current_task_revision='task-v1')

def test_hot_warm_cold_and_pin_budget(journal):
    inv = SemanticInventory(journal, InventoryLimits(hot=1, warm=2, total_records=4))
    a, b, c = add(inv, count=3)
    view = inv.tier_view(current=make_basis(), now=104, task_revision='task-v1')
    assert len(view['hot']) == len(view['warm']) == len(view['cold_ids']) == 1
    inv.pin(c, 'held', now=105)
    assert inv.tier_view(current=make_basis(), now=105, task_revision='task-v1')['hot'][0]['id'] == c
    with pytest.raises(ValueError):
        inv.pin(b, 'active_goal', now=105)
    inv.unpin(c, now=106)
    assert len(inv.records) == 3
    assert SemanticInventory(journal, inv.limits).pins == {}

@pytest.mark.parametrize('reason', ['model_said_so', '', 'confidence'])
def test_model_cannot_create_operator_pins(journal, reason):
    inv = SemanticInventory(journal)
    key, = add(inv)
    with pytest.raises(ValueError):
        inv.pin(key, reason, now=105)

def test_aggregate_and_ignored_items_retrievable(journal):
    inv = SemanticInventory(journal)
    a, = add(inv, retention='aggregate')
    b, = add(inv, make_request('ignore'), retention='ignore')
    view = inv.tier_view(current=make_basis(), now=104, task_revision='task-v1')
    assert view['hot'][0]['kind'] == 'aggregate' and view['ignored_archived'] == 1
    assert {x['id'] for x in inv.retrieve('radio', current=make_basis(), now=104)} == {a, b}
    with pytest.raises(PermissionError):
        inv.retrieve('radio', current=make_basis(episode='wrong'), now=104)

def test_old_task_results_do_not_trigger_new_task(journal):
    inv = SemanticInventory(journal)
    res = result(make_request(task_revision='old'))
    inv.accept(res, received_wall=104, current_task_revision='new')
    delta = inv.delta(after_wall=100, through_wall=104, cutoff_sim=0, task_revision='new')
    assert delta['attention_current_task'] == [] and len(delta['events']) == 1
    assert inv.known_summary(current=make_basis(), now=104, task_revision='new')[0]

def test_capacity_failure_atomic(journal):
    inv = SemanticInventory(journal, InventoryLimits(hot=1, warm=1, total_records=1))
    with pytest.raises(ValueError):
        add(inv, count=2)
    assert not inv.records and (not journal.records(inv.KIND))

def test_sighting_link_requires_actual_identity_and_separate_association(journal):
    inv = SemanticInventory(journal)
    key, = add(inv)
    identity = IdentityLedger(journal)
    b = make_basis(1, wall=105, sim=1)
    track = Tracklet(b, 'head', 'session', 'local-1', 'mask', (0.0, 0.0, 1.0), 0.02)
    entity = identity.new_entity(track, SemanticClaim('radio', 'recognized', b.evidence_ids, 'fixture'))
    with pytest.raises(PermissionError):
        inv.link_entity(key, entity=entity, identity=identity, current=b, association_check=lambda *a: None, evidence_ids=('association',), available_wall=105)
    inv.link_entity(key, entity=entity, identity=identity, current=b, association_check=lambda *a: True, evidence_ids=('association',), available_wall=105)
    row = inv.state(key, cutoff_sim=1, cutoff_wall=105)
    assert row['entity_id'] == entity and row['manipulation_authority'] is False
    assert 'position' not in row

def test_canonical_views_are_associated_complementary_and_causal(journal):
    inv = SemanticInventory(journal)
    key, = add(inv)
    f, _ = make_frame(1, color=(1, 2, 3))
    g, _ = make_frame(2, color=(3, 2, 1))
    a = CanonicalView(f, (1.0, 0.0, 0.0), 'object-frame', 0.9, ('assoc',))
    b = CanonicalView(g, (0.0, 1.0, 0.0), 'object-frame', 0.8, ('assoc',))
    current = make_basis(5, wall=105, sim=5)
    with pytest.raises(PermissionError):
        inv.add_views(key, (a, b), current=current, available_wall=105, association_check=lambda *a: False)
    inv.add_views(key, (a, b), current=current, available_wall=105, association_check=lambda *a: True)
    assert len(inv.state(key, cutoff_sim=5, cutoff_wall=105)['views']) == 2
    assert inv.state(key, cutoff_sim=0, cutoff_wall=104)['views'] == []
    assert SemanticInventory(journal).revision == inv.revision

def test_redundant_canonical_views_are_not_repeated():
    f, _ = make_frame(1)
    g, _ = make_frame(2)
    a = CanonicalView(f, (1.0, 0.0, 0.0), 'frame', 0.9, ('a',))
    b = CanonicalView(g, (1.0, 0.0, 0.0), 'frame', 0.8, ('a',))
    assert choose_canonical_views((a, b)) == (a,)
    with pytest.raises(ValueError):
        CanonicalView(f, (2.0, 0.0, 0.0), 'frame', 0.9, ('a',))

def test_place_annotation_retains_source_observation(journal):
    inv = SemanticInventory(journal)
    key, = add(inv)
    inv.set_place(key, 'room', evidence_ids=('map',), current=make_basis(), available_wall=105)
    row = inv.retrieve('radio', place_id='room', current=make_basis(), now=105)[0]
    assert row['observed_sim'] == 0 and row['authority'] == 'historical_semantic_hypothesis'
    assert inv.retrieve('radio', place_id='other', current=make_basis(), now=105) == ()

def sample(seq=0, value=0.0, **kwargs):
    f, _ = make_frame(seq)
    return ViewSample(f, (value,) * 3, **kwargs)

def test_keyframe_triggers_reference_last_submitted_view():
    k = SemanticKeyframes()
    s = sample()
    assert k.ingest(s, now=s.frame.available_wall)
    k.acknowledge_submission((s.frame,))
    assert not k.ingest(sample(1, 0.01), now=101)
    assert 'image_novelty' in k.ingest(sample(2, 0.4), now=102)

@pytest.mark.parametrize('field,value', [('room_changed', True), ('requested', True), ('important_lost', ('radio',)), ('tracks', ('new',))])
def test_semantic_trigger_signals(field, value):
    k = SemanticKeyframes()
    s = sample()
    k.ingest(s, now=s.frame.available_wall)
    k.acknowledge_submission((s.frame,))
    assert k.ingest(sample(1, **{field: value}), now=101)

def test_buffer_retains_transient_views_and_reports_eviction():
    k = SemanticKeyframes(TriggerConfig(buffer_frames=3, buffer_seconds=5, batch_images=3))
    k.ingest(sample(0, 0), now=100)
    k.ingest(sample(1, 1), now=101)
    k.ingest(sample(2, 0), now=102)
    frames = k.select(sample(2, 0).frame, now=102)
    assert any((f.basis.sim_time == 1 for f in frames))
    k.ingest(sample(3, 0.4), now=103)
    assert k.report()['evicted_frames'] == 1

def test_thumbnail_is_actual_bounded_image():
    f, raw = make_frame()
    desc = thumbnail_descriptor(raw, f)
    assert len(desc) == 16 * 16 * 3 and all((0 <= v <= 1 for v in desc))
    with pytest.raises(PermissionError):
        thumbnail_descriptor(b'bad', f)

def test_source_crop_and_sam_box_are_frame_bound():
    f, raw = make_frame()
    writes = []
    crop = crop_source(f, (0.25, 0.25, 0.75, 0.75), raw, available_wall=101, store=lambda data, meta: writes.append((data, meta)) or 'crop-1')
    assert (crop.width, crop.height) == (16, 12)
    assert crop.parent_id == f.asset_id
    assert Image.open(io.BytesIO(writes[0][0])).size == (16, 12)
    seed = BoxSeed('sighting', f, (0.25, 0.25, 0.75, 0.75), ('radio',))
    prompt = seed.sam_prompt(session_id='session', source_frame_index=3)
    assert prompt['bounding_boxes'] == [[0.25, 0.25, 0.5, 0.5]]
    require_seed_target(seed, f, now=101)
    with pytest.raises(PermissionError):
        require_seed_target(seed, make_frame(1)[0], now=101)

def test_current_tracking_does_not_claim_metric_or_identity_authority():
    f, _ = make_frame()
    seed = BoxSeed('s', f, (0.0, 0.0, 1.0, 1.0), ('radio',))
    b = make_basis(1, wall=101, sim=1)
    kwargs = dict(source_hash=f.content_sha256, session_id='session', mask_basis=b, mask_evidence='mask')
    with pytest.raises(PermissionError):
        require_current_tracking(seed, b, association_check=lambda *a: None, **kwargs)
    out = require_current_tracking(seed, b, association_check=lambda *a: True, **kwargs)
    assert out['motion_authority'] is False and 'xyz' not in out
