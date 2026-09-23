# GraspGenX Provisioning And Model Load

User explicitly approved isolated provisioning and bounded proposal-only tests
under the NVIDIA Open Model License. No motion or paid model calls authorized by
this scope. Existing simulator/SAM environments and unrelated workloads unchanged.

## Provisioned

- Source: `NVlabs/GraspGenX`, detached `b9429097728cb1c430dd78b92edf17ba318aad03`.
- Model: `adithyamurali/GraspGenXModel`, revision
  `7c834043c11a11417e31d6d5ea9355801e40a2c1`.
- Dedicated Python 3.11 environment; Torch 2.6.0+cu124, CUDA 12.4.
- Generator `epoch_736.pth`: 1,210,918,342 bytes,
  SHA-256 `8b55f31cdb8340a573b4df27b027c15cff326bd6debcb389bf631d2aaab7ac44`.
- Discriminator `epoch_1056.pth`: 483,889,478 bytes,
  SHA-256 `cbf3f3bdb2e4c03fca8486ed24de0e6a8a859e6bd22bce2f1434a610335abd3e`.
- Both YAML configs also size/hash verified against their published LFS pointers.

Provisioning used low priority, CPU affinity 19-22, capped build/download
concurrency, and no system package changes. Weight download made no automatic
retry. The environment was installed separately, not into the simulator or SAM.

## Load-Only Probe

Ran under a private network namespace (`unshare --net`) with no external network
access, four-core affinity, two numerical threads and a 300-second process alarm.
Both upstream asset-path overrides were explicit; no gripper resolution or model
inference occurred. Rechecked source revision and all four checkpoint file hashes
before import. PyTorch allocator fraction capped at 45% of the 24 GB GPU.

| Measurement | Result |
| --- | ---: |
| Parameters, generator + discriminator | 141,156,167 |
| Model construction/load time after imports | 2.546 s |
| Allocated GPU memory after load / peak | 545.322 MiB |
| Reserved GPU memory after load / peak | 566 MiB |
| Inference calls / robot actions / paid calls | 0 / 0 / 0 |

These are PyTorch allocator figures, not whole-process VRAM or inference peaks.
The process exited successfully and the independent post-exit GPU query returned
0 MiB used. Local copy of receipt: `runs/graspgenx-load-20260923-r1/receipt.json`;
verified download manifest copied alongside it.

Imports warned that optional PointNet++ extensions were unavailable and that an
offline Transformers cache could not update. Loading the actual released
`ptv3vanilla` models nevertheless succeeded; this does not qualify inference.

## Next Test

Both active configs select `sweep_volume_v2`. Upstream explicitly supports a
sweep-volume-only gripper-info path without optional point-cloud/TSDF/VAE caches.
Use the inspected simulated-hand candidate for bounded proposal-only inference,
not a substituted real Galaxea gripper. Measure inference peak memory and latency
before testing simulator/SAM co-residency. The earlier simulator+SAM peak was
16,516 MiB; adding the load-only number is not a demonstrated co-residency result.

Phase 9 remains incomplete: no native grasp execution, manipulation success, or
contact/clearance qualification follows from model loading.

## First Retained-Cloud Proposal Test

One deterministic seed-0 attempt, 32 generated candidates, top eight returned,
20 released diffusion steps, threshold -1, one try, no outlier removal or TensorRT.
Same network isolation, CPU affinity and allocator cap as the loading probe.
Conditioning uses the upstream `make_sweep_volume_gripper_info` path with the
reviewed simulated-hand open/half-open boxes and explicit 60 mm fingertip depth.
Both active backbones were checked to be `sweep_volume_v2`; dummy optional meshes
and caches from that upstream helper were not used for collision or visualization.

Input is the fixed largest metric-depth component at observation sequence 416
of the retained live-fusion trace: 1,925 points in source-head optical coordinates.
The source SAM mask, RGB identity, depth packet and trace hash were checked.
The initial local preparation pointed at the wrong trace directory; its hash
check rejected it before output/inference. The matching trace was located without
changing the expected source digest. No model result influenced patch selection.

| Measurement | Result |
| --- | ---: |
| Inference attempts | 1 |
| Returned proposals | 8 |
| Synchronized inference time | 0.6691 s |
| Peak allocated GPU memory | 591.601 MiB |
| Peak reserved GPU memory | 624 MiB |
| Robot actions / paid calls | 0 / 0 |

