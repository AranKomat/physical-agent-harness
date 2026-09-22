"""Model-authored semantic graphs: typed skills, bounded cycles, no Python/coordinates."""
from __future__ import annotations

from dataclasses import dataclass

from ..action_compiler.types import digest, encode, ids, integer, number, plain, strict_loads, text
from .contracts import Effect, ScopeBudget

KINDS = {"observe": Effect.READ, "monitor": Effect.READ, "decide": Effect.REASON,
         "reason": Effect.REASON, "act": Effect.MOTION}
OUTCOMES = frozenset({"ok", "complete", "unknown", "blocked", "failed", "escalate"})


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    capability: str
    roles: tuple[str, ...] = ()
    required_facts: tuple[str, ...] = ()
    transitions: tuple[tuple[str, str], ...] = ()
    max_wall_s: float = 30.
    max_visits: int = 3
    purpose: str = ""

    def __post_init__(self):
        text(self.id)
        if self.kind not in set(KINDS) | {"done"}:
            raise ValueError("Unknown node kind")
        if self.kind == "done":
            if self.capability != "existing_task_ledger" or self.transitions:
                raise ValueError("Done requires the independent ledger and has no edges")
        else:
            text(self.capability)
        ids(self.roles)
        ids(self.required_facts)
        if type(self.transitions) is not tuple or len(self.transitions) > len(OUTCOMES):
            raise ValueError("Bounded outcome edges required")
        if any(type(e) is not tuple or len(e) != 2 for e in self.transitions):
            raise ValueError("Typed outcome/next-node edge required")
        ids(tuple(e[0] for e in self.transitions))
        for outcome, target in self.transitions:
            if outcome not in OUTCOMES:
                raise ValueError("Unknown outcome label")
            text(target)
        number(self.max_wall_s, low=.001, high=3600)
        integer(self.max_visits, low=1, high=32)
        if not isinstance(self.purpose, str) or len(self.purpose.encode()) > 2048:
            raise ValueError("Bounded untrusted purpose text required")

    def next(self, outcome):
        return dict(self.transitions).get(outcome)


@dataclass(frozen=True)
class Graph:
    id: str
    entry: str
    nodes: tuple[Node, ...]
    budget: ScopeBudget = ScopeBudget()
    schema_version: str = "situated-graph/1"

    def __post_init__(self):
        text(self.id)
        text(self.entry)
        if self.schema_version != "situated-graph/1" or not isinstance(self.budget, ScopeBudget):
            raise ValueError("Unsupported graph schema")
        if type(self.nodes) is not tuple or not 1 <= len(self.nodes) <= self.budget.max_nodes:
            raise ValueError("Bounded immutable graph nodes required")
        if any(not isinstance(n, Node) for n in self.nodes):
            raise ValueError("Typed nodes required")
        ids(tuple(n.id for n in self.nodes))
        names = {n.id for n in self.nodes}
        if self.entry not in names or not any(n.kind == "done" for n in self.nodes):
            raise ValueError("Entry and ledger-verified terminal required")
        for n in self.nodes:
            if any(dest not in names for _, dest in n.transitions):
                raise ValueError("Dangling edge")
        reachable = {self.entry}
        for _ in self.nodes:
            reachable.update(dest for n in self.nodes if n.id in reachable for _, dest in n.transitions)
        if reachable != names:
            raise ValueError("Unreachable nodes are not part of an executable graph")

    @property
    def fingerprint(self):
        return digest(self)

    def node(self, name):
        return next(n for n in self.nodes if n.id == name)

    @classmethod
    def parse(cls, value):
        raw = strict_loads(encode(value) if isinstance(value, dict) else value, max_bytes=64000)
        if set(raw) != {"id", "entry", "nodes", "budget", "schema_version"}:
            raise ValueError("Graph fields are strict; scripts, poses and safety overrides are forbidden")
        if type(raw["nodes"]) is not list or type(raw["budget"]) is not dict:
            raise ValueError("JSON node list/budget required")
        if set(raw["budget"]) != {"max_nodes", "max_visits", "max_repairs", "max_wall_s"}:
            raise ValueError("Strict budget fields required")
        nodes = []
        for n in raw["nodes"]:
            if type(n) is not dict or set(n) != {"id", "kind", "capability", "roles", "required_facts", "transitions", "max_wall_s", "max_visits", "purpose"}:
                raise ValueError("Strict node fields required")
            if any(type(n[k]) is not list for k in ("roles", "required_facts", "transitions")):
                raise ValueError("Node vectors must be JSON arrays")
            nodes.append(Node(**dict(n, roles=tuple(n["roles"]), required_facts=tuple(n["required_facts"]),
                                     transitions=tuple(tuple(e) for e in n["transitions"]))))
        return cls(raw["id"], raw["entry"], tuple(nodes), ScopeBudget(**raw["budget"]), raw["schema_version"])


def authoring_context(capabilities, *, task: str) -> dict:
    """No provider call. Feed through the existing budgeted model transport."""
    text(task, limit=4096)
    return {"task": task, "capabilities": [plain(c) for c in capabilities],
            "schema_version": "situated-graph/1", "instructions": (
                "Use only registered capabilities. Store semantic roles and dependencies, "
                "not object-instance IDs, metric poses, trajectories, detector scores or Python. "
                "Ground each role from current sensors when its node executes. Include unknown "
                "and failed routes. If identity is branch-critical and uncertain, acquire a "
                "discriminating view before irreversible interaction. No digital twin is assumed. "
                "Finish only through the existing independent task ledger.")}
