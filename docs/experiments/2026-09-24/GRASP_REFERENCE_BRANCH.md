# Reference Geometric Grasp Branch

## Question

The eight retained diffusion proposals have no target points in the annotated
inner box. Does the reference geometric branch produce supported alternatives
on the same cloud and unchanged hand annotation, without fitting a translation?

## Reference Review

At pinned GraspGen-X revision `b9429097728cb1c430dd78b92edf17ba318aad03`,
`scripts/demo_object_pc.py` defaults to `graspmoe`: diffusion plus geometric OBB
candidates. Our prior probe used diffusion only. The gripper wizard explicitly
defines +Z approach, +X closing, native-to-canonical `base_rotation`, and
`fingertip = sweep_volume.offset`; those conventions agree with our candidate.
This source review does not physically qualify the annotation or calibration.

The diagnostic reference OBB, in the measured base frame, is approximately
256 x 84 x 148 mm. Its 84 mm dimension is narrower than the 96 mm jaw opening,
so the default automatic width gate does not skip the geometric branch.
The rendered canonical-hand/retained-target overlay is consistent with the
earlier unsupported diffusion poses; a 2D projection is not contact evidence.

## Bounded Branch Experiment

One call to the reference `_run_obb_branch`, unchanged hand/cloud, seed 0:
eight yaw samples, offsets -2 and 0 cm, dense top-and-side faces, 4 cm spacing,
automatic width gate. Proposals are scored by the released discriminator.
The base frame supplies diagnostic up; gravity alignment is not qualified.
Outputs are transformed back to the source optical frame for downstream checks.
No diffusion retry, fitted shift, widened box or support-based ranking is used.

- Generated/scored 272 candidates in 0.429 seconds, excluding model loading.
- 176/272 contain at least one retained target point in the annotated interior.
- All eight highest-scored candidates have such support.
- All 272 candidates and scores are retained; the top eight are a separate archive.
- The frame-bound numerical torso/left-arm IK screen found 8/8 pose matches
  for these top-eight candidates. Independent endpoint rechecking and collision
  screening are still required; some solutions involve large joint excursions.

This resolves the zero-support obstacle for a new candidate set, not the old
diffusion set. It does not establish antipodal contact, collision-free approach,
closure, task success, or a causal full-GraspMoE versus diffusion comparison.
Phase 9 remains partial; no motion is authorized.

## Evidence And Setup Failures

Private artifacts in `internal/physical-ai-lab/runs/`:

- `grasp704-reference-20260924-r2`: reference gate receipt and `overlay.png`.
- `grasp704-obb-20260924-r1`: all proposals, top-eight proposals, input hashes,
  reference source hash, per-candidate support and score, timing and parameters.
- `grasp704-obb-ik-20260924-r3`: numerical IK results for the top-eight archive,
  bound to the measured frame-704 start and source manifest.

Top-eight archive SHA-256:
`1e438d89a0f7117f26c0dc3448cacd19771b8ae057c9900dd41c99bfdab057b5`.

Reference-review r1 failed before output because the exported hand bundle was
missing remotely. The verified 4.6 MB local bundle was restored for r2. Importing
the reference module also triggered its dependency setup hook; subsequent runs
explicitly pointed to existing checkpoint/config directories. No new checkpoint
was used for inference.

IK launch r1 failed because the script was absent remotely; local r2 failed
because the full source trace was absent at the requested local path. Neither
performed IK. Remote r3 uses restored script and verified source inputs.
These are setup failures, not model failures or silently replaced motion trials.

No robot actions or paid calls. Next gate: numerical reachability followed by
independent endpoint/contact-support and scene/self-collision screening on this
new set. Old rejection results must not be relabeled as these new candidates.
