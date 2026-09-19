"""Broad-but-bounded executive context for strong multimodal reasoners.

The conservative ContextProjector remains useful for regression tests and small
agents.  This module is an opt-in experiment profile for GPT-class executives:
the harness organizes evidence but avoids making an overly aggressive relevance
decision on the model's behalf.

It intentionally exposes:
- the complete task ledger;
- detailed state for focus entities;
- a compact roster of many known entities;
- short per-entity histories;
- semantic runtime events with safe payload fields;
- semantic topology / current place;
- optional observation-coverage notes.

Historical episodic memory remains separate and evidence-backed.  The
BroadMemorySelector retrieves a union of entity, place, goal-query and recent
history rather than one narrow AND-filter.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from .memory.retrieval import Hit, Retriever
from .memory.schemas import Cutoff, PacketBudget, encoded
from .state import ContextBudgetExceeded, WorldState

_SAFE_RUNTIME_PAYLOAD_SCALARS = frozenset(
    {
        "skill_id",
        "reason",
        "verifier",
        "verdict",
        "confidence",
        "nav_id",
        "blocking_entity",
        "destination",
        "target_entity",
        "current_place",
        "status",
        "outcome",
        "verification",
    }
)


@dataclass(frozen=True)
class CoverageNote:
    """Advisory negative/coverage evidence, not an asserted object location.

    Example: a tabletop was rescanned with high coverage and ball_2 was not
    detected.  This should lower belief that ball_2 remains there, but it does
    not prove where the ball went.
    """

    scope_id: str
    observed_at: float
    coverage: str  # low | medium | high
    result: str  # seen | not_seen | partial | unknown
    evidence_ids: tuple[str, ...] = ()
    note: str = ""

    def __post_init__(self):
        if not isinstance(self.scope_id, str) or not self.scope_id.strip():
            raise ValueError("Coverage scope_id required")
        if (
            isinstance(self.observed_at, bool)
            or not isinstance(self.observed_at, (int, float))
            or not math.isfinite(self.observed_at)
            or self.observed_at < 0
        ):
            raise ValueError("Coverage time must be finite and nonnegative")
        if self.coverage not in {"low", "medium", "high"}:
            raise ValueError("Unknown coverage level")
        if self.result not in {"seen", "not_seen", "partial", "unknown"}:
            raise ValueError("Unknown coverage result")
        if (
            not isinstance(self.evidence_ids, tuple)
            or any(not isinstance(v, str) or not v.strip() for v in self.evidence_ids)
        ):
            raise ValueError("Coverage evidence IDs must be nonempty strings")
        if not isinstance(self.note, str) or len(self.note.encode()) > 1000:
            raise ValueError("Coverage note too large")


@dataclass(frozen=True)
class RichContextPolicy:
    """Moderately generous experiment defaults; still visibly bounded.

    These byte/pixel limits are NOT provider token accounting.  A paid runner
    must still run provider-side text/vision preflight.
    """

    max_current_images: int = 8
    max_state_events: int = 20
    max_runtime_events: int = 24
    max_roster_entities: int = 96
    max_history_entities: int = 16
    history_items_per_predicate: int = 4
    max_history_rows_per_entity: int = 24
    max_topology_places: int = 64
    max_metadata_bytes: int = 64_000

    memory_max_cards: int = 24
    memory_max_images: int = 6
    memory_max_pixels: int = 3_000_000
    memory_metadata_bytes: int = 28_000
    memory_entity_cards: int = 4
    memory_place_cards: int = 4
    memory_query_cards: int = 8
    memory_recent_cards: int = 4

    max_combined_bytes: int = 96_000
    max_combined_images: int = 14

    def __post_init__(self):
        for value in vars(self).values():
            if type(value) is not int or value < 0:
                raise ValueError("Context policy values must be nonnegative integers")


def _jsonish(value: Any) -> Any:
    """Keep useful structured values while rejecting arbitrary rich/native data."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if isinstance(value, (list, tuple)) and len(value) <= 64:
        if all(type(item) in (str, bool, int, float) and not (
            type(item) is float and not math.isfinite(item)
        ) for item in value):
            return list(value)
    return None


def _parse_belief_value(predicate: str, value: str) -> Any:
    if predicate in {"location", "identity_candidates"}:
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value
        if predicate == "identity_candidates":
            if isinstance(parsed, list) and all(isinstance(v, str) for v in parsed):
                return parsed
            return value
        if isinstance(parsed, dict):
            return parsed
    return value


