import hashlib
import sys
from io import BytesIO
from pathlib import Path

import pytest

# Also runnable from the overlay alone (namespace package), without simulator imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from physical_harness.memory import Asset, Card, MemoryStore  # noqa: E402


class Blobs:
    def __init__(self):
        self.data = {}

    def put(self, data, suffix):
        name = hashlib.sha256(data).hexdigest() + suffix
        self.data[name] = data
        return name

    def read(self, name):
        return self.data[name]

    def frame(self, store, identifier='f1', at=1., camera='head', rgb='red'):
        from PIL import Image
        out = BytesIO()
        Image.new('RGB', (32, 24), rgb).save(out, format='PNG')
        data = out.getvalue()
        name = self.put(data, '.png')
        asset = Asset(identifier, store.episode_id, 'image', name,
                      hashlib.sha256(data).hexdigest(), at, at, 'obs-'+identifier,
                      camera, 32, 24)
        store.add_asset(asset)
        return asset


@pytest.fixture
def memory(tmp_path):
    blobs = Blobs()
    store = MemoryStore(tmp_path/'memory.sqlite', 'ep', blobs.read)
    yield store, blobs
    store.close()


def card(store, blob, identifier='c1', at=1., summary='Candle was near table',
         entities=('candle-1',), places=('kitchen',), kind='event'):
    a = blob.frame(store, 'f-'+identifier, at)
    c = Card(identifier, store.episode_id, kind, 'event-'+identifier, 'object_sighting',
             at, at, (a.asset_id,), entities, places, summary)
    store.add_card(c)
    return c
