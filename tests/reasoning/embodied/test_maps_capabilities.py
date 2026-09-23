from dataclasses import replace
from types import SimpleNamespace

import networkx as nx
import pytest

from physical_harness.core.actions import Pose, Verb
from physical_harness.core.tasks import Binding, Capability, Effect, Fact, FactPacket
from physical_harness.perception.geometry import Intrinsics, ObjectCloud
from physical_harness.perception.visual import GoalKind, VisualGoal
from physical_harness.planning.inspection import InspectionCandidate
from physical_harness.planning.map_tools import (
    ExplorationLedger,
    NavigationGrid,
    PlaceCoverage,
    entity_destination,
    grid_from_existing,
    rank_frontiers,
    semantic_map_view,
    shortest_path,
)
from physical_harness.planning.tasks.capabilities import (
    MacroRegistry,
    Promotion,
    compile_graph_fragment,
    standard_macro,
)
from physical_harness.planning.tasks.graph import Graph
from physical_harness.planning.view_scoring import assess_views, assessment_report
from physical_harness.world.topology import PlaceEdge, PlaceNode, TopologicalMap
from tests.reasoning.embodied.conftest import make_basis


def grid(basis=None, *, free=None, known=None, bounds=None):
    cells = tuple(((x, y) for x in range(5) for y in range(3)))
    return NavigationGrid(basis or make_basis(), 'map-r1', 0.2, (0.0, 0.0), cells if free is None else free, cells if known is None else known, (0, 0), 'fixture_inflated_cells', bounds)

def test_shortest_path_stays_in_known_free_and_cost_aware():
    g = grid()
    path = shortest_path(g, (4, 0))
    assert len(path) == 5
    cost_path = shortest_path(g, (4, 0), extra_costs={(2, 0): 10.0})
    assert (2, 0) not in cost_path
    assert all((abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(cost_path, cost_path[1:])))
    assert shortest_path(g, (8, 8)) is None

def test_no_corner_cut_or_unknown_shortcut():
    g = grid(free=((0, 0), (1, 1)), known=((0, 0), (1, 1)))
    assert shortest_path(g, (1, 1)) is None

@pytest.mark.parametrize('changes', [dict(resolution_m=0), dict(free_cells=((9, 9),)), dict(current_cell=(True, 0)), dict(bounds=(0, 0, 0, 2))])
def test_grid_contract(changes):
    with pytest.raises(ValueError):
        replace(grid(), **changes)

def test_changed_map_or_local_frame_rejects_reuse():
    g = grid()
    for b in [replace(g.basis, geometry_revision='new'), replace(g.basis, frame_epoch='new')]:
        with pytest.raises(PermissionError):
            g.require(b, now=100)
    with pytest.raises(PermissionError):
        g.require(g.basis, now=103)

def test_existing_grid_adapter_preserves_map_convention():
    o = SimpleNamespace(episode_id='ep', last_time=0.0, revision=3, resolution=0.2, bounds=(0, 0, 5, 3), cells={(0, 0): False}, graph=lambda: nx.empty_graph([(0, 0)]), cell=lambda x, y: (0, 0))
    got = grid_from_existing(o, source_basis=make_basis(), current_pose=Pose('local'), geometry_convention='qualified_external_projection')
    assert got.free_cells == ((0, 0),) and got.revision == '3'
    o.last_time = 1.0
    with pytest.raises(PermissionError):
        grid_from_existing(o, source_basis=make_basis(), current_pose=Pose('local'), geometry_convention='x')

