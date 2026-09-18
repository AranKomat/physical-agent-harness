# Legal Observation and RTSM Sidecar

Both adapters use only the standard library and harness `WorldState`. No native
BEHAVIOR, RTSM, GPU, network client, pickle, or model API is imported or invoked.
Transport, artifact storage, native action conversion and localization are
injected. These are trusted integration boundaries, not a malicious-code sandbox.

## BEHAVIOR

`BehaviorAdapter(source, episode_id=..., action_bounds=[[-1, 1], ...],
action_codec=None, pose_estimator=None, logger=None)` wraps `source.reset()` and
`source.step(native_action)`. Both return the following normalized JSON object:

```json
{
  "schema_version": 1,
  "episode_id": "episode-1",
  "observation_id": "frame-0",
  "sim_time": 0,
  "rgb_refs": {"head": "sha256:rgb-artifact"},
  "depth_refs": {"head": "sha256:depth-artifact"},
  "proprioception": {"joint_positions": [0, 0]},
  "camera_intrinsics": {
    "head": {"width": 640, "height": 480, "fx": 500, "fy": 500,
             "cx": 320, "cy": 240, "depth_scale_m": 0.001}
  },
  "camera_frames": {"head": "head_optical"}
}
```

Optional proprio fields: `joint_velocities` (matching joint count),
`gripper_positions`, `base_velocity` (three components). All are finite numeric
lists. Additional fields at every schema boundary are rejected, including scores,
reward, termination, global pose, segmentation and scene geometry. A trusted
native wrapper must select legal sensor channels before forming this envelope;
do not pass Gym observation/info tuples. Camera refs/calibrations must have
identical keys. Optical frames are named `<camera>_optical`.

`pose_estimator(legal_observation)` may add `estimated_pose`:

```json
{
  "method": "rgbd_odometry",
  "frame": "local_map",
  "camera": "head",
  "transform": [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
  "evidence_ids": ["frame-0"],
  "confidence": 0.95
}
```

The transform is camera-to-arbitrary-local-map in meters; rotation must be
proper and rigid. Methods: `rgbd_odometry`, `proprio_odometry`, `rgbd_slam`.
The source itself cannot supply this field. The estimator must actually derive
pose from legal observations; provenance labels alone cannot prove that.
Calibration must come from trusted sensor configuration, not scene traversal.
The reference-only adapter cannot inspect pixel alignment, artifact hashes or
content; the injected artifact writer/reader must validate those.

`LegalObservation` retains original positional fields and adds `episode_id`,
`estimated_pose`, `schema_version`. No shared contracts changed. Use
`to_envelope()`/`from_envelope()` for detached, validated JSON transport. Dataclass
nested mappings are not deeply immutable; each boundary revalidates and copies.
`step([numbers], source_observation_id=...)` checks bounded action vectors and
optional stale-command correlation before calling the native codec. Runtime must
provide that ID for asynchronous commands. Reset is single-use; source failures
require a new episode. The logger receives legal frame envelopes suitable for
JSONL/video-frame indexing; video encoding stays in the source process. Scoring is
not available through the adapter.

## RTSM

Construct `RTSMWorldAdapter(world, source=callable, sim_clock=callable,
max_age_s=5, max_pending=32)`. `observe(observation, now=sim_time)` calls the injected
sidecar and ingests its reply. For asynchronous transport use
`build_request(observation)` and `ingest_snapshot(reply, now=sim_time)`.

Request: `{"schema_version":1,"type":"rtsm.observe","observation":<envelope>}`.
Reply:

```json
{
  "schema_version": 1, "episode_id": "episode-1",
  "observation_id": "frame-0", "sim_time": 0,
  "objects": [{"entity_id": "candle-1", "label": "candle",
               "position": [1,0,1], "confidence": 0.95,
               "identity_candidates": []}],
  "relations": [{"subject": "candle-1", "predicate": "HELD_BY",
                 "object": "robot", "confidence": 0.98}]
}
```

RTSM positions must already be in the input's local map. The service performs
association; identical labels do not merge IDs. Nonempty `identity_candidates`
preserves ambiguity and disables predicate verification for that identity.
Missing objects acquire inferred `visibility=not_observed`; their last-seen
location and relations remain in history. Movement replaces the active location.
Timestamp/episode must exactly match a registered input; out-of-order/expired
replies return `False`, malformed/unsolicited/replayed replies raise `ValueError`.
There are no implicit retries. Use a new episode on restart or transport failure.

Relations: `IN`, `ON`, `HELD_BY`, `NEXT_TO`, `OPEN`, `CLOSED`. The initial protocol
allows one target per subject/predicate. OPEN/CLOSED use `object="true"` and share
the `open_state` belief. Other relation targets must be observed IDs or `robot`.
Verification expressions are `OPEN(id)`, `CLOSED(id)`, or `IN(id,target)` etc.

World evidence records the legal input and validated reply together. Beliefs
include label, location JSON, visibility, confidence and identity candidates.
`predicate_evidence(expression)` returns a tuple of supporting WorldState IDs
only with a fresh injected simulator clock, matching current observed beliefs,
visible endpoints and unambiguous identity. A newer snapshot clears old support.
Same-time conflict events invalidate support even when the retained belief still
matches; newer uncontested evidence can restore it. Confidence numbers are raw
service estimates, not calibrated probabilities or guarantees of identity.
No clock means no verification support. `predicate_confidence` returns `None`
when live evidence is unavailable. The legacy unbound confidence setter never
produces supporting evidence and cannot be used on a bound adapter.

## Shared API Gaps

No shared files were edited. WorldState currently lacks a public atomic snapshot
write API, durable adapter watermark/entity enumeration and public evidence
lookup. Replies are fully prevalidated before writing, but storage failure
mid-write can leave partial state. Fail the episode on storage errors; do not
resume/recreate the adapter in an existing episode. Atomic persistence and warm
restart support need a shared API from the owner. An adapter does not consume
scorer information or infer action success from requested commands.
Until a public conflict lookup exists, verification performs an episode-scoped,
read-only SQL query of `world.db` events, matching WorldState's completion gate.

Patterns inspected in the sibling physical-ai-lab: observation allowlisting,
episode/action correlation, detached sensor snapshots, rigid estimated pose
validation. No native types or heavy imports were copied into the contracts.
