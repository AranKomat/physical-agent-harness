# Retained Arm-Path Depth Support

## Scope

CPU-only visibility diagnostic for the 28 frozen single-joint paths. The retained
stationary-SAM r2 capture exactly matches the path preparation's observation
stamp, timestamp and all 22 measured joint positions. Depth files are
content-addressed and hash-verified; intrinsics are bound to that same boundary;
camera mounts are checked against the pinned robot asset. Camera poses are
derived from own-robot kinematics, not simulator global poses.

At fractions 0.25, 0.5, 0.75 and 1.0 of each path, sample the moving authored
convex-hull vertices. Report all samples and, separately, those outside the
starting robot hull union. Removing starting-body samples is only a diagnostic
selection, not a free-space assumption. Three unresolved wheel spheres remain
excluded. These are neither uniform surface samples nor swept-volume coverage.

Reuse the existing three-camera depth-support classifier: a projected sample
needs a valid 3x3 depth neighborhood entirely more than 20 mm behind the sample.
This is a point-support diagnostic, never a collision certificate.

## Result

For samples outside the starting body, summed across all 28 paths:

| Category | Samples | Fraction of these samples |
| --- | ---: | ---: |
| Outside all three views | 138,149 | 96.44% |
| In view but lacking valid depth | 0 | 0% |
| Valid depth, insufficient beyond-sample support | 2,776 | 1.94% |
| Depth-supported | 2,322 | 1.62% |
| Total | 143,247 | 100% |

The head camera supplies zero supported samples in this set. Left/right wrist
cameras supply 1,164/1,158 respectively. The best individual path is left wrist
joint7 +0.01 rad, with only 2.55% of its selected vertex samples supported.
Changing the 20 mm depth margin cannot fix points outside every view.

No path qualifies for strict external clearance from this capture. The earlier
continuous self-separation result is independent and does not resolve this gap.
No new GPU work, commands, paid inference or privileged scene input was used.
All input hashes remained unchanged.

Private receipt: `runs/arm-depth-support-20260923-r1/receipt.json`.
SHA-256: `8a5bec61282932d4a3b85bbf6e9dc4c6f9b08475a61f0893766549b08a2e1e2f`.
Eight focused tests pass, covering own-body sample classification and mismatched
calibration/evidence rejection. Private suite after this diagnostic: 925 passed,
one existing skip; Ruff clean.

## Stop-State Caveat And Next Action

The retained capture is a stationary-world snapshot, not a physically settled
robot. Applying the existing proprioceptive `settled` predicate returns false;
two torso joint speeds are approximately +0.256 and -0.421 rad/s. No commanded
actions and unchanged simulation time do not prove measured zero velocity.
This does not invalidate frozen geometry analysis, but it prevents using that
analysis as a stopped-start execution qualification.

The user subsequently approved one explicitly labeled simulator-only wrist probe
of at most 0.01 rad out/back and 60 total control actions, contingent on actuator
and stop preflight. Unknown external clearance remains explicit and strict
benchmark gates remain unchanged. That approval is not a general motion budget;
the separate native probe receipt must establish whether preflight and execution
actually passed. Better sensor coverage is still required for strict clearance.
