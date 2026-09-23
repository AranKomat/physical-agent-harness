"""Selective image-first semantic diary backed by the EXISTING Journal.

Inventory is a retrieval/attention view, never current geometric truth. Demotion
removes items from executive context without deleting the original evidence.
Retention filtering must never filter the collision/safety perception path.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from physical_harness.core.actions import Basis, digest, ids, integer, number, plain, text, unit
from physical_harness.perception.contracts import (
    DiscoveryResult,
    FrameRef,
    Retention,
    frame_from_dict,
)


@dataclass(frozen=True)
class InventoryLimits:
    hot: int = 16
    warm: int = 128
    total_records: int = 2048
    views_per_item: int = 4

    def __post_init__(self):
        integer(self.hot, low=1, high=128)
        integer(self.warm, low=self.hot, high=2048)
        integer(self.total_records, low=self.warm, high=100000)
        integer(self.views_per_item, low=1, high=12)


class SemanticInventory:
    KIND = "embodied_inventory"

    def __init__(self, journal, limits: InventoryLimits = InventoryLimits()):
        self.journal, self.limits = journal, limits
        self.records: dict[str, dict] = {}
        self.completed: set[str] = set()
        self.pins: dict[str, str] = {}
        self._events: list[dict] = []
        for row in journal.records(self.KIND):
            self._reduce(row)
        if len(self.records) > limits.total_records:
            raise ValueError("Inventory limit shrank below durable state")

    def _reduce(self, row):
        if row["episode"] != self.journal.episode:
            raise PermissionError("Foreign inventory journal")
        if row["event"] == "discovery":
            self.completed.add(row["request_id"])
            for record in row["records"]:
                self.records[record["id"]] = record
        elif row["event"] == "replace":
            self.records[row["record"]["id"]] = row["record"]
        elif row["event"] == "pin":
            self.pins[row["item_id"]] = row["reason"]
        elif row["event"] == "unpin":
            self.pins.pop(row["item_id"], None)
        else:
            raise ValueError("Unknown durable inventory event")
        self._events.append(row)

    def _put(self, key, row):
        row = plain(dict(row, episode=self.journal.episode))
        self.journal.put(self.KIND, key, row)
        self._reduce(row)

    @property
    def revision(self):
        return digest([self.records, self.pins])

    def accept(self, result: DiscoveryResult, *, received_wall: float,
               current_task_revision: str) -> tuple[str, ...]:
        """Consume atomically on the main writer; semantic results never mutate identity.

        Out-of-order completions are recorded at their original observed time and
        actual publication time. Superseded-task relevance cannot trigger the new
        task, though historical observations may remain useful for retrieval.
        """
        if not isinstance(result, DiscoveryResult) or result.request.current.episode != self.journal.episode:
            raise PermissionError("Foreign discovery result")
        number(received_wall, low=result.completed_wall)
        if result.completed_wall > result.request.deadline_wall:
            raise PermissionError("Late discovery completion")
        if result.request.id in self.completed:
            raise PermissionError("Discovery response was already committed")
        frames = {f.asset_id: f for f in result.request.frames}
        regions = {r.id: r for r in result.request.regions}
        records = []
        for u in result.updates:
            f = frames[u.frame_id]
            identifier = "sighting:" + digest([result.request.fingerprint, u.local_id])[:24]
            state = "aggregate" if u.retention == Retention.AGGREGATE else "sighting"
            row = {"id": identifier, "kind": state, "entity_id": None,
                   "known_id_hypothesis": u.known_id,
                   "description": u.description, "hypotheses": list(u.hypotheses),
                   "semantic_status": u.status, "source_model": result.model,
                   "retention": u.retention.value, "value": plain(u.value), "rank": u.value.rank,
                   "task_revision": result.request.task_revision, "task_current_at_arrival": result.request.task_revision == current_task_revision,
                   "needs_view": u.needs_view, "frame": plain(f),
                   "box": list(u.box if u.box is not None else regions[u.region_id].box),
                   "region_id": u.region_id, "observed_sim": f.basis.sim_time,
                   "available_wall": received_wall, "views": [], "place_id": None,
                   "authority": "historical_semantic_hypothesis", "manipulation_authority": False}
            records.append(row)
        if len(self.records) + len(records) > self.limits.total_records:
            raise ValueError("Durable inventory capacity reached; rotate/archive explicitly")
        self._put(result.request.id+":discovery", {
            "event": "discovery", "request_id": result.request.id,
            "request_fingerprint": result.request.fingerprint, "result_fingerprint": result.fingerprint,
            "observed_sim": result.request.current.sim_time, "available_wall": received_wall,
            "scene_summary": result.scene_summary, "records": records,
            "attention": plain(result.attention), "task_revision": result.request.task_revision,
        })
        return tuple(r["id"] for r in records)

    def state(self, item_id: str, *, cutoff_sim: float, cutoff_wall: float) -> dict:
        number(cutoff_sim, low=0)
        number(cutoff_wall, low=0)
        text(item_id)
        # Reconstruct by dual-clock causal cutoff, not latest Python dict alone.
        value = None
        for event in self._events:
            if event["available_wall"] > cutoff_wall or event.get("observed_sim", 0) > cutoff_sim:
                continue
            if event["event"] == "discovery":
                for r in event["records"]:
                    if r["id"] == item_id and r["observed_sim"] <= cutoff_sim:
                        value = r
            elif event["event"] == "replace" and event["record"]["id"] == item_id:
                value = event["record"]
        if value is None:
            raise ValueError("Unknown item at this causal cutoff")
        return plain(value)

    def link_entity(self, item_id, *, entity: str, identity, current: Basis,
                    association_check, evidence_ids: tuple[str, ...], available_wall: float):
        """Link a sighting only after an externally qualified cross-time association.

        The callback must verify THIS sighting's source region against the current
        identity, not merely assert that some tracked entity is currently valid.
        Current geometry stays exclusively in the existing IdentityLedger.
        """
        current.fresh(available_wall, 2.)
        if current.episode != self.journal.episode:
            raise PermissionError("Foreign identity association")
        ids(evidence_ids, empty=False)
        row = self.state(item_id, cutoff_sim=current.sim_time, cutoff_wall=available_wall)
        binding = identity.binding(entity, current)
        revision = identity.revision(entity)
        if association_check(row, binding, evidence_ids) is not True:
            raise PermissionError("Sighting-to-entity association not established")
        if identity.revision(entity) != revision:
            raise PermissionError("Identity changed during sighting association")
        row.update(entity_id=entity, kind="entity_link", identity_revision=revision,
                   association_evidence=list(evidence_ids))
        self._put(digest([item_id, revision, evidence_ids]), {
            "event": "replace", "record": row, "available_wall": available_wall,
            "observed_sim": current.sim_time})

    def add_views(self, item_id: str, views: tuple[CanonicalView, ...], *, current: Basis,
                  available_wall: float, association_check):
        """Select complementary views; rejected candidates remain in journal history.

        The external association check binds each crop to this inventory item.
        Updating a visual index never reconfirms a category or current location.
        """
        if current.episode != self.journal.episode:
            raise PermissionError("Foreign canonical view")
        number(available_wall, low=current.captured_wall)
        if type(views) is not tuple or len(views) > 32:
            raise ValueError("Bounded view candidates required")
        row = self.state(item_id, cutoff_sim=current.sim_time, cutoff_wall=available_wall)
        previous = tuple(canonical_from_dict(v) for v in row["views"])
        for view in views:
            if not isinstance(view, CanonicalView):
                raise ValueError("Typed canonical view required")
            view.frame.available(current, available_wall)
            if association_check(row, view) is not True:
                raise PermissionError("Canonical image association is unestablished")
        selected = choose_canonical_views(previous + views, maximum=self.limits.views_per_item)
        row["views"] = plain(selected)
        self._put(digest([item_id, views, available_wall]), {
            "event": "replace", "record": row, "available_wall": available_wall,
            "observed_sim": current.sim_time, "view_candidates": plain(views)})

    def set_place(self, item_id: str, place_id: str, *, evidence_ids: tuple[str, ...],
                  current: Basis, available_wall: float):
        """Historical place annotation, not a metric navigation destination."""
        text(place_id)
        number(available_wall, low=current.captured_wall)
        ids(evidence_ids, empty=False)
        row = self.state(item_id, cutoff_sim=current.sim_time, cutoff_wall=available_wall)
        if current.episode != self.journal.episode:
            raise PermissionError("Foreign place annotation")
        row.update(place_id=place_id, place_evidence=list(evidence_ids))
        self._put(digest([item_id, place_id, evidence_ids, available_wall]), {
            "event": "replace", "record": row, "available_wall": available_wall,
            "observed_sim": current.sim_time})

    def pin(self, item_id, reason, *, now: float):
        if item_id not in self.records:
            raise ValueError("Unknown pin target")
        if reason not in {"held", "active_goal", "user_requested", "safety_reference"}:
            raise ValueError("Pins are operator/runtime decisions, not model retention flags")
        number(now, low=self.records[item_id]["available_wall"])
        if len(self.pins) >= self.limits.hot and item_id not in self.pins:
            raise ValueError("Pinned working set exceeds hot budget; do not evict held/goal evidence")
        self._put(digest(["pin", item_id, reason, now]), {
            "event": "pin", "item_id": item_id, "reason": reason, "available_wall": now})

    def unpin(self, item_id, *, now: float):
        number(now, low=0)
        if item_id not in self.pins:
            raise ValueError("Item was not pinned")
        self._put(digest(["unpin", item_id, now]), {
            "event": "unpin", "item_id": item_id, "available_wall": now})

    def tier_view(self, *, current: Basis, now: float, task_revision: str) -> dict:
        if current.episode != self.journal.episode:
            raise PermissionError("Foreign inventory cutoff")
        number(now, low=current.captured_wall)
        rows = []
        for item_id in self.records:
            try:
                rows.append(self.state(item_id, cutoff_sim=current.sim_time, cutoff_wall=now))
            except ValueError:
                pass
        # Rebuild pins at the same wall cutoff; future pins do not change old prompts.
        pins = {}
        for e in self._events:
            if e["available_wall"] > now:
                continue
            if e["event"] == "pin":
                pins[e["item_id"]] = e["reason"]
            elif e["event"] == "unpin":
                pins.pop(e["item_id"], None)
        ignored = sum(r["retention"] == "ignore" for r in rows)
        causal_revision = digest([rows, pins])
        rows = [r for r in rows if r["retention"] != "ignore" or r["id"] in pins]
        def key(r):
            task_weight = 4*r["value"]["task"] if r["task_revision"] != task_revision else 0
            return (r["id"] not in pins, -(r["rank"]-task_weight), -r["observed_sim"], r["id"])
        rows.sort(key=key)
        hot = rows[:self.limits.hot]
        warm = rows[self.limits.hot:self.limits.warm]
        cold = rows[self.limits.warm:]
        return {"revision": causal_revision, "hot": hot, "warm": warm,
                "cold_ids": [r["id"] for r in cold],
                "ignored_archived": ignored,
                "notice": "Tiers control context/tracking priority, never obstacle/safety sensing."}

    def delta(self, *, after_wall: float, through_wall: float, cutoff_sim: float,
              task_revision: str, limit: int = 12) -> dict:
        number(after_wall, low=0)
        number(through_wall, low=after_wall)
        integer(limit, low=1, high=64)
        rows = [e for e in self._events if after_wall < e["available_wall"] <= through_wall and
                e.get("observed_sim", 0) <= cutoff_sim and e["event"] in {"discovery", "replace"}]
        # Deltas remain historical; attention from an old objective is not a new-goal interrupt.
        selected = rows[-limit:]
        return {"events": plain(selected), "omitted": len(rows)-len(selected),
                "attention_current_task": [a for e in selected if e.get("task_revision") == task_revision
                                           for a in e.get("attention", ())],
                "through_wall": through_wall}

    def retrieve(self, query: str, *, current: Basis, now: float, place_id: str | None = None,
                 limit: int = 8, embedding_scores: dict[str, float] | None = None) -> tuple[dict, ...]:
        """Structured filters + lexical ranking; optional externally computed index scores.

        Embeddings only rank already-authorized historical candidates. No embedding
        model is loaded. A miss means no retrieved evidence, not absence in the world.
        """
        if current.episode != self.journal.episode:
            raise PermissionError("Foreign retrieval cutoff")
        number(now, low=current.captured_wall)
        text(query, limit=2048)
        integer(limit, low=1, high=32)
        words = set(re.findall(r"\w+", query.lower()))
        scores = embedding_scores or {}
        for key, score in scores.items():
            text(key)
            number(score)
        found = []
        for key in self.records:
            try:
                r = self.state(key, cutoff_sim=current.sim_time, cutoff_wall=now)
            except ValueError:
                continue
            if place_id is not None and r["place_id"] != place_id:
                continue
            content = set(re.findall(r"\w+", (r["description"]+' '+' '.join(r["hypotheses"])).lower()))
            overlap = len(words & content)
            if overlap or key in scores:
                found.append((overlap, scores.get(key, -1e9), r["observed_sim"], key, r))
        found.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3]))
        return tuple(plain(x[4]) for x in found[:limit])

    def known_summary(self, *, current: Basis, now: float, task_revision: str):
        view = self.tier_view(current=current, now=now, task_revision=task_revision)
        rows = [{"id": r["id"], "description": r["description"], "hypotheses": r["hypotheses"],
                 "status": r["semantic_status"]} for r in view["hot"]]
        return tuple(r["id"] for r in rows), json.dumps(rows, separators=(",", ":"))


@dataclass(frozen=True)
class CanonicalView:
    frame: FrameRef
    # Direction is in a stable, explicitly named local/object frame; no guessed front/back.
    direction: tuple[float, float, float] | None
    direction_frame: str | None
    quality: float
    association_evidence: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.frame, FrameRef):
            raise ValueError("FrameRef required")
        if (self.direction is None) != (self.direction_frame is None):
            raise ValueError("Direction and reference frame must be supplied together")
        if self.direction is not None:
            unit(self.direction)
            text(self.direction_frame)
        number(self.quality, low=0, high=1)
        ids(self.association_evidence, empty=False)


def choose_canonical_views(views: tuple[CanonicalView, ...], *, maximum=4,
                           separation_rad=.35) -> tuple[CanonicalView, ...]:
    """Keep actual complementary source views; no semantic auto-promotion."""
    integer(maximum, low=1, high=12)
    number(separation_rad, low=0, high=math.pi)
    if type(views) is not tuple or len(views) > 128 or any(not isinstance(v, CanonicalView) for v in views):
        raise ValueError("Bounded canonical candidates required")
    selected = []
    hashes = set()
    for v in sorted(views, key=lambda v: (-v.quality, -v.frame.basis.sim_time, v.frame.asset_id)):
        if v.frame.content_sha256 in hashes:
            continue
        redundant = any(v.direction is not None and x.direction is not None and
                        v.direction_frame == x.direction_frame and
                        v.frame.basis.frame_epoch == x.frame.basis.frame_epoch and
                        math.acos(max(-1., min(1., sum(a*b for a, b in zip(v.direction, x.direction))))) < separation_rad
                        for x in selected)
        if redundant:
            continue
        selected.append(v)
        hashes.add(v.frame.content_sha256)
        if len(selected) == maximum:
            break
    return tuple(selected)


def canonical_from_dict(value: dict) -> CanonicalView:
    return CanonicalView(frame_from_dict(value["frame"]),
                         tuple(value["direction"]) if value["direction"] is not None else None,
                         value["direction_frame"], value["quality"],
                         tuple(value["association_evidence"]))
