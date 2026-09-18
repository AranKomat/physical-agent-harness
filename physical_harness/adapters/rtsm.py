"""Source-injected RTSM sidecar, independent of native RTSM/simulator types."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from ..state import WorldState
from .behavior import LegalObservation, fields, json_copy, number, text, vector


class RTSMWorldAdapter:
    name = "rtsm"

    def __init__(
        self,
        world: WorldState | None = None,
        *,
        source: Callable[[dict[str, Any]], Mapping[str, Any]] | None = None,
        sim_clock: Callable[[], float] | None = None,
        max_age_s: float = 5.0,
        max_pending: int = 32,
    ):
        self.world, self.source, self.sim_clock = world, source, sim_clock
        self.max_age_s = number(max_age_s, 0)
        if type(max_pending) is not int or max_pending < 1:
            raise ValueError("Invalid pending request limit")
        self.max_pending = max_pending
        self._pending: dict[str, dict[str, Any]] = {}
        self._seen: set[str] = set()
        self._latest = -1.0
        self._entities: set[str] = set()
        self._predicate_confidence: dict[str, float] = {}
        self._support: dict[str, tuple[str, str, str, str]] = {}
        self._snapshot: dict[str, Any] = {}

    def build_request(self, observation: LegalObservation) -> dict[str, Any]:
        value = observation.to_envelope()
        if self.world is None or value["episode_id"] != self.world.episode:
            raise ValueError("Observation requires a matching episode WorldState")
        if value.get("estimated_pose") is None:
            raise ValueError("RTSM requires an evidence-backed legal pose estimate")
        identifier = value["observation_id"]
        if (
            identifier in self._seen
            or identifier in self._pending
            or value["sim_time"] <= self._latest
        ):
            raise ValueError("Stale/repeated observation")
        if len(self._pending) >= self.max_pending:
            raise ValueError("Pending request limit reached")
        self._pending[identifier] = json_copy(value)
        return {"schema_version": 1, "type": "rtsm.observe", "observation": value}

    def observe(self, observation: LegalObservation, *, now: float) -> bool:
        if self.source is None:
            raise ValueError("No RTSM source injected")
        return self.ingest_snapshot(self.source(self.build_request(observation)), now=now)

    @staticmethod
    def _relation(relation: dict[str, Any]) -> tuple[str, str, str]:
        subject, predicate, target = relation["subject"], relation["predicate"], relation["object"]
        if predicate in {"OPEN", "CLOSED"}:
            if target != "true":
                raise ValueError("OPEN/CLOSED use object=true")
            return f"{predicate}({subject})", "open_state", predicate.lower()
        return f"{predicate}({subject},{target})", predicate, target

    def ingest_snapshot(self, snapshot: Mapping[str, Any], *, now: float) -> bool:
        """Correlate a reply with legal input before writing any beliefs.

        Positions are local_map estimates, not camera coordinates. Service IDs
        provide identity; labels never do. Missing objects retain old geometry.
        """
        value = json_copy(snapshot)
        fields(
            value,
            {"schema_version", "episode_id", "observation_id", "sim_time", "objects", "relations"},
        )
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise ValueError("Unsupported RTSM schema")
        if self.world is None or value["episode_id"] != self.world.episode:
            raise ValueError("Cross-episode snapshot")
        identifier = text(value["observation_id"])
        at = number(value["sim_time"], 0)
        current_time = number(now, 0)
        observation = self._pending.get(identifier)
        if observation is None:
            raise ValueError("Unsolicited/replayed snapshot")
        if at != observation["sim_time"]:
            raise ValueError("Snapshot timestamp differs from source evidence")
        if at <= self._latest or current_time - at > self.max_age_s:
            del self._pending[identifier]
            self._seen.add(identifier)
            return False
        if current_time < at:
            raise ValueError("Future snapshot")
        if not isinstance(value["objects"], list) or not isinstance(value["relations"], list):
            raise ValueError("Objects/relations must be lists")
        ids: set[str] = set()
        for obj in value["objects"]:
            fields(obj, {"entity_id", "label", "position", "confidence", "identity_candidates"})
            entity = text(obj["entity_id"])
            if entity in ids:
                raise ValueError("Duplicate entity identity")
            ids.add(entity)
            text(obj["label"])
            vector(obj["position"], 3)
            number(obj["confidence"], 0, 1)
            if not isinstance(obj["identity_candidates"], list):
                raise ValueError("Identity candidates must be a list")
            for candidate in obj["identity_candidates"]:
                text(candidate)
            if (
                len(json.dumps(obj["identity_candidates"])) > 1024
                or len(json.dumps({"frame": "local_map", "position": obj["position"]})) > 1024
            ):
                raise ValueError("Entity estimate exceeds WorldState belief bounds")
        confidences = {}
        relation_keys = set()
        for relation in value["relations"]:
            fields(relation, {"subject", "predicate", "object", "confidence"})
            subject, predicate, target = (
                relation["subject"],
                relation["predicate"],
                relation["object"],
            )
            text(subject)
            text(target)
            if predicate not in {"IN", "ON", "HELD_BY", "OPEN", "CLOSED", "NEXT_TO"}:
                raise ValueError("Non-allowlisted relation")
            if subject not in ids or (target not in ids and target not in {"robot", "true"}):
                raise ValueError("Relations require currently observed endpoints")
            expression, belief_key, _ = self._relation(relation)
            if (subject, belief_key) in relation_keys:
                raise ValueError("Conflicting/duplicate single-valued relation")
            relation_keys.add((subject, belief_key))
            confidences[expression] = number(relation["confidence"], 0, 1)
        evidence_id = "rtsm:" + hashlib.sha256(identifier.encode()).hexdigest()
        self.world.add_evidence(
            evidence_id,
            at,
            "perception",
            "observation:" + identifier,
            {"observation": observation, "snapshot": value},
        )
        for obj in value["objects"]:
            beliefs = {
                "label": obj["label"],
                "location": json.dumps({"frame": "local_map", "position": obj["position"]}),
                "visibility": "visible",
                "confidence": str(obj["confidence"]),
                "identity_candidates": json.dumps(obj["identity_candidates"]),
            }
            for predicate, target in beliefs.items():
                self.world.update(obj["entity_id"], predicate, target, evidence_id)
        for entity in self._entities - ids:
            self.world.update(
                entity, "visibility", "not_observed", evidence_id, epistemic="inferred"
            )
        support = {}
        ambiguous = {obj["entity_id"] for obj in value["objects"] if obj["identity_candidates"]}
        for relation in value["relations"]:
            expression, predicate, target = self._relation(relation)
            subject = relation["subject"]
            self.world.update(subject, predicate, target, evidence_id)
            if subject not in ambiguous and relation["object"] not in ambiguous:
                support[expression] = (subject, predicate, target, evidence_id)
        self._entities.update(ids)
        self._predicate_confidence, self._support = confidences, support
        self._snapshot, self._latest = value, at
        self._seen.add(identifier)
        del self._pending[identifier]
        return True

    def set_predicate_confidence(self, predicate: str, confidence: float) -> None:
        """Legacy unbound test-double only. This never supplies evidence."""
        if self.world is not None:
            raise ValueError("Bound adapters require observation-backed snapshots")
        self._predicate_confidence[text(predicate)] = number(confidence, 0, 1)

    def predicate_evidence(self, predicate: str) -> tuple[str, ...]:
        if self.world is None or self.sim_clock is None or predicate not in self._support:
            return ()
        age = number(self.sim_clock(), 0) - self._latest
        if not 0 <= age <= self.max_age_s or self._snapshot["episode_id"] != self.world.episode:
            return ()
        subject, key, target, evidence = self._support[predicate]
        belief = self.world.belief(subject, key)
        if (
            not belief
            or belief["object"] != target
            or belief["evidence_id"] != evidence
            or belief["epistemic"] != "observed"
        ):
            return ()
        supporting_beliefs = [belief]
        for entity in {subject, target} & self._entities:
            visibility = self.world.belief(entity, "visibility")
            identity = self.world.belief(entity, "identity_candidates")
            if (
                not visibility
                or visibility["object"] != "visible"
                or visibility["evidence_id"] != evidence
            ):
                return ()
            if not identity or identity["object"] != "[]" or identity["evidence_id"] != evidence:
                return ()
            supporting_beliefs.extend([visibility, identity])
        # WorldState retains the prior belief on same-time conflict. Its event
        # log is currently the only API surface exposing unresolved disputes.
        conflicts = self.world.db.execute(
            "SELECT sim_time,payload FROM events WHERE episode=? AND type='belief_conflict' AND sim_time>=?",
            (self.world.episode, min(item["sim_time"] for item in supporting_beliefs)),
        )
        for row in conflicts:
            payload = json.loads(row["payload"])
            if any(
                row["sim_time"] >= item["sim_time"]
                and (payload.get("subject"), payload.get("predicate"))
                == (item["subject"], item["predicate"])
                for item in supporting_beliefs
            ):
                return ()
        return (evidence,)

    def predicate_confidence(self, predicate: str) -> float | None:
        if self.world is not None and not self.predicate_evidence(predicate):
            return None
        return self._predicate_confidence.get(predicate)

    def query(self, query: Mapping[str, Any]) -> Mapping[str, Any]:
        fields(query, set(), {"entity_id"})
        result = json_copy(self._snapshot)
        if "entity_id" in query and result:
            entity = text(query["entity_id"])
            result["objects"] = [obj for obj in result["objects"] if obj["entity_id"] == entity]
            result["relations"] = [rel for rel in result["relations"] if rel["subject"] == entity]
        return {"query": json_copy(query), "snapshot": result}
