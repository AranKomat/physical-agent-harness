# Natural Sofa Loss And Return

## Protocol

Phase 2 lacked a natural full-out-of-view/reappearance example. Visual screening
of retained Corvid and Kmy trash-task videos identified two camera-turn loss
segments in Corvid's existing 6,000-frame, 30 fps rollout. No new policy trial
was run. The selected source is
`shortlist-corvid-extended-20260921-r1/picking_up_trash/trial-0/rollout.mp4`.

Before inference, freeze frames 1320 through 3480 inclusive at stride 180:
13 chronological observations, six seconds apart in video presentation time.
Crop the rightmost 448-square onboard head view from the 672x448 composite;
bilinearly resize to 720 square for the existing worker contract. Wrist panels,
task state and evaluator truth are not supplied to SAM.

One SAM 3.1 session uses prompt `sofa`, official-file preprocessing and initial
image acquisition, with no later explicit reset or retry. Pre-inference visual
review marks frames 2220, 2400, 2940 and 3120 absent; all other selected frames
have visible sofa pixels, including partial edge views. These labels remain
evaluation-only and were not sent to the worker.

## Results

All 13 steps completed. All 1,589 loaded learned parameter tensors matched the
pinned checkpoint. No deadline or retry occurred.

| Video frame | Visibility review | Local SAM ID |
| --- | --- | --- |
| 1320 | Present | 0 |
| 1500 | Present | 0 |
| 1680 | Present | 0 |
| 1860 | Present | 0 |
| 2040 | Present | 1 |
| 2220 | Absent | Empty |
| 2400 | Absent | Empty |
| 2580 | Present again | 1 |
| 2760 | Present | 2 |
| 2940 | Absent | Empty |
| 3120 | Absent | Empty |
| 3300 | Present again | 2 |
| 3480 | Present | 3 |

All nine visible frames have nonempty masks and all four absent frames have
empty outputs. Overlay inspection shows masks on the sofa, without obvious
carried-bin or robot-arm leakage. There are no pixel-level ground-truth masks,
so these counts are visibility agreement, not segmentation accuracy.

First inference took 495 ms; warm median was 145 ms, excluding model load,
network transfer and image preparation. GPU memory returned to zero after exit.
Work used the existing four-core low-priority allocation and thread caps. No
system changes, instance lifecycle changes, robot actions or paid calls occurred.

## Interpretation

This fills a missing natural camera-turn loss/return tracking example for
Phase 2 scenarios 5 and 6. It does not complete Phase 2. In particular:

- Six-second sparse observations are not dense video performance.
- Natural camera-turn disappearance is not physical occlusion behind an object.
- Local IDs change even across visible frames, and reappear after absence.
  Neither continuity nor change of local ID establishes physical identity.
- No independent association producer, current metric geometry, manipulation
  binding, similar-object crossing, or valid-binding invalidation is qualified.
- Video presentation time is not qualified native sensor/availability time.

The next useful integration is consuming these real empty/return packets through
the runtime's loss and reacquisition boundary. Do not report a previously
unbindable candidate as evidence that valid geometry was invalidated on loss.

## Retention

Full model outputs and prepared images are local in
`runs/natural-sofa-loss-20260924-r1`; hash-checked overlays and analysis are in
`runs/natural-sofa-loss-analysis-20260924-r1`. The original videos remain local.

| Artifact | SHA-256 |
| --- | --- |
| Frozen plan | `a899ebc0495ec51413b40b8caa4bd32b59d895c12fdd34992e08294a5ff332cc` |
| Pre-inference visibility review | `930f81014c2d4f40c3db1b086c61548107ccfc932c1fe6ed1fb331803e2c5256` |
| Worker status | `75ef46274dbba9689d219d32406a4b204154e377700787ebb39a84998728f803` |

Preparation and analysis scripts pass Ruff. Analysis verifies source-image and
mask hashes, shape, IDs and pixel-count summaries for every returned packet.

## Packet-To-Ledger Replay

`natural-sofa-identity-20260924-r1` subsequently consumed all 13 actual packets
through the public `Tracklet`, `IdentityLedger`, `AssociationProof` and
`focus_identity_view` contracts with a SQLite journal. Source and mask hashes,
IDs, shapes and pixel-count summaries were checked before consumption. Evaluation
visibility labels were not read by this replay.

All four empty packets produced `not_observed`. Returning masks produced
`identity_uncertain`, including frames 2580 and 3300 which reuse the IDs seen
before loss. No canonical label or action binding was granted. Reloading the
journal after each of the 13 events reconstructed identical state.

This is fixture-clock packet integration, not live sensor timing or physical
association qualification. There was no valid pre-loss metric binding: the
sequence lacks qualified metric geometry and independent recognition/association
proof. Consequently it does not prove invalidation of previously valid native
geometry. The separate public identity suite's synthetic valid-binding loss
control remains separately scoped; all 20 identity tests pass.

The live SAM publisher still publishes shadow observations and does not itself
consume these results into the ledger. This replay must not be described as a
deployed live loss handler. No public runtime code changed for this follow-up.

Decision: the actual empty/return packet boundary is now exercised. Do not repeat
this negative replay. Remaining Phase 2 work requires independent association
evidence and similar-object ambiguity/crossing cases, rather than more local-ID
persistence or another easy single-object tracking run.
