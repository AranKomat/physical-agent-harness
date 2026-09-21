# Action Compiler Retained-Evidence Replay

Implemented and run on 2026-09-22, independently of online target grounding.
This is stage 2's read-only retained-evidence workstream, not stage 9 candidate
quality qualification and not authorization to connect the compiler to motion.
Implementation and adversarial test work were performed in parallel.

## Inputs And Boundaries

- Private `hybrid-calibrated-approach-20260921-r1/A` and `r2/A`, specifically
  the 13 `captures` rows in each `hybrid_short.json`, not `policy_chunks`.
- All three retained cameras per capture: 26 captures, 78 calibrated RGB-D
  pairs. Capture rows, missing annotations, explicitly empty target lists,
  invalid evidence and rejected surfaces remain represented in the denominator.
- RGB content hashes, evidence identity hashes, modality, stamp, observation
  time, intrinsics provenance, calibration evidence IDs and dimensions are
  checked before deprojection. Annotation boxes require an inspected RGB
  assertion and exact evidence binding; they cannot introduce button labels.
- No native runner changes, native motion, GPT/API calls, model inference,
  checkpoint downloads, privileged task state or simulator segmentation.
  Online detector masks were not consumed, including the unqualified masks
  reported by the parallel grounding workstream.
- Raw images, masks/annotations, point coordinates, catalogs, programs and
  reviews stay in the private lab. This document contains aggregate results.

## Geometry And Qualification

The retained calibration contains intrinsics but null extrinsics for all 78
camera records. Geometry is therefore expressed in an independent optical
camera frame for each capture. The identity transform is camera-to-itself,
not an invented camera-to-base/world pose. There is no cross-frame fusion,
robot-frame target, inferred free space or complete-object extent.

Depth follows the retained ingress contract: `BehaviorObservationFilter.convert`
preserves native `depth_linear`, and the retained OmniGibson `VisionSensor`
maps that modality to `distance_to_image_plane`. Replay declares optical-Z
meters explicitly; this is not an independent metric sensor calibration.
Recorded `observed_at` is monotonic, never refreshed to look current. The
compiler Basis requires `sim_time`; zero is an explicitly disclosed unavailable
time sentinel, not a recovered simulation timestamp.

Unlabeled full-image depth support is reported separately from object geometry.
The full-image support mask is not a semantic object mask. Each camera cloud
is deterministically capped at 4,096 points, so its bounds are sampled observed
bounds, not complete scene bounds. Invalid/nonpositive/depth-over-10m samples
are excluded. No sampled support is treated as free-space certification.

The actual compiler requires a typed gripper even for passive INSPECT. Replay
uses an explicitly named **UNQUALIFIED contract-probe placeholder**, with
synthetic joint/TCP values that are not an R1Pro profile. Its catalogs are
separate from the empty real-candidate catalog. `ReviewEngine(checks={})`
leaves every required check UNKNOWN; no all-true feasibility callbacks exist.
No executor, selection schema or native adapter is invoked.

Robot-only assets under private `runs/released_policy_audit/kinematics` were
inspected. URDF/USD/configuration files and nominal EEF/gripper mappings are
available, but do not establish a calibrated grasp-to-TCP transform, actual
gripper qualification, retained camera extrinsics, or collision/IK review.
`live-controller-audit-002.json` records zero actions and
`policy_mapping_qualified: false`. Nominal EEF visualization offsets were not
recast as grasp calibration. GraspGenX was not loaded or tested without the
required qualified actual-gripper configuration.

## Measured Results

All 78 retained RGB views were inspected in private contact sheets; the one
positive radio view was also inspected at original resolution. Empty target
annotations mean no confidently identified target in these views, not proof
that the task's object does not exist elsewhere.

| Measurement | r1/A | r2/A | Total |
| --- | ---: | ---: | ---: |
| Capture denominator / processed | 13 / 13 | 13 / 13 | 26 / 26 |
| Valid calibrated camera pairs | 39 | 39 | 78 |
| Explicitly empty target captures | 13 | 12 | 25 |
| Captures with an annotated radio body patch | 0 | 1 | 1 |
| Annotation-supported depth points | 0 | 418 | 418 |
| Accepted planar contact surfaces | 0 | 0 | 0 |
| Compiled INSPECT contract probes | 39 | 39 | 78 |
| Compiled metric contract probes | 0 | 0 | 0 |
| Eligible actions / real-qualified candidates | 0 / 0 | 0 / 0 | 0 / 0 |

The single positive is **r2 capture 12, sequence 384, head camera**. It is a
conservative visible red radio-body rectangle, not whole-object segmentation,
a button, or a demonstrated safe contact region. Its 418 masked depth samples
are valid, but `fit_surface` rejects the patch at the unchanged default
3 mm p95 residual threshold. The threshold was not relaxed and another patch
was not searched for to force an accepted candidate. Consequently there is no
surface-derived STAGE probe in this retained replay. Synthetic tests separately
exercise a planar STAGE contract probe and verify that it remains blocked.

All 78 INSPECT probes are blocked on `sensor_lineage` and `passive_capture`:
offline file validation is not a qualified native review callback. PRESS is
withheld without grounded contact semantics/tolerance; GRASP without qualified
actual gripper/TCP and up direction; NAVIGATE without extrinsics/localization
and known free space. This result measures the missing prerequisites rather
than disguising placeholders as real grasp/contact qualification.

