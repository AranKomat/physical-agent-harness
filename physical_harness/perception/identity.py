"""Persistent semantics + fresh geometry, backed by the existing experiment Journal.

Association is a separate trusted perception task. A tracker ID is scoped to its
camera/session. This module does not pretend that a SAM mask proves identity.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from physical_harness.core.actions import Basis, digest, ids, number, plain, text
from physical_harness.core.tasks import basis_from_dict, same_episode


@dataclass(frozen=True)
class Tracklet:
    basis: Basis
    camera: str
    session: str
    local_id: str
    mask_evidence_id: str
    center: tuple[float, float, float] | None = None
    radius_error_m: float | None = None

    def __post_init__(self):
        if not isinstance(self.basis, Basis):
            raise ValueError("Tracklet requires current Basis")
        for x in (self.camera, self.session, self.local_id, self.mask_evidence_id):
            text(x)
        if self.center is not None:
            if type(self.center) is not tuple or len(self.center) != 3:
                raise ValueError("Metric center must be an immutable 3-vector")
            for x in self.center:
                number(x)
            if self.radius_error_m is None:
                raise ValueError("Explicit geometric error bound required")
        if self.radius_error_m is not None:
            number(self.radius_error_m, low=0, high=10)
            if self.center is None:
                raise ValueError("Error bound without geometry")

    @property
    def key(self):
        return (self.basis.episode, self.camera, self.session, self.local_id)

    @property
    def fingerprint(self):
        return digest(self)


@dataclass(frozen=True)
class SemanticClaim:
    label: str | None
    status: str  # recognized | ambiguous | contradictory; not SAM detector logits
    evidence_ids: tuple[str, ...]
    method: str

    def __post_init__(self):
        if self.label is not None:
            text(self.label)
        if self.status not in {"recognized", "ambiguous", "contradictory"}:
            raise ValueError("Explicit semantic status required")
        if self.status != "ambiguous" and self.label is None:
            raise ValueError("A positive/contradictory claim requires a label")
        ids(self.evidence_ids, empty=False)
        text(self.method)


@dataclass(frozen=True)
class AssociationProof:
    entity: str
    prior_revision: str
    track_fingerprint: str
    unique: bool | None
    temporal_support: bool | None
    geometry_support: bool | None
    method: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self):
        for s in (self.entity, self.prior_revision, self.track_fingerprint, self.method):
            text(s)
        for v in (self.unique, self.temporal_support, self.geometry_support):
            if v is not None and type(v) is not bool:
                raise ValueError("Three-valued association checks required")
        ids(self.evidence_ids, empty=False)

    @property
    def established(self):
        return all(x is True for x in (self.unique, self.temporal_support, self.geometry_support))


def geometric_candidates(track: Tracklet, entities: tuple[dict, ...], *,
                         max_gap_s: float, max_distance_m: float) -> tuple[str, ...]:
    """Suggest associations; NEVER authorize them or call nearest == identical.

    Intended to narrow an external track/appearance matcher. Distances compare
    partial-surface centers and remain deliberately weaker than rigid pose matching.
    """
    number(max_gap_s, low=0)
    number(max_distance_m, low=0)
    if track.center is None:
        return ()
    result = []
    for entity in entities:
        old = entity.get("last_track")
        if old is None or old["center"] is None:
            continue
        basis = basis_from_dict(old["basis"])
        try:
            basis.require_continuity(track.basis)
        except PermissionError:
            continue
        if track.basis.sim_time - basis.sim_time > max_gap_s:
            continue
        distance = sum((a-b)**2 for a, b in zip(track.center, old["center"]))**.5
        if distance <= max_distance_m + track.radius_error_m + old["radius_error_m"]:
            result.append(entity["entity"])
    return tuple(sorted(result))


class IdentityLedger:
    """One episode/single writer. Replays original timestamps from existing Journal.

    Canonical recognition is an observation-supported BELIEF, never ground truth.
    A later unrecognizable side view does not erase it. Strong contradiction or
    uncertain association blocks semantic action binding until separately resolved.
    """
    KIND = "situated_identity"

    def __init__(self, journal, *, max_entities=512):
        from physical_harness.core.actions import integer
        self.journal = journal
        integer(max_entities, low=1, high=10000)
        self.max_entities = max_entities
        self._lock = threading.RLock()
        self._entities = {}
        self._events = set()
        for row in journal.records(self.KIND):
            self._reduce(row)

    def _reduce(self, row):
        if row["episode"] != self.journal.episode:
            raise PermissionError("Foreign identity journal")
        self._entities[row["entity"]] = row["state"]
        self._events.add(row["event_key"])

    def _put(self, event, entity, state):
        state = plain(state)
        key = digest([self.journal.episode, event, entity, state])
        if key in self._events:
            raise PermissionError("Duplicate identity update")
        row = {"episode": self.journal.episode, "event": event, "entity": entity,
               "state": state, "event_key": key}
        self.journal.put(self.KIND, key, row)  # durable first; failure leaves state unchanged
        self._reduce(row)

    def _basis(self, track):
        if not isinstance(track, Tracklet) or track.basis.episode != self.journal.episode:
            raise PermissionError("Foreign/untyped track")

    def new_entity(self, track: Tracklet, claim: SemanticClaim) -> str:
        with self._lock:
            self._basis(track)
            if len(self._entities) >= self.max_entities:
                raise ValueError("Identity capacity reached")
            if any(s.get("track_key") == list(track.key) for s in self._entities.values()):
                raise PermissionError("Existing scoped track needs association, not duplicate identity")
            entity = "entity:" + digest([self.journal.episode, track.key, track.basis.fingerprint])[:24]
            canonical = self._canonical(claim, track.basis) if claim.status == "recognized" else None
            state = {"entity": entity, "canonical": canonical, "conflicts": [],
                     "last_basis": plain(track.basis), "last_track": plain(track),
                     "track_key": list(track.key), "current_semantics": plain(claim),
                     "visibility": "visible", "association": "new_instance",
                     "association_evidence": list(claim.evidence_ids), "alternatives": []}
            self._put("new", entity, state)
            return entity

    @staticmethod
    def _canonical(claim, basis):
        return {"label": claim.label, "status": "observation_supported_belief",
                "observed_at": basis.sim_time, "observation_id": basis.observation_id,
                "evidence_ids": list(claim.evidence_ids), "method": claim.method}

    def state(self, entity):
        text(entity)
        try:
            return plain(self._entities[entity])  # caller cannot mutate authority
        except KeyError as exc:
            raise ValueError("Unknown entity") from exc

    def revision(self, entity):
        return digest(self.state(entity))

    def observe(self, entity: str, track: Tracklet, claim: SemanticClaim,
                proof: AssociationProof, *, alternatives: tuple[str, ...] = ()):
        with self._lock:
            self._basis(track)
            state = self.state(entity)
            old_basis = basis_from_dict(state["last_basis"])
            same_episode(old_basis, track.basis)
            if old_basis.sim_time == track.basis.sim_time and old_basis.observation_id == track.basis.observation_id:
                raise PermissionError("Repeated capture cannot refresh identity evidence")
            if (proof.entity, proof.prior_revision, proof.track_fingerprint) != (
                entity, self.revision(entity), track.fingerprint
            ):
                raise PermissionError("Stale or foreign association proof")
            ids(alternatives)
            state.update(last_basis=plain(track.basis), current_semantics=plain(claim),
                         association_evidence=list(proof.evidence_ids), alternatives=list(alternatives))
            if not proof.established or alternatives:
                # Retain old track as history; never attribute fresh geometry to a guess.
                state.update(association="ambiguous", visibility="identity_uncertain")
                self._put("ambiguous", entity, state)
                return
            # Do not allow a local tracker key to belong to two persistent entities.
            if any(e != entity and s.get("track_key") == list(track.key)
                   for e, s in self._entities.items()):
                raise PermissionError("Track already associated with another entity")
            state.update(last_track=plain(track), track_key=list(track.key),
                         association="established", visibility="visible")
            if claim.status == "recognized":
                old = state["canonical"]
                if old is None:
                    state["canonical"] = self._canonical(claim, track.basis)
                elif old["label"] != claim.label:
                    state["conflicts"] = [old, self._canonical(claim, track.basis)]
                # Same label on propagated observations does not overwrite the strong source.
            elif claim.status == "contradictory":
                state["conflicts"] = ([state["canonical"]] if state["canonical"] else []) + [
                    self._canonical(claim, track.basis)]
            self._put("observed", entity, state)

    def mark_not_observed(self, entity: str, basis: Basis, evidence_ids: tuple[str, ...]):
        with self._lock:
            state = self.state(entity)
            old = basis_from_dict(state["last_basis"])
            same_episode(old, basis)
            ids(evidence_ids, empty=False)
            if old == basis:
                raise PermissionError("No new observation")
            state.update(last_basis=plain(basis), visibility="not_observed", association="unobserved",
                         association_evidence=list(evidence_ids))
            self._put("not_observed", entity, state)

    def resolve_semantics(self, entity, track, claim, proof):
        """Explicit new discrimination, not repeated labels or a model confidence boost."""
        with self._lock:
            state = self.state(entity)
            if claim.status != "recognized" or not proof.established:
                raise PermissionError("Resolution requires new recognition and association")
            old_evidence = {e for c in state["conflicts"] for e in c["evidence_ids"]}
            if not set(claim.evidence_ids) - old_evidence:
                raise PermissionError("Conflict resolution needs new discriminating evidence")
            self.observe(entity, track, claim, proof)
            state = self.state(entity)
            state["canonical"] = self._canonical(claim, track.basis)
            state["conflicts"] = []
            self._put("semantics_resolved", entity, state)

    def binding(self, entity: str, current: Basis) -> dict:
        """The compiler may use remembered semantics with measured CURRENT geometry.

        Geometry from a past view is never refreshed by copying a label or timestamp.
        """
        state = self.state(entity)
        current.require_same(basis_from_dict(state["last_basis"]))
        if state["conflicts"] or not state["canonical"] or state["visibility"] != "visible":
            raise PermissionError("Identity/semantics not established for action binding")
        if state["association"] not in {"established", "new_instance"}:
            raise PermissionError("Association ambiguous")
        track = state["last_track"]
        current.require_same(basis_from_dict(track["basis"]))
        if track["center"] is None:
            raise PermissionError("Current depth geometry unavailable")
        return {"entity": entity, "canonical": state["canonical"],
                "geometry": {"center": track["center"], "radius_error_m": track["radius_error_m"],
                             "basis": plain(current), "mask_evidence_id": track["mask_evidence_id"]},
                "association_evidence": state["association_evidence"],
                "epistemic": "remembered_semantics_current_geometry"}

    def project_world(self, world, entity: str, evidence_id: str):
        """Optional projection into EXISTING WorldState using distinct predicates.

        Caller registers the source evidence first. Does not overwrite RTSM label,
        geometry or visibility fields. These are inferred beliefs, not truth.
        """
        state = self.state(entity)
        if world.episode != self.journal.episode:
            raise PermissionError("Foreign WorldState")
        for name, value in (("canonical_semantics", state["canonical"]),
                            ("identity_conflicts", state["conflicts"]),
                            ("identity_association", state["association"])):
            import json
            world.update(entity, name, json.dumps(value, sort_keys=True), evidence_id,
                         epistemic="inferred")


def focus_identity_view(identity, entity: str, current: Basis) -> dict:
    """Current geometry only through existing IdentityLedger.binding; no label-as-pose."""
    state = identity.state(entity)
    try:
        binding = identity.binding(entity, current)
        return {"entity": entity, "current_binding": binding, "current_geometry_available": True}
    except PermissionError:
        return {"entity": entity, "current_binding": None, "current_geometry_available": False,
                "remembered_semantics": state["canonical"], "visibility": state["visibility"],
                "conflicts": state["conflicts"], "association": state["association"],
                "notice": "Reobserve/reassociate before action; historical coordinates are not current."}
