import copy
import time
from dataclasses import replace
from threading import Event
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from physical_harness.perception.contracts import ValueHints, validate_box
from physical_harness.perception.discovery import (
    AsyncDiscovery,
    ExistingModelDiscovery,
    model_packet,
    parse_response,
    response_schema,
)
from tests.reasoning.embodied.conftest import make_frame, make_request, response


@pytest.mark.parametrize('box', [(-0.1, 0, 1, 1), (0, 0, 0, 1), (0, 1, 1, 0), (0, 0, 2, 1), (0, 0, float('nan'), 1), (False, 0, 1, 1), [0, 0, 1, 1]])
def test_invalid_coarse_boxes(box):
    with pytest.raises(ValueError):
        validate_box(box)

def test_frame_hash_and_current_lineage():
    f, data = make_frame()
    f.verify_bytes(data)
    with pytest.raises(PermissionError):
        f.verify_bytes(data + b'!')
    with pytest.raises(PermissionError):
        f.available(replace(f.basis, episode='other'), now=100)
    with pytest.raises(PermissionError):
        f.available(f.basis, now=99)

@pytest.mark.parametrize('field,value', [('width', 0), ('height', False), ('content_sha256', 'x'), ('parent_id', 'image-head-0'), ('available_wall', 99)])
def test_bad_frame_metadata(field, value):
    f, _ = make_frame()
    with pytest.raises(ValueError):
        replace(f, **{field: value})

def test_request_and_response_contract():
    r = make_request()
    raw = response(r)
    Draft202012Validator(response_schema(r)).validate(raw)
    out = parse_response(raw, r, model='configured-glm', completed_wall=104.0)
    assert out.updates[0].hypotheses == ('radio', 'speaker')
    assert out.attention[0].local_id == 'new-0'
    assert 'actions' not in model_packet(r)
    assert model_packet(r)['episode'] == 'ep'

@pytest.mark.parametrize('mutation', ['extra', 'request', 'fingerprint', 'many', 'duplicate', 'frame', 'region', 'box_and_region', 'known', 'attention', 'nan', 'action', 'missing_value', 'status', 'missing_box'])
def test_invalid_semantic_replies_are_rejected_atomically(mutation):
    r = make_request()
    raw = response(r)
    if mutation == 'extra':
        raw['xyz'] = [1, 2, 3]
    elif mutation == 'request':
        raw['request_id'] = 'other'
    elif mutation == 'fingerprint':
        raw['request_fingerprint'] = 'other'
    elif mutation == 'many':
        raw = response(r, count=5)
    elif mutation == 'duplicate':
        raw['updates'].append(copy.deepcopy(raw['updates'][0]))
    elif mutation == 'frame':
        raw['updates'][0]['frame_id'] = 'future'
    elif mutation == 'region':
        raw['updates'][0]['region_id'] = 'missing'
    elif mutation == 'box_and_region':
        raw['updates'][0]['box'] = [0, 0, 1, 1]
    elif mutation == 'known':
        raw['updates'][0]['known_id'] = 'made-up-identity'
    elif mutation == 'attention':
        raw['attention'][0]['local_id'] = 'missing'
    elif mutation == 'nan':
        raw['updates'][0]['value']['task'] = float('nan')
    elif mutation == 'action':
        raw['local_action'] = 'approach radio'
    elif mutation == 'missing_value':
        del raw['updates'][0]['value']['task']
    elif mutation == 'status':
        raw['updates'][0]['status'] = 'certain'
    else:
        raw['updates'][0]['region_id'] = None
    with pytest.raises((ValueError, PermissionError)):
        parse_response(raw, r, model='configured', completed_wall=104)

def test_coarse_box_without_a_sam_detection_is_valid():
    r = replace(make_request(), regions=())
    raw = response(r)
    raw['updates'][0].update(region_id=None, box=[0.2, 0.1, 0.4, 0.4])
    out = parse_response(raw, r, model='m', completed_wall=105)
    assert out.updates[0].region_id is None
    assert out.updates[0].box == (0.2, 0.1, 0.4, 0.4)

