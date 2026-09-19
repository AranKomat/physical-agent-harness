"""Bounded media references and event-boundary recording; no captioning in callbacks."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .schemas import Asset, Card, finite, integer, stable_id, text
from .store import MemoryStore

BOUNDARIES = frozenset({'skill_verified', 'skill_failed', 'skill_stalled', 'target_lost',
                        'state_contradiction', 'arrived', 'door_blocked', 'world_changed',
                        'execution_timeout', 'decision_required', 'place_entered',
                        'object_sighting', 'motion_observed', 'heartbeat',
                        'verifier_uncertain', 'precondition_violated',
                        'plan_exhausted', 'path_blocked'})


@dataclass(frozen=True)
class Boundary:
    event_id: str
    episode_id: str
    event_type: str
    sim_time: float
    entity_ids: tuple[str, ...] = ()
    place_ids: tuple[str, ...] = ()

    def __post_init__(self):
        from .schemas import ids
        text(self.event_id)
        text(self.episode_id)
        finite(self.sim_time)
        ids(self.entity_ids)
        ids(self.place_ids)
        if self.event_type not in BOUNDARIES:
            raise ValueError('Unknown boundary; normalize in the harness adapter')


class RecentBuffer:
    """Holds references only. Eviction does not delete source artifacts."""

    def __init__(self, episode_id: str, max_frames: int = 64, max_age_s: float = 20):
        self.episode_id = text(episode_id)
        self.max_frames = integer(max_frames, 1)
        self.max_age = finite(max_age_s)
        self._items: deque[Asset] = deque()
        self._latest: dict[str, float] = {}

    def add(self, asset: Asset) -> bool:
        if asset.episode_id != self.episode_id or asset.kind != 'image':
            raise ValueError('Buffer accepts original images of its episode only')
        if asset.observed_end <= self._latest.get(asset.camera, -1):
            return False
        self._latest[asset.camera] = asset.observed_end
        self._items.append(asset)
        cutoff = max(self._latest.values()) - self.max_age
        self._items = deque(a for a in self._items if a.observed_end >= cutoff)
        while len(self._items) > self.max_frames:
            self._items.popleft()
        return True

    def select(self, until: float, *, window_s: float = 8, max_frames: int = 4) -> tuple[Asset, ...]:
        finite(until)
        finite(window_s)
        integer(max_frames)
        items = sorted((a for a in self._items if until-window_s <= a.observed_end <= until),
                       key=lambda a: (a.observed_end, a.camera, a.asset_id))
        if not items or max_frames == 0:
            return ()
        # Latest view per camera, then earliest views. No subjective semantic detector
        # is claimed; contact-rich streams should pin additional frames explicitly.
        chosen = []
        for camera in sorted({a.camera for a in items}):
            chosen.append(next(a for a in reversed(items) if a.camera == camera))
        for a in items:
            if a not in chosen:
                chosen.append(a)
        return tuple(sorted(chosen[:max_frames], key=lambda a: (a.observed_end, a.camera)))


class EventRecorder:
    """Persist a deterministic card first; request optional narration separately.

    Call this from a sidecar/event-drain, not a hard-real-time control callback.
    It does short SQLite work, but never invokes a model or moves the robot.
    """

    def __init__(self, store: MemoryStore, recent: RecentBuffer, max_frames: int = 4):
        self.store, self.recent = store, recent
        self.max_frames = integer(max_frames, 1)
        if store.episode_id != recent.episode_id:
            raise ValueError('Episode mismatch')

    def record(self, boundary: Boundary) -> Card:
        if boundary.episode_id != self.store.episode_id:
            raise ValueError('Foreign episode event')
        card_id = stable_id('event', [boundary.episode_id, boundary.event_id])
        # Repeated receipt IDs must not produce duplicate events or change their content.
        try:
            previous = self.store.card(card_id)
        except ValueError as exc:
            if str(exc) != 'Unknown memory card':
                raise
        else:
            if (previous.event_type != boundary.event_type or previous.observed_end != boundary.sim_time
                    or previous.entity_ids != boundary.entity_ids or previous.place_ids != boundary.place_ids):
                raise ValueError('Conflicting replayed boundary')
            return previous
        assets = self.recent.select(boundary.sim_time, max_frames=self.max_frames)
        kind = {'object_sighting': 'entity_view', 'place_entered': 'place_view',
                'motion_observed': 'motion'}.get(boundary.event_type, 'event')
        if not assets or (kind == 'motion' and len({a.observed_end for a in assets}) < 2):
            kind = 'coverage_gap'
        outcome = {'skill_verified': 'verifier_reported_supported',
                   'skill_failed': 'failed', 'skill_stalled': 'uncertain',
                   'execution_timeout': 'uncertain',
                   'verifier_uncertain': 'uncertain',
                   'precondition_violated': 'uncertain',
                   'plan_exhausted': 'uncertain',
                   'path_blocked': 'uncertain'}.get(boundary.event_type, 'not_assessed')
        card = Card(
            card_id, boundary.episode_id, kind, boundary.event_id, boundary.event_type,
            min((a.observed_start for a in assets), default=boundary.sim_time), boundary.sim_time,
            tuple(a.asset_id for a in assets), boundary.entity_ids, boundary.place_ids,
            summary=f'Runtime reported {boundary.event_type}; historical event, not a current-state certificate.',
            reported_outcome=outcome,
        )
        self.store.add_card(card)
        return card


def boundary_from_runtime(event, *, entity_ids: tuple[str, ...] = (),
                          place_ids: tuple[str, ...] = ()) -> Boundary:
    """Small adapter for existing RuntimeEvent. Deliberately ignore arbitrary payload.

    Entity/place bindings must come from trusted runtime/tracker IDs, not a VLM
    inventing new global identities or a diary string being parsed as a command.
    """
    name = getattr(event.type, 'value', event.type)
    return Boundary(event.event_id, event.episode_id, name, event.sim_time, entity_ids, place_ids)
