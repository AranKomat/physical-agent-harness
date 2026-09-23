# VLX Blind Discovery And SAM 3.1 Box Handoff

## Findings

The detection-to-tracking handoff worked in two bounded retained-frame tests.
SAM maintained one radio mask and the same object ID throughout both sequences,
with approximately 159 ms median subsequent-frame processing. This supports an
occasional-discovery, frequent-tracking design, not running a VLM on every frame.

Blind discovery was substantially weaker than target-conditioned detection.
VLX found major furniture with useful boxes, but missed categories, mislabeled
objects, and often spent its output on cushion subregions or robot parts. It is
not an exhaustive or semantically authoritative inventory.

Distractor checks failed in two important ways: querying camera selected the radio,
and querying television selected wall art. No motion was enabled.

## Scope

No paid API calls, simulation actions, training, or production perception changes.
The earlier unresolved GLM provider hold was left untouched. Local models were
run sequentially on the otherwise idle 24 GB RTX 4090 because VLX alone occupies
about 19 GiB; local audit work proceeded separately. The Vast instance remains running.

The test uses retained legal native images from one room and episode. It is not
a new live trace, calibrated distance sweep, completeness benchmark, or test of
two similar objects crossing. No synthetic distractors or privileged object poses
were supplied to either model.

## Goal-Blind Discovery

Six views: 0, 288, 352, 384, 512, 768. They include different camera orientations,
partial furniture, an edge-clipped target, and larger/smaller apparent object sizes.
Two independent prompts per view, neither mentioning the target category:

```text
Identify up to twelve major noticeable visible objects in this image, covering the left, center, right, foreground and background rather than only the most salient item. Include furniture, fixtures and smaller distinct objects where visible. Do not assume a task or expected object. Use ordinary categories, or unknown if unclear. For each selected instance output <ground>category</ground><objects><objN></objects> using the supplied region index, then a short visible description and clear or uncertain identity. Do not claim completeness or invent hidden objects.
```

```text
Describe the visible contents of this room without assuming a task or expected object. Cover its major noticeable objects across the image, not just one item. Ground each named visible instance using <ground>category</ground><objects><objN></objects> with the supplied region index. Mention up to twelve objects. Mark unclear identities as uncertain; do not guess hidden contents.
```

VLX-Seek-1.5-10B used its native visual region interface with 100 WeDetect proposals,
greedy generation, and a 2048-token ceiling. No previous answers were included.
The installed worker hash and prompts are retained. Five proposal sets were reused
from identical-image prior runs; the sixth was generated anew. Reported combined
latency adds the measured original proposal-helper cost to new VLX inference.
This is a component sum, not a live end-to-end measurement.

A manual category-presence checklist was frozen before the blind outputs. It covers
39 category/view pairs across six views, excluding walls/floors, outdoor objects,
robot parts, and individual small picture frames/books. Obvious synonyms such as
couch/sofa and television set/television are joined. A bookcase label on the wall
shelf is accepted as a coarse shelf category. Window is not equated to door, nor
speaker to radio. This is a generous category-coverage proxy, not instance recall,
spatial completeness, or mAP; false labels are described separately.

| Prompt | Checklist coverage | Median VLX inference | Median including proposals |
| --- | ---: | ---: | ---: |
| Inventory | 25/39 (64%) | 4.75 s | 6.03 s |
| Room description | 21/39 (54%) | 4.73 s | 6.56 s |

| View | Inventory | Room description |
| --- | ---: | ---: |
| 0 | 3/4 | 3/4 |
| 288 | 5/6 | 4/6 |
| 352 | 4/7 | 3/7 |
| 384 | 5/8 | 3/8 |
| 512 | 4/7 | 4/7 |
| 768 | 4/7 | 4/7 |

Inventory latency including proposals ranged 5.40-8.58 s; room description
5.22-7.66 s. VLX loading took 13.27 s separately. Longer generated inventories
explain part of the difference from the earlier approximately 0.7 s radio-selection
inference, which generated only seven tokens. This does not isolate all latency causes.

Qualitative observations:

- Furniture boxes generally align well: sofas, tables, fireplaces, cabinets, lamps.
- Neither blind prompt named the radio in any of its four visible views. Inventory
  nevertheless selected its correct region as a speaker in all three fully visible
  views; this can still be a useful discovery candidate without a confirmed identity.