def _runtime_event_view(event: Any) -> dict[str, Any]:
    event_type = getattr(getattr(event, "type", None), "value", getattr(event, "type", None))
    if not isinstance(event_type, str) or not event_type:
        raise ValueError("Runtime event type required")
    sim_time = getattr(event, "sim_time", None)
    if (
        isinstance(sim_time, bool)
        or not isinstance(sim_time, (int, float))
        or not math.isfinite(sim_time)
        or sim_time < 0
    ):
        raise ValueError("Runtime event time must be finite and nonnegative")
    payload = getattr(event, "payload", {}) or {}
    if not isinstance(payload, Mapping):
        raise ValueError("Runtime event payload must be a mapping")
    details = {}
    for key, value in payload.items():
        if key not in _SAFE_RUNTIME_PAYLOAD_SCALARS:
            continue
        safe = _jsonish(value)
        if safe is not None:
            details[key] = safe
    return {
        "event_id": getattr(event, "event_id", ""),
        "type": event_type,
        "sim_time": float(sim_time),
        "details": details,
    }


def _topology_view(topology: Any, current_place: str | None, max_places: int) -> dict[str, Any]:
    if topology is None:
        return {}
    nodes = getattr(topology, "nodes", None)
    edges = getattr(topology, "edges", None)
    if not isinstance(nodes, dict) or not isinstance(edges, list):
        raise ValueError("Topology must expose nodes and edges")
    if len(nodes) > max_places:
        raise ContextBudgetExceeded(
            f"Topology has {len(nodes)} places; explicit experiment limit is {max_places}"
        )
    places = []
    for place_id, node in sorted(nodes.items()):
        metadata = {}
        for key, value in dict(getattr(node, "metadata", {}) or {}).items():
            safe = _jsonish(value)
            if safe is not None:
                metadata[key] = safe
        places.append(
            {
                "id": place_id,
                "label": getattr(node, "label", place_id),
                "kind": getattr(node, "kind", "unknown"),
                "metadata": metadata,
            }
        )
    gateway_states = getattr(topology, "gateway_states", {}) or {}
    connections = []
    for edge in edges:
        gateway = getattr(edge, "gateway_entity", None)
        connections.append(
            {
                "a": getattr(edge, "a"),
                "b": getattr(edge, "b"),
                "cost": getattr(edge, "cost", 1.0),
                "gateway_entity": gateway,
                "gateway_state": gateway_states.get(gateway, "none") if gateway else "none",
                "traversable": bool(getattr(edge, "traversable", True)),
            }
        )
    return {
        "current_place": current_place,
        "places": places,
        "connections": connections,
    }


