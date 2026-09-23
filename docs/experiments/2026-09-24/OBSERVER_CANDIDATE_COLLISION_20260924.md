# Observer Candidate Endpoint Collision Check

Date: 2026-09-24  
Run: `native-interpolated-sweep-20260924-r2-observer-candidate-collision-20260924-r1`  
Scope: CPU-only offline authored-hull endpoint check; no simulator, robot actions, paid calls, or motion authority.

## Result

The top three candidates from the expanded 512-sample right-wrist observer
survey were checked at their proposed endpoint postures against the pinned
authored convex hulls and native collision-exclusion inventory.

| Candidate | Joint limits | Authored-hull collisions | Minimum FCL distance |
| ---: | --- | ---: | ---: |
| 384 | valid | 0 / 11,003 pairs | 23.33 mm |
| 346 | valid | 0 / 11,003 pairs | 23.33 mm |
| 71 | valid | 0 / 11,003 pairs | 23.33 mm |

The identical minimum pair is on the held left arm, so it does not distinguish
the right-wrist candidate postures. This is an endpoint self-collision result,
not a reachability or path result.

## Decision

Candidate 384 remains viable for offline follow-up. It is no longer reasonable
to reject the observer strategy solely because the 128-sample search had weak
coverage. The next checks must evaluate candidate 384's reach/path, camera
optical geometry, actual depth and scene occlusion, and whether a controlled
observer path can expose the missing proximal left-arm links 1--4.

No candidate is authorized for a native observer move. Authored convex hulls do
not prove equivalence to cooked simulator collision shapes, and endpoint
self-separation does not establish swept clearance or stopping.

## Provenance

Remote artifact directory:

`/workspace/physical-ai-lab/runs/native-interpolated-sweep-20260924-r2-observer-candidate-collision-20260924-r1/`

| Artifact | SHA-256 |
| --- | --- |
| `receipt.json` | `4a8902ec828f20c6d2222a934104aa89cf2de39aef954cbc9dec598d69f45e27` |
| expanded observer receipt | `03a1fde6930780554be1af0126a65a7e694289dfd96a7e3b0ef272f4943b2285` |

The check used the pinned asset/URDF/config hashes recorded in the source
receipt and changed no GPU or simulator state.
