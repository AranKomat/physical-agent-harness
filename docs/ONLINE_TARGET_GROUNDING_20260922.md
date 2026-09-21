# Online Target Grounding: Fresh Shadow Runs

## Decision

Three ordinary native radio resets completed with grounding run synchronously
at every policy boundary. This establishes an operational online RGB-to-depth
pipeline, **not qualified navigation, contact geometry or task success**.
The radio was visually identifiable in four of 39 head-camera frames: three
were accepted and one heavily clipped edge view was missed. No accepted false
target was found in the 35 inspected negative frames. This small, highly
correlated sample is not a general detector accuracy estimate.

## Frozen Protocol

- BEHAVIOR revision `b1979916ec1549b10a4e65e630bc6504a9af1b00`, ordinary
  `turning_on_radio` public-test instance 301, separate resets with seeds 0/1/2.
  Seeds do not imply different task layouts or randomized object placements.
- Frozen Behavior-Skill checkpoint/interface, native 23D actions, 32-action
  prefixes, instruction `Move to the radio receiver on the table.`
- Exactly 384 policy actions per reset; 13 captures at sequences 0..384.
  No classical motion, assisted target pixel, GPT call or memory intervention.
- `IDEA-Research/grounding-dino-tiny`, revision
  `a2bb814dd30d776dcf7e30523b00659f4f141c71`, Apache-2.0 metadata, local
  safetensors only. Prompt: `a radio. a television. a robot gripper.`
  Box threshold 0.4 and text threshold 0.3, unchanged during all three runs.
- RGB-box-initialized GrabCut, three iterations, seeded RNG, one-pixel erosion.
  At least 16 support pixels and 80% valid measured depth, range 0..10 m.
- Robot-only FK uses hashed R1Pro geometry/config and measured proprioception;
  candidate surfaces within 0.18 m of either EEF are rejected as identity
  ambiguous. This is not calibrated full-body segmentation or contact perception
  and can reject real objects near the hand.
- All results explicitly retain `motion_authorized=false` and
  `semantic_accuracy_qualified=false`. Geometry describes a visible partial
  surface, not the complete object center, power button or contact normal.

## Results

| Reset seed | Frames | Visible radio | Accepted true | Accepted false | Missed visible | Ambiguity rejects |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 13 | 1 | 0 | 0 | 1 | 4 |
| 1 | 13 | 1 | 1 | 0 | 0 | 5 |
| 2 | 13 | 2 | 2 | 0 | 0 | 1 |
| Total | 39 | 4 | 3 | 0 | 1 | 10 |

Positive frames: seed 0 sequence 384 (missed, mostly off-screen); seed 1
sequence 384; seed 2 sequences 352 and 384. All 39 head views were visually
inspected. Labels are RGB-based assessment, not simulator truth or a blinded
human annotation study. The seed-0 edge case was also independently reviewed,
but that reviewer had seen detector outputs; no blinding claim is made.

Detector/segmentation/FK wall latency was median **0.134 s**, p95 **0.683 s**,
maximum **0.759 s**. Capture-to-result delivery, including evidence serialization
and RPC, was median **0.614 s**, p95 **1.171 s**, maximum **1.183 s**. Simulation
is synchronous/paused while this work runs; these are not real-time control
latencies or freshness qualification for physical hardware.

All 39 results match their capture stamp, RGB/depth IDs and same-boundary
calibration. Derived masks have verified hashes and original-source bindings.
Delivery occurs before the next capture; the synchronous call site places it
before the next policy chunk. No later image is used to select an earlier target.
Private run: `grounding-radio-online-20260922-r1`; audit and RGB contact sheets:
`grounding-radio-online-audit-20260922`. Licensed sensor data stays private.

## Development And Review Boundaries

The preceding [retained-frame development audit](ACTION_COMPILER_REPLAY_20260922.md#development-only-grounding-audit)
contained 26 frames, only one positive. The contrast-class prompt removed TV
false positives; near-EEF rejection removed remaining gripper confusions in
that development set. The new 39-frame result is separate and includes a miss.

After the frozen run, code review tightened four implementation checks:
separate target/distractor caps with omitted counts; cryptographic image-identity
verification before inference; expected snapshot hashes for weights and all
processor/tokenizer files; and online service configuration enforcement.
Upstream pinned HF metadata matches the actual local weight SHA-256 and all
small-file Git blob hashes. Original outputs are retained unchanged; the new
checks do not retrospectively turn a miss into a success. Later runs record
the grounding implementation hash as well.

## Extended Acquisition

The separately labeled `grounding-radio-extended-20260922-r1` completed 768
policy actions from another ordinary seed-1 reset, with 25 synchronous captures.
It uses the post-review provenance checks and separate class caps described
above; it is **not another A-short/B-short comparison**. Instructions, policy,
detector weights, prompt and numerical thresholds remained unchanged.
The original extended receipt's redundant `policy_action_ceiling` retained the
short-run default 384; `policy_action_budget=768`, action counts and all 25
captures record its actual declared exposure. The runner now makes the redundant
field agree. The historical receipt is preserved rather than rewritten.

The radio was identifiable in all 13 views from sequence 384 through 768.
Twelve were detected; sequence 480 was missed despite the radio being visible
near the image center. All 12 earlier views were negative and no false target
was accepted. Seven near-EEF ambiguity rejections occurred on negative views.
Thus the longer trace demonstrates acquisition/reacquisition across multiple
viewpoints, but also a non-edge miss and no reliable continuous tracking claim.
Visual assessment used all 25 source head images, not simulator object state.

Detector/geometry latency was median 0.610 s, p95 0.683 s, maximum 0.762 s;
capture-to-delivery was median 1.103 s, p95 1.197 s, maximum 1.237 s.
All 25 RGB-D pairs and derived masks pass source-identity/hash checks. The local
copy matches the remote run by checksum. No GPT/API calls or classical actions.

The measured horizontal base-to-visible-surface median decreased from about
1.74 m at sequence 384 to 1.14 m at 768. These are instantaneous robot-frame
partial-surface estimates; changing viewpoint changes the visible surface.
They are not a measured 0.60 m base displacement or a localization-error bound.
RGB shows policy-controlled approach toward the table, not manipulation success.

Independent mask review and the [compiler replay addendum](ACTION_COMPILER_REPLAY_20260922.md#fresh-extended-grounding-geometry)
retain all 12 masks without selecting a favorable subpatch. None passes the
compiler's whole-mask planar fit. The object detector is therefore not yet a
button/contact-region detector, even when its semantic identity is correct.

## Remaining Gate

The longer acquisition run leaves the 384-action short protocol unchanged.
No detector threshold is tuned to the missed edge frame. Target identity,
partial-mask contamination, multi-view consistency and legal moving-localization
error still need assessment. Stopping and swept-clearance qualification remain
independent blockers before target-directed classical transit.
