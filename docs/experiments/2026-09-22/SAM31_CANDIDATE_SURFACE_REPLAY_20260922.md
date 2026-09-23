# Candidate mask/depth/pose replay

## Results

Offline joins preserve the original fixed 384-512 window:

| Retained trace and acquisition | Candidate-bearing boundaries | Largest depth patch support | Neighbor-cloud p95 distance |
| --- | --- | --- | --- |
| Cached-pose trace, fixed `radio` category | 5/5 | 80.2-81.9% | 4.4-6.0 mm |
| Previously empty fusion trace, `a radio` image acquisition then tracking | 4/5 | 79.6-81.0% | 5.6-6.8 mm |

The remaining empty boundary is action 384 on the second trace. It is retained,
not excluded to manufacture complete coverage. The two rows use different
prompts/traces and are not a controlled prompt comparison.

All valid masked depth pixels are partitioned with the existing connectivity
routine; all patches remain in the report. The largest patch is inspected for
diagnostic consistency only. Review overlays place it on the radio body, with
other depth components around boundaries/handle regions. This is not an automatic
semantic part label, object center, contact surface, or collision certificate.

Neighboring largest-patch clouds are transformed using the saved sensor-derived
camera poses. Bidirectional nearest-point distances are computed without any
additional alignment or pose refitting. These are internal consistency measures:
shared depth/calibration/pose errors can remain consistent. They do not prove
absolute metric accuracy or safe manipulation geometry.

## Provenance and timing

The new private `replay_candidate_surfaces.py` checks native receipt hashes,
pose-audit binding, replay-audit hashes, chronological capture order, same-frame
RGB/depth/stamp/time agreement, rigid transforms, mask artifact hashes, tracker
IDs and bounded aligned depth support. It rejects multiple candidates rather
than silently choosing an identity. No simulator object truth is read.

This is explicitly **offline**. New masks are not assigned the old live mask
availability timestamps. The report claims neither live latency nor historical
availability of these replay computations. Existing live joins remain unchanged.
No GPU, model call, new robot action or motion authority was needed.

Private local artifacts:

- `sam31-category-surfaces-20260922-r2`: cross-trace five-view report and review.
- `sam31-acquired-surfaces-20260922-r1`: previously empty trace, five boundaries
  with four candidate clouds, report and review.
- `sam31-category-surfaces-20260922-r1`: failed initial attempt before results;
  the explicit depth scale argument was missing and was corrected to 1 metre/unit,
  matching the validated packet and existing depth diagnostics. Failure preserved.

Both successful reports record source, pose and replay SHA-256 hashes. The 34
existing focused depth-partition, same-frame join, surface-consumer and live-audit
tests pass; the new replay script passes Ruff. Both output sheets were inspected.

## Next experiment

Run the fixed category/acquisition configuration in a fresh bounded native shadow
trial while retaining frozen policy control and all existing gates. Measure
candidate-bearing same-frame joins and end-to-end freshness together. Keep
semantic identity confirmation, realistic occlusion/same-class distractors,
independent pose validation, and low-clearance qualification open. Do not promote
the largest visible patch directly into a grasp target or motion authorization.
