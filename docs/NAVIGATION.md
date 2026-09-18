# Navigation Prototype

This is a deterministic CPU prototype, not native BEHAVIOR navigation, SLAM,
or a deployment-qualified safety controller. No paid APIs or GPU services are
used. Existing public request, receipt, place and edge dataclasses are unchanged.
NetworkX (3.2 or newer, below 4) supplies both shortest-path implementations.

The repository includes an optional Open3D `RGBDOdometry` implementation that
can supply legal camera-to-local-map transforms. It is not yet qualified as the
native navigator's localization source; this document's controller and mapping
limitations still apply.

## Integration

`MetricNavigation` implements `NavigationBackend.navigate(request)`. Construct
it with an episode-scoped `OccupancyMap` and three injected callbacks:

- `observe() -> DepthObservation`: fresh, calibrated legal depth and estimated
  local pose, evidence ID and simulation timestamp.
- `move((x, y))`: execute one adjacent grid waypoint, with bounded controller
  duration, collision monitoring and velocity limits owned by the N0 adapter.
- `resolve(name) -> (x, y) | None`: a perceived destination or safe approach
  waypoint in the same arbitrary local frame. Never simulator entity poses.

Optional `publish=event_bus.publish` emits existing `RuntimeEvent` contracts.
The backend does not mutate world beliefs. It reports arrival only after a
fresh estimated pose is within tolerance. Commands alone never prove arrival.
Use a new map/backend for each episode; cross-episode frames are rejected.
Set `execution_epoch` when invalidating execution, or call `cancel(nav_id)`.
Cancellation and deadlines are checked between synchronous callback calls;
callbacks must bound their own execution and cannot be preempted here.

## Geometry And Mapping

Depth is a rectangular tuple of rows of optical z values in meters. The
prototype requires a horizontal camera: optical +z is base +x, optical +x is
base -y, XY camera translation is zero, and camera height is supplied. Pose
is camera/base XY and yaw estimated using odometry, visual odometry or SLAM.
Adapters must transform camera calibration to this convention; arbitrary
pitch, roll and camera extrinsics are not implemented. The pose-source tag
is a validation guard, not proof of sensor provenance. Upstream adapters
must enforce the no-privileged-state boundary.

Only finite positive depths below the range limit contribute. Missing,
saturated, floor and ceiling rays do not clear space. Rays within the
0.15-1.5 meter collision-height band clear traversed cells; endpoints mark
occupied cells. Hits win over clearing within a frame. A newer ray can clear
a previous obstacle; stale or duplicate timestamps cannot change the map.
Footprint inflation treats unknown and occupied cells as blocked. Planning
uses deterministic four-connected NetworkX shortest paths with no diagonal
corner cutting. Radius rounds up to whole cells and uses a square footprint.

This is a sparse 2D ray model, not a complete free-volume reconstruction.
It does not certify floor support, detect all overhangs, fuse contradictory
height layers, model localization covariance, or compensate SLAM loop closure.
Range data quality and camera coverage remain important limitations. Maps
are bounded and never automatically expanded. The default inflation is
deliberately restrictive and thin scans may have no safe path.

## Semantic Routing And Resume

Use `TopologicalMap.update_gateway(entity_id, state, evidence_ids)` for
observed open/closed/unknown states, never merely after issuing an open
command. Gateway states default to unknown, so existing edges with a gateway
ID require observed-open evidence even when `traversable=True`.

Routing prefers a fully open alternative. If none exists but a route through
a gateway does, navigation returns a blocked receipt and one `DOOR_BLOCKED`
event per call, including the blocking entity and observation evidence. It
does not repeatedly command movement at a closed door. After a fresh gateway
state update, call `navigate` again to resume from the last reached place and
recompute the route. Topological place geometry must also be supplied by
the legal resolver; topology is not a source of metric coordinates.

Unknown targets explore reachable known-free frontier approach cells. Fresh
observations and target resolution run after each move. Exploration terminates
on target discovery, exhausted frontiers, stall, cancellation, deadline or
step budget. No unknown cell is commanded as a waypoint. Visit history is
per call; repeated executive retries can revisit frontiers. Known targets
with no safe path return `PATH_BLOCKED`, not speculative unknown-space motion.

Receipts include map evidence, observed distance, map-change replan count,
movement steps and visited exploration cells. Replanning occurs on every
control iteration; the replan metric counts map revisions after initialization.

## Verification

Run `python -m pytest tests/test_navigation.py -q` with NetworkX and pytest
installed. Tests replay calibrated synthetic legal-depth inputs and use an
idealized local waypoint controller, not physical simulation. They cover
observed waypoint arrival, dynamic obstacle detours, closed-door events and
resume, alternative semantic routes, target discovery through exploration,
bounded unsuccessful exploration, inflation, stale observations, invalid
depth, pose-source and episode rejection, cancellation and execution bounds.
