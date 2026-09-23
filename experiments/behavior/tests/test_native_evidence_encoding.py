import hashlib
import io

import numpy as np
import pytest
from PIL import Image

from experiments.behavior.contracts import Stamp
from experiments.behavior.observations import EvidenceStore


@pytest.mark.parametrize("level", [0, 1, 6, 9])
def test_lossless_encoding_and_original_png_delivery(tmp_path, level):
    store = EvidenceStore(tmp_path, png_compress_level=level)
    pixels = np.random.default_rng(3).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    stamp = Stamp(session="test", epoch=0, sequence=0)
    ref = store.put(pixels, "rgb", stamp, 1.)
    payload = store.png(ref)
    assert payload == (tmp_path / ref.uri).read_bytes()
    assert np.array_equal(store.read(ref), pixels)
    assert np.array_equal(np.asarray(Image.open(io.BytesIO(payload))), pixels)
    assert ref.observed_at == 1. and ref.stamp == stamp
    assert hashlib.sha256(payload).hexdigest() == ref.uri.removesuffix(".png")


@pytest.mark.parametrize("value", [-1, 10, True, 1.5, "1"])
def test_invalid_compression_rejected(tmp_path, value):
    with pytest.raises(ValueError):
        EvidenceStore(tmp_path, png_compress_level=value)


def test_png_still_checks_integrity_and_modality(tmp_path):
    store = EvidenceStore(tmp_path)
    stamp = Stamp(session="test", epoch=0, sequence=0)
    ref = store.put(np.zeros((4, 4, 3), dtype=np.uint8), "rgb", stamp, 0.)
    (tmp_path / ref.uri).write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="hash"):
        store.png(ref)
    depth = store.put(np.ones((4, 4)), "depth", stamp, 0.)
    with pytest.raises(ValueError, match="RGB"):
        store.png(depth)
    with pytest.raises(ValueError, match="escapes"):
        store.png(ref.model_copy(update={"uri": "../escape.png"}))


def test_default_encoding_remains_pillow_default(tmp_path):
    pixels = np.random.default_rng(4).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    expected = io.BytesIO()
    Image.fromarray(pixels).save(expected, format="PNG")
    store = EvidenceStore(tmp_path)
    ref = store.put(pixels, "rgb", Stamp(session="test", epoch=0, sequence=0), 0.)
    assert store.png(ref) == expected.getvalue()
