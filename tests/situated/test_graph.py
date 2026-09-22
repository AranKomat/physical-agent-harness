from dataclasses import replace

import pytest

from physical_harness.action_compiler.types import plain
from physical_harness.situated.contracts import (
    Binding,
    Capability,
    Effect,
    Fact,
    FactPacket,
    ScopeBudget,
)
from physical_harness.situated.graph import Graph, Node
from physical_harness.situated.graph_runtime import GraphSession, Handler, NodeResult

from .conftest import make_basis


def graph(**kwargs):
    a = Node('observe', 'observe', 'sense', (), (), (('ok', 'done'),), 10, 3)
    return replace(Graph('task', 'observe', (a, Node('done', 'done', 'existing_task_ledger'))), **kwargs)

def good(ctx):
    return NodeResult(ctx.invocation_id, ctx.basis, ctx.basis, 'ok', ctx.basis.evidence_ids, True)

def session(journal, g=None, fn=good, **kwargs):
    return GraphSession(graph=g or graph(), session_id=kwargs.pop('session_id', 's'), journal=journal, handlers={'sense': Handler(Capability('sense', Effect.READ, 'fixture', 'fixture-q', ('e',)), fn), 'sense2': Handler(Capability('sense2', Effect.READ, 'fixture', 'fixture-q', ('e',)), good)}, quiescent=kwargs.pop('quiescent', lambda: True), stop=kwargs.pop('stop', lambda d: True), finish_allowed=kwargs.pop('finish_allowed', lambda b: True), clock=kwargs.pop('clock', lambda: 100.0), **kwargs)

def advance(s, basis=None, bindings=(), facts=None):
    b = basis or make_basis()
    return s.advance(basis=b, bindings=bindings, facts=facts or FactPacket(b, ()))

def test_graph_roundtrip_forbids_scene_coordinates_and_python():
    g = graph()
    assert Graph.parse(plain(g)) == g
    raw = plain(g)
    raw['nodes'][0]['python'] = 'sim.set_state()'
    with pytest.raises(ValueError):
        Graph.parse(raw)

@pytest.mark.parametrize('kind', ['dangling', 'duplicate', 'unreachable', 'bad_terminal', 'bad_kind'])
def test_graph_validation(kind):
    g = graph()
    with pytest.raises(ValueError):
        if kind == 'dangling':
            replace(g, nodes=(replace(g.nodes[0], transitions=(('ok', 'missing'),)), g.nodes[1]))
        elif kind == 'duplicate':
            replace(g, nodes=g.nodes + (g.nodes[0],))
        elif kind == 'unreachable':
            replace(g, nodes=g.nodes + (Node('extra', 'done', 'existing_task_ledger'),))
        elif kind == 'bad_terminal':
            replace(g.nodes[1], capability='LLM_says_success')
        else:
            replace(g.nodes[0], kind='eval_python')

def test_graph_execution_and_reopen_use_actual_journal(journal):
    s = session(journal)
    assert advance(s).outcome == 'ok'
    restored = session(journal)
    assert restored.current == 'done'
    advance(restored)
    assert restored.finished
    assert session(journal).finished

def test_task_finish_needs_external_ledger(journal):
    s = session(journal, finish_allowed=lambda b: False)
    advance(s)
    with pytest.raises(PermissionError, match='ledger'):
        advance(s)
    assert not s.finished

def test_unknown_roles_take_unknown_edge_without_native_call(journal):
    g = graph()
    g = replace(g, nodes=(replace(g.nodes[0], roles=('target',)), g.nodes[1]))
    s = session(journal, g, fn=lambda ctx: (_ for _ in ()).throw(AssertionError('should not call')))
    assert advance(s).outcome == 'unknown'
    assert s.suspended and (not s.faulted)

def test_known_false_fact_is_information_not_missing(journal):
    g = graph()
    g = replace(g, nodes=(replace(g.nodes[0], required_facts=('grasped',)), g.nodes[1]))
    b = make_basis()
    facts = FactPacket(b, (Fact('grasped', False, b, b.evidence_ids, 'measured', '1'),))
    s = session(journal, g)
    assert advance(s, facts=facts).outcome == 'ok'

def test_node_local_repair_retains_roles_and_limits(journal):

    def fail(ctx):
        return replace(good(ctx), outcome='failed')
    s = session(journal, fn=fail)
    advance(s)
    old = s.graph.node(s.current)
    with pytest.raises(PermissionError):
        s.repair_current(expected_graph=s.graph.fingerprint, failure_invocation=s.last_failure, replacement=replace(old, max_wall_s=20))
    s.repair_current(expected_graph=s.graph.fingerprint, failure_invocation=s.last_failure, replacement=replace(old, capability='sense2'))
    assert advance(s).outcome == 'ok'
    assert session(journal).repairs == 1

