# Bounded Exploratory Staging

Run completed: `sam-live-staging-20260924-r1`. Development radio instance 301,
seed 1. No paid calls, no automatic retry, no grasp or policy handoff afterward.

## Why This Run

The preceding 6.04 cm probe exercised the live geometry/controller connection,
but its final visible surface was 1.3296 m from the held-torso shoulder against
an optimistic 0.87155 m arm radius. A retained endpoint survey at 2 cm increments
found that another 62 cm of base travel would be needed even to enter that radius;
observed scene-point/base-hull intrusions began at 70 cm. Radius is not IK, and
zero sampled intrusions is not free space. Near-start points within 20 mm of the
robot are ambiguous, not certified self. The scene cloud used stride-four depth
from all three legal cameras; no simulator object poses were used.

Do not drive to the edge of this narrow theoretical window. This trial aims for
substantial closer staging before torso/arm planning, not base-only reachability.
Retained geometry informs development of the bounded protocol only; fresh captures
and fresh SAM selection determine every runtime target. This is not a held-out
or zero-shot benchmark comparison.

## Frozen Bounds

- 768 unchanged Behavior-Skill acquisition actions, fresh synchronous SAM captures.
- Explicit `staging` profile: 0.049 m/s commanded speed, within unchanged 0.05 m/s
  codec cap; at most 320 move actions, nominal integral at most 0.5227 m.
- Stop on 45 cm measured path; hard abort at 50 cm. The original `probe` profile
  still uses 8 cm commanded/stop and 10 cm hard abort.
- At most 500 total controller actions: 60 preholds, 320 moves, 60 final holds,
  and 60 reserved abort holds. 900 s work plus 180 s braking reserve.
- Existing joint drift, observed speed/rotation, target continuity, two-second
  SAM-consumption age and final-stop predicates unchanged. Unknown clearance remains
  explicit; no strict admission follows from exploratory completion.
- SAM capacity 576 covers worst-case acquisition/probe captures without recycling
  IDs or silently reacquiring. Original callers retain their smaller defaults.
- Frozen policy service unloads only after native acquisition has completed and a
  unique current SAM selection is published. No subsequent policy use is scheduled.
- Owner GPU ceiling remains 23,552 MiB. Low priority and CPU affinity 19-22.

Prelaunch tests caught an over-cap proposed speed and an over-cap feedback horizon;
the profile was reduced to fit existing codec and 2,000-row feedback limits. Those
checks were not weakened, and no native attempt used the rejected configurations.

## Outcome

The bounded exploratory trial and independent receipt audit passed. This is not
strict navigation qualification or native task success.

| Measurement | Result |
|---|---:|
| Frozen policy acquisition actions | 768 |
| Controller actions | 324 (6 preholds, 312 moves, 6 final holds) |
| Measured RGB-D/FK path | 0.451119 m |
| Commanded integral | 0.5096 m |
| Visible surface planar range, before / after | 1.2798 / 0.8374 m |
| Fresh captures / tracked target proposals | 351 / 326 |
| Median / maximum target consumption age | 1.3664 / 1.7274 s |
| Maximum SAM archive age | 0.8443 s |
| Controller wall time | 695.87 s |
| Peak owner-observed GPU memory | 23,136 MiB |
| Final stop / worker cleanup | Observed / completed |
| Native task success | False |
| Clearance | Unknown |
| Paid calls | 0 |

Archive hashes and exact RGB/depth/capture bindings passed the independent audit.
There were no hard aborts or brake errors. Range measures a view-dependent visible
surface, not an object center. No grasp, lift, or policy handoff followed this move.
See [receipt](SAM_LONG_STAGING_RECEIPT.json).

## Endpoint And Next Gate

The final fresh source-bound surface is still outside both optimistic held-torso
arm radii: left shoulder distance 0.99570 m versus radius 0.87155 m; right distance
0.90613 m versus radius 0.87104 m. These bounds ignore joint limits, orientation,
and collision, so even being inside would not establish grasp feasibility.

An offline translation-only calculation first enters the right radius at another
6 cm and the left radius at 18 cm. **These are not approved drive targets or
clearance estimates.** Do not extend base motion on that basis. Next evaluate
torso/arm posture, IK, observed obstacles, and return-path support from the retained
endpoint; any eventual execution needs a fresh in-episode observation and its
appropriate gates. See [endpoint reach screen](SAM_LONG_STAGING_REACH.json) and the
[torso-only screen](SAM_STAGING_TORSO_SCREEN.md). The torso-only screen suggests
that the distance gap may be removable with a large posture change, but it is not
an IK or clearance result.

Phase 5/6 exploratory integration advanced; strict Phase 6 is not complete and
this trial earns no Phase 7-9 manipulation completion. Repository verification:
1,514 tests passed, Ruff passed, repository ownership/local links passed; 11
additional private SAM streaming tests passed.