Source cloud SHA-256:
`af23641fa9d55eb5b56aefc0aaf034dfc75b3e269c3891fe6b54f9578dc1fb1d`.
Proposal archive SHA-256:
`8ce92e66e1019214f0325bea982c86b7ad20ad90215418ecb0974bd4b4c626e1`.
Private artifacts: `runs/graspgenx-cloud-20260923-r1` and
`runs/graspgenx-proposal-20260923-r1`. Worker exited successfully.

These memory figures include model allocations but not whole-process CUDA
overhead, simulator/SAM co-residency or cuRobo. This is one un-warmed inference,
not a latency distribution. Output validation established finite bounded arrays;
full pose/geometry inspection, collision, IK, contact and execution remain open.
Partial observed geometry and unqualified object identity cannot authorize motion.
The scores are uncalibrated rankings, not success probabilities.

## Proposal Geometry Inspection

Inspected all eight retained outputs without resampling or selecting a favorable
proposal. Verified input/config/proposal hashes and the 36-mesh hand package.
Rigid-transform checks pass for all eight (orthogonality, positive determinant,
homogeneous row). Transformed the observed target points into each grasp frame
and checked all 32 separate open-hand convex colliders, including the wrist-camera
housing. Rendered and inspected all eight in a single comparison image.

**None of the eight inner grasp boxes contains an observed target point.** The
nearest observed-point-to-box distances are 52.7, 25.3, 56.1, 29.8, 50.6, 37.4,
31.8 and 39.7 mm in score order. Scores range from 0.858 to 0.952; high scores
do not resolve this lack of observed target engagement. No observed points fall
inside the open hand either, but that is not positive clearance evidence.

This does not prove all candidates are physically impossible: the input is a
partial surface, not a complete object, and the hand annotation/frame convention
still needs qualification. It does rule out treating the successful inference
receipt as a demonstrated useful grasp. Do not dispatch these proposals.

The inverse-transform implementation passes a nontrivial rotation/translation
roundtrip test and rejects reflections/nonrigid matrices. Four targeted tests
and Ruff pass. Upstream raw sweep-volume construction was also checked against
its public classmethod; it uses the same helper, with no extra pose offset there.
Further model/config/geometry diagnosis is required before any motion decision.

Private artifacts: `runs/graspgenx-proposal-inspection-20260923-r1` (initial
containment/render) and `...-r2` (same outputs with nearest-box distance added).
No additional inference, paid calls, GPU work or robot commands occurred.

## Instrumented Loading/Conditioning Audit

Predeclared one additional seed-0 inference with the same cloud, hand parameters,
32 candidates and top-eight limit to test loading/wiring rather than resample for
a favorable grasp. Before inference, compared each named learned parameter with
the released checkpoint using exact tensor equality: 332 generator tensors and
291 discriminator tensors all match. Forward pre-hooks on both gripper encoders
observed exactly one invocation each with the intended 12 float32 values:
`[.096,.010,.020,0,0,.060,.046,.010,.020,0,0,.060]`.

The audit returned eight proposals in 0.5377 s, with 591.601 MiB peak allocated
and 624 MiB peak reserved. Relative to the original output, maximum absolute
matrix-element difference is 8.72e-7 and score difference 3.58e-7. This is small
numerical variation, not a bitwise determinism claim or correction of the
centimeter-scale observed-surface gap. No candidate was selected or executed.

Source inspection also confirms the active generator and discriminator directly
encode `sweep_volume_open_and_mid`; the sampler restores the cloud centroid once.
The checks rule out the audited parameter-loading and encoder-input mismatch
hypotheses, not all possible model/frame/annotation issues. Next compare geometry
conditioning and partial-view support under a declared controlled test, rather
than repeatedly sampling seeds or treating discriminator confidence as success.

Private audit: `runs/graspgenx-proposal-audit-20260923-r1`, copied locally.
The worker exited and GPU use returned to 0 MiB. No robot commands or paid calls.

## Full-Mask Versus Largest-Patch Contrast

