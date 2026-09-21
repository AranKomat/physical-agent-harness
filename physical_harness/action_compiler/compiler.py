"""Geometry proposals -> reviewed programs -> bounded model-facing action catalog."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .primitives import TemplateConfig, compile_program
from .types import (
    Basis,
    Check,
    Gripper,
    Program,
    Proposal,
    Review,
    digest,
    encode,
    ids,
    integer,
    number,
    plain,
    strict_loads,
    text,
)


@dataclass(frozen=True)
class CompiledAction:
    program: Program
    review: Review | None
    rejected_checks: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.program, Program):
            raise ValueError("Typed compiled program required")
        ids(self.rejected_checks)
        if self.review is not None and not isinstance(self.review, Review):
            raise ValueError("Typed review required")
        if not self.rejected_checks and self.review is None:
            raise ValueError("Unreviewed action cannot be eligible")
        if not self.rejected_checks and self.review.failures(self.program, self.program.proposal.basis):
            raise ValueError("Review does not authorize this candidate")

    @property
    def id(self):
        return self.program.proposal.id

    @property
    def eligible(self):
        return not self.rejected_checks


@dataclass(frozen=True)
class Catalog:
    basis: Basis
    gripper_fingerprint: str
    actions: tuple[CompiledAction, ...]
    expires_wall: float
    omitted_count: int = 0

    def __post_init__(self):
        if not isinstance(self.basis, Basis):
            raise ValueError("Typed catalog basis required")
        text(self.gripper_fingerprint)
        if type(self.actions) is not tuple or len(self.actions) > 64:
            raise ValueError("Bounded immutable catalog required")
        ids(tuple(a.id for a in self.actions))
        for a in self.actions:
            self.basis.require_same(a.program.proposal.basis)
            if a.program.proposal.gripper_fingerprint != self.gripper_fingerprint:
                raise ValueError("Mixed gripper embodiments in catalog")
        number(self.expires_wall, low=self.basis.captured_wall)
        integer(self.omitted_count)

    @property
    def id(self):
        return "catalog:"+digest(self)[:32]

    def view(self, *, max_bytes: int = 32000) -> dict:
        """Keep image evidence for semantics; do not flood context with point clouds.

        Metric parameters intentionally omitted. Object/part descriptions are
        untrusted observations, never instructions to override the tool contract.
        """
        integer(max_bytes, low=100, high=1000000)
        result = {"catalog_id": self.id, "observation_id": self.basis.observation_id,
                  "evidence_ids": list(self.basis.evidence_ids), "omitted_count": self.omitted_count,
                  "notice": "Select a listed eligible ID. Scores are not calibrated success probabilities.",
                  "actions": [{"action_id": a.id, "intent": plain(a.program.proposal.intent),
                               "eligible": a.eligible, "blocked_by": list(a.rejected_checks),
                               "generator": a.program.proposal.generator,
                               "score": a.program.proposal.score,
                               "score_kind": a.program.proposal.score_kind,
                               "parameter_count_exposed_to_model": 0,
                               "max_robot_steps": a.program.max_steps,
                               "evidence_ids": list(a.program.proposal.evidence_ids)} for a in self.actions]}
        if len(encode(result)) > max_bytes:
            raise ValueError("Catalog context budget exceeded; split explicitly, never silently truncate")
        return result

    def tool_schema(self) -> dict:
        allowed = [a.id for a in self.actions if a.eligible]
        if not allowed:
            raise PermissionError("No eligible actions; inspect/repair qualification rather than ask for motion")
        return {"type": "function", "name": "select_compiled_action",
                "description": "Select an offered interaction, not coordinates, code or safety overrides.",
                "parameters": {"type": "object", "additionalProperties": False,
                               "properties": {"catalog_id": {"type": "string", "enum": [self.id]},
                                              "action_id": {"type": "string", "enum": allowed}},
                               "required": ["catalog_id", "action_id"]}}

    def resolve(self, selection: dict | str | bytes, current: Basis, *, now: float,
                max_age_s: float = 2.) -> CompiledAction:
        if isinstance(selection, (str, bytes)):
            selection = strict_loads(selection, max_bytes=4096)
        if type(selection) is not dict or set(selection) != {"catalog_id", "action_id"}:
            raise ValueError("Only catalog_id and action_id are accepted; metric overrides are forbidden")
        if selection["catalog_id"] != self.id:
            raise PermissionError("Wrong or stale catalog ID")
        self.basis.require_same(current)
        current.fresh(now, max_age_s)
        if now >= self.expires_wall:
            raise PermissionError("Candidate catalog expired")
        result = next((a for a in self.actions if a.id == selection["action_id"]), None)
        if result is None or not result.eligible:
            raise PermissionError("Unknown, blocked or unqualified action")
        return result


class ReviewEngine:
    """Compose named native reviewers; absent checks become UNKNOWN.

    Check callbacks inspect actual swept trajectories, contact envelope, robot
    state and evidence. A list of asserted labels is not a substitute. No model
    tool can register a check. Use the same instance again immediately before
    dispatch and qualify online per-step monitoring separately.
    """
    def __init__(self, *, qualification_id: str, domain: str,
                 checks: dict[str, Callable], clock=time.monotonic):
        self.qualification_id = text(qualification_id)
        if domain not in {"fixture", "behavior_sim"}:
            raise ValueError("Invalid review domain")
        for name, fn in checks.items():
            text(name)
            if not callable(fn):
                raise ValueError("Callable reviewer required")
        self.domain, self.checks, self.clock = domain, dict(checks), clock

    def __call__(self, program: Program, basis: Basis, deadline: float) -> Review:
        if basis.domain != self.domain:
            raise PermissionError("Fixture reviewers cannot approve BEHAVIOR actions")
        values = []
        for name in program.required_checks:
            if self.clock() >= deadline:
                raise TimeoutError("Feasibility review deadline")
            callback = self.checks.get(name)
            value = callback(program, basis, deadline) if callback else Check(
                name, None, basis.evidence_ids, "Native reviewer is not installed/qualified")
            if not isinstance(value, Check) or value.name != name:
                raise ValueError("Reviewer returned mismatched check")
            values.append(value)
        if self.clock() >= deadline:
            raise TimeoutError("Discard late feasibility review")
        return Review(program.fingerprint, basis.fingerprint, self.qualification_id,
                      self.domain, tuple(values))


def compile_catalog(*, basis: Basis, proposals: tuple[Proposal, ...], gripper: Gripper,
                    template: TemplateConfig, review: Callable, deadline: float,
                    ttl_s: float = 2, max_candidates: int = 32, clock=time.monotonic,
                    emit: Callable | None = None) -> Catalog:
    """Compile all supplied verbs together; never auto-execute or call a VLM.

    Unknown feasibility stays blocked. Template errors are visible exceptions
    the caller should log them rather than silently relabeling a tool as safe.
    """
    number(ttl_s, low=.001, high=120)
    integer(max_candidates, low=1, high=64)
    if type(proposals) is not tuple or len(proposals) > 256:
        raise ValueError("Bounded proposal tuple required")
    ids(tuple(p.id for p in proposals), limit=256)
    actions = []
    # Preserve input intent ordering; do not compare incomparable model scores.
    for p in proposals[:max_candidates]:
        if clock() >= deadline:
            raise TimeoutError("Compilation deadline")
        basis.require_same(p.basis)
        program = compile_program(p, gripper, template)
        result = review(program, basis, deadline)
        if not isinstance(result, Review):
            raise ValueError("Typed feasibility review required")
        bad = result.failures(program, basis)
        action = CompiledAction(program, result, bad)
        actions.append(action)
        if emit:
            emit("candidate_review", {"action_id": action.id, "program": program.fingerprint,
                                      "basis": basis.fingerprint, "review": plain(result),
                                      "eligible": action.eligible})
    if clock() >= deadline:
        raise TimeoutError("Compilation deadline")
    return Catalog(basis, gripper.fingerprint, tuple(actions), basis.captured_wall+ttl_s,
                   max(0, len(proposals)-max_candidates))
