"""Shadow/live integration glue for multimodal episodic memory.

This module deliberately has no authority over WorldState, TaskLedger, motor
commands, or verification. It connects already-legal observations and already-
normalized runtime events to historical memory and can optionally attach a
bounded historical packet to an executive context.

The first deployment mode should be ``active=False``: build exactly the memory
packet that *would* have been delivered, persist its causal cutoff, but return
the original executive context unchanged.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .retrieval import Retriever, attach_memory
from .schemas import Asset, Cutoff, PacketBudget, finite, stable_id, text
from .selection import EventRecorder, RecentBuffer, boundary_from_runtime
from .spatial_views import SpatialViewIndex, keyframes_from_legal_envelope
from .store import MemoryStore


@dataclass(frozen=True)
class MemoryDecision:
    decision_id: str
    event_id: str
    cutoff: Cutoff
    query: str
    entity_id: str | None
    place_id: str | None
    card_ids: tuple[str, ...]
    active: bool

    def __post_init__(self):
        text(self.decision_id)
        text(self.event_id)
        if not isinstance(self.cutoff, Cutoff):
            raise ValueError("Cutoff required")
        if not isinstance(self.query, str) or len(self.query.encode()) > 2000:
            raise ValueError("Bounded query required")
        for value in (self.entity_id, self.place_id):
            if value is not None:
                text(value)
        if (
            not isinstance(self.card_ids, tuple)
            or len(set(self.card_ids)) != len(self.card_ids)
            or any(not isinstance(value, str) or not value for value in self.card_ids)
        ):
            raise ValueError("Unique card IDs required")
        if not isinstance(self.active, bool):
            raise ValueError("active must be bool")


class DecisionCutoffLog:
    """Durable decision-time cutoffs for causal replay.

    Reservations happen *before retrieval/provider work*. If retrieval crashes,
    the causal cutoff remains durable with status ``reserved`` rather than being
    silently lost.
    """

    def __init__(self, path: str | Path, episode_id: str):
        self.episode_id = text(episode_id)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS decisions(
                decision_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                episode_id TEXT NOT NULL,
                observed_through REAL NOT NULL,
                knowledge_seq INTEGER NOT NULL,
                query TEXT NOT NULL,
                entity_id TEXT,
                place_id TEXT,
                card_ids TEXT NOT NULL,
                active INTEGER NOT NULL,
                status TEXT NOT NULL
            )"""
        )
        old = self.db.execute(
            "SELECT DISTINCT episode_id FROM decisions LIMIT 2"
        ).fetchall()
        if any(row[0] != self.episode_id for row in old):
            self.db.close()
            raise ValueError("Decision log belongs to another episode")

    def close(self) -> None:
        with self._lock:
            self.db.close()

    def reserve(
        self,
        *,
        decision_id: str,
        event_id: str,
        cutoff: Cutoff,
        query: str,
        entity_id: str | None,
        place_id: str | None,
        active: bool,
    ) -> None:
        decision_id, event_id = text(decision_id), text(event_id)
        if cutoff.episode_id != self.episode_id:
            raise ValueError("Foreign decision cutoff")
        if not isinstance(query, str) or len(query.encode()) > 2000:
            raise ValueError("Bounded query required")
        for value in (entity_id, place_id):
            if value is not None:
                text(value)
        if not isinstance(active, bool):
            raise ValueError("active must be bool")
        body = (
            decision_id, event_id, self.episode_id, cutoff.observed_through,
            cutoff.knowledge_seq, query, entity_id, place_id, "[]", int(active),
            "reserved",
        )
        with self._lock, self.db:
            old = self.db.execute(
                "SELECT * FROM decisions WHERE decision_id=?", (decision_id,)
            ).fetchone()
            if old:
                existing_prefix = (
                    old["decision_id"], old["event_id"], old["episode_id"],
                    old["observed_through"], old["knowledge_seq"], old["query"],
                    old["entity_id"], old["place_id"], old["active"],
                )
                expected_prefix = (
                    decision_id, event_id, self.episode_id, cutoff.observed_through,
                    cutoff.knowledge_seq, query, entity_id, place_id, int(active),
                )
                if existing_prefix != expected_prefix:
                    raise ValueError("Conflicting replay of decision cutoff")
                return
            self.db.execute(
                "INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)", body
            )

    def finalize(self, decision_id: str, card_ids: tuple[str, ...]) -> MemoryDecision:
        decision_id = text(decision_id)
        if (
            not isinstance(card_ids, tuple)
            or len(set(card_ids)) != len(card_ids)
            or any(not isinstance(value, str) or not value for value in card_ids)
        ):
            raise ValueError("Unique card IDs required")
        encoded_ids = json.dumps(card_ids)
        with self._lock, self.db:
            row = self.db.execute(
                "SELECT * FROM decisions WHERE decision_id=?", (decision_id,)
            ).fetchone()
            if not row:
                raise ValueError("Reserve decision before finalizing")
            if row["status"] == "finalized":
                if row["card_ids"] != encoded_ids:
                    raise ValueError("Conflicting decision retrieval replay")
            else:
                self.db.execute(
                    "UPDATE decisions SET card_ids=?,status='finalized' WHERE decision_id=?",
                    (encoded_ids, decision_id),
                )
        return self.get(decision_id)

    def get(self, decision_id: str) -> MemoryDecision:
        row = self.db.execute(
            "SELECT * FROM decisions WHERE decision_id=?", (text(decision_id),)
        ).fetchone()
        if not row:
            raise ValueError("Unknown decision")
        return MemoryDecision(
            row["decision_id"],
            row["event_id"],
            Cutoff(row["episode_id"], row["observed_through"], row["knowledge_seq"]),
            row["query"],
            row["entity_id"],
            row["place_id"],
            tuple(json.loads(row["card_ids"])),
            bool(row["active"]),
        )

    def status(self, decision_id: str) -> str:
        row = self.db.execute(
            "SELECT status FROM decisions WHERE decision_id=?", (text(decision_id),)
        ).fetchone()
        if not row:
            raise ValueError("Unknown decision")
        return row[0]