Predeclared one additional inference with all 2,376 valid depth points from the
same sequence-416 SAM mask, instead of its 1,925-point largest depth component.
Hand conditioning, seed 0, model weights, 32 candidates/top-eight budget and
no-outlier-removal setting are unchanged. No reconstructed/hidden points added.

Eight proposals returned in 0.5505 s; peak allocated memory 598.670 MiB and
reserved memory 652 MiB. Inspection of every proposal finds 4/8 inner boxes
containing observed points, versus 0/8 in the largest-patch condition. Counts in
score order: **4, 7, 0, 0, 0, 4, 2, 0**. All contained points belong to other
depth components, not the original largest component (membership checked by
nearest-point distance below 1e-7 m). No observed points lie inside the open hand.

This is weak support, not useful-grasp qualification: the smaller components may
include legitimate target parts or background contamination. The contrast shows
preprocessing affects proposals but does not show that dropping partitioning is
an improvement. No production perception setting was changed, no score threshold
was tuned and no proposal was executed. Further work must establish which
surface fragments are actually part of the grasp target.

Private inputs/results: `runs/graspgenx-full-mask-cloud-20260923-r1`,
`runs/graspgenx-full-mask-proposal-20260923-r1`, and
`runs/graspgenx-full-mask-inspection-20260923-r1`. Results copied locally; worker
exited and independent GPU query returned 0 MiB. Full private suite: 1,126 passed,
one existing skip. Changed scripts pass Ruff. No paid calls or robot motion.

## Source-Pixel Support Review

Back-projected every inner-box support point from the full-mask proposals onto
the frozen RGB image. Pixel roundtrip error is below 0.001 pixels and depth
agreement within 1e-6 m. Visual review places the sparse support on the red carry
handle, rather than obvious background. These points are 40.6-46.7 mm from the
nearest largest-component point. Thus largest-component filtering may discard
a useful thin target part; zero support in that condition is not enough to
declare the model incapable of proposing a grasp.

This is a visual interpretation, not qualified semantic membership, contact,
force closure, or executable geometry. No production filter was changed.
Private review: `runs/graspgenx-support-pixels-20260923-r1/review.png` and its
receipt. No new model calls or robot actions.

## Full Observed Scene Check

Predeclared a check of all eight existing full-mask proposals against all finite
positive depth pixels in their original source image, without resampling grasps
or selecting successful outputs. This extends target-only point containment to
surrounding observed surfaces. All 518,400 pixels are deprojected in the same
optical frame; no simulator geometry, object poses, or completed hidden surfaces
are used. All 32 separate open-hand colliders include the wrist-camera housing.

The initial check finds **14 observed scene points inside proposal #3's
wrist-camera housing**. The target-only check had found zero, demonstrating why
target-only geometry cannot establish scene clearance. The other seven proposals
have zero sampled scene-point intersections; that is still not clearance in
unobserved volume, an approach-path check, or permission to execute.

Private initial result: `runs/graspgenx-scene-inspection-20260923-r1`. A direct
chunked all-point check, without the initial AABB prefilter, is retained separately
as `...-r2`, and reproduces every proposal's intersection counts. Six targeted
tests and Ruff pass. The checker has tests for collider-union counting, chunk tails,
boundary points, empty input, and rigid transforms. No robot motion, GPU work,
new inference, or paid calls were needed. Gripper/TCP calibration, IK, whole-arm
collision, approach/retract and native stopping qualification remain open.

## Simulator / SAM / GraspGen-X Co-Residency

One bounded zero-action capacity test on the existing RTX 4090 (24,564 MiB,
driver 580.178.04). Native radio development instance 301, seed 0. Load SAM 3.1,
initialize the simulator, freeze simulation, and obtain three fresh RGB-D
captures. After the first SAM response, run exactly one retained full-mask
GraspGen-X inference with the same pinned hand/cloud/model settings, retaining
its sampler in memory through the following two SAM captures. No VLA policy,
cuRobo planner or paid service is loaded. This is co-residency with serialized
inference, not concurrent model throughput or live grasp execution.

The owner samples whole-device memory approximately every 0.5 s, aborting at
23,552 MiB. Workers have bounded waits, owned process-group cleanup and CPU
affinity 19-22 at niceness 15. No system changes or unrelated process operations.
The native worker verifies unchanged simulation time and all 61 proprioception
values across each capture/response cycle. No controller actions are issued.

