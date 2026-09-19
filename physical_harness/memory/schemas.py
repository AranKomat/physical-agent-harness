"""Strict immutable memory contracts. Memory is historical evidence, never control state."""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = 1
KINDS = frozenset({'event', 'entity_view', 'place_view', 'motion', 'coverage_gap'})
MEDIA_KINDS = frozenset({'image', 'crop', 'clip', 'telemetry'})
OUTCOMES = frozenset({'not_assessed', 'execution_reported_complete', 'verifier_reported_supported',
                      'failed', 'uncertain', 'cancelled'})


def encoded(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def text(value: str, limit: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > limit:
        raise ValueError('Nonempty bounded text required')
    return value


def finite(value: float, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Number required')
    if not math.isfinite(value) or value < minimum:
        raise ValueError('Finite nonnegative number required')
    return float(value)


def integer(value: int, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError('Bounded integer required')
    return value


def ids(value: tuple[str, ...], limit: int = 64) -> tuple[str, ...]:
    if not isinstance(value, tuple) or len(value) > limit or len(set(value)) != len(value):
        raise ValueError('Unique bounded tuple of IDs required')
    for item in value:
        text(item)
    return value


@dataclass(frozen=True)
class Cutoff:
    """Two axes: sensor/simulation time AND knowledge-commit watermark.

    Save this at each decision. Reusing only simulation time in an offline replay
    can leak an annotation that completed later while simulation was paused.
    """
    episode_id: str
    observed_through: float
    knowledge_seq: int

    def __post_init__(self):
        text(self.episode_id)
        finite(self.observed_through)
        integer(self.knowledge_seq)


@dataclass(frozen=True)
class Asset:
    asset_id: str
    episode_id: str
    kind: str
    uri: str                     # local content-addressed filename, not arbitrary URL
    sha256: str
    observed_start: float
    observed_end: float
    observation_id: str
    camera: str = ''
    width: int = 0
    height: int = 0
    parent_id: str = ''
    crop_box: tuple[int, int, int, int] | tuple[()] = ()

    def __post_init__(self):
        for value in (self.asset_id, self.episode_id, self.observation_id):
            text(value)
        if self.kind not in MEDIA_KINDS:
            raise ValueError('Unknown media kind')
        if not re.fullmatch(r'[0-9a-f]{64}', self.sha256):
            raise ValueError('SHA256 required')
        if not re.fullmatch(r'[0-9a-f]{64}\.(png|jpg|mp4|json|npy|txt)', self.uri):
            raise ValueError('Only local hash-named artifact references accepted')
        if self.uri.split('.')[0] != self.sha256:
            raise ValueError('Hash/reference mismatch')
        finite(self.observed_start)
        finite(self.observed_end)
        if self.observed_end < self.observed_start:
            raise ValueError('Reversed observation interval')
        integer(self.width)
        integer(self.height)
        if self.kind in {'image', 'crop'}:
            text(self.camera)
            if not self.width or not self.height or self.width * self.height > 40_000_000:
                raise ValueError('Image geometry outside bounds')
            if self.observed_start != self.observed_end:
                raise ValueError('Image must have one capture time')
        if self.kind == 'crop':
            text(self.parent_id)
            if (not isinstance(self.crop_box, tuple) or len(self.crop_box) != 4
                    or any(type(x) is not int or x < 0 for x in self.crop_box)):
                raise ValueError('Integer pixel crop box required')
            x0, y0, x1, y1 = self.crop_box
            if x1 <= x0 or y1 <= y0 or (x1-x0, y1-y0) != (self.width, self.height):
                raise ValueError('Crop box and dimensions disagree')
        elif self.crop_box or self.parent_id:
            raise ValueError('Only crops carry parent/box in this version')


@dataclass(frozen=True)
class Card:
    card_id: str
    episode_id: str
    kind: str
    source_event_id: str
    event_type: str
    observed_start: float
    observed_end: float
    asset_ids: tuple[str, ...]
    entity_ids: tuple[str, ...] = ()
    place_ids: tuple[str, ...] = ()
    summary: str = 'Recorded event; outcome not assessed.'
    reported_outcome: str = 'not_assessed'

    def __post_init__(self):
        for value in (self.card_id, self.episode_id, self.source_event_id, self.event_type):
            text(value)
        if self.kind not in KINDS or self.reported_outcome not in OUTCOMES:
            raise ValueError('Unknown card kind/outcome')
        finite(self.observed_start)
        finite(self.observed_end)
        if self.observed_end < self.observed_start:
            raise ValueError('Reversed event interval')
        for value in (self.asset_ids, self.entity_ids, self.place_ids):
            ids(value)
        if not self.asset_ids and self.kind != 'coverage_gap':
            raise ValueError('Memory cards need source evidence')
        text(self.summary, 2400)


@dataclass(frozen=True)
class Draft:
    """A writer may produce narration and citations, not actions/facts/verdicts."""
    text: str
    cited_asset_ids: tuple[str, ...]
    input_tokens: int | None = None
    output_tokens: int | None = None

    def __post_init__(self):
        text(self.text, 2400)
        ids(self.cited_asset_ids, 16)
        if not self.cited_asset_ids:
            raise ValueError('Narration must cite source assets')
        for value in (self.input_tokens, self.output_tokens):
            if value is not None:
                integer(value)


@dataclass(frozen=True)
class PacketBudget:
    max_cards: int = 5
    max_images: int = 3           # memory images, not live images
    max_pixels: int = 1_500_000   # geometry bound, NOT an API-token estimate
    max_bytes: int = 7000        # JSON metadata/text only

    def __post_init__(self):
        for value in (self.max_cards, self.max_images, self.max_pixels, self.max_bytes):
            integer(value)


def payload(value: Any) -> dict:
    return asdict(value)


def from_payload(cls, value: dict):
    value = dict(value)
    for key in ('asset_ids', 'entity_ids', 'place_ids', 'crop_box', 'cited_asset_ids'):
        if key in value:
            value[key] = tuple(value[key])
    return cls(**value)


def stable_id(prefix: str, value: Any) -> str:
    return prefix + ':' + hashlib.sha256(encoded(value)).hexdigest()[:32]