@pytest.mark.parametrize('value', [-1, 4, 0.5, True, float('inf')])
def test_value_hints_are_ordinal_not_probabilities(value):
    with pytest.raises(ValueError):
        ValueHints(task=value)

def wait_completions(worker, n=1):
    end = time.monotonic() + 2
    values = []
    while len(values) < n and time.monotonic() < end:
        values.extend(worker.poll())
        time.sleep(0.005)
    return values

def test_actual_async_worker_does_not_write_inventory(journal):
    started, release = (Event(), Event())

    def call(r, d):
        started.set()
        release.wait(1)
        return response(r)
    w = AsyncDiscovery(journal=journal, invoke=call, model_name='test', enabled=True, clock=lambda: 104.0)
    r = make_request()
    assert w.submit(r)
    assert started.wait(1)
    assert journal.records('embodied_inventory') == []
    with pytest.raises(PermissionError):
        w.submit(r)
    release.set()
    done = wait_completions(w)
    assert len(done) == 1 and done[0].result
    assert w.close()
    assert len(journal.records(w.KIND)) == 2
    w2 = AsyncDiscovery(journal=journal, invoke=call, model_name='test', enabled=True, clock=lambda: 104.0)
    with pytest.raises(PermissionError):
        w2.submit(r)
    w2.close()

def test_pending_latest_is_coalesced_without_retry(journal):
    start, release = (Event(), Event())
    called = []

    def call(r, d):
        called.append(r.id)
        if len(called) == 1:
            start.set()
            release.wait(1)
        return response(r)
    w = AsyncDiscovery(journal=journal, invoke=call, model_name='test', enabled=True, clock=lambda: 104.0)
    w.submit(make_request('a'))
    assert start.wait(1)
    w.submit(make_request('b'))
    w.submit(make_request('c'))
    release.set()
    done = wait_completions(w, 2)
    assert called == ['a', 'c']
    assert len(done) == 2
    assert any((r['event'] == 'superseded' and r['request_id'] == 'b' for r in journal.records(w.KIND)))
    w.close()

def test_late_reply_is_not_published_as_semantic_result(journal):
    t = [104.0]

    def call(r, d):
        t[0] = 130.0
        return response(r)
    w = AsyncDiscovery(journal=journal, invoke=call, model_name='m', enabled=True, clock=lambda: t[0])
    w.submit(make_request())
    done = wait_completions(w)
    assert done[0].result is None and done[0].error_type == 'TimeoutError'
    w.close()

def test_close_does_not_claim_to_kill_hung_transport(journal):
    started, release = (Event(), Event())

    def call(r, d):
        started.set()
        release.wait(2)
        return response(r)
    w = AsyncDiscovery(journal=journal, invoke=call, model_name='m', enabled=True, clock=lambda: 104.0)
    w.submit(make_request())
    assert started.wait(1)
    assert w.close(0.001) is False
    with pytest.raises(PermissionError):
        w.submit(make_request('b'))
    release.set()
    assert w.close(1)

def test_disabled_worker_is_inert(journal):
    w = AsyncDiscovery(journal=journal, invoke=lambda *a: None, model_name='m')
    with pytest.raises(PermissionError):
        w.submit(make_request())
    assert w.thread is None and journal.records(w.KIND) == []
    assert w.close()

def test_existing_model_bridge_reuses_guarded_transport():
    now = time.monotonic()
    r = make_request(wall=now)
    f, raw = make_frame(basis=r.current)
    r = replace(r, frames=(f,))
    called = []

    class Model:
        name = 'configured-model'

        def call(self, *args):
            called.append(args)
            return response(r)
    im = SimpleNamespace(id=f.asset_id, episode='ep', width=f.width, height=f.height, data=raw)
    adapter = ExistingModelDiscovery(Model(), lambda frame: im)
    result = adapter(r, now + 20)
    assert result['request_id'] == r.id
    assert called[0][1] == 'semantic_discovery'
    im.data = b'bad'
    with pytest.raises(PermissionError):
        adapter(r, now + 20)
