"""Offline tool-use scoring. Labels are evaluator-only and never agent context."""
from __future__ import annotations

from physical_harness.core.actions import Basis, ids
from physical_harness.planning.actions.compiler import Catalog


def score_selection(catalog: Catalog, answer, *, acceptable_action_ids: tuple[str, ...],
                    current: Basis, now: float, max_age_s: float = 2) -> dict:
    ids(acceptable_action_ids)
    offered = {a.id for a in catalog.actions if a.eligible}
    if not set(acceptable_action_ids) <= offered:
        raise ValueError("Evaluation label names an unavailable action")
    try:
        action = catalog.resolve(answer, current, now=now, max_age_s=max_age_s)
    except (ValueError, PermissionError) as error:
        return {"valid_tool_use": False, "semantically_acceptable": False,
                "error_type": type(error).__name__, "robot_executed": False}
    return {"valid_tool_use": True, "semantically_acceptable": action.id in acceptable_action_ids,
            "action_id": action.id, "robot_executed": False}