def test_entity_route_is_approach_region_not_occupied_object_center():
    g = grid()
    d = entity_destination(grid=g, entity='radio', position=(1.1, 0.1), evidence_ids=('depth',), observed_basis=g.basis, approach_radius_m=0.2, tolerance_m=0.02, current_identity=True)
    assert d.kind == 'entity_approach' and (not d.requires_reacquisition)
    assert g.center(d.cell) == pytest.approx((0.9, 0.1))
    old = replace(g.basis, sim_time=0, captured_wall=99, observation_id='old')
    d = entity_destination(grid=g, entity='radio', position=(1.1, 0.1), evidence_ids=('old-depth',), observed_basis=old, approach_radius_m=0.2, tolerance_m=0.02)
    assert d.kind == 'remembered_search_region' and d.requires_reacquisition
    with pytest.raises(PermissionError):
        entity_destination(grid=g, entity='radio', position=(1.1, 0.1), evidence_ids=('old',), observed_basis=old, approach_radius_m=0.2, current_identity=True)

def test_frontier_semantic_hint_changes_rank_and_bounds_prevent_edge_invention():
    g = grid(bounds=(-1, -1, 6, 4))
    a = rank_frontiers(g, semantic_scores={(4, 2): 1.0})
    assert a[0].destination.cell == (4, 2)
    assert rank_frontiers(grid(bounds=(0, 0, 5, 3))) == ()
    assert all((s.destination.cell in g.free_cells for s in a))

def test_frontier_visits_persist_but_do_not_cross_origin_reset(journal):
    g = grid()
    d = rank_frontiers(g)[0].destination
    led = ExplorationLedger(journal)
    led.record(g, d, reached=True, evidence_ids=('reached',), observed=g.basis)
    assert d.cell in ExplorationLedger(journal).visited(g, now=100)
    assert not led.visited(replace(g, basis=replace(g.basis, frame_epoch='reset')), now=100)
    with pytest.raises(PermissionError):
        led.record(g, replace(d, map_fingerprint='wrong'), reached=True, evidence_ids=('e',), observed=g.basis)

def topology():
    t = TopologicalMap()
    t.upsert_node(PlaceNode('a', 'kitchen', 'room'))
    t.upsert_node(PlaceNode('b', 'hall', 'corridor'))
    t.add_edge(PlaceEdge('a', 'b', gateway_entity='door'))
    return t

def test_semantic_map_requires_observed_open_and_fresh_gateway():
    t = topology()
    g = grid()

    def view(cb=None):
        return semantic_map_view(basis=g.basis, grid=g, topology=t, current_place='a', entity_rows=(), frontiers=(), gateway_fresh=cb, coverage=(PlaceCoverage('a', 10, None, g.basis, ('e',)),))
    assert not view(lambda *a: True)['links'][0]['route_usable_hint']
    t.update_gateway('door', 'open', ('door-observed',))
    assert not view()['links'][0]['route_usable_hint']
    assert view(lambda *a: True)['links'][0]['route_usable_hint']
    assert view()['places'][0]['coverage']['fraction'] is None
    t.update_gateway('door', 'closed', ('e',))
    assert not view(lambda *a: True)['links'][0]['route_usable_hint']

def test_map_filters_coordinates_from_untrusted_inventory():
    g = grid()
    out = semantic_map_view(basis=g.basis, grid=g, topology=topology(), current_place='a', entity_rows=({'id': 's', 'description': 'radio?', 'xyz': [10, 20, 30], 'motion_authority': True},), frontiers=())
    assert 'xyz' not in out['entities'][0] and 'motion_authority' not in out['entities'][0]

@pytest.mark.parametrize('name', ['go_to', 'pick', 'place', 'inspect', 'press', 'pull_prismatic'])
def test_macro_artifacts_are_bounded_graphs_not_qualified_motion(journal, name):
    macro = standard_macro(name, deployment='d')
    assert Graph.parse(__import__('json').loads(__import__('physical_harness.core.actions', fromlist=['encode']).encode(macro.graph))).fingerprint == macro.graph.fingerprint
    registry = MacroRegistry(journal=journal, deployment_fingerprint='d')
    registry.register(macro)
    assert not registry.view()[0]['promotion_enabled']
    with pytest.raises(PermissionError):
        registry.available(name + '@1', basis=make_basis(), capabilities={}, facts=FactPacket(make_basis(), ()), bindings={})

