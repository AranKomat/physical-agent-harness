"""Thin bridges to the existing catalog, ActionExecutor, WorldState and event bus."""
from __future__ import annotations

from physical_harness.core.actions import Basis, Intent, ids
from physical_harness.core.tasks import Binding, basis_from_dict
from physical_harness.execution.actions import ActionExecutor, ExecutionResult
from physical_harness.execution.graph import NodeContext, NodeResult
from physical_harness.planning.actions.compiler import Catalog


class CatalogActionHandler:
    """Late binding occurs for EACH graph act node, never once for the whole plan.

    All metric work is owned by compile_current. A selector receives only the
    current catalog; absent a selector, only a unique eligible match executes.
    This class does not create a JobManager or nested HybridExecutor.
    """
    def __init__(self, *, executor: ActionExecutor, resolve_intent, compile_current,
                 select=None, max_steps=2000):
        from physical_harness.core.actions import integer
        if not isinstance(executor, ActionExecutor):
            raise ValueError("Use the existing ActionExecutor")
        if not callable(resolve_intent) or not callable(compile_current):
            raise ValueError("Semantic resolver and current compiler required")
        if select is not None and not callable(select):
            raise ValueError("Optional bounded selector must be callable")
        integer(max_steps, low=1, high=100000)
        self.executor, self.resolve, self.compile = executor, resolve_intent, compile_current
        self.select, self.max_steps = select, max_steps

    def __call__(self, ctx: NodeContext) -> NodeResult:
        intent = self.resolve(ctx)
        if not isinstance(intent, Intent):
            raise ValueError("Typed semantic intent required")
        if intent.entity not in {b.entity for b in ctx.bindings if b.unambiguous}:
            raise PermissionError("Action target is not a current role binding")
        catalog = self.compile(intent, ctx.basis, ctx.deadline)
        if not isinstance(catalog, Catalog):
            raise ValueError("Current catalog required")
        ctx.basis.require_same(catalog.basis)
        choices = [a for a in catalog.actions if a.eligible and a.program.proposal.intent == intent]
        if not choices or (len(choices) != 1 and self.select is None):
            return NodeResult(ctx.invocation_id, ctx.basis, ctx.basis, "unknown", ctx.basis.evidence_ids,
                              True, execution_ref="not_dispatched")
        if self.select:
            selected = self.select(ctx, catalog.view(), catalog.tool_schema())
        else:
            selected = {"catalog_id": catalog.id, "action_id": choices[0].id}
        action = catalog.resolve(selected, ctx.basis, now=self.executor.clock(),
                                 max_age_s=self.executor.max_age)
        if action not in choices:
            raise PermissionError("Selection changed the graph's semantic intent")
        remaining = ctx.deadline-self.executor.clock()
        if remaining <= 0:
            raise TimeoutError("No remaining action budget")
        result = self.executor.execute(catalog, selected, max_steps=self.max_steps,
                                       max_wall_s=remaining)
        if not isinstance(result, ExecutionResult):
            raise ValueError("Existing executor result required")
        evidence = tuple(dict.fromkeys(e for r in result.receipts for e in r.evidence_ids)) or result.after.evidence_ids
        return NodeResult(ctx.invocation_id, result.before, result.after,
                          "ok" if result.outcome == "completed" else "failed", evidence,
                          result.stop_acknowledged, result.native_steps, result.attempt_id)


def identity_binding(ledger, *, role: str, entity: str, part: str, current: Basis,
                     require_semantics: bool = True) -> Binding:
    """Active inspection can resolve uncertain CATEGORY without claiming identity ambiguity away."""
    state = ledger.state(entity)
    current.require_same(basis_from_dict(state["last_basis"]))
    if require_semantics:
        value = ledger.binding(entity, current)
        evidence = tuple(value["canonical"]["evidence_ids"] + value["association_evidence"])
    else:
        if state["visibility"] != "visible" or state["association"] not in {"new_instance", "established"}:
            raise PermissionError("Active inspection still needs a current tracked instance")
        current.require_same(basis_from_dict(state["last_track"]["basis"]))
        evidence = tuple(state["association_evidence"])
    evidence = tuple(dict.fromkeys(evidence))
    ids(evidence, empty=False)
    return Binding(role, entity, part, current, evidence, True)


def publish_monitor_event(signal, bus):
    """Advisory events only. Completion does not create a SKILL_VERIFIED event."""
    from physical_harness.core.events import EventType, RuntimeEvent
    event_map = {"target_lost": EventType.TARGET_LOST, "skill_failed": EventType.SKILL_FAILED,
                 "verifier_uncertain": EventType.VERIFIER_UNCERTAIN,
                 "subgoal_complete": EventType.DECISION_REQUIRED}
    event_type = event_map.get(signal.event_type)
    if event_type is None:
        return None  # Local progress/shadow results stay out of executive wake traffic.
    event = RuntimeEvent(event_type, signal.basis.episode, signal.basis.sim_time,
                         {"reason": signal.event_type, "command_id": signal.command_id,
                          "evidence_ids": list(signal.evidence_ids),
                          "semantic_authority": "advisory_only"}, event_id=signal.event_id)
    bus.publish(event)
    return event
