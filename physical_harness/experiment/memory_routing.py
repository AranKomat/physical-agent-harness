"""Deterministic routing for bounded historical-memory tiers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class MemoryTier(StrEnum):
    CURRENT = "M0"
    EVENTS = "M1"
    VISUAL = "M2"


@dataclass(frozen=True)
class InformationNeed:
    """Explicit evidence needs emitted with an executive decision."""

    prior_event: bool = False
    prior_place: bool = False
    failure_or_recovery_history: bool = False
    revisit_comparison: bool = False
    visual_identity_continuity: bool = False
    visual_motion_comparison: bool = False
    visual_appearance_comparison: bool = False
    historical_geometry: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> InformationNeed:
        if not isinstance(value, dict):
            raise ValueError("Information need must be an object")
        unknown = set(value) - set(cls.__dataclass_fields__)
        missing = set(cls.__dataclass_fields__) - set(value)
        if unknown or missing:
            raise ValueError(
                f"Information-need fields mismatch; missing={sorted(missing)}, "
                f"unknown={sorted(unknown)}"
            )
        if any(type(item) is not bool for item in value.values()):
            raise ValueError("Information-need fields must be Boolean")
        return cls(**value)


@dataclass(frozen=True)
class RoutingDecision:
    tier: MemoryTier
    reasons: tuple[str, ...]


VISUAL_FIELDS = (
    "visual_identity_continuity",
    "visual_motion_comparison",
    "visual_appearance_comparison",
    "historical_geometry",
)
EVENT_FIELDS = (
    "prior_event",
    "prior_place",
    "failure_or_recovery_history",
    "revisit_comparison",
)
INFORMATION_NEED_SCHEMA = {
    "type": "object",
    "properties": {field: {"type": "boolean"} for field in (*EVENT_FIELDS, *VISUAL_FIELDS)},
    "required": [*EVENT_FIELDS, *VISUAL_FIELDS],
    "additionalProperties": False,
}


def route_memory_tier(need: InformationNeed) -> RoutingDecision:
    """Return the least capable tier satisfying the declared information need."""

    values = asdict(need)
    visual = tuple(field for field in VISUAL_FIELDS if values[field])
    if visual:
        return RoutingDecision(MemoryTier.VISUAL, visual)
    events = tuple(field for field in EVENT_FIELDS if values[field])
    if events:
        return RoutingDecision(MemoryTier.EVENTS, events)
    return RoutingDecision(MemoryTier.CURRENT, ("current_context_only",))
