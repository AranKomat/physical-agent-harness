"""Offline synthetic trace. Not a VLM benchmark, robot simulation, or task success.

Run from repository root:
    python examples/memory_replay.py --output /tmp/memory-demo-new
Requires Pillow only for creating/cropping these synthetic image fixtures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from physical_harness.memory import (  # noqa: E402
    Asset,
    AsyncAnnotator,
    Boundary,
    Card,
    Draft,
    EventRecorder,
    MemoryStore,
    PacketBudget,
    RecentBuffer,
    Retriever,
    attach_memory,
)
from physical_harness.memory.media import make_crop, storyboard  # noqa: E402


class DemoBlobs:
    """Synthetic fixture store, not a replacement for the harness EvidenceStore."""
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir()

    def put(self, data, suffix):
        name = hashlib.sha256(data).hexdigest() + suffix
        (self.root / name).write_bytes(data)
        return name

    def read(self, name):
        if Path(name).name != name:
            raise ValueError('Unsafe fixture name')
        return (self.root/name).read_bytes()


def run(output: Path) -> dict:
    from PIL import Image, ImageDraw
    output.mkdir(parents=True, exist_ok=False)
    blobs = DemoBlobs(output/'evidence')
    with MemoryStore(output/'memory.sqlite', 'synthetic-episode', blobs.read) as store:
        recent = RecentBuffer(store.episode_id)
        recorder = EventRecorder(store, recent)
        assets = []
        for i, stamp in enumerate([1., 4., 8., 12.]):
            image = Image.new('RGB', (200, 100), 'white')
            draw = ImageDraw.Draw(image)
            # Deliberately simple synthetic shapes, not alleged robot observations.
            draw.rectangle((20+i*12, 30, 35+i*12, 60), fill='red')
            draw.rectangle((130, 10, 185, 80), outline='black', width=2)
            data = BytesIO()
            image.save(data, format='PNG')
            content = data.getvalue()
            asset = Asset(f'frame-{i}', store.episode_id, 'image', blobs.put(content, '.png'),
                          hashlib.sha256(content).hexdigest(), stamp, stamp, f'obs-{i}',
                          'head', 200, 100)
            store.add_asset(asset)
            recent.add(asset)
            assets.append(asset)
            if i == 1:
                card = recorder.record(Boundary('boundary-1', store.episode_id,
                                               'object_sighting', stamp, ('candle-1',), ('room-A',)))
        before_annotation = store.cutoff(12.)
        crop = make_crop(store, assets[1].asset_id, (30, 25, 55, 65), blobs.put, before_annotation)
        store.add_card(Card('entity-view-1', store.episode_id, 'entity_view', 'crop-event',
                            'object_crop', 4., 4., (crop.asset_id, assets[1].asset_id),
                            ('candle-1',), ('room-A',), 'Synthetic red-rectangle appearance example.'))
        # Stub narrator exercises asynchronous storage, not image understanding.
        def captioner(packet):
            return Draft('Synthetic fixture: a red rectangle appears near an outlined box; '
                         'this does not establish a placement.', (packet['assets'][-1]['asset_id'],))
        worker = AsyncAnnotator(store, captioner, model='deterministic-test-double', max_calls=1).start()
        status = worker.submit(card.card_id, store.cutoff(12.))
        if not worker.flush(5) or not worker.close(5):
            raise RuntimeError('Test worker did not finish')
        final = store.cutoff(12.)
        retriever = Retriever(store)
        packet = retriever.packet(retriever.search(final, entity_id='candle-1'), final,
                                  PacketBudget(max_images=3, max_bytes=6000))
        context = attach_memory({'episode': store.episode_id, 'goal': 'Inspect historical evidence',
                                 'images': [], 'task_ledger': []}, packet)
        report = {
            'kind': 'synthetic-memory-contract-demo', 'robot_actions': 0, 'model_calls': 0,
            'paid_api_calls': 0, 'writer_queue_status': status,
            'old_cutoff_sees_later_annotation': store.annotation(card.card_id, before_annotation) is not None,
            'new_cutoff_sees_annotation': store.annotation(card.card_id, final) is not None,
            'memory_cards': len(store.cards(final)), 'job_results': store.job_results(),
            'storyboard': storyboard(store, tuple(a.asset_id for a in assets), final, 3),
            'context': context,
        }
        (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps({k: v for k, v in report.items() if k not in {'context', 'storyboard'}}, indent=2))