def test_macro_promotion_requires_exact_code_and_external_review(journal):
    macro = standard_macro('pick', deployment='d')
    r = MacroRegistry(journal=journal, deployment_fingerprint='d')
    r.register(macro)
    p = Promotion(macro.fingerprint, 'd', 'fixture', 'q', 'reviewer', ('test',), 'software', True)
    with pytest.raises(PermissionError):
        r.promote('pick@1', p, operator_review=lambda *a: False)
    r.promote('pick@1', p, operator_review=lambda *a: True)
    b = make_basis()
    facts = FactPacket(b, (Fact('robot_ready', True, b, ('e',), 'fixture', 'v1'),))
    caps = {n.capability: Capability(n.capability, Effect.MOTION if n.kind == 'act' else Effect.REASON if n.kind == 'reason' else Effect.READ, 'fixture', 'q', ('e',)) for n in macro.graph.nodes if n.kind != 'done'}
    bindings = {'target': Binding('target', 'radio', 'whole', b, ('id',), True)}
    assert r.available('pick@1', basis=b, capabilities=caps, facts=facts, bindings=bindings) == macro.graph
    r2 = MacroRegistry(journal=journal, deployment_fingerprint='d')
    r2.register(macro)
    assert r2.view()[0]['promotion_enabled']
    with pytest.raises(PermissionError):
        r.available('pick@1', basis=b, capabilities=caps, facts=FactPacket(b, (replace(facts.facts[0], value=False),)), bindings=bindings)
    with pytest.raises(PermissionError):
        Promotion(macro.fingerprint, 'd', 'behavior_sim', 'q', 'x', ('e',), 'software', True)

@pytest.mark.parametrize('name', ['use_elevator', 'open_any_door', 'fold_towel'])
def test_no_invented_native_capabilities(name):
    with pytest.raises(ValueError):
        standard_macro(name, deployment='d')

def test_graph_fragment_not_automatically_promoted():
    m = standard_macro('press', deployment='d')
    got = compile_graph_fragment(name='press2', version='1', graph=m.graph, roles=m.parameters, preconditions=m.preconditions, postconditions=m.postconditions, deployment='d')
    assert got.fingerprint != m.fingerprint
    with pytest.raises(PermissionError):
        compile_graph_fragment(name='press2', version='1', graph=m.graph, roles=m.parameters, preconditions=(), postconditions=('done',), deployment='d', max_visits=1)

def inspection(basis):
    points = tuple(((x, y, 1.0) for x in [-0.1, 0.0, 0.1] for y in [-0.1, 0.0, 0.1]))
    c = ObjectCloud(basis, 'radio', 'whole', points, ('depth',), 0.5, 'head', (0.0, 0.0, 0.0), 1.0)
    goal = VisualGoal('goal', GoalKind.INFORMATION, 'radio', 'identity', 'resolve identity')
    cand = InspectionCandidate(goal, basis, Pose('local'), Pose('local'), Verb.STAGE, 0.5, 0.1, ('e',), 'fixture')
    intr = Intrinsics(100, 100, 100.0, 100.0, 50.0, 50.0, 1.0, 'optical_z')
    return (c, cand, intr)

def test_inspection_diagnostics_do_not_turn_unknown_into_clear():
    b = make_basis()
    cloud, cand, intr = inspection(b)
    values = assess_views((cand,), current=b, cloud=cloud, intrinsics=intr)
    assert not values[0][1].eligible_hint
    assert values[0][1].unknown_visibility_fraction == 1.0
    report = assessment_report(values)
    assert report['motion_authority'] is False
    good = assess_views((cand,), current=b, cloud=cloud, intrinsics=intr, visibility=lambda *a: True, feasible=lambda *a: True)
    assert good[0][1].eligible_hint

@pytest.mark.parametrize('verdict', [None, False])
def test_inspection_feasibility_needed(verdict):
    b = make_basis()
    cloud, cand, intr = inspection(b)
    out = assess_views((cand,), current=b, cloud=cloud, intrinsics=intr, visibility=lambda *a: True, feasible=lambda *a: verdict)
    assert not out[0][1].eligible_hint