- Room description called it a projector in the last view and omitted it in others.
- Grippers were labeled gun, glove, control, or headband. Wall decorations and outdoor
  details also attracted questionable labels. These must remain hypotheses.
- The requested uncertainty annotations were largely omitted. Some responses returned
  13-15 region references despite the twelve-object request, often overlapping cushion
  regions. Outputs were retained unchanged, not truncated to make them compliant.
- A coverage miss is not evidence of absence. These outputs cannot populate a world
  model as a complete list of everything present.

## Distractor Checks

Six additional independent native detection queries, using existing proposal sets:

| Check | Result |
| --- | --- |
| Radio in absent view 0 | No match |
| Blue radio in red-radio views 384, 512, 768 | No match, 3/3 |
| Camera in view 384 | Incorrectly selected the radio |
| Television in view 512 | Incorrectly selected wall art |

These are mismatched category/attribute probes, not an identical-instance tracking
stress test. The results show that native selection can be geometrically excellent
while semantically wrong. Matching boxes alone must not authorize movement.

## VLX Box To SAM 3.1

The prior native VLX radio detection supplied the initial pixel box. Its source
image was checked pixel-for-pixel against SAM's first observation. The adapter
converted xyxy pixels into normalized xywh exactly once for SAM's documented box
prompt, with a positive box label. No radio text was sent to SAM.

Subsequent frames were appended individually through the existing `ArrivedFrames`
guard, with official image preprocessing and normal forward propagation. No later
frame was accessible before arrival. There was no external re-detection, corrective
prompt, or manual reseeding. SAM's internal propagation implementation was unchanged.

| Trial | Frames | Stable single ID | Initial SAM step | Median subsequent step |
| --- | ---: | --- | ---: | ---: |
| Clipped seed 352 through 448 | 4 | Yes, ID 0 throughout | 0.681 s | 0.158 s |
| Full seed 384 through 768 | 13 | Yes, ID 0 throughout | 0.199 s | 0.159 s |

The sequences overlap and are not independent episodes. Model loading was 27.32 s,
excluded from step timings. The second seed benefits from a warm predictor. Timings
include adapter preprocessing and GPU synchronization, but exclude simulator capture,
depth fusion, model swapping, and file artifact writing. They do not establish
co-resident simulator/VLX/SAM performance on one GPU.

Manual-reference mask-bounding-box IoU was 0.92-0.93 at the annotated clipped-trial
frames and 0.82-0.90 at the annotated full-trial frames. Intermediate frames were
visually inspected in contact sheets; these are not pixel-perfect segmentation
scores. Masks stayed visibly on the radio. One stable ID alone would not prove
identity correctness; here it is supported by visual inspection and reference boxes.
Zero future-frame reads were observed. Full occlusion, similar-object crossings,
loss/reacquisition, and displacement were not tested.

## Decision

Continue with the two-rate design: occasional proposals and semantic hypotheses,
then box-seeded SAM tracking. Keep broad discovery advisory, retain unknown/nearby
category candidates, and require semantic checking when identity matters. Do not
enable motion from the current detector solely because the tracking test passed.

Before motion, test a genuinely similar-object or target-loss sequence and qualify
semantic acceptance against the demonstrated camera/radio and artwork/TV confusions.
This is a focused qualification gap, not a reason to add another architecture layer.

## Artifacts And Verification

Private artifacts relative to the parent workspace:

- `internal/physical-ai-lab/runs/vlx-blind-coverage-reference-20260923.json`
- `internal/physical-ai-lab/runs/vlx-blind-sweep-20260923-r1/`: requests/prompts,
  native results, coverage audit, and annotated comparison.
- `internal/physical-ai-lab/runs/sam-box-handoff-20260923-r1/`: per-frame masks,
  lineage and access logs, audit, contact sheets, and `track-352.gif` / `track-384.gif`.
- Scripts: `run_vlx_blind_sweep.py`, `analyze_vlx_blind.py`, `run_sam_box_handoff.py`,
  `analyze_sam_box_handoff.py`, and the optional-box extension to `sam31_streaming.py`.

The default text-prompt path remains unchanged. The new box conversion rejects
out-of-range, non-finite, reversed, and zero-area boxes. Twenty-one focused SAM
tests passed; Ruff passed for new/modified scripts. Input and mask hashes were
audited and visual outputs inspected. Full public harness tests were not run.
GPU jobs exited and outputs were copied locally. Nothing was committed or pushed
as part of this experiment turn.
