"""Sparse semantic supervision, not a text-only tactical motor or learned router."""
from __future__ import annotations

from dataclasses import dataclass

from physical_harness.core.actions import Intent, ids, integer, number, text
from physical_harness.planning.actions.compiler import Catalog


@dataclass(frozen=True)
class AttentionDecision:
    wake: bool
    reason: str
    action_id: str | None = None


class IntentQueue:
    """Queues semantic goals, never stale metric actions from an earlier scene.

    On each boundary, compile a NEW catalog from current sensors. A deterministic
    selection is allowed only when exactly one eligible candidate matches the
    already-approved current intent. Ambiguity returns to the executive
    success
    is acknowledged by external semantic verification, not by a motion receipt.
    """
    def __init__(self, intents: tuple[Intent, ...]):
        if type(intents) is not tuple or not 1 <= len(intents) <= 32:
            raise ValueError("Bounded immutable intent sequence required")
        if not all(isinstance(i, Intent) for i in intents):
            raise ValueError("Typed intents required")
        self.intents, self.index = intents, 0
        self._verified: set[str] = set()

    def choose(self, catalog: Catalog) -> AttentionDecision:
        if self.index == len(self.intents):
            return AttentionDecision(True, "semantic_program_complete")
        matches = [a for a in catalog.actions if a.eligible and a.program.proposal.intent == self.intents[self.index]]
        if len(matches) == 1:
            return AttentionDecision(False, "unique_candidate_for_approved_intent", matches[0].id)
        return AttentionDecision(True, "no_qualified_candidate" if not matches else "semantic_choice_required")

    def advance(self, *, intent: Intent, verdict: str, verification_id: str,
                evidence_ids: tuple[str, ...]):
        text(verification_id)
        ids(evidence_ids, empty=False)
        if self.index >= len(self.intents) or intent != self.intents[self.index]:
            raise ValueError("Verification does not match current intent")
        if verification_id in self._verified or verdict != "verified":
            raise PermissionError("Fresh independent semantic verification required")
        self._verified.add(verification_id)
        self.index += 1


class EventAttention:
    """Debounces semantic wakes. Safety monitors/controller loops remain continuous."""
    IMPORTANT = frozenset({"skill_failed", "skill_stalled", "target_lost", "world_changed",
                           "state_contradiction", "verifier_uncertain", "plan_exhausted",
                           "execution_timeout", "decision_required", "unqualified_action"})

    def __init__(self, *, heartbeat_s: float = 30., max_events: int = 4096):
        self.heartbeat_s = number(heartbeat_s, low=.001)
        self.max_events = integer(max_events, low=1, high=100000)
        self.last_wake = None
        self.seen = set()

    def consider(self, *, event_id: str, event_type: str, now: float,
                 agenda_has_next: bool = False) -> AttentionDecision:
        text(event_id)
        text(event_type)
        number(now, low=0)
        if self.last_wake is not None and now < self.last_wake:
            raise ValueError("Attention clock regressed")
        if type(agenda_has_next) is not bool:
            raise ValueError("Explicit agenda state required")
        if event_id in self.seen:
            return AttentionDecision(False, "duplicate_event")
        if len(self.seen) >= self.max_events:
            raise RuntimeError("Bounded attention session exhausted; rotate explicitly")
        self.seen.add(event_id)
        wake = event_type in self.IMPORTANT or self.last_wake is None
        if event_type == "skill_verified" and not agenda_has_next:
            wake = True
        if event_type == "heartbeat" and (self.last_wake is None or now-self.last_wake >= self.heartbeat_s):
            wake = True
        if wake:
            self.last_wake = now
        return AttentionDecision(wake, event_type if wake else "local_execution_continues")
