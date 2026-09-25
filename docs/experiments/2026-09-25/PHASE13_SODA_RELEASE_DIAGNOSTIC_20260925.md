# Phase 13 Soda-Can Release Diagnostic

## Result

One preregistered controlled fixture tested whether the release failures observed
with the oversized candle were specific to its geometry. The smaller soda can
completed the fixed grasp, 50 mm lift, closed return, open, and lateral-retreat
sequence. It separated cleanly from the gripper, but fell because the fixture's
release point was unsupported. The experiment therefore failed its placement
criterion while passing the narrower release-mechanics question.

| Measurement | Result |
| --- | ---: |
| Native public-test ID | 301 |
| Soda-can horizontal extent | 75.43 mm |
| Actions | 70/70 |
| Evaluator lift | 50.015 mm |
| Closed return error | 0.822 mm |
| Constraint active after opening | no |
| Object registered in hand after opening | no |
| Finger joint positions after opening | 40.000 / 40.000 mm |
| Lateral gripper retreat | 50.000 mm |
| Object motion during retreat | 101.928 mm |
| Final object-to-grasp-center separation | 588.250 mm |

External clearance remained unknown, `motion_qualified=false`, and no learned
motor, semantic model, or paid call participated in motion.

## Interpretation

This result rules out a general inability of the R1Pro fixture to open and release
objects. Unlike the candle, the soda can did not remain wedged or cupped in the
open gripper. At the `post_release` capture the assisted-grasp constraint was
inactive, the runtime reported no object in hand, and the can was already about
541 mm from the grasp center.

The overall protocol still failed. The fixture returned the gripper to a pose
roughly 612 mm above the world origin without a support surface under the can.
Opening therefore produced a drop rather than a placement, and the can continued
to move during the lateral retreat. This is a support-aware placement problem,
not evidence that longer opening or another retreat direction is needed.

The first attempt is retained as a zero-action setup failure. It supplied the
OmniGibson subdirectory where the runner expected the BEHAVIOR root and failed
before simulator startup. A separately labeled `r2` changed only that source
path; all workload, motion, pass, resource, and stopping parameters remained
frozen.

## Evidence

```text
parent preregistration
0fb07d7cb27a971a05f5d9bf4aeeaf1d7b72a43e839dff9310084ca064fd3d1e

zero-action setup-failure receipt
2bcc626af0f309aa38707bdd19b29df753010f3c76b51f04f5ad7b23798f62b5

setup-correction preregistration
042b5b9a56a90d10c2674e25620e296f211edce08ede98751d27f783d8886d92

completed receipt
3d89c951332871262f6ddbb8d03f2f40bca25252e0bf744f09bf3fe8ff392c84

quarantined evaluator sidecar
c3fb9d535c0c8853b56bc89dc6ab13679b9b9ad018575a2d9feb0e1cdccfc6f0
```

## Next Gate

Do not tune open duration, aperture, or retreat direction on this fixture. The
next meaningful manipulation test must provide a legally observed, physically
supporting placement region and compile a release pose above it. It must verify
both gripper separation and stable object support after retreat. A scripted
fixture can qualify those mechanics, but it cannot be reported as benchmark or
complete-task success.
