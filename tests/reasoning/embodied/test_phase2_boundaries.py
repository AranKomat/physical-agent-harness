from dataclasses import replace

import pytest

from physical_harness.perception.contracts import FrameRef, RegionRef
from physical_harness.perception.discovery import AsyncDiscovery, Completion, parse_response
from physical_harness.perception.discovery_coordinator import DiscoveryCoordinator
from physical_harness.perception.regions import BoxSeed, require_current_tracking
from physical_harness.reasoning.executive import ExecutiveCadence
from physical_harness.world.inventory import SemanticInventory
from tests.reasoning.embodied.conftest import make_basis, make_frame, make_request, response


def test_discovery_request_rejects_region_track_camera_mismatch():
    request = make_request()
    frame = request.frames[0]
    region = RegionRef('region-a', frame.asset_id, (.1, .1, .8, .8),
                       ('left_wrist', 'session', '0'))
    with pytest.raises(PermissionError, match='camera'):
        replace(request, regions=(region,))


@pytest.mark.parametrize('camera', ['head', 'left_wrist'])
def test_discovery_request_accepts_source_matched_scoped_track(camera):
    frame, _ = make_frame(camera=camera)
    request = make_request(frames=(frame,))
    region = RegionRef('region-a', frame.asset_id, (.1, .1, .8, .8),
                       (camera, 'session', '0'))
    assert replace(request, regions=(region,)).regions == (region,)


def test_tracking_callback_validates_explicit_proposed_session():
    frame, raw = make_frame()
    frame.verify_bytes(raw)
    seed = BoxSeed('sighting', frame, (.1, .1, .8, .8), ('radio',))
    basis = frame.basis
    receipt = {'seed': seed, 'basis': basis, 'mask': 'mask-evidence', 'session': 'session-1'}
    seen = []

    def check(actual_seed, mask_basis, evidence, *, session_id):
        seen.append(session_id)
        return (actual_seed == receipt['seed'] and mask_basis == receipt['basis']
                and evidence == receipt['mask'] and session_id == receipt['session'])

    kwargs = dict(source_hash=frame.content_sha256, mask_basis=basis,
                  mask_evidence=receipt['mask'], association_check=check)
    result = require_current_tracking(seed, basis, session_id='session-1', **kwargs)
    assert result['session'] == 'session-1' and result['motion_authority'] is False
    with pytest.raises(PermissionError, match='uniquely associated'):
        require_current_tracking(seed, basis, session_id='session-2', **kwargs)
    assert seen == ['session-1', 'session-2']


def test_tracking_does_not_fall_back_to_legacy_callback():
    frame, _ = make_frame()
    seed = BoxSeed('sighting', frame, (.1, .1, .8, .8), ('radio',))

    def legacy(seed, basis, evidence):
        return True

    with pytest.raises(TypeError, match='session_id'):
        require_current_tracking(seed, frame.basis, source_hash=frame.content_sha256,
                                 session_id='unverified', mask_basis=frame.basis,
                                 mask_evidence='mask', association_check=legacy)


def delivery(journal, request):
    result = parse_response(response(request), request, model='fixture',
                            completed_wall=request.submitted_wall + .25)
    worker = AsyncDiscovery(journal=journal, invoke=None, model_name='fixture', enabled=False)
    worker.completed.append(Completion(request.id, result, None, result.completed_wall))
    inventory = SemanticInventory(journal)
    cadence = ExecutiveCadence()
    coord = DiscoveryCoordinator(journal=journal, keyframes=None, worker=worker,
                                 inventory=inventory, executive_scheduler=cadence)
    return coord, inventory, cadence


@pytest.mark.parametrize('changes', [
    {'robot_fingerprint': 'other-robot'}, {'domain': 'behavior_sim'},
    {'episode': 'other-episode'}, {'captured_wall': 102.},
])
def test_discovery_rejects_incompatible_consumer_before_writes(journal, changes):
    request = make_request()
    coord, inventory, cadence = delivery(journal, request)
    with pytest.raises(PermissionError):
        coord.poll(current=replace(request.current, **changes), now=101., task_revision='task-v1')
    assert not inventory.records and not inventory.completed
    assert not journal.records(inventory.KIND)
    assert not cadence.pending


def test_all_discovery_frames_checked_before_writes_and_cross_camera_allowed(journal, monkeypatch):
    historical, _ = make_frame(0)
    current_frame, _ = make_frame(1, camera='left_wrist')
    request = make_request(frames=(historical, current_frame))
    coord, inventory, cadence = delivery(journal, request)
    checked = []
    original = FrameRef.available

    def available(frame, current, now):
        assert not inventory.records and not cadence.pending
        checked.append(frame.asset_id)
        return original(frame, current, now)

    monkeypatch.setattr(FrameRef, 'available', available)
    # A later consumer may use another local frame; discovery stays historical.
    current = make_basis(2, sim=2., wall=102., frame_epoch='relocalized')
    result = coord.poll(current=current, now=102.25, task_revision='task-v1')
    assert checked == [historical.asset_id, current_frame.asset_id]
    assert len(result) == 1 and result[0]['historical_only']
    assert len(inventory.records) == 1 and len(cadence.pending) == 1
