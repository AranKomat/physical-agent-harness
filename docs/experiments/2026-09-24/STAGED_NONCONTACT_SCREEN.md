# Staged Non-Contact Endpoint Screen

Phase 7 remains incomplete. This offline experiment asks whether the retained
staged posture admits a small target-directed endpoint without folding the
torso into an extreme configuration. No simulator actions or paid calls were
made. It does not authorize execution.

## Protocol

- Use the final legal staged observation, sequence 1092, and its source-bound
  SAM/depth cloud. Recompute the optical-camera transform from measured joints
  and the pinned authored camera mount, and compare against the cloud receipt.
- For each arm, set an endpoint 10 cm from its measured gripper pose toward the
  median visible target surface, keeping the starting orientation.
- Compare arm-only against torso-plus-arm numerical IK. Limit each active joint
  to within 0.25 rad of its measured position and its URDF limits. Hold the other
  arm and fingers at measured positions.
- Check 21 interpolated postures against all 161 authored convex hulls, using
  the previously inspected native exclusion pairs. The three wheel shapes are
  not covered. Do not substitute legacy sphere overlaps for hull collision.
- Pin robot assets, native exclusion receipt and source trace; hash other
  inputs and verify all input hashes unchanged after the run.

## Results

| Candidate | Position error | Orientation error | Maximum joint change | Sampled hull collisions |
|---|---:|---:|---:|---:|
| Left arm only | 10.39 mm | 0.08815 rad | 0.250 rad | 0 |
| Left torso + arm | 0.00091 mm | 0.000035 rad | 0.1863 rad | 0 |
| Right arm only | 43.08 mm | 0.22942 rad | 0.250 rad | 0 |
| Right torso + arm | 0.00038 mm | 0.000016 rad | 0.1319 rad | 0 |

Both coupled candidates satisfy the numerical 5 mm / 0.02 rad tolerances.
Arm-only searches fail those tolerances within the selected bounds; this is
not proof that no other arm-only solution exists. Tiny numerical IK residuals
are not estimates of native positioning accuracy.

## Interpretation And Next Gate

This supplies two concrete target-directed arm/torso candidates, unlike the
earlier current-pose planner smoke. The next check should use these fixed
candidates for observed-scene collision/coverage and continuous path screening.
Only then consider fresh in-episode execution with tracking and stop checks.

Missing: external clearance, wheel coverage, cooked geometry agreement,
continuous swept-path bounds, dynamic balance, native endpoint/stop accuracy,
and an executed return. The reverse samples describe the same geometric path,
not a qualified return trajectory. No strict phase is completed by this result.

## Private Reproduction

From the private lab root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  scripts/staged_noncontact_screen.py --lab . --output runs/staged-noncontact-new
```

Receipt: `runs/staged-noncontact-20260924-r2/receipt.json`

- Receipt SHA-256: `ef323bee10f8b9556aa8842226540e28975f0cf7beca69ba783bda548dacba45`
- Script SHA-256: `6b0e175565f7d4c4d6bbdd3bc5fe610d7d9d796f6d71703c458633889e34084f`
- Source SHA-256: `aff718fe3398df136d3079b31755d6df33cbfd135912f0c2c20c02240725dc25`

The private receipt retains candidate joint values and every sampled collision
result. Original robot assets remain private under their source licenses.
