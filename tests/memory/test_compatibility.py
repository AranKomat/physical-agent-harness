"""Run these on the merged checkout; standalone overlay skips the upstream import."""
import hashlib
import sqlite3
from io import BytesIO

import pytest

from physical_harness.memory import Asset, Card, MemoryStore, Retriever
from physical_harness.memory.media import make_crop


def test_existing_harness_evidence_store_contract(tmp_path):
    EvidenceStore = pytest.importorskip('physical_harness.evidence').EvidenceStore
    from PIL import Image
    blobs = EvidenceStore(tmp_path/'evidence')
    out = BytesIO()
    Image.new('RGB', (16, 16), 'red').save(out, format='PNG')
    data = out.getvalue()
    with MemoryStore(tmp_path/'episodic.sqlite', 'ep', blobs.read) as store:
        a = Asset('f1', 'ep', 'image', blobs.put(data, '.png'), hashlib.sha256(data).hexdigest(),
                  1, 1, 'obs1', 'head', 16, 16)
        store.add_asset(a)
        crop = make_crop(store, 'f1', (1, 1, 6, 6), blobs.put, store.cutoff(1))
        store.add_card(Card('c1', 'ep', 'entity_view', 'e1', 'object_crop', 1, 1,
                            (crop.asset_id, 'f1'), ('obj1',)))
        assert store.read_asset(crop.asset_id, store.cutoff(1))
        assert len(Retriever(store).search(store.cutoff(1), entity_id='obj1')) == 1


def test_accidentally_pointing_at_world_state_is_rejected(tmp_path):
    path = tmp_path/'world.sqlite'
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE beliefs(value TEXT)')
    db.commit()
    db.close()
    with pytest.raises(ValueError, match='separate memory database'):
        MemoryStore(path, 'ep', lambda _: b'')
    db = sqlite3.connect(path)
    assert db.execute("SELECT name FROM sqlite_master WHERE name='records'").fetchone() is None
    db.close()


def test_current_artifact_corruption_detected_again_before_model_input(memory):
    store, blobs = memory
    a = blobs.frame(store)
    blobs.data[a.uri] = b'changed-after-ingestion'
    with pytest.raises(ValueError, match='hash mismatch'):
        store.read_asset(a.asset_id, store.cutoff(1))
