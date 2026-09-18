from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .backends.base import VerifierBackend, WorldModelBackend
from .contracts import VerificationRequest, VerificationResult, VerificationVerdict


@dataclass
class VerificationPolicy:
    world_verified_threshold: float = 0.90
    world_rejected_threshold: float = 0.10
    cheap_vlm_min_confidence: float = 0.85
    frontier_min_confidence: float = 0.75

    def __post_init__(self):
        for value in vars(self).values():
            _confidence(value)
        if self.world_rejected_threshold >= self.world_verified_threshold:
            raise ValueError("World thresholds must not overlap")


def _confidence(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
    ):
        raise ValueError("Confidence must be finite and in [0,1]")
    return float(value)


def _ids(values) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or any(
        not isinstance(v, str) or not v.strip() for v in values
    ):
        raise ValueError("Evidence IDs must be a sequence of nonempty strings")
    return tuple(values)


def _validate(result: VerificationResult, request: VerificationRequest) -> VerificationResult:
    if not isinstance(result, VerificationResult) or result.request_id != request.request_id:
        raise ValueError("Verifier returned a mismatched request ID")
    _confidence(result.confidence)
    if not isinstance(result.verdict, VerificationVerdict):
        raise ValueError("Verifier returned an invalid verdict")
    _ids(result.evidence_ids)
    if not isinstance(result.verifier, str) or not result.verifier.strip():
        raise ValueError("Verifier name is required")
    return result


class VerificationRouter:
    """Tiered verification.

    Tier 0 deterministic/controller checks should normally be folded into the
    SkillReceipt before this router is called. Tier 1 is world predicates,
    optional Tier 2 is a qualified cheap semantic model, and Tier 3 is strong
    model adjudication. The v0 radio configuration leaves Tier 2 disabled and
    uses GPT-6 at Tier 3 only at semantic boundaries.

    Model verdicts may cite only supplied before/after references. That default
    checks provenance, not existence or freshness. Production callers should
    provide evidence_validator(id, request) to additionally check current episode,
    observational origin, freshness, and contradictions against their store.
    Tier 1 evidence remains the world adapter's responsibility.
    """

    def __init__(
        self,
        world: WorldModelBackend,
        cheap_vlm: VerifierBackend | None = None,
        frontier: VerifierBackend | None = None,
        policy: VerificationPolicy | None = None,
        *,
        evidence_validator: Callable[[str, VerificationRequest], bool] | None = None,
    ):
        self.world = world
        self.cheap_vlm = cheap_vlm
        self.frontier = frontier
        self.policy = policy or VerificationPolicy()
        self.evidence_validator = evidence_validator

    def _supported(self, result: VerificationResult, request: VerificationRequest) -> bool:
        supplied = set(request.before_evidence_ids) | set(request.after_evidence_ids)
        if not result.evidence_ids or any(
            identifier not in supplied for identifier in result.evidence_ids
        ):
            return False
        return self.evidence_validator is None or all(
            self.evidence_validator(identifier, request) is True
            for identifier in result.evidence_ids
        )

    def verify(self, request: VerificationRequest) -> VerificationResult:
        if not isinstance(request.request_id, str) or not request.request_id.strip():
            raise ValueError("Request ID is required")
        if not isinstance(request.skill_id, str) or not request.skill_id.strip():
            raise ValueError("Skill ID is required")
        if not isinstance(request.high_consequence, bool):
            raise ValueError("high_consequence must be boolean")
        _ids(request.expected_predicates)
        _ids(request.before_evidence_ids)
        _ids(request.after_evidence_ids)
        if not request.expected_predicates:
            return VerificationResult(
                request.request_id,
                "router",
                VerificationVerdict.UNCERTAIN,
                0.0,
                explanation="No expected predicates were specified.",
            )
        # Tier 1: all expected predicates are confidently true/false.
        if request.expected_predicates:
            confs = [self.world.predicate_confidence(p) for p in request.expected_predicates]
            for c in confs:
                if c is not None:
                    _confidence(c)
            provider = getattr(self.world, "predicate_evidence", None)
            supports = [
                _ids(provider(p)) if callable(provider) else () for p in request.expected_predicates
            ]
            if not request.high_consequence and all(
                s and c is not None and c >= self.policy.world_verified_threshold
                for c, s in zip(confs, supports)
            ):
                return VerificationResult(
                    request_id=request.request_id,
                    verifier=f"{self.world.name}:predicate",
                    verdict=VerificationVerdict.VERIFIED,
                    confidence=min(float(c) for c in confs if c is not None),
                    evidence_ids=tuple(dict.fromkeys(e for support in supports for e in support)),
                )
            rejected = [
                (c, s)
                for c, s in zip(confs, supports)
                if s and c is not None and c <= self.policy.world_rejected_threshold
            ]
            if not request.high_consequence and rejected:
                return VerificationResult(
                    request_id=request.request_id,
                    verifier=f"{self.world.name}:predicate",
                    verdict=VerificationVerdict.REJECTED,
                    confidence=max(1.0 - float(c) for c, _ in rejected),
                    evidence_ids=tuple(
                        dict.fromkeys(e for _, support in rejected for e in support)
                    ),
                )

        # Tier 2: cheap semantic verifier.
        if self.cheap_vlm is not None:
            r = _validate(self.cheap_vlm.verify(request), request)
            if (
                r.verdict != VerificationVerdict.UNCERTAIN
                and r.confidence >= self.policy.cheap_vlm_min_confidence
                and not request.high_consequence
                and self._supported(r, request)
            ):
                return r

        # Tier 3: strong model adjudication.
        if self.frontier is not None:
            r = _validate(self.frontier.verify(request), request)
            if r.confidence >= self.policy.frontier_min_confidence and (
                r.verdict == VerificationVerdict.UNCERTAIN or self._supported(r, request)
            ):
                return r
            return VerificationResult(
                request_id=request.request_id,
                verifier=r.verifier,
                verdict=VerificationVerdict.UNCERTAIN,
                confidence=r.confidence,
                evidence_ids=r.evidence_ids,
                explanation=r.explanation,
                metadata=r.metadata,
            )

        return VerificationResult(
            request_id=request.request_id,
            verifier="router",
            verdict=VerificationVerdict.UNCERTAIN,
            confidence=0.0,
            explanation="No verifier produced a confident answer.",
        )
