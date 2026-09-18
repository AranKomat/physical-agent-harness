from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from .state import ContextBudgetExceeded, WorldState


def _summary(value: dict[str, Any] | None, allowed: set[str]) -> dict[str, Any]:
    """Project only declared scalar fields, never arbitrary metadata or traces."""
    result = {}
    for key, item in (value or {}).items():
        if key not in allowed:
            continue
        if item is None or isinstance(item, (str, bool, int, float)):
            result[key] = item
        elif isinstance(item, (list, tuple)) and all(isinstance(v, str) for v in item):
            result[key] = list(item)
    return result


@dataclass
class ContextPolicy:
    max_images: int = 4
    max_events: int = 5
    max_bytes: int = 12000


class ContextProjector:
    def __init__(self, state: WorldState, policy: ContextPolicy | None = None):
        self.state = state
        self.policy = policy or ContextPolicy()

    def build(
        self,
        *,
        goal: str,
        relevant_entities: Iterable[str],
        image_evidence: list[str],
        navigation_summary: dict[str, Any] | None = None,
        executor_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        base = self.state.project(
            goal,
            relevant_entities,
            image_evidence,
            max_images=self.policy.max_images,
            max_events=self.policy.max_events,
            max_bytes=self.policy.max_bytes,
        )
        base["navigation"] = _summary(
            navigation_summary,
            {
                "nav_id",
                "status",
                "outcome",
                "destination",
                "target_entity",
                "reached_region",
                "blocking_entity",
                "distance_remaining_m",
                "semantic_waypoints",
                "evidence_ids",
                "current_place",
            },
        )
        base["executors"] = _summary(
            executor_summary,
            {
                "skill_id",
                "backend",
                "status",
                "outcome",
                "policy_calls",
                "chunks_generated",
                "action_steps_executed",
                "evidence_ids",
                "observed_predicates",
                "execution_epoch",
                "remaining_budget",
            },
        )
        size = len(json.dumps(base, allow_nan=False, sort_keys=True).encode("utf-8"))
        if size > self.policy.max_bytes:
            raise ContextBudgetExceeded(
                f"Final context uses {size} bytes; budget {self.policy.max_bytes}"
            )
        return base
