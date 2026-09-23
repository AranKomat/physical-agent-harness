# Expanded Return Observer Survey

Date: 2026-09-24  
Run: `native-interpolated-sweep-20260924-r2-observer-survey-512`  
Scope: CPU-only offline observer search; no simulator, robot actions, paid calls, or motion authority.

## Result

The earlier opposite-wrist search sampled 128 Sobol right-arm configurations.
This follow-up evaluates 512 Sobol configurations against the same retained
pose-bound return-surface sample set and the same authored robot-hull ray
occlusion test. The candidate search is deterministic (`seed=0`) and changes
only its Sobol sample count from `2^7` to `2^9`.

The best candidate is index `384`:

| Candidate | In frustum | Unblocked by authored hulls |
| ---: | ---: | ---: |
| 384 | 6,757 | 6,545 |
| 346 | 4,776 | 863 |
| 71 | 9,742 | 193 |

Candidate 384 is materially better than the previous best candidate, but its
unblocked support is concentrated on distal geometry. It observes zero sampled
points on `left_arm_link1` through `left_arm_link4`; its support is on links 5–7,
the gripper, and the wrist-camera link. Therefore this is not yet evidence that
it can observe or qualify the proximal return corridor.

## Decision

The earlier conclusion “no observer candidate is worth considering” was too
strong for the 128-sample search. Candidate 384 merits a separate offline
endpoint audit covering:

- authored-hull self-collision at the candidate posture;
- joint-limit and reachability validity;
- camera-origin and optical-mesh treatment;
- scene occlusion and actual candidate-view depth;
- whether a candidate path can observe the missing proximal links.

Until those checks pass, candidate 384 must not be used for a native observer
move. This survey does not qualify clearance, stopping, reachability, or arm
return and does not promote Phase 7.

## Provenance

Remote artifact directory:

`/workspace/physical-ai-lab/runs/native-interpolated-sweep-20260924-r2-observer-survey-512/`

| Artifact | SHA-256 |
| --- | --- |
| `receipt.json` | `03a1fde6930780554be1af0126a65a7e694289dfd96a7e3b0ef272f4943b2285` |
| modified observer script (`2^9` samples) | `dbb118a1b9d0679b76b16b31376c9c90128a90a66e47cf6a49ae2e4fb3904e85` |

The retained source sweep and all geometry/depth input hashes are recorded in
the receipt. No GPU memory was allocated during this search.
