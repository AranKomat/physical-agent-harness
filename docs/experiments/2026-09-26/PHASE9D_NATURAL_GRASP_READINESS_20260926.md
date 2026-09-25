# Phase 9D Natural Grasp Readiness

Date: 2026-09-26

## Scope

This report records proposal-only and exploratory path evidence from one natural
`picking_up_trash` start. It does not report contact, lift, benchmark success, or
strict clearance.

The retained policy approach completed 768/768 Behavior-Skill actions and 48
policy calls across two `move to` and two `pick up from` instructions. It ended
with a soda can visible in the current right-wrist RGB-D view. The native task was
not successful and both grippers remained open.

## Target Evidence

SAM 3.1 text grounding for `soda can` returned no candidates on the frozen head
view. A separately labeled current-image assisted right-wrist box
`[360, 165, 460, 322]` produced one SAM mask in 0.551 seconds. The original mask
cloud had 8,313 valid-depth points, but it mixed the foreground can with deeper
floor/background pixels.

A preregistered depth split retained the nearest supported 5 mm histogram mode:

- source points: 8,313;
- retained foreground points: 2,659;
- cutoff depth: 0.511101 m;
- retained camera-frame bounds: approximately 70 x 77 x 30 mm;
- no new image, model call, robot action, or simulator truth was used.

This is an assisted target-selection diagnostic. Autonomous text grounding
remains open.

## Candidate Comparison

One pinned GraspGen-X inference used the original frozen right-wrist cloud:

- eight proposals in 1.148 seconds;
- 623 generator/discriminator tensors matched the released checkpoints;
- peak reserved VRAM was 728 MiB;
- seven proposals had numerical right-arm IK matches;
- all reachable learned paths penetrated the sensor-derived floor by 8.4-51.1 cm;
- two also created new sampled self-collisions.

No additional learned proposal batch was run.

The first analytic proposal incorrectly used the contaminated cloud median and
placed the palm/camera through the target. After the frozen depth cleanup, the
same deterministic median/PCA/camera-ray construction produced a physically
different candidate:

- all pregrasp, grasp, and 50 mm lift poses matched right-arm IK;
- 430/2,659 visible target points fell inside the declared closing sweep;
- zero target points intersected open-hand collision geometry along the accepted
  staged sequence;
- all three sequential path segments had no new sampled self-collision;
- all three had no non-target observed-point intrusion after the documented
  10 mm start-robot self-filter;
- minimum moving-geometry floor margins were 0.168 m at pregrasp and 0.102 m at
  grasp/lift.

The 10 mm self-filter is exploratory. Sensitivity runs showed that residual
head-camera points tracked authored arm links and that the exclusion count
plateaued from 10 through 30 mm. An obstacle already within 10 mm could still be
filtered, so `scene_clearance_qualified` remains false.

## Right Gripper

A separate simulator-only empty-hand right-gripper calibration passed 35/35
actions:

- controller action index: 22;
- initial mean aperture coordinate: 0.0499990 m;
- closed final mean: 0.000000149 m;
- reopened final mean: 0.0499991 m;
- maximum finger asymmetry: 0.00000170 m;
- maximum held-joint drift: 0.0000142.

This qualifies command/feedback symmetry only. It does not qualify contact,
force closure, payload retention, or release.

## Frozen Evidence

Key private receipt SHA-256 values:

- GraspGen-X receipt:
  `12949d09dad02cb4584530de572947291171a90f1d64b42eff510e7b604881b7`;
- GraspGen-X proposal archive:
  `5c3c6b7670e930ba748dec7d4c2e3de72321fc8e84e57bbe9a6a240e32220bd7`;
- right-gripper calibration receipt:
  `3dfcb376bbc4600cbab4343307b12bb987dfb91244c76d5a0870de32cfed0fef`;
- depth-foreground receipt:
  `a20e33184bb30f996302f7276083ad57a237f0318abcd4fc9d2d0b0fc71e25a5`;
- cleaned analytic candidate receipt:
  `cb86bf2332e550c5741a62b2ec8bcbf8cfa1471c8f8d60e18283068c71cd0e85`;
- staged sequential IK receipt:
  `27e3791bf7bf58fa52cf717950d39ae8087494578323f38a4b753ff12d90df85`;
- final exploratory sequential path receipt:
  `0a98ccd5aef7129441a44b6b0bafef266dad7cfef42b9d14c31092ca3e8cb69f`.

## Remaining Gate

Do not execute retained absolute poses or joints. The next run must reacquire a
fresh causal boundary and repeat target-cloud extraction, analytic candidate
generation, IK, and path screening in the same episode.

The next experiment is one bounded exploratory sequence through the normal
`ActionExecutor` authority:

1. fresh pregrasp and stop;
2. bounded approach;
3. measured right-gripper close;
4. lift only if settled nonzero aperture and current target association support a
   grasp;
5. 50 mm lift and fresh legal RGB-D/proprio verification.

The pass condition is a semantically useful physical effect: at least 30 mm
target rise while the object remains associated with the right gripper. Hidden
simulator object/task state may be recorded only afterward for evaluation.

No paid model calls were used in the work reported here.