@pytest.mark.parametrize('error', [RuntimeError, KeyboardInterrupt, TimeoutError])
def test_fault_survives_reopen_and_new_session_id(journal, error):

    def fail(ctx):
        raise error()
    s = session(journal, fn=fail)
    with pytest.raises(error):
        advance(s)
    assert s.faulted
    for sid in ('s', 'new-session'):
        restored = session(journal, session_id=sid)
        assert restored.faulted
        with pytest.raises(PermissionError):
            advance(restored)

@pytest.mark.parametrize('mutation', ['wrong_id', 'unacknowledged', 'moved_read', 'foreign_after'])
def test_untrusted_receipt_is_not_success(journal, mutation):

    def fn(ctx):
        r = good(ctx)
        if mutation == 'wrong_id':
            return replace(r, invocation_id='wrong')
        if mutation == 'unacknowledged':
            return replace(r, stop_acknowledged=False)
        if mutation == 'moved_read':
            return replace(r, after=make_basis(1), native_steps=30)
        return replace(r, after=make_basis(0, episode='other'))
    s = session(journal, fn=fn)
    with pytest.raises((PermissionError, ValueError)):
        advance(s)
    assert s.faulted

def test_cycles_bounded_and_reopen_does_not_reset_visits(journal):
    g = graph()
    node = replace(g.nodes[0], transitions=(('ok', 'observe'), ('complete', 'done')), max_visits=2)
    g = replace(g, nodes=(node, g.nodes[1]))
    s = session(journal, g)
    advance(s)
    advance(s)
    restored = session(journal, g)
    with pytest.raises(PermissionError, match='visit budget'):
        advance(restored)

def test_capability_domain_and_effect_checked(journal):
    with pytest.raises(PermissionError):
        GraphSession(graph=graph(), session_id='x', journal=journal, handlers={'sense': Handler(Capability('sense', Effect.MOTION, 'fixture', 'q', ('e',)), good)}, quiescent=lambda: True, stop=lambda d: True, finish_allowed=lambda b: True)
    s = session(journal)
    s.handlers['sense'] = Handler(Capability('sense', Effect.READ, 'behavior_sim', 'q', ('e',)), good)
    with pytest.raises(PermissionError):
        advance(s)

def test_stale_bindings_and_busy_actuator_block_before_work(journal):
    s = session(journal, quiescent=lambda: False)
    with pytest.raises(PermissionError):
        advance(s)
    assert not s.faulted
    g = graph()
    g = replace(g, nodes=(replace(g.nodes[0], roles=('target',)), g.nodes[1]))
    s = session(journal, g, session_id='bound')
    role = Binding('target', 'e', 'whole', make_basis(1), ('e',), True)
    with pytest.raises(PermissionError):
        advance(s, bindings=(role,))

def test_elapsed_deadline_faults_callback_result(journal):
    now = [100.0]

    def late(ctx):
        now[0] += 11
        return good(ctx)
    s = session(journal, fn=late, clock=lambda: now[0])
    with pytest.raises(TimeoutError):
        advance(s)
    assert s.faulted

def test_handler_effect_cannot_change_after_graph_admission(journal):
    s = session(journal)
    s.handlers['sense'] = Handler(Capability('sense', Effect.MOTION, 'fixture', 'q', ('e',)), good)
    with pytest.raises(PermissionError, match='effect'):
        advance(s)
    assert not s.visits

def test_operator_graph_budget_is_independent_from_model_graph(journal):
    g = graph(budget=ScopeBudget(max_wall_s=600))
    with pytest.raises(PermissionError, match='operator budget'):
        session(journal, g)
    s = session(journal, g, budget_limit=ScopeBudget(max_wall_s=600))
    assert advance(s).outcome == 'ok'

@pytest.mark.parametrize('contract', ['roles', 'facts'])
def test_graph_cannot_omit_operator_capability_requirements(journal, contract):
    s = session(journal)
    old = s.handlers['sense']
    required = {'required_roles': ('target',)} if contract == 'roles' else {'required_facts': ('target_visible',)}
    s.handlers['sense'] = replace(old, capability=replace(old.capability, **required))
    with pytest.raises(PermissionError, match='omitted capability'):
        advance(s)
    assert not s.visits
