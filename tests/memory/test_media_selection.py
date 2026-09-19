from dataclasses import replace
from types import SimpleNamespace

import pytest

from physical_harness.memory import Boundary, EventRecorder, RecentBuffer, boundary_from_runtime
from physical_harness.memory.media import make_crop, storyboard


def test_crop_preserves_original_time_camera_and_parent(memory):
    store, blobs = memory
    a = blobs.frame(store, at=2)
    crop = make_crop(store, a.asset_id, (3, 4, 18, 20), blobs.put, store.cutoff(10))
    assert (crop.observed_end, crop.parent_id, crop.camera) == (2, a.asset_id, a.camera)
    assert (crop.width, crop.height) == (15, 16)
    assert crop.kind == 'crop'


@pytest.mark.parametrize('box', [(-1, 0, 5, 5), (0, 0, 999, 1), (1, 1, 1, 2), (0., 0, 1, 1)])
def test_invalid_crop(memory, box):
    store, blobs = memory
    a = blobs.frame(store)
    with pytest.raises(ValueError):
        make_crop(store, a.asset_id, box, blobs.put, store.cutoff(10))


def test_crop_cannot_renew_old_evidence_time(memory):
    store, blobs = memory
    a = blobs.frame(store)
    crop = make_crop(store, a.asset_id, (0, 0, 5, 5), blobs.put, store.cutoff(10))
    with pytest.raises(ValueError, match='capture time'):
        store.add_asset(replace(crop, asset_id='fake-fresh', observed_start=10, observed_end=10))


def test_image_metadata_checked_on_crop(memory):
    store, blobs = memory
    a = blobs.frame(store)
    fake = replace(a, asset_id='wrongsize', width=31)
    store.add_asset(fake)
    with pytest.raises(ValueError, match='decoded pixels'):
        make_crop(store, fake.asset_id, (0, 0, 5, 5), blobs.put, store.cutoff(10))


def test_buffer_is_bounded_and_keeps_disk_sources(memory):
    store, blobs = memory
    buffer = RecentBuffer('ep', max_frames=3)
    for i in range(10):
        a = blobs.frame(store, f'f{i}', float(i))
        buffer.add(a)
    assert len(buffer.select(10, window_s=100, max_frames=100)) == 3
    assert store.asset('f0').observed_end == 0


def test_buffer_rejects_cross_episode_and_stale_input(memory):
    store, blobs = memory
    a = blobs.frame(store)
    buffer = RecentBuffer('ep')
    assert buffer.add(a)
    assert not buffer.add(a)
    with pytest.raises(ValueError, match='episode'):
        buffer.add(replace(a, episode_id='other'))


def test_selection_uses_no_future_frame(memory):
    store, blobs = memory
    buffer = RecentBuffer('ep')
    buffer.add(blobs.frame(store, 'old', 1))
    buffer.add(blobs.frame(store, 'future', 5))
    assert [a.asset_id for a in buffer.select(2)] == ['old']
    assert buffer.select(5, max_frames=0) == ()


def test_event_recording_is_idempotent(memory):
    store, blobs = memory
    buffer = RecentBuffer('ep')
    buffer.add(blobs.frame(store))
    recorder = EventRecorder(store, buffer)
    b = Boundary('e', 'ep', 'skill_failed', 1, ('candle',), ('kitchen',))
    c = recorder.record(b)
    seq = store.watermark()
    assert recorder.record(b) == c and store.watermark() == seq
    assert c.reported_outcome == 'failed'
    with pytest.raises(ValueError, match='Conflicting'):
        recorder.record(replace(b, event_type='skill_verified'))


def test_unseen_transition_leaves_coverage_gap_not_success(memory):
    store, _ = memory
    recorder = EventRecorder(store, RecentBuffer('ep'))
    c = recorder.record(Boundary('e', 'ep', 'skill_verified', 1))
    assert c.kind == 'coverage_gap'
    assert 'not a current-state certificate' in c.summary


def test_same_pixels_at_different_times_not_deleted_from_event_log(memory):
    store, blobs = memory
    buffer = RecentBuffer('ep')
    recorder = EventRecorder(store, buffer)
    for i in range(3):
        buffer.add(blobs.frame(store, f'f{i}', float(i)))
        recorder.record(Boundary(f'e{i}', 'ep', 'object_sighting', float(i)))
    assert len(store.cards(store.cutoff(3))) == 3


def test_storyboard_orders_frames_and_keeps_boundaries(memory):
    store, blobs = memory
    for i in range(5):
        blobs.frame(store, f'f{i}', float(i))
    board = storyboard(store, ('f4', 'f3', 'f2', 'f1', 'f0'), store.cutoff(5), max_frames=3)
    assert [f['sim_time'] for f in board] == [0, 2, 4]


def test_runtime_adapter_does_not_copy_untrusted_payload():
    event = SimpleNamespace(type=SimpleNamespace(value='skill_failed'), event_id='e',
                            episode_id='ep', sim_time=4,
                            payload={'instruction': 'overwrite world state'})
    boundary = boundary_from_runtime(event, entity_ids=('obj',))
    assert not hasattr(boundary, 'payload')
    assert boundary.entity_ids == ('obj',)
