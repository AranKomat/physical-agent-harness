"""Sequential semantic graph execution above existing actuator ownership.

No parallel actuator writers. A callback must bound itself or run under the
existing supervised process bridge. Timeout is NOT a physical stop receipt.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace

from physical_harness.core.actions import Basis, digest, ids, number, plain, text
from physical_harness.core.tasks import Binding, Capability, Effect, FactPacket, ScopeBudget
from physical_harness.planning.tasks.graph import KINDS, OUTCOMES, Graph, Node


@dataclass(frozen=True)
class NodeContext:
    node: Node
    basis: Basis
    bindings: tuple[Binding, ...]
    facts: FactPacket
    deadline: float
    invocation_id: str


@dataclass(frozen=True)
class NodeResult:
    invocation_id: str
    before: Basis
    after: Basis
    outcome: str
    evidence_ids: tuple[str, ...]
    stop_acknowledged: bool
    native_steps: int = 0
    execution_ref: str | None = None

    def require(self, ctx: NodeContext, effect: Effect, dt: float):
        from physical_harness.core.actions import integer
        if self.invocation_id != ctx.invocation_id:
            raise PermissionError("Foreign node result")
        ctx.basis.require_same(self.before)
        self.before.require_continuity(self.after)
        ids(self.evidence_ids, empty=False)
        integer(self.native_steps)
        if self.outcome not in OUTCOMES or self.stop_acknowledged is not True:
            raise PermissionError("Unknown outcome or unresolved stop")
        if effect != Effect.MOTION:
            if self.native_steps != 0 or self.before.sim_time != self.after.sim_time:
                raise PermissionError("Read/reason node may not advance physics")
        else:
            if not self.execution_ref:
                raise PermissionError("Motion requires an existing executor receipt reference")
            if abs(self.after.sim_time-self.before.sim_time-self.native_steps*dt) > 1e-5:
                raise ValueError("Unaccounted graph motion steps")
            if self.native_steps and self.after.observation_id == self.before.observation_id:
                raise ValueError("Motion reused a pre-action capture")


@dataclass(frozen=True)
class Handler:
    capability: Capability
    call: object

    def __post_init__(self):
        if not isinstance(self.capability, Capability) or not callable(self.call):
            raise ValueError("Explicit capability and native handler required")


class GraphSession:
    KIND = "situated_graph"

    def __init__(self, *, graph: Graph, session_id: str, journal, handlers: dict[str, Handler],
                 quiescent, stop, finish_allowed, clock=time.monotonic,
                 max_age_s=2., control_dt=1/30, budget_limit: ScopeBudget = ScopeBudget()):
        text(session_id)
        if not isinstance(graph, Graph) or not isinstance(budget_limit, ScopeBudget):
            raise ValueError("Typed graph and operator budget ceiling required")
        for name in ("max_nodes", "max_visits", "max_repairs", "max_wall_s"):
            if getattr(graph.budget, name) > getattr(budget_limit, name):
                raise PermissionError("Graph exceeds the operator budget ceiling")
        if not all(callable(x) for x in (quiescent, stop, finish_allowed, clock)):
            raise ValueError("Real ownership, stop and ledger callbacks required")
        self.graph, self.session_id, self.journal = graph, session_id, journal
        self.handlers = dict(handlers)
        self.quiescent, self.stop, self.finish_allowed, self.clock = quiescent, stop, finish_allowed, clock
        self.max_age = number(max_age_s, low=.001)
        self.dt = number(control_dt, low=.000001)
        self.current = graph.entry
        self.visits, self.repairs = {}, 0
        self.finished = self.faulted = self.suspended = False
        self.elapsed_s = 0.
        self.last_failure = None
        self._lock = threading.Lock()
        self._check_registry(graph)
        rows = journal.records(self.KIND)
        unresolved = {r["invocation_id"] for r in rows if r["event"] == "reserved"}
        unresolved -= {r["invocation_id"] for r in rows if r["event"] == "result"}
        # A new session ID cannot hide another pending/uncertain actuation in this episode.
        if unresolved or any(r["event"] == "fault" for r in rows):
            self.faulted = True
        own = [r for r in rows if r["session_id"] == session_id]
        if own:
            initial = next((r for r in own if r["event"] == "created"), None)
            if initial is None or initial["graph_fingerprint"] != graph.fingerprint:
                raise PermissionError("Session graph changed outside the repair protocol")
            for r in own:
                if r["event"] == "reserved":
                    self.visits[r["node"]] = self.visits.get(r["node"], 0)+1
                elif r["event"] == "result":
                    self.current = r["next_node"] or r["node"]
                    self.suspended = r["next_node"] is None
                    self.last_failure = r["invocation_id"] if self.suspended else None
                    self.elapsed_s += r["elapsed_s"]
                elif r["event"] == "repaired":
                    self.graph = Graph.parse(r["graph"])
                    self._check_registry(self.graph)
                    self.repairs += 1
                    self.suspended = False
                elif r["event"] == "finished":
                    self.finished = True
        else:
            self._write("created", "create", graph_fingerprint=graph.fingerprint, graph=plain(graph))

    def _check_registry(self, graph):
        for node in graph.nodes:
            if node.kind == "done":
                continue
            handler = self.handlers.get(node.capability)
            if not isinstance(handler, Handler) or handler.capability.id != node.capability:
                raise PermissionError("Graph references an unregistered capability")
            if handler.capability.effect != KINDS[node.kind]:
                raise PermissionError("Capability effect does not match node kind")
            if not set(handler.capability.required_roles) <= set(node.roles):
                raise PermissionError("Graph omitted capability-required roles")
            if not set(handler.capability.required_facts) <= set(node.required_facts):
                raise PermissionError("Graph omitted capability-required facts")

    def _write(self, event, key, **body):
        record = {"event": event, "session_id": self.session_id, **plain(body)}
        self.journal.put(self.KIND, f"{self.session_id}:{key}", record)

    def advance(self, *, basis: Basis, bindings: tuple[Binding, ...], facts: FactPacket):
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("One graph node is already executing")
        invocation = None
        started = self.clock()
        try:
            if self.faulted or self.finished or self.suspended:
                raise PermissionError("Graph is finished, suspended or faulted")
            if basis.episode != self.journal.episode:
                raise PermissionError("Foreign graph episode")
            facts.basis.require_same(basis)
            basis.fresh(self.clock(), self.max_age)
            if self.quiescent() is not True:
                raise PermissionError("Existing actuator ownership is not quiescent")
            node = self.graph.node(self.current)
            if self.elapsed_s >= self.graph.budget.max_wall_s or sum(self.visits.values()) >= self.graph.budget.max_visits:
                raise PermissionError("Graph execution budget exhausted")
            if node.kind == "done":
                if self.finish_allowed(basis) is not True:
                    raise PermissionError("Independent task ledger has not verified completion")
                self._write("finished", "finished", semantic_authority="external_task_ledger")
                self.finished = True
                return None
            if self.visits.get(node.id, 0) >= node.max_visits:
                raise PermissionError("Node visit budget exhausted; no unbounded retry")
            # Registry objects are Python integration state, not model output. Recheck
            # here as well so a live reconfiguration cannot bypass effect validation.
            self._check_registry(self.graph)
            handler = self.handlers[node.capability]
            handler.capability.require(basis)
            if type(bindings) is not tuple or any(not isinstance(b, Binding) for b in bindings):
                raise ValueError("Typed immutable role bindings required")
            ids(tuple(b.role for b in bindings))
            chosen = tuple(b for b in bindings if b.role in node.roles)
            for b in chosen:
                basis.require_same(b.basis)
            unknown = facts.missing(node.required_facts) or any(not b.unambiguous for b in chosen) or set(node.roles) != {b.role for b in chosen}
            deadline = min(started+node.max_wall_s,
                           started+self.graph.budget.max_wall_s-self.elapsed_s)
            invocation = "node:" + digest([self.session_id, self.graph.fingerprint, node.id,
                                            self.visits.get(node.id, 0), basis.fingerprint])[:32]
            self._write("reserved", invocation+":reserved", invocation_id=invocation,
                        node=node.id, graph_fingerprint=self.graph.fingerprint, basis=plain(basis))
            self.visits[node.id] = self.visits.get(node.id, 0)+1
            ctx = NodeContext(node, basis, chosen, facts, deadline, invocation)
            if unknown:
                result = NodeResult(invocation, basis, basis, "unknown", basis.evidence_ids, True,
                                    execution_ref="not_dispatched" if node.kind == "act" else None)
            else:
                result = handler.call(ctx)
            if self.clock() >= deadline:
                raise TimeoutError("Late graph callback")
            if not isinstance(result, NodeResult):
                raise ValueError("Typed node receipt required")
            result.require(ctx, handler.capability.effect, self.dt)
            result.after.fresh(self.clock(), self.max_age)
            if self.quiescent() is not True:
                raise RuntimeError("Node returned while actuation remains unresolved")
            target = node.next(result.outcome)
            elapsed = self.clock()-started
            self._write("result", invocation+":result", invocation_id=invocation, node=node.id,
                        next_node=target, elapsed_s=elapsed, result=plain(result))
            self.elapsed_s += elapsed
            self.current = target or node.id
            self.suspended = target is None
            self.last_failure = invocation if self.suspended else None
            return result
        except BaseException as exc:
            if invocation is not None:
                self.faulted = True
                acknowledged = False
                try:
                    deadline = self.clock()+5
                    acknowledged = self.stop(deadline) is True and self.clock() <= deadline
                except BaseException:
                    pass
                try:
                    self._write("fault", invocation+":fault", invocation_id=invocation,
                                error_type=type(exc).__name__, stop_acknowledged=acknowledged)
                except BaseException:
                    pass
            raise
        finally:
            self._lock.release()

    def repair_current(self, *, expected_graph: str, failure_invocation: str, replacement: Node):
        """A stopped, evidence-correlated node-local edit; cannot enlarge budgets/authority."""
        with self._lock:
            if self.faulted or self.finished or not self.suspended or self.quiescent() is not True:
                raise PermissionError("Only an acknowledged, suspended boundary can be repaired")
            if expected_graph != self.graph.fingerprint or failure_invocation != self.last_failure:
                raise PermissionError("Stale repair request")
            if self.repairs >= self.graph.budget.max_repairs:
                raise PermissionError("Repair budget exhausted")
            old = self.graph.node(self.current)
            if replacement.id != old.id or replacement.kind != old.kind or replacement.roles != old.roles:
                raise PermissionError("Repair must preserve node identity/effect/semantic roles")
            if (not set(old.required_facts) <= set(replacement.required_facts)
                    or replacement.max_wall_s > old.max_wall_s or replacement.max_visits > old.max_visits):
                raise PermissionError("Repair cannot weaken requirements or expand limits")
            graph = replace(self.graph, nodes=tuple(replacement if n.id == old.id else n for n in self.graph.nodes))
            self._check_registry(graph)
            self._write("repaired", f"repair:{self.repairs}", previous=expected_graph,
                        failure_invocation=failure_invocation, graph=plain(graph))
            self.graph = graph
            self.repairs += 1
            self.suspended = False
