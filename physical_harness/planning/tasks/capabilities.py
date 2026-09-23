"""Versioned, qualified semantic macros using Situated Graph, never saved trajectories.

The artifact is a graph over registered handlers. Promotion is an explicit review
operation, not "three successes => safe" and not runtime self-modification.
"""
from __future__ import annotations

from dataclasses import dataclass

from physical_harness.core.actions import Basis, digest, ids, integer, plain, text
from physical_harness.core.tasks import Capability, ScopeBudget
from physical_harness.planning.tasks.graph import Graph, Node


@dataclass(frozen=True)
class CapabilityMacro:
    name: str
    version: str
    graph: Graph
    parameters: tuple[str, ...]
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...]
    deployment_fingerprint: str

    def __post_init__(self):
        for s in (self.name, self.version, self.deployment_fingerprint):
            text(s)
        if not isinstance(self.graph, Graph):
            raise ValueError("Existing validated semantic Graph required")
        ids(self.parameters)
        ids(self.preconditions)
        ids(self.postconditions, empty=False)
        roles = {r for n in self.graph.nodes for r in n.roles}
        if not roles <= set(self.parameters):
            raise ValueError("Graph contains undeclared role parameters")

    @property
    def fingerprint(self):
        return digest(self)


@dataclass(frozen=True)
class Promotion:
    macro_fingerprint: str
    deployment_fingerprint: str
    domain: str
    review_id: str
    reviewer: str
    evidence_ids: tuple[str, ...]
    level: str  # evidence category, NOT an ordinal certification ladder
    native_enabled: bool

    def __post_init__(self):
        for s in (self.macro_fingerprint, self.deployment_fingerprint, self.review_id, self.reviewer):
            text(s)
        if self.domain not in {"fixture", "behavior_sim"}:
            raise PermissionError("Real robot macros are outside this delivery")
        if self.level not in {"software", "retained_replay", "sim_native_reviewed"}:
            raise ValueError("Explicit qualification evidence category required")
        ids(self.evidence_ids, empty=False)
        if type(self.native_enabled) is not bool:
            raise ValueError("Explicit native permission required")
        if self.native_enabled and self.domain != "fixture" and self.level != "sim_native_reviewed":
            raise PermissionError("Offline tests cannot promote native motion")


class MacroRegistry:
    def __init__(self, *, journal, deployment_fingerprint: str):
        text(deployment_fingerprint)
        self.journal, self.deployment = journal, deployment_fingerprint
        self.macros: dict[str, CapabilityMacro] = {}
        self.promotions: dict[str, Promotion] = {}

    def register(self, macro: CapabilityMacro):
        if macro.deployment_fingerprint != self.deployment:
            raise PermissionError("Macro belongs to a different deployment")
        key = macro.name+"@"+macro.version
        if key in self.macros:
            raise PermissionError("Immutable macro version already registered")
        self.macros[key] = macro
        # Replay approval only if exactly this artifact/configuration was reviewed.
        for r in self.journal.records("embodied_macro_promotion"):
            if r["macro_fingerprint"] == macro.fingerprint:
                d = {k:v for k,v in r.items() if k in Promotion.__dataclass_fields__}
                d["evidence_ids"] = tuple(d["evidence_ids"])
                self.promotions[key] = Promotion(**d)

    def promote(self, key: str, promotion: Promotion, *, operator_review):
        macro = self.macros[key]
        if (promotion.macro_fingerprint, promotion.deployment_fingerprint) != (macro.fingerprint, self.deployment):
            raise PermissionError("Promotion doesn't match exact code/config")
        if operator_review(macro, promotion) is not True:
            raise PermissionError("Explicit external qualification review required")
        self.journal.put("embodied_macro_promotion", digest(promotion), plain(promotion))
        self.promotions[key] = promotion

    def available(self, key: str, *, basis: Basis, capabilities: dict[str, Capability],
                  facts, bindings) -> Graph:
        macro = self.macros[key]
        promotion = self.promotions.get(key)
        if promotion is None or promotion.domain != basis.domain or not promotion.native_enabled:
            raise PermissionError("Macro isn't enabled for this execution domain")
        facts.basis.require_same(basis)
        if facts.missing(macro.preconditions):
            raise PermissionError("Macro preconditions are unknown")
        # Boolean preconditions must be true, not merely present.
        values = {f.name:f.value for f in facts.facts}
        if any(values.get(k) is not True for k in macro.preconditions):
            raise PermissionError("Macro preconditions not established")
        if set(bindings) != set(macro.parameters):
            raise ValueError("Explicit complete role binding required")
        for role, binding in bindings.items():
            basis.require_same(binding.basis)
            if binding.role != role or not binding.unambiguous:
                raise PermissionError("Macro role is ambiguous or stale")
        for n in macro.graph.nodes:
            if n.kind == "done":
                continue
            c = capabilities.get(n.capability)
            if c is None:
                raise PermissionError("Macro handler unavailable: " + n.capability)
            c.require(basis)
        return macro.graph  # Run through the EXISTING GraphSession and independent ledger.

    def view(self) -> tuple[dict, ...]:
        return tuple({"id": k, "name": m.name, "version": m.version,
                      "parameters": m.parameters, "preconditions": m.preconditions,
                      "postconditions": m.postconditions, "graph": m.graph.fingerprint,
                      "qualification": plain(self.promotions[k]) if k in self.promotions else None,
                      "promotion_enabled": k in self.promotions and self.promotions[k].native_enabled,
                      "requires_current_admission": True}
                     for k,m in sorted(self.macros.items()))


