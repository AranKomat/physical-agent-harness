"""CPU-only, bounded navigation prototype; not a native base controller or SLAM."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable

import networkx as nx

from .contracts import EventType, NavigationReceipt, NavigationRequest, RuntimeEvent
from .navigation import TopologicalMap

Cell = tuple[int, int]


@dataclass(frozen=True)
class LocalPose:
    x: float
    y: float
    yaw: float = 0.0


@dataclass(frozen=True)
class DepthObservation:
    """Optical z-depth in meters, horizontal calibrated camera, local odometry.

    Camera +z faces base +x, camera +x faces base -y. Camera translation
    relative to the base is zero in XY; height is explicit. No global pose,
    segmentation, oracle target positions, or simulator scene inputs exist.
    """

    episode_id: str
    evidence_id: str
    sim_time: float
    pose: LocalPose
    depth: tuple[tuple[float, ...], ...]
    fx: float
    fy: float
    cx: float
    cy: float
    camera_height: float = 0.7
    pose_source: str = "odometry"


class OccupancyMap:
    """Sparse bounded grid. Unknown is blocked; only measured rays clear cells."""

    def __init__(
        self,
        episode_id: str,
        *,
        resolution: float = 0.2,
        bounds: tuple[int, int, int, int] = (-100, -100, 100, 100),
        robot_radius: float = 0.25,
        max_depth: float = 8.0,
    ):
        if (
            not episode_id
            or not all(math.isfinite(v) for v in (resolution, robot_radius, max_depth))
            or resolution <= 0
            or robot_radius < 0
            or max_depth <= 0
            or len(bounds) != 4
            or not all(isinstance(v, int) for v in bounds)
            or bounds[0] >= bounds[2]
            or bounds[1] >= bounds[3]
        ):
            raise ValueError("Invalid map configuration")
        self.episode_id = episode_id
        self.resolution = resolution
        self.bounds = bounds
        self.robot_radius = robot_radius
        self.max_depth = max_depth
        self.cells: dict[Cell, bool] = {}  # True occupied, False observed free
        self.revision = 0
        self.last_time = -math.inf
        self.evidence_ids: list[str] = []

    def cell(self, x: float, y: float) -> Cell:
        return math.floor(x / self.resolution), math.floor(y / self.resolution)

    def center(self, cell: Cell) -> tuple[float, float]:
        return tuple((v + 0.5) * self.resolution for v in cell)

    def inside(self, cell: Cell) -> bool:
        x, y = cell
        a, b, c, d = self.bounds
        return a <= x < c and b <= y < d

    def integrate(self, obs: DepthObservation) -> bool:
        if obs.episode_id != self.episode_id:
            raise ValueError("Observation belongs to another episode")
        if obs.pose_source not in {"odometry", "slam", "visual_odometry"}:
            raise ValueError("Only estimated local pose sources are allowed")
        values = (
            obs.sim_time,
            obs.pose.x,
            obs.pose.y,
            obs.pose.yaw,
            obs.fx,
            obs.fy,
            obs.cx,
            obs.cy,
            obs.camera_height,
        )
        if (
            not all(math.isfinite(v) for v in values)
            or obs.fx <= 0
            or obs.fy <= 0
            or not obs.evidence_id
            or not obs.depth
            or not obs.depth[0]
            or any(len(row) != len(obs.depth[0]) for row in obs.depth)
        ):
            raise ValueError("Invalid calibrated depth observation")
        if obs.sim_time <= self.last_time:
            return False
        free, hits = set(), set()
        cosine, sine = math.cos(obs.pose.yaw), math.sin(obs.pose.yaw)
        for v, row in enumerate(obs.depth):
            for u, z in enumerate(row):
                if not math.isfinite(z) or not 0 < z < self.max_depth:
                    continue  # Missing/saturated measurements are not free space.
                height = obs.camera_height - (v - obs.cy) * z / obs.fy
                if not (0.15 <= height <= 1.5 and 0.15 <= obs.camera_height <= 1.5):
                    continue  # No carving using floor/ceiling rays.
                lateral = -(u - obs.cx) * z / obs.fx
                dx, dy = cosine * z - sine * lateral, sine * z + cosine * lateral
                if math.hypot(dx, dy) >= self.max_depth:
                    continue
                endpoint = self.cell(obs.pose.x + dx, obs.pose.y + dy)
                count = max(1, math.ceil(math.hypot(dx, dy) / (self.resolution / 4)))
                for i in range(count):
                    cell = self.cell(obs.pose.x + dx * i / count, obs.pose.y + dy * i / count)
                    if self.inside(cell) and cell != endpoint:
                        free.add(cell)
                if self.inside(endpoint):
                    hits.add(endpoint)
        updated = dict(self.cells)
        updated.update((cell, False) for cell in free)
        updated.update((cell, True) for cell in hits)  # Hits win within a frame.
        if updated != self.cells:
            self.cells = updated
            self.revision += 1
        self.last_time = obs.sim_time
        self.evidence_ids.append(obs.evidence_id)
        self.evidence_ids = self.evidence_ids[-32:]
        return True

    def graph(self) -> nx.Graph:
        # Inflate obstacles AND unknown cells by a conservative square footprint.
        radius = math.ceil(self.robot_radius / self.resolution)
        safe = {
            c
            for c, occupied in self.cells.items()
            if not occupied
            and all(
                self.cells.get((c[0] + dx, c[1] + dy), True) is False
                for dx in range(-radius, radius + 1)
                for dy in range(-radius, radius + 1)
            )
        }
        graph = nx.Graph()
        graph.add_nodes_from(sorted(safe))
        for x, y in sorted(safe):
            for neighbor in ((x + 1, y), (x, y + 1)):
                if neighbor in safe:
                    graph.add_edge((x, y), neighbor)
        return graph

    def path(self, start: Cell, goal: Cell) -> list[Cell] | None:
        try:
            return nx.shortest_path(self.graph(), start, goal)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def frontier_path(self, start: Cell, visited: set[Cell]) -> list[Cell] | None:
        graph = self.graph()
        if start not in graph:
            return None
        paths = nx.single_source_shortest_path(graph, start)
        reach = math.ceil(self.robot_radius / self.resolution) + 1
        candidates = [
            path
            for cell, path in paths.items()
            if cell not in visited
            and any(
                self.inside(n) and n not in self.cells
                for n in (
                    (cell[0] + reach, cell[1]),
                    (cell[0] - reach, cell[1]),
                    (cell[0], cell[1] + reach),
                    (cell[0], cell[1] - reach),
                )
            )
        ]
        return min(candidates, key=lambda p: (len(p), p[-1])) if candidates else None


class MetricNavigation:
    """NavigationBackend using legal observations and an injected bounded N0 move.

    observe() must return a fresh frame. move(xy) executes at most one grid edge
    and must provide its own real-time collision checks and velocity limits.
    resolve(name) returns perceived local XY, never simulator target coordinates.
    Call navigate again after observed gateway updates to resume/replan.
    """

    name = "metric_navigation_prototype"

    def __init__(
        self,
        occupancy: OccupancyMap,
        observe: Callable[[], DepthObservation],
        move: Callable[[tuple[float, float]], None],
        resolve: Callable[[str], tuple[float, float] | None],
        *,
        topology: TopologicalMap | None = None,
        current_place: str | None = None,
        publish: Callable[[RuntimeEvent], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
        max_steps: int = 100,
        tolerance: float = 0.15,
    ):
        if max_steps <= 0 or not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("Invalid navigation bounds")
        self.map, self.observe, self.move, self.resolve = occupancy, observe, move, resolve
        self.topology, self.current_place = topology, current_place
        self.publish = publish or (lambda event: None)
        self.clock, self.max_steps, self.tolerance = clock, max_steps, tolerance
        self.execution_epoch = 0
        self.cancelled: set[str] = set()

    def cancel(self, nav_id: str) -> None:
        self.cancelled.add(nav_id)

    def navigate(self, request: NavigationRequest) -> NavigationReceipt:
        started = self.clock()
        if not math.isfinite(request.max_wall_s) or request.max_wall_s <= 0:
            raise ValueError("max_wall_s must be positive and finite")
        visited: set[Cell] = set()
        replans, steps, distance = 0, 0, 0.0
        previous_pose = None
        previous_revision = None
        stalled = 0
        remaining = None
        targets = list(request.semantic_waypoints) + [request.target_entity or request.destination]

        def finish(outcome, event=None, blocking=None, reason=None):
            evidence = tuple(self.map.evidence_ids)
            if blocking and self.topology:
                evidence += self.topology.gateway_evidence.get(blocking, ())
            metadata = {
                "replans": replans,
                "steps": steps,
                "distance_m": distance,
                "exploration_frontiers": len(visited),
                "reason": reason,
                "prototype": True,
            }
            if event:
                self.publish(
                    RuntimeEvent(
                        event,
                        self.map.episode_id,
                        max(0.0, self.map.last_time),
                        {
                            "nav_id": request.nav_id,
                            "blocking_entity": blocking,
                            "evidence_ids": evidence,
                            **metadata,
                        },
                    )
                )
            return NavigationReceipt(
                request.nav_id,
                outcome,
                reached_region=request.destination if outcome == "arrived" else None,
                evidence_ids=evidence,
                blocking_entity=blocking,
                distance_remaining_m=remaining,
                metadata=metadata,
            )

        for _ in range(self.max_steps + 1):
            if request.nav_id in self.cancelled or request.execution_epoch != self.execution_epoch:
                return finish("cancelled")
            if self.clock() - started >= request.max_wall_s:
                return finish("timeout", EventType.EXECUTION_TIMEOUT)
            obs = self.observe()
            if not self.map.integrate(obs):
                return finish("blocked", EventType.PATH_BLOCKED, reason="stale_observation")
            if request.nav_id in self.cancelled or request.execution_epoch != self.execution_epoch:
                return finish("cancelled")
            if self.clock() - started >= request.max_wall_s:
                return finish("timeout", EventType.EXECUTION_TIMEOUT)
            if previous_pose is not None:
                delta = math.hypot(obs.pose.x - previous_pose.x, obs.pose.y - previous_pose.y)
                distance += delta
                stalled = stalled + 1 if delta < 1e-4 else 0
                if stalled >= 3:
                    return finish("blocked", EventType.PATH_BLOCKED, reason="controller_stalled")
                previous_pose = None
            if previous_revision is not None and previous_revision != self.map.revision:
                replans += 1
            previous_revision = self.map.revision
            start = self.map.cell(obs.pose.x, obs.pose.y)
            name = targets[0]
            gateway_destination = None
            if (
                self.topology
                and self.current_place
                and name in self.topology.nodes
                and name != self.current_place
            ):
                route = self.topology.route(self.current_place, name)
                if route is None:
                    blocked_route = self.topology.route(
                        self.current_place, name, include_blocked=True
                    )
                    blocker = next(
                        (
                            edge.gateway_entity
                            for edge in blocked_route or []
                            if edge.gateway_entity
                            and (
                                not edge.traversable
                                or self.topology.gateway_states.get(edge.gateway_entity) != "open"
                            )
                        ),
                        None,
                    )
                    return finish(
                        "blocked",
                        EventType.DOOR_BLOCKED if blocker else EventType.PATH_BLOCKED,
                        blocker,
                        "gateway_requires_observation_or_opening",
                    )
                edge = route[0]
                gateway_destination = edge.b if edge.a == self.current_place else edge.a
                name = gateway_destination
            goal = self.resolve(name)
            if goal is not None and (len(goal) != 2 or not all(math.isfinite(v) for v in goal)):
                raise ValueError("Resolver must return finite local XY")
            if goal is not None:
                remaining = math.hypot(obs.pose.x - goal[0], obs.pose.y - goal[1])
                if remaining <= self.tolerance:
                    if gateway_destination:
                        self.current_place = gateway_destination
                        continue
                    if self.topology and name in self.topology.nodes:
                        self.current_place = name
                    targets.pop(0)
                    if not targets:
                        return finish("arrived", EventType.ARRIVED)
                    continue
                path = self.map.path(start, self.map.cell(*goal))
            elif request.allow_exploration:
                remaining = None
                visited.add(start)
                path = self.map.frontier_path(start, visited)
                if path is None:
                    return finish("target_not_found", EventType.PLAN_EXHAUSTED)
            else:
                return finish("target_not_found", EventType.TARGET_LOST)
            if path is None:
                return finish("blocked", EventType.PATH_BLOCKED, reason="no_known_safe_path")
            if steps >= self.max_steps or self.clock() - started >= request.max_wall_s:
                return finish("timeout", EventType.EXECUTION_TIMEOUT)
            if request.nav_id in self.cancelled or request.execution_epoch != self.execution_epoch:
                return finish("cancelled")
            waypoint = self.map.center(path[1]) if len(path) > 1 else goal
            previous_pose = obs.pose
            self.move(waypoint)
            steps += 1
        return finish("timeout", EventType.EXECUTION_TIMEOUT)
