"""Small evidence contracts on top of the existing Action Compiler Basis.

No map, policy, source-of-truth database, simulator or provider is constructed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from physical_harness.core.actions import Basis, digest, ids, integer, number, plain, text


class Effect(str, Enum):
    READ = "read"
    MOTION = "motion"
    REASON = "reason"


def same_episode(a: Basis, b: Basis) -> None:
    """Semantic identity survives localization resets, never episode/robot changes."""
    if not isinstance(a, Basis) or not isinstance(b, Basis):
        raise ValueError("Typed Basis required")
    for k in ("episode", "robot_fingerprint", "domain"):
        if getattr(a, k) != getattr(b, k):
            raise PermissionError("Foreign identity evidence")
    if b.sim_time < a.sim_time or b.captured_wall < a.captured_wall:
        raise PermissionError("Evidence time regressed")


def basis_from_dict(value: dict) -> Basis:
    data = dict(value)
    data["evidence_ids"] = tuple(data["evidence_ids"])
    return Basis(**data)


@dataclass(frozen=True)
class Fact:
    """A compiled observation, not a confidence-as-truth boolean."""
    name: str
    value: bool | str | float | int | None
    basis: Basis
    evidence_ids: tuple[str, ...]
    method: str
    revision: str

    def __post_init__(self):
        text(self.name)
        text(self.method)
        text(self.revision)
        if not isinstance(self.basis, Basis):
            raise ValueError("Fact requires Basis")
        if self.value is not None and type(self.value) not in (str, float, int, bool):
            raise ValueError("Scalar fact required; do not hide sensor objects")
        if type(self.value) in (float, int):
            number(self.value)
        if type(self.value) is str:
            text(self.value, limit=2048)
        ids(self.evidence_ids, empty=False)

    @property
    def fingerprint(self):
        return digest(self)


@dataclass(frozen=True)
class FactPacket:
    basis: Basis
    facts: tuple[Fact, ...]

    def __post_init__(self):
        if not isinstance(self.basis, Basis) or type(self.facts) is not tuple:
            raise ValueError("Typed immutable fact packet required")
        if len(self.facts) > 128 or any(not isinstance(f, Fact) for f in self.facts):
            raise ValueError("Bounded typed facts required")
        ids(tuple(f.name for f in self.facts))
        for f in self.facts:
            self.basis.require_same(f.basis)

    def missing(self, required: tuple[str, ...]) -> tuple[str, ...]:
        ids(required)
        known = {f.name for f in self.facts if f.value is not None}
        return tuple(n for n in required if n not in known)

    def view(self, required: tuple[str, ...]) -> dict:
        if self.missing(required):
            raise PermissionError("Branch-critical facts are unknown")
        return {f.name: plain(f) for f in self.facts if f.name in required}


@dataclass(frozen=True)
class Binding:
    """Late-bound semantic role; no metric pose or stale candidate ID in the graph."""
    role: str
    entity: str
    part: str
    basis: Basis
    identity_evidence: tuple[str, ...]
    unambiguous: bool

    def __post_init__(self):
        for s in (self.role, self.entity, self.part):
            text(s)
        if not isinstance(self.basis, Basis) or type(self.unambiguous) is not bool:
            raise ValueError("Typed current binding required")
        ids(self.identity_evidence, empty=False)


@dataclass(frozen=True)
class Capability:
    id: str
    effect: Effect
    domain: str
    qualification_id: str | None
    qualification_evidence: tuple[str, ...] = ()
    required_roles: tuple[str, ...] = ()
    required_facts: tuple[str, ...] = ()

    def __post_init__(self):
        text(self.id)
        if not isinstance(self.effect, Effect) or self.domain not in {"fixture", "behavior_sim"}:
            raise ValueError("Explicit capability effect/domain required")
        ids(self.qualification_evidence)
        ids(self.required_roles)
        ids(self.required_facts)
        if self.qualification_id is not None:
            text(self.qualification_id)
            if not self.qualification_evidence:
                raise ValueError("Qualification needs evidence")

    def require(self, basis: Basis):
        if self.domain != basis.domain or self.qualification_id is None:
            raise PermissionError("Capability unavailable in this domain")


@dataclass(frozen=True)
class ScopeBudget:
    max_nodes: int = 32
    max_visits: int = 64
    max_repairs: int = 2
    max_wall_s: float = 300.

    def __post_init__(self):
        integer(self.max_nodes, low=1, high=128)
        integer(self.max_visits, low=1, high=1024)
        integer(self.max_repairs, high=16)
        number(self.max_wall_s, low=.001, high=86400)