def standard_macro(name: str, *, deployment: str, version: str = "1") -> CapabilityMacro:
    """Six reusable orchestration recipes; handlers remain external qualified skills.

    Missing opening/elevator mechanics are NOT advertised. These templates are
    unqualified until independently promoted against the actual robot ports.
    """
    recipes = {
        "go_to": (("target",), ("locate", "navigate", "verify_arrival"), ("arrived",)),
        "inspect": (("target",), ("locate", "choose_view", "inspect", "verify_information"), ("information_resolved",)),
        "pick": (("target",), ("locate", "navigate", "stage", "compile_grasp", "grasp", "verify_grasp"), ("held",)),
        "place": (("payload", "destination"), ("locate_destination", "navigate", "compile_place", "place", "verify_release"), ("placed",)),
        "press": (("target",), ("locate_part", "stage", "compile_press", "press", "verify_outcome"), ("outcome_observed",)),
        "pull_prismatic": (("target",), ("locate_handle", "verify_axis", "stage", "pull", "verify_outcome"), ("outcome_observed",)),
    }
    if name not in recipes:
        raise ValueError("No qualified macro implementation for that mechanism")
    roles, steps, post = recipes[name]
    motion = {"navigate", "stage", "grasp", "place", "press", "pull", "inspect"}
    nodes = []
    for i, step in enumerate(steps):
        identifier = "n"+str(i)
        next_id = "n"+str(i+1) if i+1 < len(steps) else "done"
        nodes.append(Node(identifier, "act" if step in motion else "observe", "macro."+step,
                          roles=roles, required_facts=(), transitions=(("ok", next_id), ("unknown", "repair"),
                          ("failed", "repair"), ("blocked", "repair")), max_wall_s=30., max_visits=2,
                          purpose="Late-bind live evidence; no stored scene coordinates."))
    nodes.append(Node("repair", "reason", "executive.repair", roles, (), (), 30., 1,
                      "Return control to the embodied executive; no automatic native retry."))
    nodes.append(Node("done", "done", "existing_task_ledger"))
    graph = Graph("macro."+name+"."+version, "n0", tuple(nodes), ScopeBudget(max_nodes=32, max_visits=32, max_repairs=1, max_wall_s=300))
    return CapabilityMacro(name, version, graph, roles, ("robot_ready",), post, deployment)


def compile_graph_fragment(*, name: str, version: str, graph: Graph, roles: tuple[str, ...],
                           preconditions: tuple[str, ...], postconditions: tuple[str, ...],
                           deployment: str, max_visits: int = 64) -> CapabilityMacro:
    """Freeze an already validated semantic graph as an unqualified reusable artifact."""
    integer(max_visits, low=1, high=1024)
    if graph.budget.max_visits > max_visits:
        raise PermissionError("Graph exceeds operator scope")
    return CapabilityMacro(name, version, graph, roles, preconditions, postconditions, deployment)
