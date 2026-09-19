import hashlib
from dataclasses import replace

import pytest

from physical_harness.memory import Asset, Card, Cutoff, Draft, MemoryStore

from .conftest import card


def test_store_reopens_and_is_episode_isolated(tmp_path):
    db = tmp_path/'m.sqlite'
    with MemoryStore(db, 'ep', lambda _: b'') as store:
        watermark = store.watermark()
    with MemoryStore(db, 'ep', lambda _: b'') as store:
        assert store.watermark() == watermark
    with pytest.raises(ValueError, match='another episode'):
        MemoryStore(db, 'different', lambda _: b'')


def test_asset_idempotent_and_cannot_be_reused(memory):
    store, blobs = memory
    a = blobs.frame(store)
    watermark = store.watermark()
    assert store.add_asset(a) == watermark
    assert store.watermark() == watermark
    with pytest.raises(ValueError, match='immutable'):
        store.add_asset(replace(a, camera='wrist'))


def test_corrupted_source_rejected(memory):
    store, blobs = memory
    a = blobs.frame(store)
    blobs.data[a.uri] = b'bad'
    with pytest.raises(ValueError, match='hash mismatch'):
        store.add_asset(a)


def test_card_must_have_evidence(memory):
    store, _ = memory
    with pytest.raises(ValueError, match='source evidence'):
        Card('c', 'ep', 'event', 'e', 'x', 0, 0, ())
    gap = Card('gap', 'ep', 'coverage_gap', 'e', 'x', 0, 0, ())
    store.add_card(gap)
    assert len(store.cards(store.cutoff(0))) == 1


def test_card_rejects_unknown_sources(memory):
    store, _ = memory
    with pytest.raises(ValueError, match='Unknown source'):
        store.add_card(Card('c', 'ep', 'event', 'e', 'x', 0, 1, ('missing',)))


def test_card_rejects_future_frames(memory):
    store, blobs = memory
    a = blobs.frame(store, at=10)
    with pytest.raises(ValueError, match='outside event interval'):
        store.add_card(Card('c', 'ep', 'event', 'e', 'x', 0, 5, (a.asset_id,)))


def test_foreign_card_and_asset_rejected(memory):
    store, blobs = memory
    a = blobs.frame(store)
    with pytest.raises(ValueError, match='Foreign episode'):
        store.add_asset(replace(a, episode_id='other'))
    with pytest.raises(ValueError, match='Foreign episode'):
        store.add_card(Card('c', 'other', 'event', 'e', 'x', 1, 1, (a.asset_id,)))


def test_future_observation_invisible_even_if_already_imported(memory):
    store, blobs = memory
    card(store, blobs, 'old', at=1)
    card(store, blobs, 'future', at=10)
    cut = store.cutoff(5)
    assert [c.card_id for c in store.cards(cut)] == ['old']
    with pytest.raises(ValueError, match='unavailable'):
        store.card('future', cut)
    with pytest.raises(ValueError, match='unavailable'):
        store.asset('f-future', cut)


def test_late_card_unavailable_at_old_knowledge_watermark(memory):
    store, blobs = memory
    cut = store.cutoff(10)
    c = card(store, blobs, at=1)
    assert store.cards(cut) == []
    with pytest.raises(ValueError, match='unavailable'):
        store.card(c.card_id, cut)


def test_late_narration_cannot_leak_into_replayed_decision(memory):
    store, blobs = memory
    c = card(store, blobs)
    basis = store.cutoff(5)
    store.add_annotation(c.card_id, Draft('Candle near table', c.asset_ids),
                         model='test', prompt_id='v1', basis=basis, wall_seconds=1)
    assert store.annotation(c.card_id, basis) is None
    assert store.annotation(c.card_id, store.cutoff(5))['authority'] == 'untrusted_narration'


def test_writer_cannot_cite_unseen_or_foreign_evidence(memory):
    store, blobs = memory
    c = card(store, blobs)
    future = blobs.frame(store, 'future', 9)
    with pytest.raises(ValueError, match='not in its input'):
        store.add_annotation(c.card_id, Draft('Wrong', (future.asset_id,)), model='test',
                             prompt_id='v1', basis=store.cutoff(10), wall_seconds=1)


def test_card_does_not_silently_change(memory):
    store, blobs = memory
    c = card(store, blobs)
    assert store.add_card(c) == store.watermark()
    with pytest.raises(ValueError, match='immutable'):
        store.add_card(replace(c, summary='Overwritten'))


def test_clip_cannot_be_retrieved_before_its_end(memory):
    store, blobs = memory
    data = b'synthetic-clip-container-not-a-real-mp4'
    name = blobs.put(data, '.mp4')
    a = Asset('clip', 'ep', 'clip', name, hashlib.sha256(data).hexdigest(), 0, 20, 'recording')
    store.add_asset(a)
    store.add_card(Card('motion', 'ep', 'motion', 'e', 'x', 0, 20, ('clip',)))
    assert store.cards(store.cutoff(10)) == []
    assert len(store.cards(store.cutoff(20))) == 1


def test_single_image_is_not_a_motion(memory):
    store, blobs = memory
    a = blobs.frame(store)
    with pytest.raises(ValueError, match='Motion needs'):
        store.add_card(Card('c', 'ep', 'motion', 'e', 'x', 1, 1, (a.asset_id,)))


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, True])
def test_invalid_time(value):
    with pytest.raises(ValueError):
        Cutoff('ep', value, 0)


def test_invalid_watermark(memory):
    store, _ = memory
    with pytest.raises(ValueError, match='watermark'):
        store.cards(Cutoff('ep', 1, 100))
    with pytest.raises(ValueError, match='Foreign'):
        store.cards(Cutoff('other', 1, 0))


def test_reference_scan_fails_explicitly_instead_of_truncating(memory):
    store, blobs = memory
    card(store, blobs, 'a')
    card(store, blobs, 'b')
    with pytest.raises(ValueError, match='scan budget'):
        store.cards(store.cutoff(1), max_scan=1)


def test_schema_version_is_not_silently_reinterpreted(tmp_path):
    import sqlite3
    db = tmp_path/'memory.sqlite'
    with MemoryStore(db, 'ep', lambda _: b''):
        pass
    connection = sqlite3.connect(db)
    connection.execute("UPDATE meta SET value='999' WHERE key='schema'")
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match='schema'):
        MemoryStore(db, 'ep', lambda _: b'')
