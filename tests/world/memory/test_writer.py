import threading

import pytest

from physical_harness.world.memory import AsyncAnnotator, Draft, parse_draft
from tests.world.memory.conftest import card


def test_writer_really_runs_off_caller_thread(memory):
    store, blobs = memory
    c = card(store, blobs)
    entered, release = threading.Event(), threading.Event()
    threads = []
    def caption(packet):
        threads.append(threading.get_ident())
        entered.set()
        assert release.wait(3)
        return Draft('Historical sighting', c.asset_ids)
    worker = AsyncAnnotator(store, caption, model='fixture').start()
    try:
        basis = store.cutoff(2)
        assert worker.submit(c.card_id, basis) == 'queued'
        assert entered.wait(2)
        assert not worker.flush(0)
        assert store.annotation(c.card_id, store.cutoff(2)) is None
        release.set()
        assert worker.flush(3)
        assert threads[0] != threading.get_ident()
        assert store.annotation(c.card_id, basis) is None
        assert store.annotation(c.card_id, store.cutoff(2))
    finally:
        release.set()
        assert worker.close(3)


def test_budget_and_duplicate_jobs(memory):
    store, blobs = memory
    c1, c2 = card(store, blobs, 'a'), card(store, blobs, 'b')
    worker = AsyncAnnotator(store, lambda p: Draft('Text', tuple(p['card']['asset_ids'])),
                            model='fixture', max_calls=1).start()
    try:
        cut = store.cutoff(3)
        assert worker.submit(c1.card_id, cut) == 'queued'
        assert worker.submit(c1.card_id, cut) == 'duplicate'
        assert worker.submit(c2.card_id, cut) == 'budget_exhausted'
        assert worker.flush(3)
    finally:
        assert worker.close(3)


def test_failed_writer_does_not_destroy_source_card(memory):
    store, blobs = memory
    c = card(store, blobs)
    def bad(_):
        raise RuntimeError('secret-provider-key-must-not-be-logged')
    worker = AsyncAnnotator(store, bad, model='fixture').start()
    try:
        worker.submit(c.card_id, store.cutoff(2))
        assert worker.flush(3)
        assert store.card(c.card_id) == c
        assert store.annotation(c.card_id, store.cutoff(2)) is None
        results = store.job_results()
        assert results[0]['status'] == 'failed'
        assert 'secret' not in str(results)
    finally:
        assert worker.close(3)


def test_writer_cannot_promote_a_claim(memory):
    store, blobs = memory
    c = card(store, blobs)
    worker = AsyncAnnotator(store, lambda _: {'text': 'Success', 'verified': True}, model='fixture').start()
    try:
        worker.submit(c.card_id, store.cutoff(2))
        assert worker.flush(3)
        assert store.annotation(c.card_id, store.cutoff(2)) is None
        assert store.job_results()[0]['status'] == 'failed'
    finally:
        assert worker.close(3)


def test_fake_citations_fail_closed(memory):
    store, blobs = memory
    c = card(store, blobs)
    worker = AsyncAnnotator(store, lambda _: Draft('Wrong', ('fake',)), model='fixture').start()
    try:
        worker.submit(c.card_id, store.cutoff(2))
        assert worker.flush(3)
        assert store.job_results()[0]['status'] == 'failed'
    finally:
        assert worker.close(3)


def test_backpressure_is_visible_and_cards_survive(memory):
    store, blobs = memory
    cards = [card(store, blobs, str(i)) for i in range(3)]
    entered, release = threading.Event(), threading.Event()
    def blocked(packet):
        entered.set()
        assert release.wait(3)
        return Draft('Text', tuple(packet['card']['asset_ids']))
    worker = AsyncAnnotator(store, blocked, model='fixture', queue_size=1).start()
    try:
        cut = store.cutoff(2)
        assert worker.submit(cards[0].card_id, cut) == 'queued'
        assert entered.wait(2)
        assert worker.submit(cards[1].card_id, cut) == 'queued'
        assert worker.submit(cards[2].card_id, cut) == 'queue_full'
        assert len(store.cards(store.cutoff(2))) == 3
        assert any(r['status'] == 'queue_full' for r in store.job_results())
    finally:
        release.set()
        assert worker.flush(3)
        assert worker.close(3)


def test_close_reports_uncancellable_inflight_call(memory):
    store, blobs = memory
    c = card(store, blobs)
    entered, release = threading.Event(), threading.Event()
    def wait(_):
        entered.set()
        assert release.wait(3)
        return Draft('Text', c.asset_ids)
    worker = AsyncAnnotator(store, wait, model='fixture').start()
    worker.submit(c.card_id, store.cutoff(2))
    assert entered.wait(2)
    assert worker.close(0) is False
    release.set()
    assert worker.close(3) is True
    with pytest.raises(RuntimeError):
        worker.submit(c.card_id, store.cutoff(2))


@pytest.mark.parametrize('extra', ['verified', 'world_update', 'action', 'confidence'])
def test_narration_parser_rejects_authority_fields(extra):
    with pytest.raises(ValueError):
        parse_draft({'text': 'Text', 'cited_asset_ids': ['f'], extra: True})


def test_narration_parser():
    result = parse_draft({'text': 'Uncertain historical sighting.', 'cited_asset_ids': ['f']})
    assert result.text.startswith('Uncertain')
