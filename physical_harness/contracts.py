from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class EventType(str, Enum):
    SKILL_VERIFIED = "skill_verified"
    SKILL_FAILED = "skill_failed"
    SKILL_STALLED = "skill_stalled"
    TARGET_LOST = "target_lost"
    STATE_CONTRADICTION = "state_contradiction"
    VERIFIER_UNCERTAIN = "verifier_uncertain"
    PRECONDITION_VIOLATED = "precondition_violated"
    PLAN_EXHAUSTED = "plan_exhausted"
    DECISION_REQUIRED = "decision_required"
    EXECUTION_TIMEOUT = "execution_timeout"
    ARRIVED = "arrived"
    PATH_BLOCKED = "path_blocked"
    DOOR_BLOCKED = "door_blocked"
    WORLD_CHANGED = "world_changed"


@dataclass(frozen=True)
class RuntimeEvent:
    type: EventType
    episode_id: str
    sim_time: float
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    wall_time: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SkillRequest:
    skill_id: str
    skill_type: str
    instruction: str
    target_entities: tuple[str, ...] = ()
    destination_entity: str | None = None
    expected_predicates: tuple[str, ...] = ()
    resources: frozenset[str] = frozenset({"base", "left_arm", "right_arm"})
    max_wall_s: float = 30.0
    max_policy_chunks: int = 30
    source_observation_id: str = ""
    execution_epoch: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillReceipt:
    skill_id: str
    backend: str
    outcome: str  # completed | failed | stalled | timeout | cancelled
    sim_time_start: float
    sim_time_end: float
    policy_calls: int = 0
    chunks_generated: int = 0
    action_steps_executed: int = 0
    evidence_ids: tuple[str, ...] = ()
    observed_predicates: tuple[str, ...] = ()
    failure_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class VerificationVerdict(str, Enum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class VerificationRequest:
    request_id: str
    skill_id: str
    expected_predicates: tuple[str, ...]
    before_evidence_ids: tuple[str, ...] = ()
    after_evidence_ids: tuple[str, ...] = ()
    relevant_entities: tuple[str, ...] = ()
    high_consequence: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationResult:
    request_id: str
    verifier: str
    verdict: VerificationVerdict
    confidence: float
    evidence_ids: tuple[str, ...] = ()
    explanation: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NavigationRequest:
    nav_id: str
    destination: str
    target_entity: str | None = None
    semantic_waypoints: tuple[str, ...] = ()
    max_wall_s: float = 120.0
    allow_exploration: bool = True
    execution_epoch: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NavigationReceipt:
    nav_id: str
    outcome: str  # arrived | blocked | target_not_found | timeout | cancelled
    reached_region: str | None = None
    evidence_ids: tuple[str, ...] = ()
    blocking_entity: str | None = None
    distance_remaining_m: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