class RichContextBuilder:
    """High-recall context construction without learned relevance decisions."""

    def __init__(self, state: WorldState, policy: RichContextPolicy | None = None):
        self.state = state
        self.policy = policy or RichContextPolicy()

    def build(
        self,
        *,
        goal: str,
        focus_entities: Iterable[str],
        image_evidence: list[str],
        roster_entities: Iterable[str] | None = None,
        history_entities: Iterable[str] | None = None,
        runtime_events: Sequence[Any] = (),
        topology: Any | None = None,
        current_place: str | None = None,
        observation_coverage: Sequence[CoverageNote] = (),
        navigation_summary: Mapping[str, Any] | None = None,
        executor_summary: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        focus = tuple(dict.fromkeys(focus_entities))
        if roster_entities is None:
            provider = getattr(self.state, "subjects", None)
            roster = tuple(provider()) if callable(provider) else focus
        else:
            roster = tuple(dict.fromkeys(roster_entities))
        # Focus entities are always retained even if the caller forgot to include them.
        roster = tuple(dict.fromkeys((*focus, *roster)))
        if len(roster) > self.policy.max_roster_entities:
            raise ContextBudgetExceeded(
                f"Entity roster has {len(roster)} entries; explicit limit is "
                f"{self.policy.max_roster_entities}. Raise the policy or select deliberately."
            )

        histories = tuple(dict.fromkeys(history_entities if history_entities is not None else focus))
        if len(histories) > self.policy.max_history_entities:
            raise ContextBudgetExceeded("Too many detailed entity histories requested")

        # Ask WorldState for the broad current snapshot.  We then render it into a
        # compact roster rather than duplicating one row per predicate everywhere.
        base = self.state.project(
            goal,
            roster,
            image_evidence,
            max_images=self.policy.max_current_images,
            max_events=self.policy.max_state_events,
            max_bytes=self.policy.max_metadata_bytes,
        )

        by_subject: dict[str, list[dict[str, Any]]] = {}
        for belief in base.pop("beliefs", []):
            by_subject.setdefault(belief["subject"], []).append(belief)

        focus_state = {}
        entity_roster = []
        for subject in roster:
            rows = by_subject.get(subject, [])
            detailed = {}
            compact = {"id": subject, "last_update": None}
            relations = {}
            inferred = []
            for row in rows:
                predicate = row["predicate"]
                value = _parse_belief_value(predicate, row["object"])
                detailed[predicate] = {
                    "value": value,
                    "observed_at": row["sim_time"],
                    "evidence_id": row["evidence_id"],
                    "epistemic": row["epistemic"],
                }
                if row["epistemic"] != "observed":
                    inferred.append(predicate)
                if compact["last_update"] is None or row["sim_time"] > compact["last_update"]:
                    compact["last_update"] = row["sim_time"]
                if predicate in {"label", "visibility", "location", "confidence", "identity_candidates"}:
                    compact[predicate] = value
                else:
                    relations[predicate] = value
            if relations:
                compact["relations"] = relations
            if inferred:
                compact["inferred_fields"] = sorted(inferred)
            entity_roster.append(compact)
            if subject in focus:
                focus_state[subject] = detailed

        entity_history = {}
        for subject in histories:
            # Preserve several changes for EACH predicate rather than simply the
            # last N database rows. Frequent visibility/confidence updates should
            # not erase an older but important location or containment transition.
            grouped: dict[str, list[dict[str, Any]]] = {}
            for row in self.state.history(subject):
                grouped.setdefault(row["predicate"], []).append(row)
            selected = []
            if self.policy.history_items_per_predicate:
                for predicate_rows in grouped.values():
                    selected.extend(
                        predicate_rows[-self.policy.history_items_per_predicate :]
                    )
            selected.sort(key=lambda row: (row["sim_time"], row["predicate"], row.get("seq", 0)))
            if len(selected) > self.policy.max_history_rows_per_entity:
                raise ContextBudgetExceeded(
                    f"History for {subject} has {len(selected)} retained rows; explicit per-entity "
                    f"limit is {self.policy.max_history_rows_per_entity}. Raise the policy deliberately."
                )
            entity_history[subject] = [
                {
                    "predicate": row["predicate"],
                    "value": _parse_belief_value(row["predicate"], row["object"]),
                    "observed_at": row["sim_time"],
                    "valid_until": row["valid_until"],
                    "evidence_id": row["evidence_id"],
                    "epistemic": row["epistemic"],
                }
                for row in selected
            ]

        runtime = list(runtime_events)
        if self.policy.max_runtime_events:
            runtime = runtime[-self.policy.max_runtime_events :]
        else:
            runtime = []
        runtime_view = [_runtime_event_view(event) for event in runtime]

        coverage = []
        for note in observation_coverage:
            if not isinstance(note, CoverageNote):
                raise ValueError("observation_coverage must contain CoverageNote values")
            coverage.append(
                {
                    "scope_id": note.scope_id,
                    "observed_at": note.observed_at,
                    "coverage": note.coverage,
                    "result": note.result,
                    "evidence_ids": list(note.evidence_ids),
                    "note": note.note,
                }
            )

        def safe_summary(value: Mapping[str, Any] | None) -> dict[str, Any]:
            result = {}
            for key, item in dict(value or {}).items():
                safe = _jsonish(item)
                if safe is not None:
                    result[key] = safe
            return result

        result = {
            "episode": base["episode"],
            "goal": base["goal"],
            "task_ledger": base["task_ledger"],
            "current_images": base["images"],
            "current_focus": focus_state,
            "entity_roster": entity_roster,
            "entity_history": entity_history,
            "navigation": safe_summary(navigation_summary),
            "topology": _topology_view(topology, current_place, self.policy.max_topology_places),
            "observation_coverage": coverage,
            "executors": safe_summary(executor_summary),
            "runtime_events": runtime_view,
            "state_recent_events": base["recent_events"],
            "context_notice": (
                "Broad context by design. Beliefs and histories are fallible; identity "
                "ambiguity and not-observed state must not be converted into certainty. "
                "The harness organizes evidence but leaves semantic judgment to the executive."
            ),
            "context_profile": {
                "roster_entities": len(entity_roster),
                "focus_entities": len(focus_state),
                "detailed_histories": len(entity_history),
                "runtime_events": len(runtime_view),
                "current_images": len(base["images"]),
            },
        }
        size = len(json.dumps(result, allow_nan=False, sort_keys=True).encode())
        if size > self.policy.max_metadata_bytes:
            raise ContextBudgetExceeded(
                f"Rich context uses {size} bytes; explicit limit is "
                f"{self.policy.max_metadata_bytes}. Do not silently prune."
            )
        return result


def attach_rich_memory(
    base: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    policy: RichContextPolicy | None = None,
    provider_check: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    """Attach an offline M1/M2 packet without silently pruning M0 context.

    This helper does not enable memory in the live executive path. It applies
    the declared combined byte/image guards for causal replay and leaves actual
    provider token/tile accounting to ``provider_check``.
    """

    policy = policy or RichContextPolicy()
    if "episodic_memory" in base:
        raise ValueError("Memory already attached")
    cutoff = packet.get("cutoff")
    if not isinstance(cutoff, Mapping) or base.get("episode") != cutoff.get("episode_id"):
        raise ValueError("Current context/memory episode mismatch")

    result = json.loads(encoded(dict(base, episodic_memory=dict(packet))))
    current_images = result.get("current_images", [])
    historical_images = result["episodic_memory"].get("images", [])
    if not isinstance(current_images, list) or not isinstance(historical_images, list):
        raise ValueError("Context image collections must be lists")
    if len(current_images) + len(historical_images) > policy.max_combined_images:
        raise ContextBudgetExceeded("Combined rich context exceeds the image limit")
    if len(encoded(result)) > policy.max_combined_bytes:
        raise ContextBudgetExceeded("Combined rich context exceeds the metadata limit")
    if provider_check is not None and provider_check(result) is not True:
        raise ValueError("Provider text/vision budget rejected context")
    return result


class BroadMemorySelector:
    """High-recall historical retrieval for replay / GPT experiments.

    It unions several transparent retrievals rather than asking a weaker model to
    decide one narrow query.  The source card remains evidence-backed and every
    included card carries a human-readable selection reason.
    """

    def __init__(self, store: Any, policy: RichContextPolicy | None = None):
        self.store = store
        self.policy = policy or RichContextPolicy()
        self.retriever = Retriever(store)

    def packet(
        self,
        cutoff: Cutoff,
        *,
        goal: str,
        focus_entities: Iterable[str] = (),
        current_place: str | None = None,
        include_images: bool = True,
    ) -> dict[str, Any]:
        chosen: dict[str, Hit] = {}
        reasons: dict[str, list[str]] = {}
        query_rank: dict[str, int] = {}

        def add(hits: Iterable[Hit], reason: str) -> None:
            for hit in hits:
                chosen.setdefault(hit.card.card_id, hit)
                reasons.setdefault(hit.card.card_id, []).append(reason)

        for entity_id in tuple(dict.fromkeys(focus_entities)):
            add(
                self.retriever.history(
                    cutoff, entity_id=entity_id, limit=self.policy.memory_entity_cards
                ),
                f"focus_entity:{entity_id}",
            )
        if current_place:
            add(
                self.retriever.history(
                    cutoff, place_id=current_place, limit=self.policy.memory_place_cards
                ),
                f"current_place:{current_place}",
            )
        if goal.strip():
            query_hits = self.retriever.search(
                cutoff, query=goal, limit=self.policy.memory_query_cards
            )
            add(
                query_hits,
                "goal_query",
            )
            query_rank = {
                hit.card.card_id: index for index, hit in enumerate(query_hits)
            }
        add(
            self.retriever.search(
                cutoff, query="", limit=self.policy.memory_recent_cards
            ),
            "recent_history",
        )

        hits = sorted(
            chosen.values(),
            key=lambda hit: (
                query_rank.get(hit.card.card_id, len(query_rank)),
                -hit.card.observed_end,
                hit.card.card_id,
            ),
        )
        if len(hits) > self.policy.memory_max_cards:
            # Quotas above are deliberately generous; if they exceed the explicit
            # experiment cap, fail instead of silently deciding which evidence GPT
            # is not allowed to see.
            raise ContextBudgetExceeded(
                f"Broad memory selection produced {len(hits)} cards; explicit limit is "
                f"{self.policy.memory_max_cards}. Raise the budget or narrow inputs deliberately."
            )

        budget = PacketBudget(
            max_cards=self.policy.memory_max_cards,
            max_images=self.policy.memory_max_images,
            max_pixels=self.policy.memory_max_pixels,
            max_bytes=self.policy.memory_metadata_bytes,
        )
        packet = self.retriever.packet(
            hits, cutoff, budget=budget, include_images=include_images
        )
        visible = {item["card_id"] for item in packet["cards"]}
        packet["selection_reasons"] = {
            card_id: reasons[card_id] for card_id in visible
        }
        packet["selection_policy"] = (
            "union of focus-entity history, current-place history, goal query, "
            "and recent history; lexical query matches first, then event-diverse images; "
            "no learned relevance model"
        )
        if packet.get("omitted_cards"):
            raise ContextBudgetExceeded(
                "Historical packet omitted selected cards to meet metadata budget; "
                "raise the experiment budget or narrow the requested inputs deliberately."
            )
        if len(encoded(packet)) > self.policy.memory_metadata_bytes:
            raise ContextBudgetExceeded("Selection metadata pushed memory packet over budget")
        return packet