Running both inputs without annotations also preserves 13 unannotated captures
per run and produces no object geometry. Byte-for-byte input inventories cover
all 160 files in the two source directories, including their manifests and
videos; none changed during validation. Annotated reruns exactly equal the
initial reports. Raw depth has finite positive support in all 78 arrays.

## Validation And Reproduction

Validation logs and code/input hashes are retained in private
`runs/compiler_replay_20260922/compiler_replay_validation.json` and the
adjacent `compiler_replay_*tests.log`, `compiler_replay_full_suite.log` and
`compiler_replay_owned_ruff.log`. Checks include the complete compiler suite,
the new adversarial replay tests, the full repository suite, and owned-file
Ruff. Concurrent work in other files is not part of this change.

Final measured validation: **13 replay tests passed; 164 combined compiler and
replay tests passed; 812 repository tests passed**. Owned-file and repository-wide
Ruff passed, as did `git diff --check`. The full-suite count includes concurrent
grounding tests present in the shared checkout, not additional replay coverage.

From the harness checkout, an individual replay is:

```sh
.venv/bin/python -m experiments.behavior.compiler_replay \
  --run-dir ../internal/physical-ai-lab/runs/hybrid-calibrated-approach-20260921-r2/A \
  --annotations ../internal/physical-ai-lab/runs/compiler_replay_20260922/compiler_replay_annotations_r2.json \
  --output ../internal/physical-ai-lab/runs/compiler_replay_20260922/compiler_replay_r2_repeat.json
```

The CLI refuses outputs inside its source run and refuses to overwrite an
existing report. Omitting `--annotations` is an explicit unannotated baseline.
The private `scripts/compiler_replay_validate.py` reruns both inputs with and
without annotations, checks determinism/source integrity, and runs validation.

## Owned Paths

Public checkout, new files only:

- `experiments/behavior/compiler_replay.py`
- `experiments/behavior/tests/test_compiler_replay.py`
- `docs/ACTION_COMPILER_REPLAY_20260922.md`

Private lab, new files only:

- `scripts/compiler_replay_inspect.py`
- `scripts/compiler_replay_annotations.py`
- `scripts/compiler_replay_validate.py`
- `runs/compiler_replay_20260922/compiler_replay*`: inspection sheets/log,
  evidence-bound annotation JSON, r1/r2 replay reports and validation artifacts.

Next prerequisites remain autonomous object grounding,
qualified gripper/TCP and frame/up calibration, grounded contact semantics,
native feasibility reviews and execution monitors. Positive manipulation
candidate quality and task success are not established by this replay.

## Development-Only Grounding Audit

Independent comparison against the preexisting head-view inspection labels:
26 retained frames, one positive and 25 negative, matched by RGB evidence ID
and verified against capture stamp, depth ID and source run. No new image
review or detector/threshold changes. These frames were used for development;
**this is not holdout evaluation** and excludes fresh online shadow runs.

| Grounding variant | Accepted targets | TP | FP | FN | Near-hand ambiguous rejections |
| --- | ---: | ---: | ---: | ---: | ---: |
| r1: radio-only prompt | 17 | 1 | 16 | 0 | 0 |
| r2: contrasting classes | 12 | 1 | 11 | 0 | 0 |
| r3: contrasting classes + near-EEF filter | 1 | 1 | 0 | 0 | 11 |

Only non-rejected target candidates count as accepted; distractors do not.
All 11 r3 ambiguity rejections are on negative-labeled frames and are reported
separately, not counted as accepted false positives or certified robot masks.
The r2/r3 target boxes and derived-mask hashes are identical before filtering.
The sole accepted positive in all variants corresponds to the previously
annotated r2 sequence-384 radio body. This audit does not qualify mask IoU,
base-frame/FK accuracy, button identity, motion, or generalization. Per-frame
counts and input hashes are private in
`runs/compiler_replay_20260922/compiler_replay_grounding_audit.json`.

## Fresh Extended Grounding Geometry

After the separate 768-action online acquisition, the actual compiler geometry
functions were run on all 12 accepted detector masks. All 25 capture boundaries
remain in the denominator, including the 13 without an accepted candidate.
No manual patch substitution, alternate-mask search or threshold tuning occurred.

- 12 RGB-derived masks visually inspected; 29,667 valid measured depth points.
- **0/12 planar surfaces accepted; 12/12 rejected** at the unchanged 3 mm p95
  residual and 2 mm minimum-span defaults.
- Diagnostic p95 residuals range from **18.60 to 103.66 mm**. These residuals
  describe the original whole-visible-body masks, not localized contact patches.
- Radio-body identity is supported by RGB, but the masks are incomplete and
  upper-handle/background purity is uncertain. A nonplanar whole-object mask is
  not proof that the radio lacks a usable local contact surface.
- No button/contact semantics, qualified grasp, motion candidate or native
  action follows. All 170 files in the source run remained unchanged.

Private reproduction script: `scripts/compiler_replay_grounding_extended.py`.
Results and visual-review notes: `compiler_replay_extended_geometry.json` and
`compiler_replay_extended_review.json` in the existing compiler replay directory.
This connects actual online detections to offline geometry rejection; it does
not replace the required part-level grounding or demonstrate compiler execution.