class MemorySidecar:
    """Episode-local bridge from legal observations/events to historical memory.

    The sidecar can be connected to ``BehaviorAdapter.logger`` and
    ``EventBus.subscribe``.  It does not call models synchronously and it never
    updates current beliefs or task state.
    """

    def __init__(
        self,
        *,
        episode_id: str,
        store: MemoryStore,
        decisions: DecisionCutoffLog,
        resolve_rgb_ref: Callable[[str], str],
        recent: RecentBuffer | None = None,
        recorder: EventRecorder | None = None,
        annotator: Any | None = None,
        current_place: Callable[[], str | None] | None = None,
        spatial_index: SpatialViewIndex | None = None,
    ):
        self.episode_id = text(episode_id)
        if store.episode_id != self.episode_id or decisions.episode_id != self.episode_id:
            raise ValueError("Memory components must share the episode")
        if not callable(resolve_rgb_ref):
            raise ValueError("RGB reference resolver required")
        self.store = store
        self.decisions = decisions
        self.resolve_rgb_ref = resolve_rgb_ref
        self.recent = recent or RecentBuffer(self.episode_id)
        self.recorder = recorder or EventRecorder(self.store, self.recent)
        self.annotator = annotator
        self.current_place = current_place or (lambda: None)
        if spatial_index is not None and spatial_index.episode_id != self.episode_id:
            raise ValueError("Spatial memory must share the episode")
        self.spatial_index = spatial_index
        self.retriever = Retriever(self.store)
        self._skill_entities: dict[str, tuple[str, ...]] = {}
        self._skill_places: dict[str, tuple[str, ...]] = {}
        self._last_observed = -1.0

    @staticmethod
    def _hash_from_uri(uri: str) -> str:
        if not isinstance(uri, str) or "." not in uri:
            raise ValueError("Resolved RGB reference must be a hash-named artifact")
        digest = uri.split(".", 1)[0]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Resolved RGB artifact must use its SHA256 filename")
        return digest

    def ingest_observation(
        self,
        envelope: Mapping[str, Any],
        *,
        keyframe_reason: str | None = None,
        keyframe_entity_ids: tuple[str, ...] = (),
        keyframe_place_ids: tuple[str, ...] = (),
        keyframe_tags: tuple[str, ...] = (),
        quality_by_camera: Mapping[str, float] | None = None,
    ) -> tuple[Asset, ...]:
        """Register RGB source images from an already-validated legal envelope.

        The caller must resolve opaque native references to names in the existing
        content-addressed EvidenceStore. Dimensions come from the legal camera
        calibration. Depth is deliberately not copied into the visual diary.

        Posed keyframes are opt-in per observation. They require both an attached
        ``SpatialViewIndex`` and a legally estimated pose; an unposed observation
        remains valid ordinary memory and produces no spatial keyframe.
        """
        value = json.loads(json.dumps(dict(envelope), allow_nan=False))
        required = {
            "episode_id", "observation_id", "sim_time", "rgb_refs",
            "camera_intrinsics",
        }
        if not required <= value.keys() or value["episode_id"] != self.episode_id:
            raise ValueError("Legal observation envelope/episode required")
        observed = finite(value["sim_time"])
        if observed <= self._last_observed:
            raise ValueError("Stale observation cannot enter memory")
        if keyframe_reason is not None and self.spatial_index is None:
            raise ValueError("Posed keyframe recording requires a SpatialViewIndex")
        rgb_refs = value["rgb_refs"]
        intrinsics = value["camera_intrinsics"]
        if not isinstance(rgb_refs, dict) or set(rgb_refs) != set(intrinsics):
            raise ValueError("RGB/calibration camera mismatch")
        assets = []
        for camera in sorted(rgb_refs):
            text(camera)
            calibration = intrinsics[camera]
            width, height = calibration["width"], calibration["height"]
            if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
                raise ValueError("Positive image geometry required")
            uri = self.resolve_rgb_ref(rgb_refs[camera])
            digest = self._hash_from_uri(uri)
            asset = Asset(
                asset_id=stable_id(
                    "image", [self.episode_id, value["observation_id"], camera, uri]
                ),
                episode_id=self.episode_id,
                kind="image",
                uri=uri,
                sha256=digest,
                observed_start=observed,
                observed_end=observed,
                observation_id=text(value["observation_id"]),
                camera=camera,
                width=width,
                height=height,
            )
            assets.append(asset)
        keyframes = ()
        if keyframe_reason is not None and value.get("estimated_pose") is not None:
            keyframes = keyframes_from_legal_envelope(
                value,
                rgb_asset_ids={asset.camera: asset.asset_id for asset in assets},
                reason=keyframe_reason,
                entity_ids=keyframe_entity_ids,
                place_ids=keyframe_place_ids,
                tags=keyframe_tags,
                quality_by_camera=quality_by_camera,
            )
        for asset in assets:
            self.store.add_asset(asset)
            self.recent.add(asset)
        for keyframe in keyframes:
            self.spatial_index.add_keyframe(keyframe)
        self._last_observed = observed
        return tuple(assets)

    def write_spatial_snapshot(self, path: str | Path) -> None:
        """Atomically persist the opt-in shadow index for offline replay."""
        if self.spatial_index is None:
            raise ValueError("No spatial memory is attached")
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp")
        payload = json.dumps(
            self.spatial_index.snapshot(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        temporary.write_text(payload + "\n", encoding="utf-8")
        temporary.replace(destination)

    def bind_skill(
        self,
        skill_id: str,
        *,
        entity_ids: tuple[str, ...] = (),
        place_ids: tuple[str, ...] = (),
    ) -> None:
        skill_id = text(skill_id)
        for values in (entity_ids, place_ids):
            if not isinstance(values, tuple) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError("Entity/place bindings must be tuples of IDs")
        self._skill_entities[skill_id] = tuple(dict.fromkeys(entity_ids))
        self._skill_places[skill_id] = tuple(dict.fromkeys(place_ids))

    def record_event(
        self,
        event: Any,
        *,
        entity_ids: tuple[str, ...] | None = None,
        place_ids: tuple[str, ...] | None = None,
        narrate: bool = False,
    ):
        if getattr(event, "episode_id", None) != self.episode_id:
            raise ValueError("Foreign runtime event")
        payload = getattr(event, "payload", {}) or {}
        skill_id = payload.get("skill_id") if isinstance(payload, Mapping) else None
        if entity_ids is None:
            entity_ids = self._skill_entities.get(skill_id, ())
        if place_ids is None:
            bound = self._skill_places.get(skill_id, ())
            current = self.current_place()
            place_ids = bound or ((current,) if current else ())
        boundary = boundary_from_runtime(
            event, entity_ids=entity_ids, place_ids=place_ids
        )
        card = self.recorder.record(boundary)
        if narrate and self.annotator is not None:
            # Capture the basis AFTER the deterministic card exists but BEFORE
            # asynchronous narration can complete.
            basis = self.store.cutoff(boundary.sim_time)
            self.annotator.submit(card.card_id, basis)
        return card

    def prepare_decision(
        self,
        *,
        decision_id: str,
        event_id: str,
        observed_through: float,
        base_context: Mapping[str, Any],
        query: str = "",
        entity_id: str | None = None,
        place_id: str | None = None,
        budget: PacketBudget | None = None,
        include_images: bool = True,
        active: bool = False,
        max_total_bytes: int = 12000,
        max_total_images: int = 6,
        provider_check: Callable[[dict], bool] | None = None,
    ) -> tuple[dict[str, Any], MemoryDecision, dict[str, Any]]:
        """Build the same packet in shadow and active modes.

        Shadow mode returns the original base context *unchanged* while returning
        the packet separately for replay scoring. Active mode explicitly attaches
        the packet under the normal context budget.
        """
        decision_id, event_id = text(decision_id), text(event_id)
        cutoff = self.store.cutoff(finite(observed_through))
        # Persist the causal watermark before retrieval or any provider path.
        self.decisions.reserve(
            decision_id=decision_id,
            event_id=event_id,
            cutoff=cutoff,
            query=query,
            entity_id=entity_id,
            place_id=place_id,
            active=active,
        )
        hits = self.retriever.search(
            cutoff,
            query=query,
            entity_id=entity_id,
            place_id=place_id,
            limit=(budget or PacketBudget()).max_cards,
        )
        packet = self.retriever.packet(
            hits, cutoff, budget or PacketBudget(), include_images=include_images
        )
        decision = self.decisions.finalize(
            decision_id, tuple(card["card_id"] for card in packet["cards"])
        )
        base_copy = json.loads(json.dumps(dict(base_context), allow_nan=False))
        if not active:
            return base_copy, decision, packet
        attached = attach_memory(
            base_copy,
            packet,
            max_total_bytes=max_total_bytes,
            max_total_images=max_total_images,
            provider_check=provider_check,
        )
        return attached, decision, packet
