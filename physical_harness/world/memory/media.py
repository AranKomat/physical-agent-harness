"""Source-preserving crops and storyboard descriptors. Pillow is optional."""
from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Callable

from physical_harness.world.memory.schemas import Asset, Cutoff, stable_id
from physical_harness.world.memory.store import MemoryStore


def make_crop(store: MemoryStore, parent_id: str, box: tuple[int, int, int, int],
              put_blob: Callable[[bytes, str], str], cutoff: Cutoff) -> Asset:
    """Create pixels, retain parent, camera, bbox and original capture time.

    A crop is appearance evidence. The caller must retrieve the parent scene for
    containment, clearance, scale, or collision reasoning.
    """
    from PIL import Image

    parent = store.asset(parent_id, cutoff)
    if parent.kind != 'image' or len(box) != 4 or any(type(x) is not int for x in box):
        raise ValueError('Original image and integer pixel box required')
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= parent.width and 0 <= y0 < y1 <= parent.height):
        raise ValueError('Crop outside original image')
    data = store.read_blob(parent.uri)
    if hashlib.sha256(data).hexdigest() != parent.sha256:
        raise ValueError('Parent artifact was modified')
    with Image.open(BytesIO(data)) as image:
        if image.size != (parent.width, parent.height) or image.format not in {'PNG', 'JPEG'}:
            raise ValueError('Image metadata does not match decoded pixels')
        image.load()
        crop = image.convert('RGB').crop(box)
        out = BytesIO()
        crop.save(out, format='PNG')
    body = out.getvalue()
    digest = hashlib.sha256(body).hexdigest()
    asset = Asset(
        stable_id('crop', [parent.asset_id, box]), parent.episode_id, 'crop',
        put_blob(body, '.png'), digest, parent.observed_start, parent.observed_end,
        parent.observation_id, parent.camera, x1-x0, y1-y0, parent.asset_id, box,
    )
    store.add_asset(asset)
    return asset


def storyboard(store: MemoryStore, asset_ids: tuple[str, ...], cutoff: Cutoff,
               max_frames: int = 8) -> list[dict]:
    """Ordered frame handles, not an invented continuous action video.

    Spacing stays explicit. A receiving VLM adapter must preserve order and time.
    Raw-video slicing/encoding is intentionally not performed by this function.
    """
    if type(max_frames) is not int or max_frames < 1:
        raise ValueError('Positive frame limit required')
    assets = sorted((store.asset(i, cutoff) for i in dict.fromkeys(asset_ids)),
                    key=lambda a: (a.observed_end, a.camera, a.asset_id))
    assets = [a for a in assets if a.kind in {'image', 'crop'}]
    if len(assets) > max_frames:
        if max_frames == 1:
            assets = [assets[-1]]
        else:
            indexes = [round(i*(len(assets)-1)/(max_frames-1)) for i in range(max_frames)]
            assets = [assets[i] for i in indexes]
    return [{'asset_id': a.asset_id, 'uri': a.uri, 'sim_time': a.observed_end,
             'camera': a.camera, 'parent_id': a.parent_id, 'crop_box': list(a.crop_box),
             'width': a.width, 'height': a.height} for a in assets]
