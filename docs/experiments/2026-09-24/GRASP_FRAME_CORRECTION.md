# Grasp Feasibility Correction

## Invalidated Evidence

The original `grasp-pose-ik-20260924-r1` runner compared
`camera_from_canonical @ canonical_from_tcp` against `base_from_gripper` FK.
It omitted the measured camera-to-base transform and mixed the TCP and gripper
link endpoints. The 8/8 numerical successes solved the wrong targets.

Consequently the authored and native-convex path screens describe paths to
unrelated endpoints, not feasibility of the eight retained grasps. Their zero
intersection counts must not be used as Phase 9A completion evidence.
No robot motion was performed from these solutions. The subsequent scene-point
job was terminated before completion; it also transformed depth using default
rather than measured joints. It produced no accepted result.

The torso-only screen had a separate reporting error: candidate 6's residual
was +12.8 mm, not -12.8 mm. Its receipt establishes only 1/8 candidates inside
the optimistic radius (candidate 2), not the previously reported 2/8.

## Corrected Experiment

`grasp-pose-ik-20260924-r2` uses the pinned source, URDF, camera mounting and
canonical-hand configuration with:

```text
base_from_gripper_goal = base_from_source_camera
                      @ source_camera_from_canonical_hand
                      @ canonical_hand_from_native_gripper
```

The camera pose is computed once from the source's measured joints and kept
fixed while optimizing the four torso and seven left-arm joints. FK is evaluated
at `left_gripper_link`, not a TCP with a different offset. Other measured joints
are initialized before optimization. Six deterministic starts per target use
at most 500 solver evaluations each. Acceptance remains 5 mm position and
0.02 rad orientation; numerical convergence alone does not count as success.

**Result: 0/8 pose matches.** The selected numerical solutions have position
residuals of 0.0981--0.3396 m and angular residuals of 0.8345--2.0215 rad.
This finite local search is not a proof of global infeasibility. No collision
checks on these failed endpoints can qualify them as grasps.

All eight corrected target transforms agree with the independently computed
earlier reach-screen transforms to at most 2.23e-16 elementwise. This establishes
internal frame consistency, not native camera/TCP calibration.

Corrected receipt SHA-256:
`09b1fb23a130c646d243131faecedafc3564fab3d91619fc3cb324fe36a796a6`.
Private local receipt: `internal/physical-ai-lab/runs/grasp-pose-ik-20260924-r2-receipt.json`
relative to the parent GPU workspace. The remote run remains under the lab's
`runs/grasp-pose-ik-20260924-r2/`. Old receipts remain unmodified.

## Prevention And Next Action

The three downstream private screens now require the declared corrected frame
contract, exact gripper-link endpoint, and successful pose matches before doing
any geometry work. Six rejection checks (r1 and r2 against each screen) passed;
no output directory was created. These guards are not independent certificates
and must not replace source/FK verification.

Do not rerun path screens for this failed proposal set. Phase 9 remains partial.
The next useful experiment requires closer legally observed staging or a
different, demonstrably reachable target, followed by fresh proposal generation.
Do not infer completed manipulation, qualified clearance, or a solved motor
problem from the invalidated runs. Zero actions and zero paid calls in r2.
