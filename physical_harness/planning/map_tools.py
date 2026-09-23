"""Compact semantic map projection over existing occupancy/topology/identity stores.

The map is a mutable observed cache, not a digital twin. No new global SLAM is
implemented. Even a path through known-free cells is only a PROPOSAL: the native
footprint, localization, swept clearance and stop checks still own admission.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from physical_harness.core.actions import Basis, Pose, digest, ids, integer, number, plain, text

Cell = tuple[int, int]


def _cell(c):
    if type(c) is not tuple or len(c) != 2 or any(type(x) is not int for x in c):
        raise ValueError("Integer grid cell required")


@dataclass(frozen=True)
class NavigationGrid:
    basis: Basis
    revision: str
    resolution_m: float
    origin_xy: tuple[float, float]
    free_cells: tuple[Cell, ...]  # Already footprint-inflated by the existing map.
    known_cells: tuple[Cell, ...]
    current_cell: Cell
    geometry_convention: str
    bounds: tuple[int, int, int, int] | None = None

    def __post_init__(self):
        if not isinstance(self.basis, Basis):
            raise ValueError("Map evidence basis required")
        text(self.revision)
        text(self.geometry_convention)
        number(self.resolution_m, low=.001, high=10)
        if type(self.origin_xy) is not tuple or len(self.origin_xy) != 2:
            raise ValueError("Grid origin required")
        for n in self.origin_xy:
            number(n)
        for collection in (self.free_cells, self.known_cells):
            if type(collection) is not tuple or len(collection) > 50000:
                raise ValueError("Bounded immutable grid required")
            for c in collection:
                _cell(c)
            if len(set(collection)) != len(collection):
                raise ValueError("Duplicate map cells")
        if not set(self.free_cells) <= set(self.known_cells):
            raise ValueError("Unknown space cannot be a free navigation cell")
        _cell(self.current_cell)
        if self.bounds is not None:
            if (type(self.bounds) is not tuple or len(self.bounds) != 4 or
                    any(type(x) is not int for x in self.bounds) or
                    self.bounds[0] >= self.bounds[2] or self.bounds[1] >= self.bounds[3]):
                raise ValueError("Invalid map bounds")
            if any(not self.inside(c) for c in self.known_cells):
                raise ValueError("Known cells lie outside bounded map")

    def inside(self, cell):
        if self.bounds is None:
            return True
        a,b,c,d = self.bounds
        return a <= cell[0] < c and b <= cell[1] < d

    def center(self, c: Cell):
        _cell(c)
        return (self.origin_xy[0] + (c[0]+.5)*self.resolution_m,
                self.origin_xy[1] + (c[1]+.5)*self.resolution_m)

    @property
    def fingerprint(self):
        return digest(self)

    def require(self, current: Basis, *, now: float, max_age_s: float = 2):
        self.basis.require_continuity(current)
        if current.geometry_revision != self.basis.geometry_revision:
            raise PermissionError("Map geometry revision changed")
        self.basis.fresh(now, max_age_s)


def grid_from_existing(occupancy, *, source_basis: Basis, current_pose: Pose,
                       geometry_convention: str) -> NavigationGrid:
    """Projection only. Does not reinterpret pitched RGB-D as a horizontal scan.

    Use only after the existing OccupancyMap camera assumptions have been audited.
    Passing a label here is documentation, not proof of that audit.
    """
    if occupancy.episode_id != source_basis.episode or occupancy.last_time != source_basis.sim_time:
        raise PermissionError("Map source timestamp/episode mismatch")
    if current_pose.frame != source_basis.frame:
        raise ValueError("Current base pose and grid use different frames")
    graph = occupancy.graph()
    return NavigationGrid(source_basis, str(occupancy.revision), occupancy.resolution, (0., 0.),
                          tuple(sorted(graph.nodes)), tuple(sorted(occupancy.cells)),
                          occupancy.cell(*current_pose.xyz[:2]), geometry_convention, tuple(occupancy.bounds))


def shortest_path(grid: NavigationGrid, goal: Cell, *, extra_costs: dict[Cell, float] | None = None) -> tuple[Cell, ...] | None:
    """Deterministic cost-aware 4-neighbor A*, no diagonal/unknown-space shortcut."""
    _cell(goal)
    free = set(grid.free_cells)
    start = grid.current_cell
    if goal not in free or start not in free:
        return None
    costs = extra_costs or {}
    for c, n in costs.items():
        _cell(c)
        number(n, low=0)
    def heuristic(c):
        return grid.resolution_m*(abs(c[0]-goal[0])+abs(c[1]-goal[1]))
    queue = [(heuristic(start), 0., start)]
    best = {start: 0.}
    parent = {}
    while queue:
        _, g, here = heapq.heappop(queue)
        if g != best[here]:
            continue
        if here == goal:
            result = [here]
            while here in parent:
                here = parent[here]
                result.append(here)
            return tuple(reversed(result))
        x, y = here
        for nxt in sorted(((x-1, y), (x+1, y), (x, y-1), (x, y+1))):
            if nxt not in free:
                continue
            ng = g + grid.resolution_m + costs.get(nxt, 0.)
            if ng < best.get(nxt, math.inf):
                best[nxt], parent[nxt] = ng, here
                heapq.heappush(queue, (ng+heuristic(nxt), ng, nxt))
    return None


def reachable_distances(grid: NavigationGrid) -> dict[Cell, float]:
    """One deterministic breadth-first expansion of the unweighted safe grid."""
    from collections import deque
    free = set(grid.free_cells)
    if grid.current_cell not in free:
        return {}
    counts = {grid.current_cell: 0}
    queue = deque([grid.current_cell])
    while queue:
        x, y = queue.popleft()
        for c in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
            if c in free and c not in counts:
                counts[c] = counts[(x,y)] + 1
                queue.append(c)
    return {c: n*grid.resolution_m for c, n in counts.items()}


@dataclass(frozen=True)
class Destination:
    id: str
    kind: str  # place | entity_approach | frontier | remembered_search_region
    subject: str
    cell: Cell
    basis: Basis
    map_fingerprint: str
    evidence_ids: tuple[str, ...]
    requires_reacquisition: bool

    def __post_init__(self):
        for x in (self.id, self.subject, self.map_fingerprint):
            text(x)
        if self.kind not in {"place", "entity_approach", "frontier", "remembered_search_region"}:
            raise ValueError("Unknown destination kind")
        _cell(self.cell)
        ids(self.evidence_ids, empty=False)
        if not isinstance(self.basis, Basis) or type(self.requires_reacquisition) is not bool:
            raise ValueError("Current map basis/reacquisition flag required")
        if self.kind == "remembered_search_region" and not self.requires_reacquisition:
            raise ValueError("Historical targets require current reacquisition")


def entity_destination(*, grid: NavigationGrid, entity: str, position: tuple[float, float],
                       evidence_ids: tuple[str, ...], observed_basis: Basis,
                       approach_radius_m: float, tolerance_m: float = .15,
                       current_identity: bool = False) -> Destination:
    """Find reachable staging cells around a measured target; not the occupied center.

    A historical position is a search hint only; exact source lineage and named
    frame must still be compatible. No semantic label supplies position.
    """
    text(entity)
    if type(current_identity) is not bool:
        raise ValueError("Current identity flag must be boolean")
    observed_basis.require_continuity(grid.basis)
    if current_identity:
        observed_basis.require_same(grid.basis)
    if type(position) is not tuple or len(position) != 2:
        raise ValueError("Measured XY estimate required")
    for n in position:
        number(n)
    number(approach_radius_m, low=.01, high=5)
    number(tolerance_m, low=.001, high=1)
    choices = []
    reachable = reachable_distances(grid)
    for c in grid.free_cells:
        distance = math.dist(grid.center(c), position)
        if abs(distance-approach_radius_m) > tolerance_m:
            continue
        if c in reachable:
            choices.append((reachable[c], abs(distance-approach_radius_m), c))
    if not choices:
        raise ValueError("No known-free reachable approach region")
    _, _, cell = min(choices)
    kind = "entity_approach" if current_identity else "remembered_search_region"
    return Destination("destination:" + digest([grid.fingerprint, entity, kind, cell])[:24], kind,
                       entity, cell, grid.basis, grid.fingerprint, evidence_ids, not current_identity)


@dataclass(frozen=True)
class FrontierScore:
    destination: Destination
    travel_m: float
    unknown_neighbor_count: int
    semantic_relevance: float
    score: float
    reason: str


def rank_frontiers(grid: NavigationGrid, *, visited: frozenset[Cell] = frozenset(),
                   semantic_scores: dict[Cell, float] | None = None, maximum: int = 6) -> tuple[FrontierScore, ...]:
    """Semantic frontier ranker on known-free approach cells, not learned VLFM itself."""
    integer(maximum, low=1, high=32)
    scores = semantic_scores or {}
    for c, s in scores.items():
        _cell(c)
        number(s, low=0, high=1)
    known = set(grid.known_cells)
    out = []
    reachable = reachable_distances(grid)
    for c in grid.free_cells:
        if c in visited:
            continue
        x, y = c
        gain = sum(grid.inside(n) and n not in known for n in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)))
        if gain == 0:
            continue
        if c not in reachable:
            continue
        travel = reachable[c]
        semantic = scores.get(c, 0.)
        score = 2*semantic + gain/4 - .1*travel
        dest = Destination("frontier:"+digest([grid.fingerprint, c])[:24], "frontier", "unexplored",
                           c, grid.basis, grid.fingerprint, grid.basis.evidence_ids, True)
        out.append(FrontierScore(dest, travel, gain, semantic, score,
                                 "heuristic semantic value + boundary count - path distance"))
    return tuple(sorted(out, key=lambda x: (-x.score, x.destination.id))[:maximum])


class ExplorationLedger:
    """Persistent visited frontiers, scoped to map frame epoch; no repeat-loop amnesia."""
    def __init__(self, journal):
        self.journal = journal

    def record(self, grid: NavigationGrid, destination: Destination, *, reached: bool,
               evidence_ids: tuple[str, ...], observed: Basis):
        if type(reached) is not bool:
            raise ValueError("Measured reach result required")
        grid.basis.require_continuity(observed)
        if observed.episode != self.journal.episode:
            raise PermissionError("Foreign exploration")
        ids(evidence_ids, empty=False)
        if destination.map_fingerprint != grid.fingerprint or destination.basis != grid.basis:
            raise PermissionError("Destination belongs to another map snapshot")
        key = digest([destination.id, observed.fingerprint])
        self.journal.put("embodied_exploration", key, {
            "episode": observed.episode, "frame_epoch": observed.frame_epoch, "frame": observed.frame,
            "resolution": grid.resolution_m, "origin": grid.origin_xy, "cell": destination.cell,
            "reached": reached, "observed_sim": observed.sim_time, "available_wall": observed.captured_wall,
            "evidence_ids": evidence_ids})

    def visited(self, grid: NavigationGrid, *, now: float) -> frozenset[Cell]:
        number(now, low=grid.basis.captured_wall)
        if grid.basis.episode != self.journal.episode:
            raise PermissionError("Foreign exploration cutoff")
        rows = self.journal.records("embodied_exploration")
        return frozenset(tuple(r["cell"]) for r in rows if r["episode"] == grid.basis.episode and
                         r["frame_epoch"] == grid.basis.frame_epoch and r["frame"] == grid.basis.frame and
                         r["resolution"] == grid.resolution_m and tuple(r["origin"]) == grid.origin_xy and
                         r["observed_sim"] <= grid.basis.sim_time and r["available_wall"] <= now and r["reached"] is True)


@dataclass(frozen=True)
class PlaceCoverage:
    place_id: str
    observed_cells: int
    region_cells: int | None
    basis: Basis
    evidence_ids: tuple[str, ...]

    def __post_init__(self):
        text(self.place_id)
        if not isinstance(self.basis, Basis):
            raise ValueError("Coverage source basis required")
        integer(self.observed_cells)
        if self.region_cells is not None:
            integer(self.region_cells, low=max(1, self.observed_cells))
        ids(self.evidence_ids, empty=False)

    @property
    def fraction(self):
        # Unknown denominator stays unknown; no invented "87% explored".
        return None if self.region_cells is None else self.observed_cells/self.region_cells


def semantic_map_view(*, basis: Basis, grid: NavigationGrid, topology,
                      current_place: str | None, entity_rows: tuple[dict, ...],
                      frontiers: tuple[FrontierScore, ...], coverage: tuple[PlaceCoverage, ...] = (),
                      gateway_fresh=None, max_places: int = 32, max_entities: int = 32) -> dict:
    """Join existing stores into a bounded model view, not another authoritative map."""
    grid.basis.require_same(basis)
    integer(max_places, low=1, high=128)
    integer(max_entities, low=1, high=128)
    if current_place is not None and current_place not in topology.nodes:
        raise ValueError("Unknown current place")
    visible_places = sorted(topology.nodes)
    if len(visible_places) > max_places:
        # Prefer current place and neighbors; expose omission counts.
        relevant = {current_place} | {e.a for e in topology.neighbors(current_place)} | {e.b for e in topology.neighbors(current_place)} if current_place else set()
        visible_places.sort(key=lambda k: (k not in relevant, k))
    kept = set(visible_places[:max_places])
    covers = {}
    for c in coverage:
        c.basis.require_continuity(basis)
        covers[c.place_id] = {"observed_cells": c.observed_cells, "region_cells": c.region_cells,
                              "fraction": c.fraction, "observed_at": c.basis.sim_time}
    links = []
    for edge in topology.edges:
        if edge.a not in kept or edge.b not in kept:
            continue
        # TopologicalMap lacks time on gateways: an external freshness check is mandatory.
        open_now = (edge.traversable and (edge.gateway_entity is None or
                    (topology.gateway_states.get(edge.gateway_entity) == "open" and gateway_fresh is not None and gateway_fresh(edge.gateway_entity, basis) is True)))
        links.append({"from": edge.a, "to": edge.b, "gateway": edge.gateway_entity,
                      "route_usable_hint": bool(open_now), "cost": edge.cost,
                      "notice": "Not metric clearance or authorization to pass a door"})
    if type(entity_rows) is not tuple or len(entity_rows) > 2048:
        raise ValueError("Bounded semantic inventory rows required")
    if type(frontiers) is not tuple or len(frontiers) > 32:
        raise ValueError("Bounded frontier packet required")
    for f in frontiers:
        if f.destination.map_fingerprint != grid.fingerprint:
            raise PermissionError("Stale frontier catalog")
    safe_rows = []
    allowed = {"id", "entity_id", "place_id", "description", "hypotheses", "observed_sim",
               "authority", "needs_view", "kind", "semantic_status"}
    for r in entity_rows[:max_entities]:
        safe_rows.append({k: plain(v) for k, v in r.items() if k in allowed})
    return {"basis": basis.fingerprint, "map_revision": grid.revision,
            "current_place": current_place, "base_cell": grid.current_cell,
            "places": [{"id": k, "label": topology.nodes[k].label, "kind": topology.nodes[k].kind,
                        "coverage": covers.get(k)} for k in visible_places[:max_places]],
            "links": links, "entities": safe_rows, "frontiers": [
                {"id": f.destination.id, "cell": f.destination.cell, "travel_m": f.travel_m,
                 "score": f.score, "semantic_relevance": f.semantic_relevance,
                 "unknown_neighbors": f.unknown_neighbor_count, "reason": f.reason}
                for f in frontiers],
            "omitted_places": max(0, len(topology.nodes)-max_places),
            "omitted_entities": max(0, len(entity_rows)-max_entities),
            "notice": "Observed map and historical sightings; no full pre-map or digital twin assumed."}


class MapTool:
    """Opaque destinations for the executive; returns a path proposal, not motion.

    Native navigation rechecks its own localization/footprint/obstacles. This
    helper never turns a remembered object center into a current contact pose.
    """
    def __init__(self, grid: NavigationGrid, destinations: tuple[Destination, ...]):
        if not isinstance(grid, NavigationGrid) or type(destinations) is not tuple or len(destinations) > 64:
            raise ValueError("Bounded map-tool catalog required")
        ids(tuple(d.id for d in destinations))
        for d in destinations:
            if d.map_fingerprint != grid.fingerprint or d.basis != grid.basis:
                raise PermissionError("Mixed map revisions in destination catalog")
        self.grid, self.destinations = grid, {d.id: d for d in destinations}

    def select(self, destination_id: str, *, current: Basis, now: float):
        text(destination_id)
        self.grid.require(current, now=now)
        self.grid.basis.require_same(current)
        if destination_id not in self.destinations:
            raise PermissionError("Unknown semantic-map destination")
        d = self.destinations[destination_id]
        path = shortest_path(self.grid, d.cell)
        if path is None:
            raise PermissionError("No observed-free approach route")
        return {"destination_id": d.id, "subject": d.subject, "basis": current.fingerprint,
                "kind": d.kind, "path_xy": [self.grid.center(c) for c in path],
                "requires_reacquisition": d.requires_reacquisition,
                "motion_authority": False}


def place_destination(grid: NavigationGrid, place_id: str, *, current_anchor: Pose,
                      evidence_ids: tuple[str, ...]) -> Destination:
    """A measured reachable place-entry anchor supplied by the existing resolver."""
    if not isinstance(current_anchor, Pose) or current_anchor.frame != grid.basis.frame:
        raise ValueError("Current place anchor must use the local map frame")
    cell = (math.floor((current_anchor.xyz[0]-grid.origin_xy[0])/grid.resolution_m),
            math.floor((current_anchor.xyz[1]-grid.origin_xy[1])/grid.resolution_m))
    if shortest_path(grid, cell) is None:
        raise PermissionError("Place has no current observed-free approach")
    return Destination("place:"+digest([grid.fingerprint, place_id, current_anchor])[:24],
                       "place", place_id, cell, grid.basis, grid.fingerprint, evidence_ids, False)
