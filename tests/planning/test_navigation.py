import math
from dataclasses import replace

import pytest

from physical_harness.core.contracts import NavigationRequest
from physical_harness.core.events import EventType
from physical_harness.planning.navigation import (
    DepthObservation,
    LocalPose,
    MetricNavigation,
    OccupancyMap,
)
from physical_harness.world.topology import PlaceEdge, PlaceNode, TopologicalMap


def frame(t, pose=LocalPose(1.5, 3.5), depth=((0.0,),), **kwargs):
    return DepthObservation("episode", f"depth-{t}", t, pose, depth, 1.0, 1.0, 0.0, 0.0, **kwargs)


def mapped_room(radius=0):
    grid = OccupancyMap(
        "episode", resolution=1, bounds=(0, 0, 8, 8), robot_radius=radius, max_depth=12
    )
    # A replay of eight calibrated horizontal range observations, not GT cells.
    for row in range(8):
        grid.integrate(frame(row, LocalPose(0.5, row + 0.5), ((8.0,),)))
    return grid


class ReplayController:
    """Idealized local controller for deterministic CPU acceptance, not physics."""

    def __init__(self, pose=LocalPose(1.5, 3.5), obstacle=False, stall=False):
        self.pose, self.obstacle, self.stall = pose, obstacle, stall
        self.t = 10
        self.moves = []

    def observe(self):
        self.t += 1
        depth = ((1.0,),) if self.obstacle and len(self.moves) == 1 else ((0.0,),)
        return frame(self.t, self.pose, depth)

    def move(self, xy):
        self.moves.append(xy)
        if not self.stall:
            self.pose = LocalPose(*xy)


def service(grid=None, controller=None, goals=None, **kwargs):
    grid = mapped_room() if grid is None else grid
    controller = controller or ReplayController()
    goals = {"waypoint": (6.5, 3.5)} if goals is None else goals
    events = []
    nav = MetricNavigation(
        grid, controller.observe, controller.move, goals.get, publish=events.append, **kwargs
    )
    return nav, controller, events


def test_reaches_visible_waypoint_from_observed_pose():
    nav, control, events = service()
    receipt = nav.navigate(NavigationRequest("nav", "waypoint"))
    assert receipt.outcome == "arrived"
    assert control.pose == LocalPose(6.5, 3.5)
    assert receipt.distance_remaining_m == 0
    assert receipt.metadata["distance_m"] == 5
    assert receipt.evidence_ids and events[-1].type == EventType.ARRIVED


def test_new_depth_obstacle_replans_and_detours():
    nav, control, events = service(controller=ReplayController(obstacle=True))
    receipt = nav.navigate(NavigationRequest("nav", "waypoint"))
    assert receipt.outcome == "arrived"
    assert nav.map.cells[(3, 3)] is True
    assert (3.5, 3.5) not in control.moves
    assert any(y != 3.5 for _, y in control.moves)
    assert receipt.metadata["replans"] >= 1
    assert receipt.metadata["distance_m"] > 5


def topology():
    graph = TopologicalMap()
    for place in ("room_a", "room_b", "corridor"):
        graph.upsert_node(PlaceNode(place, place, "room"))
    graph.add_edge(PlaceEdge("room_a", "room_b", gateway_entity="door"))
    graph.update_gateway("door", "closed", ("closed-depth",))
    return graph


def test_closed_door_event_no_loop_and_resume_after_observed_open():
    graph = topology()
    nav, control, events = service(
        topology=graph, current_place="room_a", goals={"room_b": (6.5, 3.5)}
    )
    request = NavigationRequest("nav", "room_b")
    blocked = nav.navigate(request)
    assert blocked.outcome == "blocked" and blocked.blocking_entity == "door"
    assert [e.type for e in events] == [EventType.DOOR_BLOCKED]
    assert not control.moves
    graph.update_gateway("door", "open", ("open-depth",))
    assert nav.navigate(request).outcome == "arrived"
    assert nav.current_place == "room_b"


def test_semantic_route_uses_open_alternate():
    graph = topology()
    graph.add_edge(PlaceEdge("room_a", "corridor", cost=2))
    graph.add_edge(PlaceEdge("corridor", "room_b", cost=2))
    assert [e.b for e in graph.route("room_a", "room_b")] == ["corridor", "room_b"]


def test_unknown_gateway_requires_evidence():
    graph = topology()
    graph.update_gateway("door", "unknown", ("ambiguous",))
    assert graph.route("room_a", "room_b") is None
    with pytest.raises(ValueError):
        graph.update_gateway("door", "open", ())


def exploration_map():
    grid = OccupancyMap("episode", resolution=1, bounds=(0, 0, 8, 8), robot_radius=0)
    grid.integrate(frame(1, LocalPose(0.5, 3.5), ((5.0,),)))
    return grid