Results:

- All three paused capture cycles pass; native startup 141.45 s.
- Sampled aggregate peak **17,456 MiB (17.05 GiB)**, leaving 6,096 MiB below the
  safety ceiling and 7,108 MiB below reported total capacity. Sampling can miss
  brief peaks; this is not a guaranteed worst-case allocation bound.
- GraspGen-X returns eight proposals in **0.5885 s**; allocator peak reserved
  652 MiB, peak allocated 598.670 MiB.
- Subsequent SAM three-prompt capture batches take 0.389 and 0.403 s while
  GraspGen-X remains resident. These single-frame capacity calls are not a video
  tracking latency benchmark; radio detection remains absent in these prompts.
- All owned workers exit successfully. Independent GPU query returns 0 MiB.
- No motion, paid calls, action qualification or task-success claim.

One 4090 is sufficient for this tested configuration; a second GPU is not
justified by GraspGen-X memory alone. Policy/planner additions, longer tracking
history, more objects and overlapping inference remain unmeasured.

Private artifact: `runs/grasp-sam-capacity-20260923-r1`, copied locally.
SHA-256 pins:

| Artifact | SHA-256 |
| --- | --- |
| Owner receipt | `872081a5db415e2c7ee8b49e503533417047a827e6e0b89d5fd097f712dd208b` |
| Native receipt | `74537a78576fd2aeb8e9b68b56cee7baad9fc1daca800e689848611978749864` |
| Capacity coordinator | `a25138f0db4cca130d02b22692c4a9ca9bf60191d0ca4f7f2ab4c334138de6a7` |
| Grasp worker | `8cd667abfac4801958e942109e8aba923d0ad20935dac827146150adf5c9ea5b` |
| SAM capacity worker | `850d266e3be08141151d62c2001470362e4256cabba668e85d13d3f11fa1fe40` |
| Native capacity worker | `fa5427340266fb587c5bbfefacf046e4827494376139fa170b3e410830723031` |

The remote public tree is a deployed copy without Git metadata, not a separately
verified checkout commit. Native source and model checks remain enforced by the
workers. Full local private suite: **1,128 passed, one existing skip**. Changed
scripts pass Ruff.

## Held-Torso Reach Bound

Before attempting GPU IK on the eight original full-mask proposals, derived a
conditional robot-base transform using sequence-416 measured joints, the pinned
URDF camera mount, and the OpenGL-to-optical axis conversion. This source has
no recorded camera extrinsics; the derivation does not upgrade capture timing or
the candidate canonical hand frame to motion-qualified calibration.

For canonical hand poses, use
`T_base_native_gripper = T_base_optical * T_optical_canonical * B`, where `B`
is the reviewed native-to-canonical hand rotation. The endpoint is the native
gripper root, not a guessed fingertip/TCP offset. Hold the torso fixed at the
source posture. The sum of joint-origin translation norms from the first arm
joint to the gripper root is **0.87155 m**. All joints in that chain are fixed or
revolute; the triangle inequality bounds endpoint distance for every arm angle,
even ignoring the tighter actual joint limits. Prismatic chains are rejected.

All eight proposed gripper roots are **1.68576-2.05476 m** from the shoulder,
exceeding that conservative bound by **0.81421-1.18321 m**. Thus none warrants
an IK search from this held-torso posture under the stated frame assumptions.
This does not establish a collision-free base destination, or rule out other
base/torso postures. The excess distance is not a command to translate the base
by that amount.

As an independent source-joint mapping check, FK reproduces recorded left EEF
position within 9.95e-7 m and orientation within 6.07e-7 rad. Two focused tests
pass: opposed link translations cannot cancel the reach bound, and a prismatic
chain is rejected. Ruff passes. All original proposals remain reported; none
was regenerated, executed or substituted. No GPU or paid calls were used.

Private artifacts: `runs/grasp-reach-bound-20260923-r1` and `...-r2` (adds the
source EEF consistency check). This supports returning to Phase 5/6 staging and
fresh close-range observation before native manipulation. It is not a negative
benchmark result for the grasp model, and the original far-view inference remains
a proposal/interface experiment rather than a ready-to-execute grasp test.