def test_unknown_target_explores_then_perception_resolves_target():
    nav, control, _ = service(grid=exploration_map(), goals={})
    nav.resolve = lambda name: (4.5, 3.5) if len(control.moves) >= 2 else None
    receipt = nav.navigate(NavigationRequest("nav", "missing_entity"))
    assert receipt.outcome == "arrived"
    assert receipt.metadata["exploration_frontiers"] >= 2
    assert len(control.moves) >= 2


def test_unknown_target_exhausts_without_oscillating_forever():
    nav, control, events = service(grid=exploration_map(), goals={})
    receipt = nav.navigate(NavigationRequest("nav", "missing"))
    assert receipt.outcome == "target_not_found"
    assert len(control.moves) < 12
    assert events[-1].type == EventType.PLAN_EXHAUSTED


def test_unknown_target_exploration_disabled():
    nav, control, events = service(goals={})
    assert (
        nav.navigate(NavigationRequest("nav", "missing", allow_exploration=False)).outcome
        == "target_not_found"
    )
    assert not control.moves and events[-1].type == EventType.TARGET_LOST


def test_observed_stall_is_not_arrival():
    nav, control, events = service(controller=ReplayController(stall=True))
    receipt = nav.navigate(NavigationRequest("nav", "waypoint"))
    assert receipt.outcome == "blocked"
    assert receipt.metadata["reason"] == "controller_stalled"
    assert len(control.moves) == 3


def test_inflation_blocks_obstacle_neighbors_and_unknown_boundary():
    grid = mapped_room(radius=0.1)
    grid.integrate(frame(10, LocalPose(2.5, 3.5), ((1.0,),)))
    graph = grid.graph()
    assert (3, 3) not in graph and (2, 3) not in graph and (4, 3) not in graph
    assert (0, 0) not in graph
    assert (1, 1) in graph


def test_invalid_depth_does_not_clear_and_stale_frame_rejected():
    grid = mapped_room()
    grid.integrate(frame(10, LocalPose(2.5, 3.5), ((1.0,),)))
    revision = grid.revision
    grid.integrate(frame(11, depth=((0, -1, math.nan, math.inf, 12),)))
    assert grid.revision == revision and grid.cells[(3, 3)] is True
    assert not grid.integrate(frame(9, LocalPose(2.5, 3.5), ((3.0,),)))
    assert grid.cells[(3, 3)] is True
    grid.integrate(frame(12, LocalPose(2.5, 3.5), ((3.0,),)))
    assert grid.cells[(3, 3)] is False  # New ray proves old obstacle absent.


def test_local_camera_projection_respects_yaw_and_intrinsics():
    grid = OccupancyMap("episode", resolution=1, robot_radius=0)
    grid.integrate(frame(1, LocalPose(0.5, 0.5, math.pi / 2), ((2.0,),)))
    assert grid.cells[(0, 2)] is True
    assert grid.cells[(0, 1)] is False
    assert (1, 0) not in grid.cells


@pytest.mark.parametrize(
    "mutation",
    [
        {"episode_id": "other"},
        {"pose_source": "simulator_gt"},
        {"fx": 0},
        {"pose": LocalPose(math.nan, 0)},
    ],
)
def test_rejects_wrong_episode_or_untrusted_geometry(mutation):
    grid = mapped_room()
    before = dict(grid.cells)
    with pytest.raises(ValueError):
        grid.integrate(replace(frame(10), **mutation))
    assert grid.cells == before


def test_known_target_unknown_space_is_blocked():
    nav, control, events = service(grid=exploration_map(), goals={"waypoint": (6.5, 3.5)})
    assert nav.navigate(NavigationRequest("nav", "waypoint")).outcome == "blocked"
    assert not control.moves
    assert events[-1].type == EventType.PATH_BLOCKED


def test_cancel_epoch_and_step_budget():
    nav, control, _ = service(max_steps=1)
    assert (
        nav.navigate(NavigationRequest("old", "waypoint", execution_epoch=1)).outcome == "cancelled"
    )
    nav.cancel("cancel")
    assert nav.navigate(NavigationRequest("cancel", "waypoint")).outcome == "cancelled"
    assert not control.moves
    assert nav.navigate(NavigationRequest("nav", "waypoint")).outcome == "timeout"
    assert len(control.moves) == 1


def test_wall_deadline_is_checked_after_observation_before_move():
    ticks = iter([0, 0, 2])
    nav, control, events = service(clock=lambda: next(ticks))
    assert nav.navigate(NavigationRequest("nav", "waypoint", max_wall_s=1)).outcome == "timeout"
    assert not control.moves


def test_semantic_waypoints_are_visited_in_order():
    nav, control, _ = service(goals={"via": (1.5, 5.5), "waypoint": (6.5, 3.5)})
    assert (
        nav.navigate(NavigationRequest("nav", "waypoint", semantic_waypoints=("via",))).outcome
        == "arrived"
    )
    assert control.moves.index((1.5, 5.5)) < control.moves.index((6.5, 3.5))
